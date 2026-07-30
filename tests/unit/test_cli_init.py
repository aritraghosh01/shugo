import json

import yaml
from typer.testing import CliRunner

from shugo.cli import app

runner = CliRunner()


def _write_config(path, servers):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")


def test_init_writes_guardrails_yaml_and_prints_snippet(tmp_path):
    cfg = tmp_path / "claude_desktop_config.json"
    _write_config(
        cfg,
        {
            "github": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"], "env": {}},
        },
    )
    out = tmp_path / "guardrails.yaml"
    result = runner.invoke(
        app,
        ["init", "--from", str(cfg), "--out", str(out), "--skip-enumerate"],
    )
    assert result.exit_code == 0
    assert out.exists()
    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert doc["version"] == "0.1"
    assert "github" in doc["upstreams"]
    ids = [r["id"] for r in doc["rules"]]
    assert "read-only-github" in ids
    assert "write-needs-approval-github" in ids
    # Snippet with uvx invocation printed
    assert "mcpServers" in result.output
    assert "uvx" in result.output


def test_init_backs_up_existing(tmp_path):
    cfg = tmp_path / "cfg.json"
    _write_config(cfg, {"gh": {"command": "npx", "args": ["srv"]}})
    out = tmp_path / "guardrails.yaml"
    out.write_text("old-content", encoding="utf-8")
    result = runner.invoke(app, ["init", "--from", str(cfg), "--out", str(out), "--skip-enumerate"])
    assert result.exit_code == 0
    backup = out.with_suffix(out.suffix + ".shugo-backup")
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == "old-content"


def test_init_no_config_found_errors(tmp_path):
    result = runner.invoke(app, ["init", "--from", str(tmp_path / "nope.json"), "--skip-enumerate"])
    assert result.exit_code == 1


def test_init_empty_config_errors(tmp_path):
    cfg = tmp_path / "cfg.json"
    _write_config(cfg, {})
    result = runner.invoke(app, ["init", "--from", str(cfg), "--skip-enumerate"])
    assert result.exit_code == 1
