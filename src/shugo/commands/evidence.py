from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from shugo import paths
from shugo.errors import ShugoError
from shugo.evidence import generate_bundle, list_frameworks


def run(
    *,
    framework: str,
    since: str,
    out: Path,
    config: Path,
    console: Console,
) -> int:
    if framework not in list_frameworks():
        console.print(
            f"[red]unknown framework {framework!r}[/red]. "
            f"available: {', '.join(list_frameworks())}"
        )
        raise typer.Exit(code=1)
    try:
        result = generate_bundle(
            framework=framework,
            since=since,
            out_dir=out,
            policy_path=config,
            audit_path=paths.audit_log(),
        )
    except ShugoError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]bundle written[/green] -> {result.out_dir}")
    console.print(
        f"  framework: {result.framework}  "
        f"controls: {result.controls_matched}/{result.controls_total} covered  "
        f"audit: {result.entries_in_window}/{result.entries_scanned} in window"
    )
    for f in result.files_written:
        console.print(f"  - {f.name}")
    return 0
