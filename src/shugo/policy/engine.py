from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Any, Literal

from shugo.policy.models import Approval, Config, Rule


DecisionKind = Literal["allow", "deny", "escalate"]


@dataclass(frozen=True)
class EvalContext:
    server: str
    tool: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    kind: DecisionKind
    rule_id: str | None
    reason: str | None = None
    controls: tuple[str, ...] = ()
    approval: Approval | None = None
    approver: str | None = None

    def with_verdict(self, verdict: DecisionKind, approver: str | None) -> "Decision":
        if self.kind != "escalate":
            raise ValueError("with_verdict only valid on an escalate decision")
        if verdict not in ("allow", "deny"):
            raise ValueError(f"invalid verdict: {verdict}")
        return Decision(
            kind=verdict,
            rule_id=self.rule_id,
            reason=self.reason,
            controls=self.controls,
            approval=self.approval,
            approver=approver,
        )


def _globs(field: str | list[str] | None) -> list[str] | None:
    if field is None:
        return None
    if isinstance(field, str):
        return [field]
    return list(field)


def _match_any(value: str, patterns: list[str] | None) -> bool:
    if patterns is None:
        return True
    return any(fnmatch.fnmatchcase(value, p) for p in patterns)


def _match_args(spec: dict[str, Any] | None, actual: dict[str, Any]) -> bool:
    """Nested equality: every key in `spec` must exist in `actual` with equal value.

    Nested dicts recurse; lists / scalars use `==`. Extra keys in `actual` are fine.
    """
    if spec is None:
        return True
    if not isinstance(actual, dict):
        return False
    for key, expected in spec.items():
        if key not in actual:
            return False
        got = actual[key]
        if isinstance(expected, dict):
            if not isinstance(got, dict) or not _match_args(expected, got):
                return False
        else:
            if got != expected:
                return False
    return True


def _rule_matches(rule: Rule, ctx: EvalContext) -> bool:
    if not _match_any(ctx.server, _globs(rule.match.server)):
        return False
    if not _match_any(ctx.tool, _globs(rule.match.tool)):
        return False
    if not _match_args(rule.match.args, ctx.args):
        return False
    return True


class PolicyEngine:
    def __init__(self, config: Config) -> None:
        self._config = config

    @property
    def config(self) -> Config:
        return self._config

    def evaluate(self, ctx: EvalContext) -> Decision:
        for rule in self._config.rules:
            if _rule_matches(rule, ctx):
                return Decision(
                    kind=rule.decision,
                    rule_id=rule.id,
                    reason=rule.reason,
                    controls=tuple(rule.controls),
                    approval=rule.approval,
                )
        return Decision(
            kind=self._config.defaults.decision,
            rule_id=None,
            reason="no rule matched; applied default decision",
        )
