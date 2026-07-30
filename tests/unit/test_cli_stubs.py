from typer.testing import CliRunner

from shugo.cli import app

runner = CliRunner()


def test_version_flag_prints_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "shugo" in result.output


def test_help_lists_all_subcommands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ["serve", "init", "validate", "explain", "audit", "evidence", "approve", "deny", "halt", "unhalt"]:
        assert cmd in result.output


def test_audit_subgroup_has_tail_and_verify():
    result = runner.invoke(app, ["audit", "--help"])
    assert result.exit_code == 0
    assert "tail" in result.output
    assert "verify" in result.output


def test_serve_missing_config_exits_1(tmp_path):
    result = runner.invoke(app, ["serve", "--config", str(tmp_path / "nope.yaml")])
    assert result.exit_code == 1
