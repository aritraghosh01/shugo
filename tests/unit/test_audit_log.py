import json

import pytest

from shugo.audit.log import AuditLog, SEED_HASH, canonical_json, redact
from shugo.audit.verify import verify_log
from shugo.errors import AuditError


def _build(log: AuditLog, tool: str = "get_x", **extra):
    return log.build(
        request_id=extra.pop("request_id", "req-1"),
        server=extra.pop("server", "gh"),
        tool=tool,
        args=extra.pop("args", {}),
        decision=extra.pop("decision", "allow"),
        matched_rule_id=extra.pop("matched_rule_id", "r1"),
        ts=extra.pop("ts", "2026-07-30T00:00:00.000000+00:00"),
    )


def test_canonical_json_is_stable_and_sorted():
    a = canonical_json({"b": 1, "a": 2})
    b = canonical_json({"a": 2, "b": 1})
    assert a == b == b'{"a":2,"b":1}'


def test_canonical_json_nfc_normalizes_strings():
    decomposed = "café"  # NFD form of "café"
    composed = "café"
    assert canonical_json({"x": decomposed}) == canonical_json({"x": composed})


def test_redact_replaces_dotted_paths():
    args = {"a": {"secret": "hunter2", "b": 1}, "c": 3}
    out = redact(args, ["a.secret"])
    assert out == {"a": {"secret": "***", "b": 1}, "c": 3}
    # original untouched (deep copy)
    assert args["a"]["secret"] == "hunter2"


def test_redact_missing_path_is_noop():
    out = redact({"a": 1}, ["b.c"])
    assert out == {"a": 1}


def test_append_and_chain(tmp_path):
    log = AuditLog(tmp_path / "audit.log")
    assert log.head == SEED_HASH

    e1 = log.append(_build(log, tool="t1"))
    assert e1["prev_hash"] == SEED_HASH
    assert len(e1["this_hash"]) == 64

    e2 = log.append(_build(log, tool="t2", request_id="req-2"))
    assert e2["prev_hash"] == e1["this_hash"]

    # persisted to disk
    lines = (tmp_path / "audit.log").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["this_hash"] == e2["this_hash"]


def test_resume_from_existing_log(tmp_path):
    log1 = AuditLog(tmp_path / "audit.log")
    log1.append(_build(log1))
    head_after_first = log1.head

    log2 = AuditLog(tmp_path / "audit.log")
    assert log2.head == head_after_first


def test_corrupt_last_line_fails_startup(tmp_path):
    p = tmp_path / "audit.log"
    p.write_text('{"bad": "no-hash"}\n', encoding="utf-8")
    with pytest.raises(AuditError):
        AuditLog(p)


def test_verify_ok_on_valid_chain(tmp_path):
    log = AuditLog(tmp_path / "audit.log")
    for i in range(5):
        log.append(_build(log, request_id=f"req-{i}"))
    result = verify_log(tmp_path / "audit.log")
    assert result.ok
    assert result.entries == 5


def test_verify_detects_tampering(tmp_path):
    log = AuditLog(tmp_path / "audit.log")
    log.append(_build(log, request_id="a"))
    log.append(_build(log, request_id="b"))
    p = tmp_path / "audit.log"
    lines = p.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    entry["server"] = "TAMPERED"
    lines[0] = json.dumps(entry, sort_keys=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = verify_log(p)
    assert not result.ok
    assert result.error_line == 1


def test_verify_empty_log_ok(tmp_path):
    result = verify_log(tmp_path / "does-not-exist.log")
    assert result.ok
    assert result.entries == 0


def test_redaction_applied_to_stored_entry(tmp_path):
    log = AuditLog(tmp_path / "audit.log", redact_paths=["secret"])
    entry = log.build(
        request_id="r1",
        server="s",
        tool="t",
        args={"secret": "hunter2", "keep": 1},
        decision="allow",
        matched_rule_id="rule",
    )
    log.append(entry)
    stored = json.loads((tmp_path / "audit.log").read_text().splitlines()[0])
    assert stored["args_redacted"] == {"secret": "***", "keep": 1}


def test_tail_returns_last_n(tmp_path):
    log = AuditLog(tmp_path / "audit.log")
    for i in range(10):
        log.append(_build(log, request_id=f"r{i}"))
    tail = log.tail(3)
    assert [e["request_id"] for e in tail] == ["r7", "r8", "r9"]
