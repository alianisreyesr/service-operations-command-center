from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import main
from app.repository import InMemoryIncidentRepository

FIXED_NOW = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)


class FakeClock:
    """Deterministic, advanceable clock injected into app.main."""

    def __init__(self) -> None:
        self.current = FIXED_NOW

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current += timedelta(**delta)


@pytest.fixture(autouse=True)
def clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    """Every test gets a fixed clock, a freshly seeded repository and an empty audit log."""
    fake = FakeClock()
    monkeypatch.setattr(main, "clock", fake)
    monkeypatch.setattr(main, "incidents", InMemoryIncidentRepository(main._seed()))
    main.AUDIT_EVENTS.clear()
    return fake


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(main.app) as test_client:
        yield test_client
