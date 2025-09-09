# CMS + etcd + OPA (MVP1 demo)

This minimal stack lets you update a policy via the CMS and see it stored in etcd and synced to OPA.

## Services
- etcd: key-value store (Bitnami image)
- OPA: policy engine (server mode)
- CMS: FastAPI service providing simple GET/PUT/PATCH for a single demo policy under /policies/projects/demo
- sync: tiny agent that watches etcd /policies/projects/demo and pushes rego+data to OPA

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
- The sync agent overwrites the OPA policy package named `demo` fully on each change.
- Adjust keys and packages later to match your full design (/policies/platform and per-project).
