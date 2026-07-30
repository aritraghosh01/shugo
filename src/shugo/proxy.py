from __future__ import annotations

import uuid
from contextlib import AsyncExitStack
from typing import Any, Mapping

from mcp import types as mcp_types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError

from shugo import paths, router
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

        # v0.1 PR #4 scope: allow/deny only. Escalate is not yet wired — treat as deny.
        # PR #5 replaces this with the real approval channel.
        if decision.kind == "escalate":
            decision = Decision(
                kind="deny",
                rule_id=decision.rule_id,
                reason="escalate not yet supported in this build (needs PR #5 approvals)",
                controls=decision.controls,
            )

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
) -> None:
    """Run the proxy against a caller-provided upstreams mapping and MCP streams.

    Factored out so integration tests can inject fake upstreams and in-memory streams.
    """
    paths.ensure_layout()
    engine = PolicyEngine(config)
    audit = AuditLog(paths.audit_log(), redact_paths=config.redact)
    server = _build_server(upstreams, engine, audit)
    await server.run(
        read_stream,
        write_stream,
        server.create_initialization_options(NotificationOptions()),
    )


async def serve(config: Config) -> None:
    """Production entry point: spawn stdio upstreams and run the proxy over stdio."""
    paths.ensure_layout()
    async with AsyncExitStack() as stack:
        upstreams: dict[str, UpstreamProtocol] = {}
        for name, spec in config.upstreams.items():
            upstreams[name] = await StdioUpstream.start(name, spec, stack)

        engine = PolicyEngine(config)
        audit = AuditLog(paths.audit_log(), redact_paths=config.redact)
        server = _build_server(upstreams, engine, audit)

        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(NotificationOptions()),
            )
