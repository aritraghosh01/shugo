from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from shugo.errors import PolicyError
from shugo.policy.models import Config


def load_config(path: str | Path) -> Config:
    p = Path(path)
    if not p.exists():
        raise PolicyError(f"policy file not found: {p}")
    try:
        raw: Any = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise PolicyError(f"invalid YAML in {p}: {e}") from e
    if raw is None:
        raise PolicyError(f"policy file {p} is empty")
    if not isinstance(raw, dict):
        raise PolicyError(f"policy root must be a mapping, got {type(raw).__name__}")
    try:
        return Config.model_validate(raw)
    except ValidationError as e:
        raise PolicyError(f"policy schema errors in {p}:\n{e}") from e
