from __future__ import annotations

import asyncio

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage

from shugo.approval.file_channel import FileApprovalChannel, apply_verdict, list_pending
from shugo.policy.models import Config
from shugo.proxy import serve_with_upstreams

from .conftest import FakeUpstream


def _cfg_escalate(on_timeout: str = "deny", timeout_s: int = 5):
    return Config.model_validate(
        {
            "version": "0.1",
            "defaults": {"decision": "deny", "on_error": "deny"},
            "upstreams": {"gh": {"command": "x"}},
            "rules": [
                {
                    "id": "write-needs-approval",
                    "match": {"tool": "create_*"},
                    "decision": "escalate",
                    "approval": {"channel": "cli", "timeout_seconds": timeout_s, "on_timeout": on_timeout},
                }
            ],
        }
    )


async def _drive(cfg, upstreams, driver, home, wait_and_approve=None, wait_and_deny=None):
    approval = FileApprovalChannel(home=home)

    client_to_proxy_send, client_to_proxy_recv = anyio.create_memory_object_stream[SessionMessage | Exception](32)
    proxy_to_client_send, proxy_to_client_recv = anyio.create_memory_object_stream[SessionMessage](32)

    async with anyio.create_task_group() as tg:
        tg.start_soon(
            serve_with_upstreams,
            cfg,
            upstreams,
            client_to_proxy_recv,
            proxy_to_client_send,
            approval,
        )

        async def sidecar_approver():
            await asyncio.sleep(0.3)
            pending = list_pending(home)
            if not pending:
                await asyncio.sleep(0.5)
                pending = list_pending(home)
            if pending:
                if wait_and_approve:
                    apply_verdict(home, pending[0]["id"], "allow", approver="test")
                elif wait_and_deny:
                    apply_verdict(home, pending[0]["id"], "deny", approver="test")

        if wait_and_approve or wait_and_deny:
            tg.start_soon(sidecar_approver)

        async with ClientSession(proxy_to_client_recv, client_to_proxy_send) as session:
            await session.initialize()
            result = await driver(session)

        tg.cancel_scope.cancel()

    return result


@pytest.mark.anyio
async def test_escalate_approve_forwards_to_upstream(isolated_home):
    up = FakeUpstream("gh")
    up.add_tool("create_pr")
    cfg = _cfg_escalate(timeout_s=5)

    async def driver(session):
        return await session.call_tool("gh__create_pr", {"title": "hi"})

    result = await _drive(cfg, {"gh": up}, driver, isolated_home, wait_and_approve=True)
    assert not result.isError
    assert up.calls == [("create_pr", {"title": "hi"})]


@pytest.mark.anyio
async def test_escalate_deny_blocks_upstream(isolated_home):
    up = FakeUpstream("gh")
    up.add_tool("create_pr")
    cfg = _cfg_escalate(timeout_s=5)

    async def driver(session):
        return await session.call_tool("gh__create_pr", {})

    result = await _drive(cfg, {"gh": up}, driver, isolated_home, wait_and_deny=True)
    assert result.isError
    assert up.calls == []


@pytest.mark.anyio
async def test_escalate_timeout_denies_by_default(isolated_home):
    up = FakeUpstream("gh")
    up.add_tool("create_pr")
    cfg = _cfg_escalate(on_timeout="deny", timeout_s=1)

    async def driver(session):
        return await session.call_tool("gh__create_pr", {})

    result = await _drive(cfg, {"gh": up}, driver, isolated_home)
    assert result.isError
    assert up.calls == []


@pytest.mark.anyio
async def test_escalate_timeout_allow_forwards(isolated_home):
    up = FakeUpstream("gh")
    up.add_tool("create_pr")
    cfg = _cfg_escalate(on_timeout="allow", timeout_s=1)

    async def driver(session):
        return await session.call_tool("gh__create_pr", {})

    result = await _drive(cfg, {"gh": up}, driver, isolated_home)
    assert not result.isError
    assert up.calls == [("create_pr", {})]


@pytest.fixture
def anyio_backend():
    return "asyncio"
