# Final Architecture with Corrected Request Flow

This document provides the definitive, comprehensive view of the system architecture. It details the multi-datacenter HA setup, the multi-tenant policy model, and the correct internal request flow.

## 1. High-Availability Architecture Diagram

This diagram shows the complete architecture, including the correct request routing from the APISIX gateway to the backend services. This version is also safe to import into `diagrams.net`.

```mermaid
graph TD
    subgraph "End Users"
        CMS_USER[Platform Admin]
        TEAM_ADMIN[Team Admin / User]
        RAG_USER[RAG Platform User]
    end

    subgraph "Network Layer"
        LB["Load Balancer (HA Pair)"]
    end

    subgraph "Datacenter 1"
        subgraph "App Node 1 (VM)"
            APISIX_DC1["APISIX Gateway"]
            CMS_DC1[CMS Microservice]
            OPA_DC1[OPA Microservice]
            RAG_APP_DC1[RAG Application Service]
        end

        subgraph "Data Node 1 (VM)"
            ETCD_DC1[(etcd)]
            VAULT_DC1[(Vault)]
            VECTOR_DB_DC1[(Vector DB)]
        end
    end

    subgraph "Datacenter 2"
        subgraph "App Node 2 (VM)"
            APISIX_DC2["APISIX Gateway"]
            CMS_DC2[CMS Microservice]
            OPA_DC2[OPA Microservice]
            RAG_APP_DC2[RAG Application Service]
        end

        subgraph "Data Node 2 (VM)"
            ETCD_DC2[(etcd)]
            VAULT_DC2[(Vault)]
            VECTOR_DB_DC2[(Vector DB)]
        end
    end
    
    subgraph "External & Managed Services"
        LLM["Large Language Models"]
        MANAGED_MONGO["MongoDB Atlas<br/>(Managed Service)"]
    end

    %% --- Connections ---
    %% External to Gateway
    CMS_USER --> LB
    TEAM_ADMIN --> LB
    RAG_USER --> LB
    LB --> APISIX_DC1 & APISIX_DC2

    %% CORRECTED: Gateway to Backend Services
    APISIX_DC1 --> CMS_DC1
    APISIX_DC1 --> OPA_DC1
    APISIX_DC1 --> RAG_APP_DC1
    APISIX_DC2 --> CMS_DC2
    APISIX_DC2 --> OPA_DC2
    APISIX_DC2 --> RAG_APP_DC2

    %% Backend Services to Data Stores
    APISIX_DC1 & APISIX_DC2 --> VAULT_DC1 & VAULT_DC2
    CMS_DC1 & CMS_DC2 --> ETCD_DC1 & ETCD_DC2
    OPA_DC1 & OPA_DC2 --> ETCD_DC1 & ETCD_DC2
    RAG_APP_DC1 & RAG_APP_DC2 --> VECTOR_DB_DC1 & VECTOR_DB_DC2
    
    %% Secure Connection to Managed Service
    CMS_DC1 & CMS_DC2 -- "Secure Connection" --> MANAGED_MONGO
    RAG_APP_DC1 & RAG_APP_DC2 -- "Secure Connection" --> MANAGED_MONGO
    
    %% Hairpin and External LLM
    RAG_APP_DC1 & RAG_APP_DC2 --> APISIX_DC1 & APISIX_DC2
    APISIX_DC1 & APISIX_DC2 -.->|Proxies to| LLM

    %% Data Replication
    ETCD_DC1 -->|Replication| ETCD_DC2
    ETCD_DC2 -->|Replication| ETCD_DC1
    VAULT_DC1 -->|Replication| VAULT_DC2
    VAULT_DC2 -->|Replication| VAULT_DC1
    VECTOR_DB_DC1 -->|Replication| VECTOR_DB_DC2
    VECTOR_DB_DC2 -->|Replication| VECTOR_DB_DC1
```

## 2. Component Descriptions & Rationale

-   **etcd:** Used for live configuration and OPA policies. It stores policies in a **namespaced structure** to support multi-tenancy (e.g., `/policies/platform/...`, `/policies/team-alpha/...`).
-   **OPA (Open Policy Agent):** Loads all policies from all namespaces in `etcd`. It uses request context (like `team_id`) to evaluate against the correct combination of global and team-specific policies.
-   **MongoDB (Managed):** Used for all general application data (user profiles, document metadata, policy metadata).
-   **HashiCorp Vault:** A dedicated secrets management tool for all API keys and credentials.
-   **Vector Database:** A specialized database for storing and querying vector embeddings.

---

## 3. Multi-Tenant Policy Model

The system uses a hybrid policy model to provide both centralized control and delegated flexibility.

-   **Platform-Level Policies:** Managed by Platform Admins. These are global rules that apply to all teams and cannot be overridden. They enforce universal security and operational guardrails.
-   **Team-Level Policies:** Managed by individual teams via the CMS API. These define business logic and access control specific to that team's resources.

This is achieved by storing policies in a structured way within the `etcd` cluster:

```
/policies/
├── platform/
│   ├── security.rego
│   └── defaults.json
├── team-alpha/
│   ├── access_control.rego
│   └── data.json
└── team-bravo/
    ├── validation.rego
    └── data.json
```

---

## 4. Detailed Workflow Sequence Diagrams

### End-to-End RAG Query Flow

*(This flow remains correct and unchanged)*

```mermaid
sequenceDiagram
    autonumber

    participant USER as End User
    participant APISIX as APISIX Gateway
    participant RAG as RAG Service
    participant MONGO as "MongoDB Atlas (Managed)"
    participant VDB as Vector DB
    participant VAULT as Vault
    participant LLM as External LLM

    USER->>+APISIX: 1. User sends query
    APISIX->>+RAG: 2. Route to RAG Service
    RAG->>+MONGO: 3. Fetch app data
    MONGO-->>-RAG: 4. Return application data
    RAG->>+VDB: 5. Get context from Vector DB
    VDB-->>-RAG: 6. Return context documents
    RAG->>+APISIX: 7. "Hairpin Call" with enriched prompt
    APISIX->>+VAULT: 8. Fetch LLM API Key
    VAULT-->>-APISIX: 9. Return secret API Key
    APISIX->>+LLM: 10. Proxy to external LLM
    LLM-->>-APISIX: 11. LLM sends response back
    APISIX-->>-RAG: 12. Forward response to RAG
    RAG-->>-APISIX: 13. Send final polished answer
    APISIX-->>-USER: 14. Deliver final answer
```

### CMS Team-Specific Policy Update Flow

*(This flow remains correct and unchanged)*

```mermaid
sequenceDiagram
    autonumber

    participant ADMIN as Team Admin
    participant APISIX as APISIX Gateway
    participant CMS as CMS Service
    participant MONGO as "MongoDB Atlas (Managed)"
    participant ETCD as "etcd Cluster (Self-Hosted)"
    participant OPA as OPA Service

    ADMIN->>+APISIX: 1. Submit request to update policy for 'Team Alpha'
    APISIX->>+CMS: 2. Route to CMS Service (with team context)

    CMS->>+MONGO: 3. Write policy metadata (author, team, version)
    MONGO-->>-CMS: 4. Confirm metadata saved

    CMS->>+ETCD: 5. Write policy to namespaced path<br/>(e.g., /policies/team-alpha/access.rego)
    ETCD-->>-CMS: 6. Confirm policy content saved

    note over OPA, ETCD: OPA service is watching all /policies/** paths and is notified instantly.

    OPA->>ETCD: 7. Read the new/updated policy content from etcd
    
    note over OPA: OPA loads the new policy into memory for evaluation.

    CMS-->>-APISIX: 8. Return "Update Successful" message
    APISIX-->>-ADMIN: 9. Display "Update Successful" to admin
```
