"""FastAPI entry point for service operations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import HTMLResponse

from app.domain import Incident, IncidentCreate, OwnerChange, Severity, Status, StatusChange, create_incident, transition


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
AUDIT_EVENTS: list[dict[str, str]] = []


def _record(event: str, incident: Incident, actor: str, detail: str) -> None:
    AUDIT_EVENTS.append(
        {
            "event": event,
            "incident_id": incident.id,
            "actor": actor,
            "detail": detail,
            "occurred_at": datetime.now(UTC).isoformat(),
        }
    )


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    snapshot = metrics()
    queue = priority_queue()
    rows = "".join(
        f"<tr><td>{item['id']}</td><td>{item['title']}</td><td><span class='severity {item['severity']}'>{item['severity']}</span></td><td>{item['owner'] or 'Unassigned'}</td><td>{'Breached' if item['breached'] else 'On track'}</td></tr>"
        for item in queue
    )
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Service Operations Command Center</title><style>
:root{{--ink:#102a43;--muted:#627d98;--line:#d9e2ec;--blue:#1565c0;--bg:#f4f7fb;--danger:#c62828;--amber:#a15c00}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);font:15px Inter,system-ui;color:var(--ink)}}main{{max-width:1160px;margin:auto;padding:42px 28px}}
.eyebrow{{font-size:12px;text-transform:uppercase;letter-spacing:.12em;font-weight:800;color:var(--blue)}}h1{{font-size:38px;margin:8px 0}}.sub{{color:var(--muted);max-width:760px}}
.metrics{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:28px 0}}.card,.panel{{background:#fff;border:1px solid var(--line);border-radius:14px;box-shadow:0 8px 26px #102a430d}}
.card{{padding:18px}}.label{{color:var(--muted);font-size:12px;text-transform:uppercase}}.value{{font-size:28px;font-weight:800;margin-top:6px}}.panel{{padding:22px}}
h2{{margin:0 0 16px;font-size:18px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:13px 10px;border-bottom:1px solid var(--line);text-align:left}}th{{font-size:11px;text-transform:uppercase;color:var(--muted)}}
.severity{{font-weight:750;text-transform:capitalize;padding:5px 9px;border-radius:99px;background:#e3f2fd;color:var(--blue)}}.severity.high,.severity.critical{{background:#ffebee;color:var(--danger)}}.severity.medium{{background:#fff3e0;color:var(--amber)}}
footer{{font-size:12px;color:var(--muted);margin-top:18px}}@media(max-width:800px){{.metrics{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><main><div class='eyebrow'>Synthetic service operations</div><h1>Command Center</h1><p class='sub'>SLA-aware incident visibility with explicit ownership and explainable prioritization.</p>
<section class='metrics'><div class='card'><div class='label'>Total</div><div class='value'>{snapshot['total']}</div></div><div class='card'><div class='label'>Open</div><div class='value'>{snapshot['open']}</div></div><div class='card'><div class='label'>Breached</div><div class='value'>{snapshot['breached']}</div></div><div class='card'><div class='label'>Resolved</div><div class='value'>{snapshot['resolved']}</div></div><div class='card'><div class='label'>Unassigned</div><div class='value'>{snapshot['unassigned']}</div></div></section>
<section class='panel'><h2>Priority queue</h2><table><thead><tr><th>Incident</th><th>Summary</th><th>Severity</th><th>Owner</th><th>SLA state</th></tr></thead><tbody>{rows}</tbody></table></section>
<footer>Portfolio prototype · fictional incidents only · X-Actor demonstrates attribution, not authentication</footer></main></body></html>"""


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
    _record("incident.created", incident, x_actor, f"severity={incident.severity}")
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
    _record("incident.status_changed", updated, x_actor, f"{incident.status}->{updated.status}")
    return updated


@app.patch("/api/incidents/{incident_id}/owner", response_model=Incident)
def assign_owner(incident_id: str, payload: OwnerChange, x_actor: str = Header(default="portfolio-user")) -> Incident:
    incident = INCIDENTS.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    updated = incident.model_copy(update={"owner": payload.owner, "updated_by": x_actor})
    INCIDENTS[incident_id] = updated
    _record("incident.owner_assigned", updated, x_actor, f"owner={payload.owner}")
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


@app.get("/api/audit-events")
def audit_events() -> list[dict[str, str]]:
    return list(reversed(AUDIT_EVENTS))
