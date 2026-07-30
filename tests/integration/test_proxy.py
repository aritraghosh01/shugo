from __future__ import annotations

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage

from shugo.audit.verify import verify_log
from shugo.policy.models import Config
from shugo.proxy import serve_with_upstreams

from .conftest import FakeUpstream


def _cfg(rules):
    return Config.model_validate(
        {
            "version": "0.1",
            "defaults": {"decision": "deny", "on_error": "deny"},
            "upstreams": {"gh": {"command": "unused-in-fake"}},
            "rules": rules,
        }
    )


async def _run_proxy_and_client(cfg, upstreams, driver):
    """Wire an in-memory client <-> proxy over paired memory streams and drive it.

    driver: async callable taking (session) -> result to assert on.
    """
    client_to_proxy_send, client_to_proxy_recv = anyio.create_memory_object_stream[SessionMessage | Exception](32)
    proxy_to_client_send, proxy_to_client_recv = anyio.create_memory_object_stream[SessionMessage](32)

    async with anyio.create_task_group() as tg:
        tg.start_soon(serve_with_upstreams, cfg, upstreams, client_to_proxy_recv, proxy_to_client_send)

        async with ClientSession(proxy_to_client_recv, client_to_proxy_send) as session:
            await session.initialize()
            result = await driver(session)

        tg.cancel_scope.cancel()

    return result


@pytest.mark.anyio
async def test_tools_list_namespaces_upstream_tools(isolated_home):
    up = FakeUpstream("gh")
    up.add_tool("get_repo")
    up.add_tool("create_pr")
    cfg = _cfg([])

    async def driver(session):
        return await session.list_tools()

    result = await _run_proxy_and_client(cfg, {"gh": up}, driver)
    names = sorted(t.name for t in result.tools)
    assert names == ["gh__create_repo".replace("create_repo", "create_pr"), "gh__get_repo"]  # sorted


@pytest.mark.anyio
async def test_allow_path_forwards_to_upstream(isolated_home):
    up = FakeUpstream("gh")
    up.add_tool("get_repo")
    cfg = _cfg([{"id": "r1", "match": {"tool": "get_*"}, "decision": "allow"}])

    async def driver(session):
        return await session.call_tool("gh__get_repo", {"name": "octocat"})

    result = await _run_proxy_and_client(cfg, {"gh": up}, driver)
    assert not result.isError
    assert up.calls == [("get_repo", {"name": "octocat"})]

    verify = verify_log(isolated_home / "audit.log")
    assert verify.ok and verify.entries == 1


@pytest.mark.anyio
async def test_deny_path_blocks_upstream(isolated_home):
    up = FakeUpstream("gh")
    up.add_tool("push")
    cfg = _cfg(
        [
            {
                "id": "no-force",
                "match": {"tool": "push", "args": {"force": True}},
                "decision": "deny",
                "reason": "no force push",
            }
        ]
    )

    async def driver(session):
        return await session.call_tool("gh__push", {"force": True})

    result = await _run_proxy_and_client(cfg, {"gh": up}, driver)
    assert result.isError
    assert up.calls == []
    text = " ".join(getattr(c, "text", "") for c in result.content)
    assert "no force push" in text or "denied" in text.lower()

    verify = verify_log(isolated_home / "audit.log")
    assert verify.ok and verify.entries == 1


@pytest.mark.anyio
async def test_default_deny_blocks_unmatched(isolated_home):
    up = FakeUpstream("gh")
    up.add_tool("get_repo")
    cfg = _cfg([])

    async def driver(session):
        return await session.call_tool("gh__get_repo", {})

    result = await _run_proxy_and_client(cfg, {"gh": up}, driver)
    assert result.isError
    assert up.calls == []


@pytest.mark.anyio
async def test_escalate_denies_without_approval_channel(isolated_home):
    up = FakeUpstream("gh")
    up.add_tool("create_pr")
    cfg = _cfg(
        [
            {
                "id": "esc",
                "match": {"tool": "*"},
                "decision": "escalate",
                "approval": {"channel": "cli", "timeout_seconds": 60, "on_timeout": "deny"},
            }
        ]
    )

    async def driver(session):
        return await session.call_tool("gh__create_pr", {})

    # Not injecting an approval channel — should deny with a clear reason.
    result = await _run_proxy_and_client(cfg, {"gh": up}, driver)
    assert result.isError
    assert up.calls == []


@pytest.mark.anyio
async def test_halt_blocks_all_calls(isolated_home):
    (isolated_home / "HALT").write_text("halted\n", encoding="utf-8")
    up = FakeUpstream("gh")
    up.add_tool("get_repo")
    cfg = _cfg([{"id": "r1", "match": {"tool": "*"}, "decision": "allow"}])

    async def driver(session):
        return await session.call_tool("gh__get_repo", {})

    result = await _run_proxy_and_client(cfg, {"gh": up}, driver)
    assert result.isError
    assert up.calls == []


@pytest.mark.anyio
async def test_unknown_upstream_errors(isolated_home):
    up = FakeUpstream("gh")
    up.add_tool("get_repo")
    cfg = _cfg([{"id": "r1", "match": {"tool": "*"}, "decision": "allow"}])

    async def driver(session):
        return await session.call_tool("unknown__something", {})

    result = await _run_proxy_and_client(cfg, {"gh": up}, driver)
    assert result.isError


@pytest.fixture
def anyio_backend():
    return "asyncio"
