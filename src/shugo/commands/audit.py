from __future__ import annotations

import json
import time

import typer
from rich.console import Console

from shugo import paths
from shugo.audit.verify import verify_log


def run_tail(n: int, follow: bool, console: Console) -> int:
    p = paths.audit_log()
    if not p.exists():
        console.print(f"[yellow]no audit log at {p}[/yellow]")
        return 0
    with p.open("r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f if line.strip()]
    for line in lines[-n:]:
        _print_entry(console, line)
    if not follow:
        return 0
    with p.open("r", encoding="utf-8") as f:
        f.seek(0, 2)
        try:
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                line = line.rstrip("\n")
                if line.strip():
                    _print_entry(console, line)
        except KeyboardInterrupt:
            return 0


def _print_entry(console: Console, line: str) -> None:
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        console.print(f"[red]corrupt line:[/red] {line}")
        return
    decision = entry.get("decision", "?")
    color = {"allow": "green", "deny": "red", "escalate": "yellow"}.get(decision, "white")
    console.print(
        f"[dim]{entry.get('ts', '?')}[/dim] "
        f"[{color}]{decision:<8}[/{color}] "
        f"{entry.get('server', '?')}::{entry.get('tool', '?')} "
        f"[dim]rule={entry.get('matched_rule_id') or '-'} "
        f"id={entry.get('request_id', '?')[:8]}[/dim]"
    )


def run_verify(console: Console) -> int:
    p = paths.audit_log()
    result = verify_log(p)
    if result.ok:
        console.print(f"[green]OK[/green] {p}: {result.entries} entries verified")
        return 0
    console.print(f"[red]FAIL[/red] {p}: {result.error} (line {result.error_line})")
    raise typer.Exit(code=1)
