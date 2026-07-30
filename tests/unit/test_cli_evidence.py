import yaml
from typer.testing import CliRunner

from shugo.audit.log import AuditLog
from shugo.cli import app

runner = CliRunner()


def _write_policy(tmp_path):
    p = tmp_path / "guardrails.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "version": "0.1",
                "upstreams": {"gh": {"command": "x"}},
                "rules": [{"id": "r1", "match": {"tool": "*"}, "decision": "allow"}],
            }
        ),
        encoding="utf-8",
    )
    return p


def test_evidence_cli_generates_bundle(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("SHUGO_HOME", str(home))
    # seed a couple of audit entries
    log = AuditLog(home / "audit.log")
    log.append(log.build(request_id="r1", server="gh", tool="t", args={}, decision="allow", matched_rule_id="r1"))

    policy = _write_policy(tmp_path)
    out = tmp_path / "out"

    result = runner.invoke(
        app,
        ["evidence", "-f", "owasp-llm", "-s", "30d", "-o", str(out), "-c", str(policy)],
    )
    assert result.exit_code == 0
    assert any(p.name == "report.md" for p in out.rglob("report.md"))


def test_evidence_cli_unknown_framework(tmp_path, monkeypatch):
    monkeypatch.setenv("SHUGO_HOME", str(tmp_path / "home"))
    policy = _write_policy(tmp_path)
    result = runner.invoke(
        app,
        ["evidence", "-f", "no-such-framework", "-s", "30d", "-o", str(tmp_path / "out"), "-c", str(policy)],
    )
    assert result.exit_code == 1
    assert "unknown framework" in result.output
