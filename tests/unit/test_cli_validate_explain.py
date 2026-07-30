from pathlib import Path

from typer.testing import CliRunner

from shugo.cli import app

runner = CliRunner()
STARTER = Path(__file__).resolve().parents[2] / "policies" / "starter.yaml"


def test_validate_ok():
    result = runner.invoke(app, ["validate", "--config", str(STARTER)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_validate_missing_file_exits_1(tmp_path):
    result = runner.invoke(app, ["validate", "--config", str(tmp_path / "nope.yaml")])
    assert result.exit_code == 1


def test_explain_allow_path():
    result = runner.invoke(
        app,
        ["explain", "--config", str(STARTER), "--server", "github", "--tool", "get_repo"],
    )
    assert result.exit_code == 0
    assert "allow" in result.output
    assert "read-only-github" in result.output


def test_explain_deny_with_args():
    result = runner.invoke(
        app,
        [
            "explain",
            "--config", str(STARTER),
            "--server", "github",
            "--tool", "push",
            "--args", '{"force": true}',
        ],
    )
    assert result.exit_code == 0
    assert "deny" in result.output
    assert "no-force-push" in result.output


def test_explain_escalate_fallthrough():
    result = runner.invoke(
        app,
        ["explain", "--config", str(STARTER), "--server", "github", "--tool", "create_pr"],
    )
    assert result.exit_code == 0
    assert "escalate" in result.output
    assert "write-needs-approval" in result.output


def test_explain_bad_args_json_exits_1():
    result = runner.invoke(
        app,
        ["explain", "--config", str(STARTER), "--server", "gh", "--tool", "x", "--args", "not-json"],
    )
    assert result.exit_code == 1
