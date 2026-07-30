import os
from pathlib import Path


def shugo_home() -> Path:
    override = os.environ.get("SHUGO_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".shugo"


def ensure_layout() -> Path:
    home = shugo_home()
    for sub in ("pending", "approved", "denied", "timeout"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    return home


def audit_log() -> Path:
    return shugo_home() / "audit.log"


def halt_sentinel() -> Path:
    return shugo_home() / "HALT"


def pending_dir() -> Path:
    return shugo_home() / "pending"


def approved_dir() -> Path:
    return shugo_home() / "approved"


def denied_dir() -> Path:
    return shugo_home() / "denied"


def timeout_dir() -> Path:
    return shugo_home() / "timeout"
