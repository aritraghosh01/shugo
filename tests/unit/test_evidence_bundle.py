import json

import pytest
import yaml

from shugo.audit.log import AuditLog
from shugo.errors import ShugoError
from shugo.evidence import generate_bundle, list_frameworks, load_framework


def test_list_frameworks_includes_all_four():
    assert set(list_frameworks()) >= {"owasp-llm", "nist-ai-rmf", "eu-ai-act", "iso-42001"}


def test_load_framework_ok():
    fw = load_framework("owasp-llm")
    assert fw["framework"] == "OWASP-LLM"
    assert any(c["id"] == "OWASP-LLM06" for c in fw["controls"])


def test_load_framework_unknown_raises():
    with pytest.raises(ShugoError):
        load_framework("does-not-exist")


def _write_policy(path):
    path.write_text(
        yaml.safe_dump(
            {
                "version": "0.1",
                "upstreams": {"gh": {"command": "x"}},
                "rules": [
                    {
                        "id": "no-force-push",
                        "match": {"tool": "push", "args": {"force": True}},
                        "decision": "deny",
                        "controls": ["OWASP-LLM06"],
                    },
                    {
                        "id": "write-needs-approval",
                        "match": {"tool": "create_*"},
                        "decision": "escalate",
                        "controls": ["EU-AI-ACT-ART-14"],
                        "approval": {"channel": "cli", "timeout_seconds": 60},
                    },
                ],
            }
        )
    )


def _seed_audit(home):
    log = AuditLog(home / "audit.log")
    log.append(
        log.build(
            request_id="r1",
            server="gh",
            tool="push",
            args={"force": True},
            decision="deny",
            matched_rule_id="no-force-push",
            controls=["OWASP-LLM06"],
            ts="2026-07-25T00:00:00+00:00",
        )
    )
    log.append(
        log.build(
            request_id="r2",
            server="gh",
            tool="create_pr",
            args={"title": "hi"},
            decision="allow",
            matched_rule_id="write-needs-approval",
            approver="alice",
            controls=["EU-AI-ACT-ART-14"],
            ts="2026-07-29T00:00:00+00:00",
        )
    )
    # Stale entry — should be outside the window.
    log.append(
        log.build(
            request_id="old",
            server="gh",
            tool="get_repo",
            args={},
            decision="allow",
            matched_rule_id="none",
            ts="2020-01-01T00:00:00+00:00",
        )
    )
    return log.path


def test_bundle_owasp_llm_writes_all_files(tmp_path):
    policy = tmp_path / "guardrails.yaml"
    _write_policy(policy)
    audit = _seed_audit(tmp_path / "home")
    out = tmp_path / "out"

    result = generate_bundle(
        framework="owasp-llm",
        since="30d",
        out_dir=out,
        policy_path=policy,
        audit_path=audit,
    )

    names = {p.name for p in result.files_written}
    assert names == {"report.md", "rules.yaml", "audit-window.jsonl", "manifest.json"}

    report = (result.out_dir / "report.md").read_text(encoding="utf-8")
    assert "OWASP-LLM" in report
    assert "does not certify" in report
    assert "OWASP-LLM06" in report

    # LLM06 should show fires from the deny + escalate rule with matching control
    assert "no-force-push" in report or "write-needs-approval" in report

    # Old entry outside 30d should not be in the window file
    window_lines = (result.out_dir / "audit-window.jsonl").read_text(encoding="utf-8").splitlines()
    request_ids = {json.loads(line)["request_id"] for line in window_lines}
    assert request_ids == {"r1", "r2"}

    manifest = json.loads((result.out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["framework"] == "OWASP-LLM"
    assert set(manifest["files"].keys()) == {"report.md", "rules.yaml", "audit-window.jsonl"}
    # Each hash is 64 hex chars
    for h in manifest["files"].values():
        assert len(h) == 64


def test_bundle_all_frameworks_smoke(tmp_path):
    policy = tmp_path / "guardrails.yaml"
    _write_policy(policy)
    audit = _seed_audit(tmp_path / "home")
    for fw in list_frameworks():
        out = tmp_path / f"out-{fw}"
        result = generate_bundle(
            framework=fw,
            since="365d",
            out_dir=out,
            policy_path=policy,
            audit_path=audit,
        )
        assert (result.out_dir / "report.md").exists()
        assert result.controls_total > 0


def test_bundle_since_absolute_date(tmp_path):
    policy = tmp_path / "guardrails.yaml"
    _write_policy(policy)
    audit = _seed_audit(tmp_path / "home")
    result = generate_bundle(
        framework="owasp-llm",
        since="2026-07-01",
        out_dir=tmp_path / "out",
        policy_path=policy,
        audit_path=audit,
    )
    assert result.entries_in_window == 2  # r1 and r2


def test_bundle_bad_since_raises(tmp_path):
    policy = tmp_path / "guardrails.yaml"
    _write_policy(policy)
    audit = _seed_audit(tmp_path / "home")
    with pytest.raises(ShugoError):
        generate_bundle(
            framework="owasp-llm",
            since="last-tuesday",
            out_dir=tmp_path / "out",
            policy_path=policy,
            audit_path=audit,
        )
