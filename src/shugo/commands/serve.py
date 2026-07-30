from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from shugo.errors import PolicyError, ShugoError
from shugo.policy.loader import load_config
from shugo.proxy import serve as _serve


def run(config: Path, console: Console) -> int:
    try:
        cfg = load_config(config)
    except PolicyError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    if not cfg.upstreams:
        console.print("[red]no upstreams configured in policy — nothing to guard[/red]")
        raise typer.Exit(code=1)

    try:
        asyncio.run(_serve(cfg))
    except (ShugoError, KeyboardInterrupt) as e:
        if isinstance(e, KeyboardInterrupt):
            raise typer.Exit(code=0)
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    return 0
