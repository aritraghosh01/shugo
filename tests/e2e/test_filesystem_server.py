"""End-to-end test against a real MCP server subprocess.

Uses `@modelcontextprotocol/server-filesystem` via `npx`. Marked slow;
opt-in via `pytest -m slow`. Skipped automatically if npx is not on
PATH — CI runs it only on Ubuntu.
"""
from __future__ import annotations

import shutil
from contextlib import AsyncExitStack

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage

from shugo.policy.models import Config
from shugo.proxy import serve_with_upstreams
from shugo.upstream import StdioUpstream


pytestmark = [pytest.mark.slow]


def _npx_available() -> bool:
    return shutil.which("npx") is not None


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.skipif(not _npx_available(), reason="npx not on PATH")
@pytest.mark.anyio
async def test_read_allowed_write_denied_against_real_filesystem_server(tmp_path, monkeypatch):
    monkeypatch.setenv("SHUGO_HOME", str(tmp_path / "shugo-home"))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "hello.txt").write_text("hi\n", encoding="utf-8")

    cfg = Config.model_validate(
        {
            "version": "0.1",
            "defaults": {"decision": "deny", "on_error": "deny"},
            "upstreams": {
                "fs": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", str(workspace)],
                    "env": {},
                }
            },
            "rules": [
                {"id": "read", "match": {"tool": "read_*"}, "decision": "allow"},
                {"id": "list", "match": {"tool": "list_*"}, "decision": "allow"},
                {"id": "write-denied", "match": {"tool": "write_*"}, "decision": "deny"},
            ],
        }
    )

    async with AsyncExitStack() as stack:
        upstreams = {"fs": await StdioUpstream.start("fs", cfg.upstreams["fs"], stack)}

        c_send, c_recv = anyio.create_memory_object_stream[SessionMessage | Exception](32)
        p_send, p_recv = anyio.create_memory_object_stream[SessionMessage](32)

        async with anyio.create_task_group() as tg:
            tg.start_soon(serve_with_upstreams, cfg, upstreams, c_recv, p_send)

            async with ClientSession(p_recv, c_send) as session:
                await session.initialize()

                tools = await session.list_tools()
                names = [t.name for t in tools.tools]
                assert any(n.startswith("fs__") for n in names)

                read_result = await session.call_tool("fs__read_text_file", {"path": "hello.txt"})
                assert not read_result.isError

                write_result = await session.call_tool(
                    "fs__write_file", {"path": "nope.txt", "content": "x"}
                )
                assert write_result.isError

            tg.cancel_scope.cancel()
