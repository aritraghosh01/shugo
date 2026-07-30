from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict
from pathlib import Path

from shugo import paths
from shugo.approval.channel import PendingApproval, Verdict


POLL_INTERVAL_SEC = 0.25


class FileApprovalChannel:
    """Approval channel backed by a filesystem queue under ~/.shugo/.

    The proxy writes `pending/<uuid>.json`. An operator (sidecar TUI or
    one-shot CLI) moves the file into `approved/`, `denied/`, or
    `timeout/`. This channel polls those directories until a verdict lands
    or the timeout expires.

    Atomicity: writes go to a `.tmp` file then `os.replace` — cross-platform
    atomic. Verdicts are moved via `os.replace` too, so double-approve is
    resolved by whoever wins the rename.
    """

    def __init__(self, home: Path | None = None) -> None:
        self._home = home or paths.shugo_home()
        for sub in ("pending", "approved", "denied", "timeout"):
            (self._home / sub).mkdir(parents=True, exist_ok=True)

    async def request(self, pending: PendingApproval) -> Verdict:
        pending_path = self._home / "pending" / f"{pending.id}.json"
        tmp_path = self._home / "pending" / f".{pending.id}.json.tmp"
        payload = asdict(pending)
        payload["controls"] = list(pending.controls)
        tmp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        os.replace(tmp_path, pending_path)

        loop = asyncio.get_running_loop()
        deadline = loop.time() + pending.timeout_s

        while True:
            if not pending_path.exists():
                # Someone else moved it — figure out where.
                approved = self._home / "approved" / f"{pending.id}.json"
                denied = self._home / "denied" / f"{pending.id}.json"
                if approved.exists():
                    return _verdict_from(approved, "allow")
                if denied.exists():
                    return _verdict_from(denied, "deny")
                # Race window between rename source/target existence — retry.
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue

            if loop.time() >= deadline:
                timeout_path = self._home / "timeout" / f"{pending.id}.json"
                try:
                    os.replace(pending_path, timeout_path)
                except FileNotFoundError:
                    # Just got picked up — loop once more to find verdict.
                    continue
                return Verdict(kind="timeout")

            await asyncio.sleep(POLL_INTERVAL_SEC)


def _verdict_from(path: Path, kind: str) -> Verdict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    return Verdict(
        kind=kind,  # type: ignore[arg-type]
        approver=data.get("_approver"),
        note=data.get("_note"),
    )


def apply_verdict(
    home: Path,
    approval_id: str,
    kind: str,
    approver: str | None = None,
    note: str | None = None,
) -> Path:
    """Move pending/<id>.json to approved|denied/<id>.json with optional metadata.

    Returns the destination path. Raises FileNotFoundError if the pending
    request has already been resolved (or never existed).
    """
    assert kind in ("allow", "deny")
    dest_dir = "approved" if kind == "allow" else "denied"
    src = home / "pending" / f"{approval_id}.json"
    dest = home / dest_dir / f"{approval_id}.json"
    data = json.loads(src.read_text(encoding="utf-8"))  # may raise FileNotFoundError
    if approver is not None:
        data["_approver"] = approver
    if note is not None:
        data["_note"] = note
    tmp = home / dest_dir / f".{approval_id}.json.tmp"
    tmp.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    os.replace(tmp, dest)
    try:
        os.remove(src)
    except FileNotFoundError:
        pass
    return dest


def list_pending(home: Path) -> list[dict]:
    pending_dir = home / "pending"
    if not pending_dir.exists():
        return []
    out = []
    for p in sorted(pending_dir.glob("*.json")):
        if p.name.startswith("."):
            continue
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return out
