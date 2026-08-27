# Changelog

All notable changes to this portfolio project are documented in this file.

The project follows semantic versioning for public portfolio releases. Version numbers describe the repository's software baseline; they do not indicate production readiness of the service.

## [1.0.0] — 2026-08-27

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
