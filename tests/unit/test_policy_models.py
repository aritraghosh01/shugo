import pytest
from pydantic import ValidationError

from shugo.policy.models import Config, Rule


def _minimal(**overrides):
    base = {
        "version": "0.1",
        "upstreams": {"gh": {"command": "npx", "args": ["-y", "srv"]}},
        "rules": [],
    }
    base.update(overrides)
    return base


def test_minimal_config_validates():
    cfg = Config.model_validate(_minimal())
    assert cfg.version == "0.1"
    assert cfg.defaults.decision == "deny"
    assert cfg.defaults.on_error == "deny"


def test_unknown_top_level_key_rejected():
    with pytest.raises(ValidationError):
        Config.model_validate(_minimal(unknown_field=True))


def test_duplicate_rule_ids_rejected():
    with pytest.raises(ValidationError, match="duplicate rule id"):
        Config.model_validate(
            _minimal(
                rules=[
                    {"id": "r1", "match": {"tool": "*"}, "decision": "allow"},
                    {"id": "r1", "match": {"tool": "*"}, "decision": "deny"},
                ]
            )
        )


def test_escalate_without_approval_rejected():
    with pytest.raises(ValidationError, match="requires an approval block"):
        Config.model_validate(
            _minimal(
                rules=[{"id": "r1", "match": {"tool": "*"}, "decision": "escalate"}]
            )
        )


def test_escalate_with_approval_ok():
    cfg = Config.model_validate(
        _minimal(
            rules=[
                {
                    "id": "r1",
                    "match": {"tool": "*"},
                    "decision": "escalate",
                    "approval": {"channel": "cli", "timeout_seconds": 60},
                }
            ]
        )
    )
    assert cfg.rules[0].approval.timeout_seconds == 60


def test_rule_id_must_be_non_empty():
    with pytest.raises(ValidationError):
        Rule.model_validate({"id": "  ", "match": {}, "decision": "allow"})


def test_upstream_missing_command_rejected():
    with pytest.raises(ValidationError):
        Config.model_validate(
            {"version": "0.1", "upstreams": {"x": {"args": ["a"]}}, "rules": []}
        )
