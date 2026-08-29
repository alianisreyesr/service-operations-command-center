"""Repository boundary for incident persistence.

The HTTP layer (app/main.py) and domain rules (app/domain.py) talk only to
this interface, never to a storage mechanism directly — the documented
intent (README.md / docs/ARCHITECTURE.md) is that a PostgreSQL-backed
implementation of IncidentRepository can replace InMemoryIncidentRepository
without any change to route handlers or business rules. Previously this
boundary was only a diagram: app/main.py held a bare module-level dict and
mutated it directly, so nothing actually depended on this interface.
"""
from __future__ import annotations

from typing import Protocol

from app.domain import Incident


class IncidentRepository(Protocol):
    def get(self, incident_id: str) -> Incident | None: ...

    def list(self) -> list[Incident]: ...

    def save(self, incident: Incident) -> None: ...


class InMemoryIncidentRepository:
    """Demonstration adapter — synthetic, process-local storage only."""

    def __init__(self, seed: list[Incident] | None = None) -> None:
        self._items: dict[str, Incident] = {item.id: item for item in (seed or [])}

    def get(self, incident_id: str) -> Incident | None:
        return self._items.get(incident_id)

    def list(self) -> list[Incident]:
        return list(self._items.values())

    def save(self, incident: Incident) -> None:
        self._items[incident.id] = incident
