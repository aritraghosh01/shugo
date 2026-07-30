from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console

from shugo import paths


def run_halt(console: Console) -> int:
    paths.ensure_layout()
    sentinel = paths.halt_sentinel()
    sentinel.write_text(
        f"halted-at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n",
        encoding="utf-8",
    )
    console.print(f"[red]HALT[/red] set at {sentinel} — all calls will be denied")
    return 0


def run_unhalt(console: Console) -> int:
    sentinel = paths.halt_sentinel()
    if sentinel.exists():
        sentinel.unlink()
        console.print(f"[green]cleared[/green] {sentinel}")
    else:
        console.print(f"[dim]no halt sentinel at {sentinel}[/dim]")
    return 0
