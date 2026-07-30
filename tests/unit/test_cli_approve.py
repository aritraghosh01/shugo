import json

from typer.testing import CliRunner

from shugo.cli import app

runner = CliRunner()


def _seed_pending(home, pid="req-abc"):
    (home / "pending").mkdir(parents=True, exist_ok=True)
    (home / "approved").mkdir(parents=True, exist_ok=True)
    (home / "denied").mkdir(parents=True, exist_ok=True)
    (home / "timeout").mkdir(parents=True, exist_ok=True)
    (home / "pending" / f"{pid}.json").write_text(
        json.dumps({"id": pid, "server": "gh", "tool": "create_pr", "args": {}, "rule_id": "r1"}),
        encoding="utf-8",
    )


def test_approve_moves_pending_to_approved(tmp_path, monkeypatch):
    home = tmp_path / "h"
    home.mkdir()
    _seed_pending(home)
    monkeypatch.setenv("SHUGO_HOME", str(home))
    result = runner.invoke(app, ["approve", "req-abc"])
    assert result.exit_code == 0
    assert (home / "approved" / "req-abc.json").exists()
    assert not (home / "pending" / "req-abc.json").exists()


def test_deny_moves_pending_to_denied(tmp_path, monkeypatch):
    home = tmp_path / "h"
    home.mkdir()
    _seed_pending(home)
    monkeypatch.setenv("SHUGO_HOME", str(home))
    result = runner.invoke(app, ["deny", "req-abc", "--note", "nope"])
    assert result.exit_code == 0
    data = json.loads((home / "denied" / "req-abc.json").read_text())
    assert data["_note"] == "nope"


def test_approve_missing_id_no_watch_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("SHUGO_HOME", str(tmp_path / "h"))
    result = runner.invoke(app, ["approve"])
    assert result.exit_code == 1


def test_approve_missing_pending_errors(tmp_path, monkeypatch):
    home = tmp_path / "h"
    (home / "pending").mkdir(parents=True)
    monkeypatch.setenv("SHUGO_HOME", str(home))
    result = runner.invoke(app, ["approve", "nope"])
    assert result.exit_code == 1
