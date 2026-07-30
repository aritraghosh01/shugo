from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any

import yaml

from shugo.audit.verify import verify_log
from shugo.errors import ShugoError
from shugo.policy.loader import load_config

_MAPPINGS_DIR = Path(__file__).parent / "mappings"


def list_frameworks() -> list[str]:
    return sorted(p.stem for p in _MAPPINGS_DIR.glob("*.yaml"))


def load_framework(name: str) -> dict[str, Any]:
    path = _MAPPINGS_DIR / f"{name}.yaml"
    if not path.exists():
        raise ShugoError(f"unknown framework {name!r}; try one of: {', '.join(list_frameworks())}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


_DURATION_RE = re.compile(r"^(\d+)([dhm])$")


def _parse_since(since: str) -> datetime:
    """Accepts 'Nd' / 'Nh' / 'Nm' or an ISO date/datetime."""
    m = _DURATION_RE.match(since.strip())
    if m:
        n, unit = int(m.group(1)), m.group(2)
        delta = {"d": timedelta(days=n), "h": timedelta(hours=n), "m": timedelta(minutes=n)}[unit]
        return datetime.now(timezone.utc) - delta
    try:
        dt = datetime.fromisoformat(since)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise ShugoError(f"cannot parse --since {since!r}; use e.g. 30d, 12h, or YYYY-MM-DD")


@dataclass
class BundleResult:
    out_dir: Path
    framework: str
    entries_scanned: int
    entries_in_window: int
    controls_total: int
    controls_matched: int
    files_written: list[Path] = field(default_factory=list)


def _entry_matches_control(entry: dict, control_id: str, all_rule_ids_for_control: set[str]) -> bool:
    if entry.get("matched_rule_id") in all_rule_ids_for_control:
        return True
    controls = entry.get("controls") or []
    return control_id in controls


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_bundle(
    *,
    framework: str,
    since: str,
    out_dir: Path,
    policy_path: Path,
    audit_path: Path,
) -> BundleResult:
    fw = load_framework(framework)
    cfg = load_config(policy_path)
    since_dt = _parse_since(since)

    # Rule -> controls index
    controls_by_rule: dict[str, list[str]] = {}
    for rule in cfg.rules:
        controls_by_rule[rule.id] = list(rule.controls)

    # Filter audit log to window and (optionally) verify integrity along the way.
    window_entries: list[dict] = []
    scanned = 0
    if audit_path.exists():
        with audit_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                scanned += 1
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                try:
                    ts = datetime.fromisoformat(e.get("ts", ""))
                except ValueError:
                    continue
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= since_dt:
                    window_entries.append(e)

    verify_result = verify_log(audit_path)

    # Per-control statistics.
    controls_report: list[dict[str, Any]] = []
    controls_matched = 0
    for ctrl in fw.get("controls", []):
        ctrl_id = ctrl["id"]
        matching_rule_ids = {
            rid for rid, ctrls in controls_by_rule.items() if ctrl_id in ctrls
        }
        matching_entries = [e for e in window_entries if _entry_matches_control(e, ctrl_id, matching_rule_ids)]
        approved = [e for e in matching_entries if e.get("approver")]
        denies = [e for e in matching_entries if e.get("decision") == "deny"]
        latencies_ms: list[float] = []  # v0.1 doesn't record approval latency; leave empty for now
        controls_report.append(
            {
                "id": ctrl_id,
                "title": ctrl["title"],
                "matched_rule_ids": sorted(matching_rule_ids),
                "fire_count": len(matching_entries),
                "approval_count": len(approved),
                "deny_count": len(denies),
                "latency_p50_ms": (median(latencies_ms) if latencies_ms else None),
                "shugo_evidence": ctrl.get("shugo_evidence", []),
            }
        )
        if matching_rule_ids or matching_entries:
            controls_matched += 1

    # Emit bundle files.
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    bundle_dir = out_dir / f"{framework}-{date_tag}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # rules.yaml — snapshot of the policy in force during the window.
    rules_out = bundle_dir / "rules.yaml"
    rules_out.write_text(policy_path.read_text(encoding="utf-8"), encoding="utf-8")

    # audit-window.jsonl — filtered entries.
    audit_out = bundle_dir / "audit-window.jsonl"
    with audit_out.open("w", encoding="utf-8", newline="\n") as f:
        for e in window_entries:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    # report.md
    report_out = bundle_dir / "report.md"
    lines: list[str] = []
    lines.append(f"# SHUGO evidence bundle — {fw['framework']} {fw.get('version', '')}")
    lines.append("")
    lines.append(
        "> **Scope note.** SHUGO produces evidence *about the guardrail layer*. "
        "It does not certify an organisation as compliant with any standard."
    )
    lines.append("")
    lines.append(f"- Source URL: {fw.get('source_url', '-')}")
    lines.append(f"- Window: since `{since}` ({since_dt.isoformat()})")
    lines.append(f"- Policy: `{policy_path.name}` ({len(cfg.rules)} rules, {len(cfg.upstreams)} upstreams)")
    lines.append(f"- Audit log: {audit_path} — scanned {scanned}, in window {len(window_entries)}")
    lines.append(
        f"- Log integrity: {'OK' if verify_result.ok else 'FAIL'} "
        f"({verify_result.entries} entries)"
    )
    lines.append(
        f"- Coverage: {controls_matched}/{len(controls_report)} controls have matched rules or audit evidence"
    )
    if fw.get("disclaimer"):
        lines.append("")
        lines.append("## Disclaimer")
        lines.append(fw["disclaimer"].strip())
    lines.append("")
    lines.append("## Controls")
    lines.append("")
    lines.append("| Control | Title | Matched rules | Fires | Approvals | Denies |")
    lines.append("|---|---|---|---|---|---|")
    for c in controls_report:
        rules_str = ", ".join(c["matched_rule_ids"]) or "—"
        lines.append(
            f"| `{c['id']}` | {c['title']} | {rules_str} | {c['fire_count']} | "
            f"{c['approval_count']} | {c['deny_count']} |"
        )
    gaps = [c for c in controls_report if not c["matched_rule_ids"] and c["fire_count"] == 0]
    if gaps:
        lines.append("")
        lines.append("## Coverage gaps")
        lines.append("")
        for g in gaps:
            lines.append(f"- `{g['id']}` — {g['title']}")
    report_out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # manifest.json — SHA-256 of each file for tamper detection of the bundle itself.
    manifest_out = bundle_dir / "manifest.json"
    manifest = {
        "framework": fw["framework"],
        "framework_version": fw.get("version"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "since": since,
        "files": {
            "report.md": _sha256_file(report_out),
            "rules.yaml": _sha256_file(rules_out),
            "audit-window.jsonl": _sha256_file(audit_out),
        },
        "audit_log_verify": {
            "ok": verify_result.ok,
            "entries": verify_result.entries,
            "error": verify_result.error,
        },
    }
    manifest_out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return BundleResult(
        out_dir=bundle_dir,
        framework=fw["framework"],
        entries_scanned=scanned,
        entries_in_window=len(window_entries),
        controls_total=len(controls_report),
        controls_matched=controls_matched,
        files_written=[report_out, rules_out, audit_out, manifest_out],
    )
