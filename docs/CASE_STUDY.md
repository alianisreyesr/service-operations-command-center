# Case study: operational clarity for service teams

## Problem

Teams lose time when incident priority, ownership, and SLA state are implicit in chat messages or inconsistent ticket fields. Leaders also struggle to distinguish total volume from actionable risk.

## Product response

The API centralizes incident intake and uses explicit severity-to-SLA rules. A priority queue elevates breached work before severity and due time. Operational metrics distinguish open, breached, resolved, and unassigned incidents.

## Engineering decisions

- Business transitions live in the domain module, not route handlers.
- Invalid lifecycle shortcuts return `409 Conflict` rather than silently changing state.
- Mutations capture a portfolio actor for inspectable behavior without claiming authentication.
- Assignment and lifecycle changes generate reverse-chronological audit events.
- The repository boundary makes future PostgreSQL persistence a replaceable adapter.
- Tests exercise business behavior through the public HTTP contract.

## Verified result

Seven automated tests verify the public health boundary, recruiter-facing dashboard, incident creation, severity-based SLA calculation, invalid transition rejection, attributable owner assignment, audit history, priority ordering, and workload metrics.

## Limitations

The initial portfolio release uses an in-memory adapter and a synthetic seed. Production evolution includes identity, tenant isolation, durable persistence, notifications, background jobs, operational telemetry, and recovery testing.
