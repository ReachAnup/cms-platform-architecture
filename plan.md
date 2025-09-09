# MVP1 Local Setup Plan (Windows Laptop) — CMS + RAG with APISIX, OPA, etcd, AWS SSM

This plan aligns with `readme19.md` and your choices:
- Secrets: AWS Systems Manager Parameter Store (Standard) in ap-south-1 (Mumbai)
- DB: MongoDB Atlas M0 (you’ll share the SRV URI)
- Ingress: APISIX from the Apache GitHub repo (required); Docker fallback only if needed
- AuthZ: OPA; policies stored in etcd; propagation via etcd→OPA watcher sync (separate process)
- Security: TLS at APISIX; mTLS from APISIX→CMS and APISIX→OPA (others HTTP)
- No Kubernetes; Docker for local services is acceptable; production uses VMs

---

## 1) Objectives & Scope
- Stand up a single-DC dev stack on a laptop to validate: APISIX → OPA decisioning, CMS policy writes to etcd, real-time propagation to OPA via etcd watch, JWT validation, and mTLS to upstreams.
- Keep APISIX stateless; fetch secrets via a helper (llm-proxy later, not in first cut).

---

## 2) Requirements
- Windows 10/11 with admin rights
- Docker Desktop with WSL2 backend (8–10 GB free RAM)
- Git, curl, OpenSSL
- AWS CLI v2 configured for region ap-south-1 (Mumbai)
- Optional: Python 3.11+ (for small helpers if we run them outside Docker; otherwise all in Docker)

---

## 3) Service Topology (local)
- APISIX (prefer repo build; Docker fallback for speed)
- etcd (policies + APISIX config)
- OPA (HTTP 8181)
- CMS (FastAPI; 8001)
- etcd-opa-sync (Python; watches /policies/ → pushes to OPA)
- MongoDB: Atlas M0 (preferred) or local Mongo container (fallback)
- JWKS server (static JWKS over HTTP 8081)
- TLS/mTLS CA + certs (self-signed) for APISIX→CMS/OPA
- (Later) llm-proxy to fetch API keys from SSM for hairpin calls

---

## 4) Ports (proposed)
- APISIX: 9080 (HTTP), 9443 (HTTPS)
- OPA: 8181
- CMS: 8001
- etcd: 2379
- JWKS: 8081
- Mongo (local fallback): 27017

Please flag any port conflicts.

---

## 5) Secrets — AWS SSM Parameter Store (Standard)
Region: ap-south-1

Parameter type: String (free)

Parameter paths (Standard tier):
- /cms/atlas/uri → MongoDB Atlas SRV URI (string)
- /cms/jwt/private_pem → PEM-encoded RSA private key (string)
- /cms/jwks/json → JWKS public JSON (string)
- /cms/opa/admin_token → Optional OPA management token (string)
- /cms/llm/api_key → Reserved for later (string)

Notes
- To remain strictly free, use `String` parameters (no KMS). If you want encryption at rest, use `SecureString` with AWS-managed KMS (may incur tiny KMS request charges).
- IAM policy (read-only) to attach to your dev identity/instance profile:

SSM read-only policy (replace ACCOUNT and REGION):
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParameterHistory"
      ],
      "Resource": "arn:aws:ssm:REGION:ACCOUNT:parameter/cms/*"
    }
  ]
}

Runtime usage
- Helpers (cms or a tiny secrets fetcher) will call AWS SDK to read parameters at startup and cache them in-memory.

MongoDB Atlas SRV URI (provided)
```
mongodb+srv://datadriven_db_user:<db_password>@cluster0.suu7js2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
```
Store this value at `/cms/atlas/uri` (SSM String). Replace `<db_password>` with your password (URL-encode special characters, e.g., @ -> %40).

---

## 6) TLS/mTLS Plan
- Generate a local CA and issue certs for CMS and OPA server names.
- APISIX will be configured with `lua_ssl_trusted_certificate` to trust the CA.
- Upstreams (CMS, OPA) will require client certs from APISIX (mTLS). We’ll generate APISIX client certs signed by the same CA.

Deliverables
- scripts/tls/gen_certs.ps1|sh → CA + server/client certs
- configs/apisix/ssl.conf → references CA bundle

---

## 7) JWT/JWKS Plan
- Generate RSA keypair.
- Serve JWKS (public key) at http://localhost:8081/jwks.json via a tiny static server.
- APISIX JWT plugin validates tokens using the JWKS URL.
- Provide a small token mint script (CLI) to generate role-bearing JWTs (platform_admin, project_user) with claims: {sub, roles, project}.

---

## 8) OPA Policy & Paths (to avoid mismatches)
- Package: `package gateway.authz`
- Rule: `allow` returning boolean
- APISIX calls: `POST http://<OPA_HOST>:8181/v1/data/gateway/authz/allow` with input {claims, path, method}
- Seed policy ensures deny-by-default.

---

## 9) etcd → OPA Watcher Sync
- Watches prefix `/policies/` using etcd watch API.
- On create/update/delete events, updates OPA via REST:
  - Rego: PUT /v1/policies/<id>
  - Data: PUT /v1/data/<path>
- Keeps architecture intact: CMS writes only to etcd; OPA updated via pushed events.

---

## 10) APISIX Setup
Source: Apache APISIX GitHub repo (required)
- Repo: https://github.com/apache/apisix
- Environment: WSL2 Ubuntu or a Linux VM on your laptop (recommended path on Windows).
- Version: Pin to the tag matching your future prod binary to avoid plugin drift.
- Plugins: Ensure the OPA authorization integration is available/enabled. If using APISIX AI Gateway features, install per repo docs (same organization).

Docker fallback (optional)
- You may temporarily use the official APISIX Docker image with the same version tag to validate OPA integration, then switch to the repo/binary build on VM.

Bootstrap (common)
- Create upstreams for CMS and OPA (using their TLS endpoints and APISIX mTLS client certs).
- Enable JWT plugin with JWKS URL.
- Enable OPA authz plugin with endpoint `/v1/data/gateway/authz/allow`.
- Add a sample protected route (/demo) and a CMS route.

---

## 11) MongoDB Atlas
- You’ll create an M0 cluster and share the SRV connection string.
- We store it in SSM at `/cms/atlas/uri`.
- CMS reads it on startup (via AWS SDK) and connects to Atlas.

Fallback: local Mongo container if Atlas is not reachable.

---

## 12) Bring-up Sequence (high level)
1) Create SSM parameters in ap-south-1 (String type is fine for dev).
2) Generate TLS CA + service/client certs.
3) Generate RSA keypair and JWKS; start JWKS static server (port 8081).
4) Start Docker services: etcd, OPA, CMS, etcd-opa-sync (and Mongo if local).
5) Seed OPA with a deny-by-default policy; verify with curl.
6) Start APISIX (repo path or Docker); point it at etcd for config and at OPA/CMS upstreams with mTLS.
7) Bootstrap APISIX: add upstreams, route, JWT + OPA plugins.
8) Test:
   - Call /demo without JWT → 401.
   - Call with JWT but policy denies → 403.
   - Use CMS PUT/PATCH to allow; verify near-instant allow via OPA.

---

## 13) Risks & Fallbacks
- Building APISIX from repo on Windows is non-trivial → use WSL2 Ubuntu or Docker image.
- TLS trust issues → ensure APISIX trusts the CA and client certs are presented.
- OPA rule path mismatches → keep `gateway.authz.allow` consistent across policy and APISIX config.
- Atlas network → ensure outbound to Atlas is open; else use local Mongo.

---

## 14) Inputs Needed
- Confirm APISIX path: repo on WSL2 (per above) or Docker fallback for laptop.
- Confirm using SSM String type (free) or SecureString (KMS).
- Provide MongoDB Atlas SRV URI once ready.
- Any port conflicts to avoid.

---

## 15) Next Steps
- After your confirmations, I’ll scaffold:
  - docker-compose.yml (etcd, OPA, CMS, etcd-opa-sync, optional Mongo)
  - APISIX bootstrap files and configs
  - TLS/JWKS generation scripts and token mint script
  - Seed OPA policy and a minimal CMS FastAPI app
  - A short "Try it" guide
