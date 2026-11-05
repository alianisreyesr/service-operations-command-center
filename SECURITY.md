# Security policy

## Reporting a vulnerability

Report vulnerabilities privately with GitHub Security Advisories ("Report a vulnerability" on the Security tab). Do not place exploit details, secrets, personal information, or real incident data in public issues. You can expect an acknowledgement within 7 days; this is a portfolio project maintained on a best-effort basis.

## Scope

In scope: the API (`app/`), the dashboard, the container image, and the CI configuration. Out of scope: findings that require real incident data (the project accepts fictional data only) and the production controls listed under "Known limitations".

## Supported versions

Only the latest commit on `main` is supported.

## Built-in safeguards

- User-supplied text rendered in the HTML view is escaped; blank and over-long fields are rejected with 422.
- The `X-Actor` header is limited to 1-64 characters. It is attribution for the demo, **not an authentication control** and can be spoofed.
- Pagination limits bound response size; the audit log is capped at 1000 events.
- The container runs as an unprivileged user (`65532`) and ships no secrets.
- CI runs CodeQL, secret scanning and `pip-audit` on runtime dependencies; Dependabot keeps dependencies and actions current.

## Known limitations

No authentication or authorization, no rate limiting, no CORS policy, no security headers (CSP), and state is held in memory. Do not expose this service to untrusted networks.
