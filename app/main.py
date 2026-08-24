"""FastAPI entry point for service operations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Header, HTTPException, status

from app.domain import Incident, IncidentCreate, Severity, Status, StatusChange, create_incident, transition


app = FastAPI(title="Service Operations Command Center", version="0.1.0")


def _seed() -> dict[str, Incident]:
    now = datetime.now(UTC)
    examples = [
        create_incident(IncidentCreate(title="Checkout latency above target", service="checkout", severity=Severity.high, owner="maya"), "synthetic-seed", now - timedelta(hours=6)),
        create_incident(IncidentCreate(title="Delayed inventory synchronization", service="inventory", severity=Severity.medium), "synthetic-seed", now - timedelta(hours=2)),
        create_incident(IncidentCreate(title="Customer portal image unavailable", service="portal", severity=Severity.low, owner="noah"), "synthetic-seed", now - timedelta(minutes=30)),
    ]
    return {item.id: item for item in examples}


INCIDENTS = _seed()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "data_boundary": "fictional portfolio data only"}


@app.get("/api/incidents", response_model=list[Incident])
def list_incidents() -> list[Incident]:
    return list(INCIDENTS.values())


@app.post("/api/incidents", response_model=Incident, status_code=status.HTTP_201_CREATED)
def add_incident(payload: IncidentCreate, x_actor: str = Header(default="portfolio-user")) -> Incident:
    incident = create_incident(payload, x_actor)
    INCIDENTS[incident.id] = incident
    return incident


@app.patch("/api/incidents/{incident_id}/status", response_model=Incident)
def update_status(incident_id: str, payload: StatusChange, x_actor: str = Header(default="portfolio-user")) -> Incident:
    incident = INCIDENTS.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    try:
        updated = transition(incident, payload.status, x_actor)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    INCIDENTS[incident_id] = updated
    return updated


@app.get("/api/incidents/priority-queue")
def priority_queue() -> list[dict[str, object]]:
    severity_rank = {Severity.critical: 0, Severity.high: 1, Severity.medium: 2, Severity.low: 3}
    active = [item for item in INCIDENTS.values() if item.status != Status.resolved]
    ordered = sorted(active, key=lambda item: (not item.breached, severity_rank[item.severity], item.sla_due_at))
    return [
        {
            "id": item.id,
            "title": item.title,
            "severity": item.severity,
            "owner": item.owner,
            "breached": item.breached,
            "sla_due_at": item.sla_due_at,
        }
        for item in ordered
    ]


@app.get("/api/metrics")
def metrics() -> dict[str, int]:
    incidents = list(INCIDENTS.values())
    return {
        "total": len(incidents),
        "open": sum(item.status != Status.resolved for item in incidents),
        "breached": sum(item.breached for item in incidents),
        "resolved": sum(item.status == Status.resolved for item in incidents),
        "unassigned": sum(item.owner is None and item.status != Status.resolved for item in incidents),
    }
