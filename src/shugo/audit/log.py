from __future__ import annotations

import copy
import hashlib
import json
import os
import threading
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from shugo.errors import AuditError

SEED_HASH = "0" * 64
_HASH_FIELD = "this_hash"
_PREV_FIELD = "prev_hash"


def _normalize(obj: Any) -> Any:
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {_normalize(k): _normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    if isinstance(obj, tuple):
        return [_normalize(v) for v in obj]
    return obj


def canonical_json(obj: Any) -> bytes:
    """Deterministic JSON encoding: sorted keys, no whitespace, NFC-normalized strings, UTF-8."""
    return json.dumps(
        _normalize(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _hash_entry(entry: dict[str, Any], prev_hash: str) -> str:
    payload = {k: v for k, v in entry.items() if k != _HASH_FIELD}
    payload[_PREV_FIELD] = prev_hash
    h = hashlib.sha256()
    h.update(prev_hash.encode("ascii"))
    h.update(canonical_json(payload))
    return h.hexdigest()


def _apply_redaction(args: Any, paths: Iterable[str]) -> Any:
    """Return a deep copy of args with the given dotted paths replaced by '***'.

    Paths use dot-separated keys; list indices are not supported in v0.1.
    """
    out = copy.deepcopy(args)
    for dotted in paths:
        keys = dotted.split(".")
        cur = out
        for key in keys[:-1]:
            if not isinstance(cur, dict) or key not in cur:
                cur = None
                break
            cur = cur[key]
        if isinstance(cur, dict) and keys[-1] in cur:
            cur[keys[-1]] = "***"
    return out


def redact(args: Any, paths: Iterable[str]) -> Any:
    return _apply_redaction(args, paths)


def _read_chain_head(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return SEED_HASH
    try:
        with path.open("rb") as f:
            last = b""
            for line in f:
                stripped = line.strip()
                if stripped:
                    last = stripped
            if not last:
                return SEED_HASH
            entry = json.loads(last)
            h = entry.get(_HASH_FIELD)
            if not isinstance(h, str) or len(h) != 64:
                raise AuditError(f"corrupt last-entry hash in {path}")
            return h
    except (OSError, json.JSONDecodeError) as e:
        raise AuditError(f"cannot read audit log {path}: {e}") from e


class AuditLog:
    """Append-only JSONL log with a rolling SHA-256 hash chain.

    Thread-safe (single-process). One line per entry. Redaction is applied
    before hashing so the stored record and its hash agree.
    """

    def __init__(self, path: str | Path, *, redact_paths: Iterable[str] = ()) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._redact_paths = tuple(redact_paths)
        self._lock = threading.Lock()
        self._prev_hash = _read_chain_head(self._path)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def head(self) -> str:
        return self._prev_hash

    def build(
        self,
        *,
        request_id: str,
        server: str,
        tool: str,
        args: dict[str, Any],
        decision: str,
        matched_rule_id: str | None,
        reason: str | None = None,
        controls: Iterable[str] = (),
        approver: str | None = None,
        ts: str | None = None,
    ) -> dict[str, Any]:
        args_redacted = _apply_redaction(args, self._redact_paths)
        return {
            "ts": ts or datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            "request_id": request_id,
            "server": server,
            "tool": tool,
            "args_redacted": args_redacted,
            "decision": decision,
            "matched_rule_id": matched_rule_id,
            "reason": reason,
            "controls": list(controls),
            "approver": approver,
        }

    def append(self, entry: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            this_hash = _hash_entry(entry, self._prev_hash)
            record = dict(entry)
            record[_PREV_FIELD] = self._prev_hash
            record[_HASH_FIELD] = this_hash
            line = json.dumps(record, ensure_ascii=False, sort_keys=True)
            with self._path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(line + "\n")
                f.flush()
                try:
                    os.fsync(f.fileno())
                except (OSError, AttributeError):
                    pass
            self._prev_hash = this_hash
            return record

    def tail(self, n: int = 20) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        with self._path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        return [json.loads(line) for line in lines[-n:]]
