# Changelog

All notable changes to this portfolio project are documented in this file.

The project follows semantic versioning for public portfolio releases. Version numbers describe the repository's software baseline; they do not indicate production readiness of the service.

## [Unreleased]

### Fixed

- Reject blank (whitespace-only) title, service and owner with 422, including empty owner on creation and owner change
- Limit `X-Actor` to 1-64 characters (422 otherwise)
- Version aligned with the application (`0.1.0`) and case-study test count corrected

### Changed

- CI now runs `ruff` and `mypy`, declares least-privilege `permissions`, and enforces `--cov-fail-under=90` (branch coverage, including `dashboard.py`)
- `pytest` and `httpx` moved from `requirements.txt` to `requirements-dev.txt`; `pydantic` declared explicitly; `streamlit>=1.49` (first release accepting `width="stretch"`, verified) and `pandas>=2.2,<4` aligned with the other portfolio projects
- Audit log is bounded (1000 events); `GET /api/incidents` is paginated (`limit`, `offset`, `X-Total-Count`)
- Incident ids use 12 hex characters instead of 8
- Priority queue is deterministic (ties by `created_at`, then `id`) and uses one clock reading per request; `severity_rank` is now the domain constant `SEVERITY_RANK`
- Time is read through an injectable clock; tests run with a fixed clock and isolated state
- Docs state that the Streamlit dashboard does not call the API; misleading `depends_on` removed from `docker-compose.yml`; Docker `HEALTHCHECK` added
- Dashboard no longer fails on an empty repository
- `.gitignore`, `CONTRIBUTING.md` and `SECURITY.md` expanded

### Added

- Tests for 404/422 paths, queue ordering and ties, SLA boundaries, audit ordering and bound, pagination, and state isolation

## [0.1.0] — 2026-08-27

### Added

- Incident intake with severity-based SLA targets
- Controlled status transitions and owner assignment
- Priority queue ordered by breach state, severity, and due time
- Portfolio-safe actor attribution on mutations (`X-Actor`)
- Reverse-chronological audit events for creation, assignment, and status changes
- Operational metrics for open, breached, resolved, and unassigned work
- FastAPI service with OpenAPI documentation and container packaging
- Interactive Python/Streamlit command center dashboard
- Automated test suite (`pytest`)

### Known limitations

- `X-Actor` header is attributable demo identification, not identity verification
- No OIDC/RBAC, PostgreSQL persistence, background workers, or notifications
- Synthetic data only; not a production ticketing or emergency-response system
