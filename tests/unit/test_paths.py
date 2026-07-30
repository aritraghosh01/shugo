from pathlib import Path

from shugo import paths


def test_shugo_home_respects_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SHUGO_HOME", str(tmp_path / "custom"))
    assert paths.shugo_home() == tmp_path / "custom"


def test_ensure_layout_creates_all_subdirs(monkeypatch, tmp_path):
    monkeypatch.setenv("SHUGO_HOME", str(tmp_path / "h"))
    home = paths.ensure_layout()
    for sub in ("pending", "approved", "denied", "timeout"):
        assert (home / sub).is_dir()


def test_helpers_point_inside_home(monkeypatch, tmp_path):
    monkeypatch.setenv("SHUGO_HOME", str(tmp_path / "h"))
    home = paths.shugo_home()
    assert paths.audit_log() == home / "audit.log"
    assert paths.halt_sentinel() == home / "HALT"
    assert paths.pending_dir() == home / "pending"
    assert paths.approved_dir() == home / "approved"
    assert paths.denied_dir() == home / "denied"
    assert paths.timeout_dir() == home / "timeout"
