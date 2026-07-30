from __future__ import annotations

import os
from contextlib import AsyncExitStack
from typing import Any, Protocol

from mcp import types as mcp_types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from shugo.errors import UpstreamError
from shugo.policy.models import UpstreamSpec


class UpstreamProtocol(Protocol):
    name: str

    async def list_tools(self) -> list[mcp_types.Tool]: ...

    async def call_tool(self, tool: str, arguments: dict[str, Any]) -> mcp_types.CallToolResult: ...


class StdioUpstream:
    """MCP client connected to a stdio subprocess upstream."""

    def __init__(self, name: str, session: ClientSession) -> None:
        self.name = name
        self._session = session

    @classmethod
    async def start(cls, name: str, spec: UpstreamSpec, stack: AsyncExitStack) -> "StdioUpstream":
        env = {**os.environ, **spec.env}
        params = StdioServerParameters(command=spec.command, args=list(spec.args), env=env)
        try:
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
        except Exception as e:
            raise UpstreamError(f"failed to start upstream {name!r}: {e}") from e
        return cls(name, session)

    async def list_tools(self) -> list[mcp_types.Tool]:
        result = await self._session.list_tools()
        return list(result.tools)

    async def call_tool(self, tool: str, arguments: dict[str, Any]) -> mcp_types.CallToolResult:
        return await self._session.call_tool(tool, arguments)
