from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from shugo.errors import PolicyError
from shugo.policy.engine import EvalContext, PolicyEngine
from shugo.policy.loader import load_config


def run(
    server: str,
    tool: str,
    args_json: str | None,
    config: Path,
    console: Console,
) -> int:
    try:
        cfg = load_config(config)
    except PolicyError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    args: dict = {}
    if args_json:
        try:
            parsed = json.loads(args_json)
        except json.JSONDecodeError as e:
            console.print(f"[red]--args is not valid JSON: {e}[/red]")
            raise typer.Exit(code=1)
        if not isinstance(parsed, dict):
            console.print("[red]--args must be a JSON object[/red]")
            raise typer.Exit(code=1)
        args = parsed

    engine = PolicyEngine(cfg)
    decision = engine.evaluate(EvalContext(server=server, tool=tool, args=args))

    color = {"allow": "green", "deny": "red", "escalate": "yellow"}[decision.kind]
    console.print(f"[{color}]decision:[/{color}] {decision.kind}")
    console.print(f"rule:     {decision.rule_id or '(none — default applied)'}")
    if decision.reason:
        console.print(f"reason:   {decision.reason}")
    if decision.controls:
        console.print(f"controls: {', '.join(decision.controls)}")
    if decision.approval:
        console.print(
            f"approval: channel={decision.approval.channel}, "
            f"timeout={decision.approval.timeout_seconds}s, "
            f"on_timeout={decision.approval.on_timeout}"
        )
    return 0
