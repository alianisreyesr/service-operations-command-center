from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_declares_portfolio_boundary():
    response = client.get("/health")
    assert response.status_code == 200
    assert "fictional" in response.json()["data_boundary"]


def test_create_incident_calculates_sla_and_actor():
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


def test_invalid_status_transition_is_rejected():
    incident = client.post(
        "/api/incidents",
        json={"title": "Search response time elevated", "service": "search", "severity": "medium"},
    ).json()
    response = client.patch(f"/api/incidents/{incident['id']}/status", json={"status": "resolved"})
    assert response.status_code == 409


def test_priority_queue_places_breached_work_first():
    response = client.get("/api/incidents/priority-queue")
    assert response.status_code == 200
    queue = response.json()
    assert queue
    assert queue[0]["breached"] is True


def test_metrics_expose_workload():
    metrics = client.get("/api/metrics").json()
    assert metrics["total"] >= 3
    assert metrics["open"] >= 1
    assert metrics["unassigned"] >= 1
