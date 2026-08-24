"""Incident domain models and lifecycle rules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


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
TRANSITIONS = {
    Status.open: {Status.investigating},
    Status.investigating: {Status.mitigated, Status.resolved},
    Status.mitigated: {Status.resolved, Status.investigating},
    Status.resolved: set(),
}


class IncidentCreate(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    service: str = Field(min_length=2, max_length=60)
    severity: Severity
    owner: str | None = None


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

    @property
    def breached(self) -> bool:
        return self.status != Status.resolved and datetime.now(UTC) > self.sla_due_at


class StatusChange(BaseModel):
    status: Status


def create_incident(payload: IncidentCreate, actor: str, now: datetime | None = None) -> Incident:
    created = now or datetime.now(UTC)
    return Incident(
        id=f"INC-{uuid4().hex[:8].upper()}",
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
