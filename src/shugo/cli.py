from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from shugo import __version__

app = typer.Typer(
    name="shugo",
    help="SHUGO — MCP guardrails proxy. Policy-first, human approvals, hash-chained audit.",
    no_args_is_help=True,
    add_completion=False,
)

audit_app = typer.Typer(help="Inspect and verify the audit log.", no_args_is_help=True)
app.add_typer(audit_app, name="audit")

console = Console()


def _not_implemented(name: str) -> None:
    console.print(f"[yellow]shugo {name}[/yellow]: not implemented yet (v0.1 in development)")
    raise typer.Exit(code=2)


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit."),
) -> None:
    if version:
        console.print(f"shugo {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command()
def serve(
    config: Path = typer.Option(Path("guardrails.yaml"), "--config", "-c", help="Path to guardrails.yaml"),
    approvals: str = typer.Option("file", "--approvals", help="Approval channel: file, http, or both"),
    approvals_port: int = typer.Option(6247, "--approvals-port", help="Port for HTTP approval UI"),
) -> None:
    """Run the guard proxy over stdio."""
    from shugo.commands import serve as _cmd

    _cmd.run(config=config, console=console, approvals=approvals, approvals_port=approvals_port)


@app.command(name="init")
def init_cmd(
    from_: Optional[Path] = typer.Option(None, "--from", help="Path to existing MCP client config"),
    out: Path = typer.Option(Path("guardrails.yaml"), "--out", "-o", help="Output policy path"),
    skip_enumerate: bool = typer.Option(
        False, "--skip-enumerate", help="Don't spawn upstreams to enumerate tools"
    ),
) -> None:
    """Scaffold guardrails.yaml from installed MCP servers."""
    from shugo.commands import init as _cmd

    _cmd.run(from_=from_, out=out, console=console, enumerate_upstreams=not skip_enumerate)


@app.command()
def validate(
    config: Path = typer.Option(Path("guardrails.yaml"), "--config", "-c"),
) -> None:
    """Lint and schema-check the policy file."""
    from shugo.commands import validate as _cmd

    _cmd.run(config, console)


@app.command()
def explain(
    server: str = typer.Option(..., "--server", "-s"),
    tool: str = typer.Option(..., "--tool", "-t"),
    args: Optional[str] = typer.Option(None, "--args", "-a", help="JSON-encoded tool args"),
    config: Path = typer.Option(Path("guardrails.yaml"), "--config", "-c"),
) -> None:
    """Dry-run a call — show which rule fires and why."""
    from shugo.commands import explain as _cmd

    _cmd.run(server=server, tool=tool, args_json=args, config=config, console=console)


@audit_app.command("tail")
def audit_tail(
    follow: bool = typer.Option(False, "-f", "--follow"),
    n: int = typer.Option(20, "-n", help="Number of entries to show"),
) -> None:
    """Show recent audit log entries."""
    from shugo.commands import audit as _cmd

    _cmd.run_tail(n=n, follow=follow, console=console)


@audit_app.command("verify")
def audit_verify() -> None:
    """Verify the audit log hash chain."""
    from shugo.commands import audit as _cmd

    _cmd.run_verify(console=console)


@app.command()
def evidence(
    framework: str = typer.Option(..., "--framework", "-f"),
    since: str = typer.Option("30d", "--since", "-s"),
    out: Path = typer.Option(Path("evidence"), "--out", "-o"),
    config: Path = typer.Option(Path("guardrails.yaml"), "--config", "-c"),
) -> None:
    """Generate a framework-mapped evidence bundle from the audit log."""
    from shugo.commands import evidence as _cmd

    _cmd.run(framework=framework, since=since, out=out, config=config, console=console)


@app.command()
def approve(
    approval_id: Optional[str] = typer.Argument(None, help="Pending approval id"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Interactive TUI over pending approvals"),
    note: Optional[str] = typer.Option(None, "--note", help="Optional note on the decision"),
) -> None:
    """Approve a pending call, or run the watch TUI."""
    from shugo.commands import approve as _cmd

    _cmd.run_approve(approval_id=approval_id, watch=watch, note=note, console=console)


@app.command()
def deny(
    approval_id: str = typer.Argument(..., help="Pending approval id"),
    note: Optional[str] = typer.Option(None, "--note", help="Optional note on the decision"),
) -> None:
    """Deny a pending call."""
    from shugo.commands import approve as _cmd

    _cmd.run_deny(approval_id=approval_id, note=note, console=console)


@app.command()
def halt() -> None:
    """Kill switch — deny all subsequent calls until unhalted."""
    from shugo.commands import halt as _cmd

    _cmd.run_halt(console)


@app.command()
def unhalt() -> None:
    """Clear the halt sentinel."""
    from shugo.commands import halt as _cmd

    _cmd.run_unhalt(console)


if __name__ == "__main__":
    app()
