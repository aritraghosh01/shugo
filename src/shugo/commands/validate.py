from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from shugo.errors import PolicyError
from shugo.policy.loader import load_config


def run(config: Path, console: Console) -> int:
    try:
        cfg = load_config(config)
    except PolicyError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    console.print(
        f"[green]OK[/green] {config}: version={cfg.version}, "
        f"upstreams={len(cfg.upstreams)}, rules={len(cfg.rules)}"
    )
    return 0
