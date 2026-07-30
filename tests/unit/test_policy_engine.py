import pytest

from shugo.policy.engine import EvalContext, PolicyEngine
from shugo.policy.models import Config


def _cfg(rules, defaults_decision="deny"):
    return Config.model_validate(
        {
            "version": "0.1",
            "defaults": {"decision": defaults_decision, "on_error": "deny"},
            "upstreams": {"gh": {"command": "x"}},
            "rules": rules,
        }
    )


def test_no_rules_applies_default_deny():
    engine = PolicyEngine(_cfg([]))
    d = engine.evaluate(EvalContext("gh", "get_repo"))
    assert d.kind == "deny"
    assert d.rule_id is None


def test_no_rules_applies_default_allow_when_configured():
    engine = PolicyEngine(_cfg([], defaults_decision="allow"))
    d = engine.evaluate(EvalContext("gh", "get_repo"))
    assert d.kind == "allow"


def test_first_match_wins():
    engine = PolicyEngine(
        _cfg(
            [
                {"id": "r1", "match": {"tool": "get_*"}, "decision": "allow"},
                {"id": "r2", "match": {"tool": "*"}, "decision": "deny"},
            ]
        )
    )
    d = engine.evaluate(EvalContext("gh", "get_repo"))
    assert d.kind == "allow" and d.rule_id == "r1"


def test_server_glob_matches():
    engine = PolicyEngine(
        _cfg(
            [
                {"id": "r1", "match": {"server": "git*", "tool": "*"}, "decision": "allow"},
            ]
        )
    )
    assert engine.evaluate(EvalContext("github", "x")).kind == "allow"
    assert engine.evaluate(EvalContext("gitlab", "x")).kind == "allow"
    assert engine.evaluate(EvalContext("bitbucket", "x")).kind == "deny"


def test_server_list_of_globs():
    engine = PolicyEngine(
        _cfg(
            [
                {"id": "r1", "match": {"server": ["gh", "gl"]}, "decision": "allow"},
            ]
        )
    )
    assert engine.evaluate(EvalContext("gh", "x")).kind == "allow"
    assert engine.evaluate(EvalContext("gl", "x")).kind == "allow"
    assert engine.evaluate(EvalContext("bb", "x")).kind == "deny"


def test_tool_list_of_globs():
    engine = PolicyEngine(
        _cfg([{"id": "r1", "match": {"tool": ["get_*", "list_*"]}, "decision": "allow"}])
    )
    assert engine.evaluate(EvalContext("x", "get_a")).kind == "allow"
    assert engine.evaluate(EvalContext("x", "list_b")).kind == "allow"
    assert engine.evaluate(EvalContext("x", "delete_c")).kind == "deny"


def test_args_exact_match():
    engine = PolicyEngine(
        _cfg(
            [
                {
                    "id": "no-force",
                    "match": {"tool": "push", "args": {"force": True}},
                    "decision": "deny",
                    "reason": "no force push",
                },
                {"id": "allow-push", "match": {"tool": "push"}, "decision": "allow"},
            ]
        )
    )
    assert engine.evaluate(EvalContext("gh", "push", {"force": True})).kind == "deny"
    assert engine.evaluate(EvalContext("gh", "push", {"force": False})).kind == "allow"
    assert engine.evaluate(EvalContext("gh", "push", {})).kind == "allow"


def test_args_nested_match():
    engine = PolicyEngine(
        _cfg(
            [
                {
                    "id": "r1",
                    "match": {"tool": "run", "args": {"opts": {"dangerous": True}}},
                    "decision": "deny",
                }
            ]
        )
    )
    assert engine.evaluate(EvalContext("x", "run", {"opts": {"dangerous": True, "n": 5}})).kind == "deny"
    assert engine.evaluate(EvalContext("x", "run", {"opts": {"dangerous": False}})).kind == "deny"  # no match -> default deny; still deny by default here
    assert engine.evaluate(EvalContext("x", "run", {"opts": {"n": 5}})).kind == "deny"


def test_args_extra_keys_ok():
    engine = PolicyEngine(
        _cfg([{"id": "r1", "match": {"args": {"a": 1}}, "decision": "allow"}])
    )
    assert engine.evaluate(EvalContext("x", "y", {"a": 1, "b": 2})).kind == "allow"


def test_escalate_carries_approval_and_controls():
    engine = PolicyEngine(
        _cfg(
            [
                {
                    "id": "r1",
                    "match": {"tool": "*"},
                    "decision": "escalate",
                    "controls": ["EU-AI-ACT-ART-14"],
                    "approval": {"channel": "cli", "timeout_seconds": 60, "on_timeout": "deny"},
                }
            ]
        )
    )
    d = engine.evaluate(EvalContext("gh", "push"))
    assert d.kind == "escalate"
    assert d.controls == ("EU-AI-ACT-ART-14",)
    assert d.approval is not None and d.approval.timeout_seconds == 60


def test_decision_with_verdict_only_on_escalate():
    from shugo.policy.engine import Decision

    d = Decision(kind="allow", rule_id="r1")
    with pytest.raises(ValueError):
        d.with_verdict("allow", None)


def test_decision_with_verdict_ok():
    from shugo.policy.engine import Decision

    d = Decision(kind="escalate", rule_id="r1")
    resolved = d.with_verdict("allow", approver="cli-user")
    assert resolved.kind == "allow"
    assert resolved.approver == "cli-user"
    assert resolved.rule_id == "r1"
