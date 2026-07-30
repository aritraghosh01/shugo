from __future__ import annotations

from shugo.errors import ShugoError

SEP = "__"


def namespace(server: str, tool: str) -> str:
    if SEP in server:
        raise ShugoError(f"upstream name {server!r} must not contain {SEP!r}")
    return f"{server}{SEP}{tool}"


def unpack(qualified: str) -> tuple[str, str]:
    if SEP not in qualified:
        raise ShugoError(f"tool name {qualified!r} is not namespaced (missing {SEP!r})")
    server, _, tool = qualified.partition(SEP)
    if not server or not tool:
        raise ShugoError(f"malformed namespaced tool {qualified!r}")
    return server, tool
