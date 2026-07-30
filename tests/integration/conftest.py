from __future__ import annotations

from typing import Any

import pytest
from mcp import types as mcp_types


class FakeUpstream:
    """In-memory MCP-like upstream — bypasses the subprocess/stdio layer."""

    def __init__(self, name: str, tools: list[mcp_types.Tool] | None = None) -> None:
        self.name = name
        self._tools = tools or []
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def add_tool(self, name: str, description: str = "") -> None:
        self._tools.append(
            mcp_types.Tool(
                name=name,
                description=description or f"fake tool {name}",
                inputSchema={"type": "object", "properties": {}, "additionalProperties": True},
            )
        )

    async def list_tools(self) -> list[mcp_types.Tool]:
        return list(self._tools)

    async def call_tool(self, tool: str, arguments: dict[str, Any]) -> mcp_types.CallToolResult:
        self.calls.append((tool, arguments))
        return mcp_types.CallToolResult(
            content=[mcp_types.TextContent(type="text", text=f"{self.name}::{tool} ok")],
        )


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    home = tmp_path / "shugo-home"
    home.mkdir()
    monkeypatch.setenv("SHUGO_HOME", str(home))
    return home
