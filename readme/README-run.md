# CMS + etcd + OPA (Bundle Architecture Demo)

This minimaExpected: true for admin role, false otherwise.

## Notes
- This is intentionally simple: one demo project, no auth, no TLS.
- CMS serves OPA bundles; OPA polls for updates every 15 seconds using ETag caching.
- Bundle polling is the production-standard method for policy distribution.
- Adjust keys and packages later to match your full design (/policies/platform and per-project).k demonstrates policy management with OPA bundle polling for near real-time updates.

## Services
- etcd: key-value store (Bitnami image)
- OPA: policy engine (server mode with bundle polling)
- CMS: FastAPI service providing policy CRUD API and OPA bundle endpoint

## Architecture
- CMS writes policies to etcd and serves bundles to OPA
- OPA polls CMS `/bundles/demo` endpoint every 15 seconds
- Policy updates propagate within 15-20 seconds (near real-time)
- ETag caching ensures efficient pollingtcd + OPA (MVP1 demo)

This minimal stack lets you update a policy via the CMS and see it stored in etcd and synced to OPA.

## Services
- etcd: key-value store (Bitnami image)
- OPA: policy engine (server mode)
- CMS: FastAPI service providing simple GET/PUT/PATCH for a single demo policy under /policies/projects/demo
- sync (optional, local-only): tiny helper that watches etcd /policies/projects/demo and pushes rego+data to OPA when OPA isn’t configured to watch etcd directly

## Run

1) Start the stack

```cmd
docker compose up --build -d
```

2) Seed a basic policy (allow only admin role)

```cmd
curl -s -X PUT http://localhost:8080/policies/demo ^
  -H "Content-Type: application/json" ^
  -d "{\"rego\": \"package demo\n\nimport input\n\nallow { input.user.role == \"admin\" }\", \"data\": {\"valid_roles\": [\"admin\"]}}"
```

3) Verify in etcd (policy keys present)

```cmd
docker compose exec etcd /opt/bitnami/etcd/bin/etcdctl get --keys-only --prefix /policies/projects/demo
```

4) Verify in OPA (policy and data loaded)

```cmd
curl -s http://localhost:8181/v1/policies | jq .
curl -s http://localhost:8181/v1/data/demo | jq .
```

5) Exercise a decision

```cmd
curl -s -X POST http://localhost:8181/v1/data/demo/allow ^
  -H "Content-Type: application/json" ^
  -d "{\"input\": {\"user\": {\"role\": \"admin\"}}}"
```

Expected: true for admin role, false otherwise.

## Notes
- This is intentionally simple: one demo project, no auth, no TLS.
- CMS only writes to etcd. In production, OPA consumes updates via an etcd watch/bundle workflow. For local demo, the optional sync helper simulates that behavior if your OPA isn’t wired to watch etcd.
- Adjust keys and packages later to match your full design (/policies/platform and per-project).
