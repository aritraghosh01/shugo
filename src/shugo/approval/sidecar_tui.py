from __future__ import annotations

import time
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from shugo import paths
from shugo.approval.file_channel import apply_verdict, list_pending


def run_watch(console: Console, poll_seconds: float = 0.5, max_iterations: int | None = None) -> int:
    """Interactive sidecar loop.

    Polls the pending directory; when new requests appear, prints them and
    prompts for [a]pprove / [d]eny / [s]kip. Runs until Ctrl-C, or up to
    max_iterations (used by tests to keep runs finite).
    """
    home = paths.shugo_home()
    console.print(f"[dim]watching {home / 'pending'} — Ctrl-C to quit[/dim]")
    seen: set[str] = set()
    iterations = 0
    try:
        while True:
            if max_iterations is not None and iterations >= max_iterations:
                return 0
            iterations += 1
            for entry in list_pending(home):
                pid = entry["id"]
                if pid in seen:
                    continue
                seen.add(pid)
                _print_pending(console, entry)
                choice = Prompt.ask(
                    "[bold]decision[/bold]",
                    choices=["a", "d", "s"],
                    default="s",
                )
                if choice == "s":
                    continue
                kind = "allow" if choice == "a" else "deny"
                try:
                    apply_verdict(home, pid, kind, approver="cli-watch")
                    console.print(f"[green]{kind}[/green] {pid[:8]}")
                except FileNotFoundError:
                    console.print(f"[yellow]{pid[:8]} already resolved[/yellow]")
            time.sleep(poll_seconds)
    except KeyboardInterrupt:
        return 0


def _print_pending(console: Console, entry: dict) -> None:
    console.print()
    console.print(f"[bold]pending[/bold] {entry['id'][:8]}  "
                  f"[dim]rule={entry.get('rule_id') or '-'}[/dim]")
    console.print(f"  server: {entry.get('server')}")
    console.print(f"  tool:   {entry.get('tool')}")
    if entry.get('args'):
        console.print(f"  args:   {entry.get('args')}")
    if entry.get('reason'):
        console.print(f"  reason: {entry.get('reason')}")
    if entry.get('controls'):
        console.print(f"  controls: {', '.join(entry.get('controls'))}")
