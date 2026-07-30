from pathlib import Path

import pytest

from shugo.errors import PolicyError
from shugo.policy.loader import load_config


def test_loads_starter_policy():
    p = Path(__file__).resolve().parents[2] / "policies" / "starter.yaml"
    cfg = load_config(p)
    assert cfg.version == "0.1"
    assert "github" in cfg.upstreams
    ids = [r.id for r in cfg.rules]
    assert ids == ["read-only-github", "no-force-push", "write-needs-approval"]


def test_missing_file_errors(tmp_path):
    with pytest.raises(PolicyError, match="not found"):
        load_config(tmp_path / "nope.yaml")


def test_empty_file_errors(tmp_path):
    p = tmp_path / "e.yaml"
    p.write_text("", encoding="utf-8")
    with pytest.raises(PolicyError, match="empty"):
        load_config(p)


def test_bad_yaml_errors(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text(": : : bad", encoding="utf-8")
    with pytest.raises(PolicyError, match="invalid YAML"):
        load_config(p)


def test_bad_schema_errors(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("version: '0.1'\nunknown_top_key: true\nupstreams: {}\nrules: []\n", encoding="utf-8")
    with pytest.raises(PolicyError, match="schema errors"):
        load_config(p)
