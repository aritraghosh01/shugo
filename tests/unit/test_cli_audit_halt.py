import json

from typer.testing import CliRunner

from shugo.audit.log import AuditLog
from shugo.cli import app

runner = CliRunner()


def _seed_log(tmp_path, n=3):
    home = tmp_path / "shugo-home"
    home.mkdir()
    log = AuditLog(home / "audit.log")
    for i in range(n):
        log.append(
            log.build(
                request_id=f"req-{i}",
                server="gh",
                tool=f"t{i}",
                args={},
                decision="allow",
                matched_rule_id="r1",
                ts=f"2026-07-30T00:00:0{i}+00:00",
            )
        )
    return home


def test_audit_tail_prints_entries(tmp_path, monkeypatch):
    home = _seed_log(tmp_path, n=3)
    monkeypatch.setenv("SHUGO_HOME", str(home))
    result = runner.invoke(app, ["audit", "tail", "-n", "2"])
    assert result.exit_code == 0
    assert "t1" in result.output
    assert "t2" in result.output


def test_audit_verify_ok(tmp_path, monkeypatch):
    home = _seed_log(tmp_path, n=2)
    monkeypatch.setenv("SHUGO_HOME", str(home))
    result = runner.invoke(app, ["audit", "verify"])
    assert result.exit_code == 0
    assert "OK" in result.output
    assert "2 entries" in result.output


def test_audit_verify_fails_on_tamper(tmp_path, monkeypatch):
    home = _seed_log(tmp_path, n=2)
    p = home / "audit.log"
    lines = p.read_text().splitlines()
    e = json.loads(lines[0])
    e["server"] = "evil"
    lines[0] = json.dumps(e, sort_keys=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.setenv("SHUGO_HOME", str(home))
    result = runner.invoke(app, ["audit", "verify"])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_halt_and_unhalt(tmp_path, monkeypatch):
    home = tmp_path / "shugo-home"
    home.mkdir()
    monkeypatch.setenv("SHUGO_HOME", str(home))
    assert not (home / "HALT").exists()
    r1 = runner.invoke(app, ["halt"])
    assert r1.exit_code == 0
    assert (home / "HALT").exists()
    r2 = runner.invoke(app, ["unhalt"])
    assert r2.exit_code == 0
    assert not (home / "HALT").exists()
    r3 = runner.invoke(app, ["unhalt"])
    assert r3.exit_code == 0
    assert "no halt sentinel" in r3.output
