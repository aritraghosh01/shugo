from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


VerdictKind = Literal["allow", "deny", "timeout"]


@dataclass(frozen=True)
class Verdict:
    kind: VerdictKind
    approver: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class PendingApproval:
    id: str
    ts: str
    server: str
    tool: str
    args: dict[str, Any]
    rule_id: str | None
    reason: str | None
    timeout_s: int
    pid: int
    controls: tuple[str, ...] = field(default_factory=tuple)


class ApprovalChannel(Protocol):
    async def request(self, pending: PendingApproval) -> Verdict: ...
