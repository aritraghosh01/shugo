from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from shugo.audit.log import SEED_HASH, _hash_entry


@dataclass
class VerifyResult:
    ok: bool
    entries: int
    error: str | None = None
    error_line: int | None = None


def verify_log(path: str | Path) -> VerifyResult:
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return VerifyResult(ok=True, entries=0)

    prev = SEED_HASH
    count = 0
    with p.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                return VerifyResult(ok=False, entries=count, error=f"invalid JSON: {e}", error_line=lineno)

            if entry.get("prev_hash") != prev:
                return VerifyResult(
                    ok=False,
                    entries=count,
                    error=f"prev_hash mismatch (expected {prev}, got {entry.get('prev_hash')})",
                    error_line=lineno,
                )

            stored = entry.get("this_hash")
            recomputed = _hash_entry(entry, prev)
            if stored != recomputed:
                return VerifyResult(
                    ok=False,
                    entries=count,
                    error=f"this_hash mismatch (stored {stored}, recomputed {recomputed})",
                    error_line=lineno,
                )
            prev = stored
            count += 1
    return VerifyResult(ok=True, entries=count)
