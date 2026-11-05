from datetime import timedelta

from app import main
from app.domain import Incident, IncidentCreate, Severity, Status, create_incident
from app.repository import InMemoryIncidentRepository
from tests.conftest import FIXED_NOW

VALID = {"title": "Payment gateway response degraded", "service": "payments", "severity": "critical"}


def _create(client, **overrides):
    response = client.post("/api/incidents", json={**VALID, **overrides})
    assert response.status_code == 201
    return response.json()


def test_unknown_incident_returns_404_for_status_and_owner(client):
    status = client.patch("/api/incidents/INC-NOPE/status", json={"status": "investigating"})
    owner = client.patch("/api/incidents/INC-NOPE/owner", json={"owner": "sam"})
    assert status.status_code == owner.status_code == 404
    assert status.json()["detail"] == "Incident not found"


def test_invalid_payloads_return_422(client):
    assert client.post("/api/incidents", json={**VALID, "severity": "urgent"}).status_code == 422
    assert client.post("/api/incidents", json={"title": "Only a title"}).status_code == 422
    created = _create(client)
    assert client.patch(f"/api/incidents/{created['id']}/status", json={"status": "closed"}).status_code == 422
    assert client.patch(f"/api/incidents/{created['id']}/status", json={}).status_code == 422


def test_incident_ids_are_long_and_unique(client):
    ids = {_create(client)["id"] for _ in range(50)}
    assert len(ids) == 50
    assert all(len(i) == len("INC-") + 12 and i.startswith("INC-") for i in ids)


def test_sla_breach_follows_the_injected_clock(client, clock):
    created = _create(client, severity="critical")  # SLA 1h
    queue = {item["id"]: item for item in client.get("/api/incidents/priority-queue").json()}
    assert queue[created["id"]]["breached"] is False
    clock.advance(minutes=59)
    assert client.get("/api/metrics").json()["breached"] == 1  # only the seeded 6h-old high one
    clock.advance(minutes=2)
    assert client.get("/api/metrics").json()["breached"] == 2


def test_resolving_clears_breach_and_leaves_the_queue(client):
    seeded = client.get("/api/incidents/priority-queue").json()[0]
    for target in ("investigating", "resolved"):
        assert client.patch(f"/api/incidents/{seeded['id']}/status", json={"status": target}).status_code == 200
    queue_ids = [item["id"] for item in client.get("/api/incidents/priority-queue").json()]
    assert seeded["id"] not in queue_ids
    assert client.get("/api/metrics").json() == {"total": 3, "open": 2, "breached": 0, "resolved": 1, "unassigned": 1}


def test_priority_queue_orders_by_breach_then_severity_then_due_time(client, clock):
    # Seed: high (breached), medium, low. Add a critical (not yet due) and a second high.
    critical = _create(client, title="Critical newcomer", severity="critical")
    clock.advance(minutes=5)
    high = _create(client, title="Second high incident", severity="high")
    order = [item["id"] for item in client.get("/api/incidents/priority-queue").json()]
    titles = {i["id"]: i["title"] for i in client.get("/api/incidents").json()}
    assert [titles[i] for i in order] == [
        "Checkout latency above target",  # breached always first
        "Critical newcomer",  # then by severity
        "Second high incident",
        "Delayed inventory synchronization",
        "Customer portal image unavailable",
    ]
    assert order[1] == critical["id"] and order[2] == high["id"]


def test_priority_queue_ties_are_deterministic():
    """Identical severity and due time fall back to created_at, then id, in any storage order."""
    def make(title: str, ident: str) -> Incident:
        item = create_incident(IncidentCreate(title=title, service="svc", severity=Severity.low), "t", FIXED_NOW)
        return item.model_copy(update={"id": ident})

    first = [make("Alpha incident", "INC-A"), make("Bravo incident", "INC-B")]
    for stored in (first, list(reversed(first))):
        main.incidents = InMemoryIncidentRepository(stored)
        assert [item["id"] for item in main.priority_queue()] == ["INC-A", "INC-B"]


def test_audit_events_are_newest_first_with_clock_timestamps(client, clock):
    created = _create(client)
    clock.advance(minutes=1)
    client.patch(f"/api/incidents/{created['id']}/status", json={"status": "investigating"}, headers={"X-Actor": "ana"})
    clock.advance(minutes=1)
    client.patch(f"/api/incidents/{created['id']}/owner", json={"owner": "sam"}, headers={"X-Actor": "bo"})
    events = client.get("/api/audit-events").json()
    assert [e["event"] for e in events] == ["incident.owner_assigned", "incident.status_changed", "incident.created"]
    assert [e["actor"] for e in events] == ["bo", "ana", "portfolio-user"]
    assert events[0]["occurred_at"] == (FIXED_NOW + timedelta(minutes=2)).isoformat()
    assert events[1]["detail"] == "open->investigating"


def test_audit_log_is_bounded(client, monkeypatch):
    monkeypatch.setattr(main, "AUDIT_EVENTS", type(main.AUDIT_EVENTS)(maxlen=5))
    for index in range(8):
        _create(client, title=f"Incident number {index}")
    events = client.get("/api/audit-events").json()
    assert len(events) == 5
    assert main.AUDIT_MAX_EVENTS >= 100
    assert "number 7" in main.incidents.get(events[0]["incident_id"]).title


def test_incident_list_is_paginated(client):
    for index in range(4):
        _create(client, title=f"Extra incident {index}")  # 3 seeded + 4 = 7
    page = client.get("/api/incidents", params={"limit": 3, "offset": 0})
    assert page.status_code == 200 and len(page.json()) == 3
    assert page.headers["X-Total-Count"] == "7"
    second = client.get("/api/incidents", params={"limit": 3, "offset": 3}).json()
    last = client.get("/api/incidents", params={"limit": 3, "offset": 6}).json()
    everything = client.get("/api/incidents", params={"limit": 200}).json()
    assert [i["id"] for i in page.json() + second + last] == [i["id"] for i in everything]
    assert len(last) == 1
    assert client.get("/api/incidents", params={"offset": 99}).json() == []
    assert len(client.get("/api/incidents").json()) == 7  # default page covers the demo data


def test_pagination_bounds_are_validated(client):
    for params in ({"limit": 0}, {"limit": 201}, {"offset": -1}):
        assert client.get("/api/incidents", params=params).status_code == 422


def test_state_is_isolated_between_tests_first(client):
    _create(client, title="Leaks into other tests?")
    assert client.get("/api/metrics").json()["total"] == 4


def test_state_is_isolated_between_tests_second(client):
    assert client.get("/api/metrics").json()["total"] == 3
    assert client.get("/api/audit-events").json() == []


def test_transition_helper_and_rank_constants():
    item = create_incident(IncidentCreate(title="Rank check", service="svc", severity=Severity.high), "t", FIXED_NOW)
    assert not item.is_breached(FIXED_NOW + timedelta(hours=4))
    assert item.is_breached(FIXED_NOW + timedelta(hours=4, seconds=1))
    assert item.model_copy(update={"status": Status.resolved}).is_breached(FIXED_NOW + timedelta(days=9)) is False
    assert isinstance(item.breached, bool)
