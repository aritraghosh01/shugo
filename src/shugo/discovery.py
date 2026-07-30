from __future__ import annotations

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path

from mcp import types as mcp_types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@dataclass
class DiscoveredServer:
    name: str
    command: str
    args: list[str]
    env: dict[str, str]


def default_client_config_paths() -> list[Path]:
    """Best-effort ordered list of MCP client config paths per OS."""
    home = Path.home()
    paths: list[Path] = []
    if sys.platform == "darwin":
        paths.append(home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json")
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(Path(appdata) / "Claude" / "claude_desktop_config.json")
    else:
        paths.append(home / ".config" / "Claude" / "claude_desktop_config.json")

    paths.extend(
        [
            Path.cwd() / ".cursor" / "mcp.json",
            Path.cwd() / ".vscode" / "mcp.json",
            home / ".cursor" / "mcp.json",
        ]
    )
    return paths


def find_client_config() -> Path | None:
    for p in default_client_config_paths():
        if p.exists():
            return p
    return None


def parse_client_config(path: Path) -> list[DiscoveredServer]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    servers_map = raw.get("mcpServers") or raw.get("servers") or {}
    if not isinstance(servers_map, dict):
        return []
    out: list[DiscoveredServer] = []
    for name, spec in servers_map.items():
        if not isinstance(spec, dict):
            continue
        command = spec.get("command")
        if not command:
            continue
        out.append(
            DiscoveredServer(
                name=_normalize_name(name),
                command=command,
                args=list(spec.get("args") or []),
                env=dict(spec.get("env") or {}),
            )
        )
    return out


def _normalize_name(name: str) -> str:
    return name.strip().lower().replace(" ", "-").replace("__", "-")


async def _enumerate_tools_once(spec: DiscoveredServer, timeout_s: float = 10.0) -> list[str]:
    params = StdioServerParameters(
        command=spec.command,
        args=list(spec.args),
        env={**os.environ, **spec.env},
    )

    async def _do():
        async with AsyncExitStack() as stack:
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            result = await session.list_tools()
            return [t.name for t in result.tools]

    return await asyncio.wait_for(_do(), timeout=timeout_s)


def enumerate_tools(spec: DiscoveredServer, timeout_s: float = 10.0) -> list[str] | None:
    """Blocking helper for CLI use. Returns None if enumeration fails."""
    try:
        return asyncio.run(_enumerate_tools_once(spec, timeout_s=timeout_s))
    except Exception:
        return None
