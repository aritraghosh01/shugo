from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Match(BaseModel):
    model_config = ConfigDict(extra="forbid")

    server: str | list[str] | None = None
    tool: str | list[str] | None = None
    args: dict[str, Any] | None = None


class Approval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["cli"] = "cli"
    timeout_seconds: int = Field(default=300, ge=1)
    on_timeout: Literal["allow", "deny"] = "deny"


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    description: str | None = None
    match: Match
    decision: Literal["allow", "deny", "escalate"]
    reason: str | None = None
    controls: list[str] = Field(default_factory=list)
    approval: Approval | None = None

    @field_validator("id")
    @classmethod
    def _id_shape(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("rule id must be non-empty")
        return stripped


class Defaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["allow", "deny"] = "deny"
    on_error: Literal["allow", "deny"] = "deny"


class UpstreamSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str = Field(min_length=1)
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal["0.1"]
    defaults: Defaults = Field(default_factory=Defaults)
    upstreams: dict[str, UpstreamSpec] = Field(default_factory=dict)
    rules: list[Rule] = Field(default_factory=list)
    redact: list[str] = Field(default_factory=list)

    @field_validator("rules")
    @classmethod
    def _unique_rule_ids(cls, v: list[Rule]) -> list[Rule]:
        seen: set[str] = set()
        for r in v:
            if r.id in seen:
                raise ValueError(f"duplicate rule id: {r.id}")
            seen.add(r.id)
        return v

    @field_validator("rules")
    @classmethod
    def _escalate_requires_approval(cls, v: list[Rule]) -> list[Rule]:
        for r in v:
            if r.decision == "escalate" and r.approval is None:
                raise ValueError(
                    f"rule {r.id!r}: decision=escalate requires an approval block"
                )
        return v
