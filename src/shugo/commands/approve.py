from __future__ import annotations

import typer
from rich.console import Console

from shugo import paths
from shugo.approval.file_channel import apply_verdict
from shugo.approval.sidecar_tui import run_watch


def run_approve(
    approval_id: str | None,
    watch: bool,
    note: str | None,
    console: Console,
) -> int:
    if watch:
        return run_watch(console)
    if not approval_id:
        console.print("[red]approval id required (or pass --watch)[/red]")
        raise typer.Exit(code=1)
    return _resolve(approval_id, "allow", note, console)


def run_deny(approval_id: str, note: str | None, console: Console) -> int:
    return _resolve(approval_id, "deny", note, console)


def _resolve(approval_id: str, kind: str, note: str | None, console: Console) -> int:
    home = paths.shugo_home()
    try:
        dest = apply_verdict(home, approval_id, kind, approver="cli-oneshot", note=note)
    except FileNotFoundError:
        console.print(f"[yellow]{approval_id}: no pending approval (already resolved?)[/yellow]")
        raise typer.Exit(code=1)
    color = "green" if kind == "allow" else "red"
    console.print(f"[{color}]{kind}[/{color}] {approval_id[:8]} -> {dest}")
    return 0
