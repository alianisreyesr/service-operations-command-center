# Architecture

```mermaid
flowchart LR
  A["Streamlit operations dashboard"] --> D["Incident domain model"]
  B["API clients"] --> C["FastAPI interface"]
  C --> D
  D --> E["Repository boundary"]
  E --> F["In-memory demonstration adapter"]
  C --> G["Metrics and priority endpoints"]
  G --> A
```

## Layers

1. **HTTP interface:** FastAPI request validation, response models, and status semantics.
2. **Domain:** incident creation, SLA targets, and permitted transitions.
3. **Repository adapter:** in-memory demonstration store, replaceable by PostgreSQL.
4. **Decision endpoints:** priority queue and operational metrics.

## Production roadmap

```mermaid
flowchart LR
  A["OIDC and organization RBAC"] --> B["FastAPI service"]
  B --> C["PostgreSQL and Alembic"]
  B --> D["Redis escalation workers"]
  B --> E["Python operations dashboard"]
  F["OpenTelemetry"] -. observes .-> B
  F -. observes .-> D
  G["Contract, load, accessibility, and end-to-end tests"] -. validates .-> B
  G -. validates .-> E
```
