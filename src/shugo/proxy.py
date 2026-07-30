from __future__ import annotations

import os
import uuid
from contextlib import AsyncExitStack
from datetime import datetime, timezone
from typing import Any, Mapping

from mcp import types as mcp_types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError

from shugo import paths, router
from shugo.approval.channel import ApprovalChannel, PendingApproval
from shugo.approval.file_channel import FileApprovalChannel
from shugo.audit.log import AuditLog
from shugo.errors import ShugoError
from shugo.policy.engine import Decision, EvalContext, PolicyEngine
from shugo.policy.models import Config
from shugo.upstream import StdioUpstream, UpstreamProtocol

_MCP_ERROR_INTERNAL = -32000


def _mcp_error(message: str, code: int = _MCP_ERROR_INTERNAL) -> McpError:
    return McpError(mcp_types.ErrorData(code=code, message=message))


def _build_server(
    upstreams: Mapping[str, UpstreamProtocol],
    engine: PolicyEngine,
    audit: AuditLog,
    approval: ApprovalChannel | None = None,
) -> Server:
    server = Server("shugo")

    @server.list_tools()
    async def _list() -> list[mcp_types.Tool]:
        merged: list[mcp_types.Tool] = []
        for name, up in upstreams.items():
            for tool in await up.list_tools():
                renamed = tool.model_copy(update={"name": router.namespace(name, tool.name)})
                merged.append(renamed)
        return merged

    @server.call_tool()
    async def _call(qualified: str, arguments: dict[str, Any]) -> list[mcp_types.ContentBlock]:
        if paths.halt_sentinel().exists():
            raise _mcp_error("SHUGO halted — all calls denied until unhalt")

        try:
            server_name, tool_name = router.unpack(qualified)
        except ShugoError as e:
            raise _mcp_error(str(e))

        if server_name not in upstreams:
            raise _mcp_error(f"unknown upstream: {server_name}")

        req_id = uuid.uuid4().hex
        decision = engine.evaluate(EvalContext(server=server_name, tool=tool_name, args=arguments))

        if decision.kind == "escalate":
            if approval is None:
                decision = Decision(
                    kind="deny",
                    rule_id=decision.rule_id,
                    reason="escalate rule matched but no approval channel is configured",
                    controls=decision.controls,
                )
            else:
                assert decision.approval is not None
                pending = PendingApproval(
                    id=req_id,
                    ts=datetime.now(timezone.utc).isoformat(timespec="microseconds"),
                    server=server_name,
                    tool=tool_name,
                    args=dict(arguments),
                    rule_id=decision.rule_id,
                    reason=decision.reason,
                    timeout_s=decision.approval.timeout_seconds,
                    pid=os.getpid(),
                    controls=decision.controls,
                )
                verdict = await approval.request(pending)
                if verdict.kind == "timeout":
                    on_timeout = decision.approval.on_timeout
                    decision = Decision(
                        kind=on_timeout,
                        rule_id=decision.rule_id,
                        reason=f"approval timed out after {decision.approval.timeout_seconds}s "
                               f"(on_timeout={on_timeout})",
                        controls=decision.controls,
                        approver=None,
                    )
                else:
                    decision = decision.with_verdict(verdict.kind, approver=verdict.approver)

        entry = audit.build(
            request_id=req_id,
            server=server_name,
            tool=tool_name,
            args=arguments,
            decision=decision.kind,
            matched_rule_id=decision.rule_id,
            reason=decision.reason,
            controls=decision.controls,
            approver=decision.approver,
        )
        audit.append(entry)

        if decision.kind == "deny":
            raise _mcp_error(decision.reason or "denied by policy")

        try:
            result = await upstreams[server_name].call_tool(tool_name, arguments)
        except Exception as e:
            raise _mcp_error(f"upstream {server_name} failed: {e}")

        return list(result.content)

    return server


async def serve_with_upstreams(
    config: Config,
    upstreams: Mapping[str, UpstreamProtocol],
    read_stream,
    write_stream,
    approval: ApprovalChannel | None = None,
) -> None:
    """Run the proxy against a caller-provided upstreams mapping and MCP streams.

    Factored out so integration tests can inject fake upstreams and in-memory streams.
    """
    paths.ensure_layout()
    engine = PolicyEngine(config)
    audit = AuditLog(paths.audit_log(), redact_paths=config.redact)
    server = _build_server(upstreams, engine, audit, approval=approval)
    await server.run(
        read_stream,
        write_stream,
        server.create_initialization_options(NotificationOptions()),
    )


async def serve(
    config: Config,
    approvals: str = "file",
    approvals_port: int = 6247,
) -> None:
    """Production entry point: spawn stdio upstreams and run the proxy over stdio.

    approvals: 'file' (default), 'http', or 'both'.
    approvals_port: port for the HTTP approval UI (bound to 127.0.0.1).
    """
    import asyncio

    if approvals not in ("file", "http", "both"):
        raise ShugoError(f"approvals must be file|http|both, got {approvals!r}")

    paths.ensure_layout()
    async with AsyncExitStack() as stack:
        upstreams: dict[str, UpstreamProtocol] = {}
        for name, spec in config.upstreams.items():
            upstreams[name] = await StdioUpstream.start(name, spec, stack)

        engine = PolicyEngine(config)
        audit = AuditLog(paths.audit_log(), redact_paths=config.redact)
        approval = FileApprovalChannel()  # both channels share the file-drop backend
        server = _build_server(upstreams, engine, audit, approval=approval)

        http_task: asyncio.Task | None = None
        if approvals in ("http", "both"):
            from shugo.approval.http_ui import run_http_ui

            http_task = asyncio.create_task(
                run_http_ui(paths.shugo_home(), port=approvals_port),
                name="shugo-http-approvals",
            )

        try:
            async with stdio_server() as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options(NotificationOptions()),
                )
        finally:
            if http_task is not None:
                http_task.cancel()
                try:
                    await http_task
                except (asyncio.CancelledError, Exception):
                    pass
