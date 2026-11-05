"""Incident domain models and lifecycle rules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, StringConstraints


class Severity(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class Status(StrEnum):
    open = "open"
    investigating = "investigating"
    mitigated = "mitigated"
    resolved = "resolved"


SLA_HOURS = {Severity.critical: 1, Severity.high: 4, Severity.medium: 12, Severity.low: 24}
# Lower rank = more urgent. Used to order the priority queue.
SEVERITY_RANK = {Severity.critical: 0, Severity.high: 1, Severity.medium: 2, Severity.low: 3}
TRANSITIONS = {
    Status.open: {Status.investigating},
    Status.investigating: {Status.mitigated, Status.resolved},
    Status.mitigated: {Status.resolved, Status.investigating},
    Status.resolved: set(),
}


# Whitespace is stripped before length checks so blank values are rejected (422).
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=120)]
Service = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)]
Owner = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]


class IncidentCreate(BaseModel):
    title: Title
    service: Service
    severity: Severity
    owner: Owner | None = None


class Incident(BaseModel):
    id: str
    title: str
    service: str
    severity: Severity
    status: Status
    owner: str | None
    created_at: datetime
    sla_due_at: datetime
    updated_by: str

    def is_breached(self, now: datetime | None = None) -> bool:
        """SLA state at ``now`` (injectable so callers and tests can use a fixed clock)."""
        return self.status != Status.resolved and (now or datetime.now(UTC)) > self.sla_due_at

    @property
    def breached(self) -> bool:
        return self.is_breached()


class StatusChange(BaseModel):
    status: Status


class OwnerChange(BaseModel):
    owner: Owner


def create_incident(payload: IncidentCreate, actor: str, now: datetime | None = None) -> Incident:
    created = now or datetime.now(UTC)
    return Incident(
        # 12 hex chars = 48 bits: collisions are negligible at demo scale (8 hex was 32 bits).
        id=f"INC-{uuid4().hex[:12].upper()}",
        title=payload.title,
        service=payload.service,
        severity=payload.severity,
        status=Status.open,
        owner=payload.owner,
        created_at=created,
        sla_due_at=created + timedelta(hours=SLA_HOURS[payload.severity]),
        updated_by=actor,
    )


def transition(incident: Incident, target: Status, actor: str) -> Incident:
    if target not in TRANSITIONS[incident.status]:
        raise ValueError(f"Invalid transition: {incident.status} -> {target}")
    return incident.model_copy(update={"status": target, "updated_by": actor})
