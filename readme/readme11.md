# Final Architecture with Multi-Tenancy

This document provides the definitive, comprehensive view of the system architecture. It details the multi-datacenter HA setup, the use of a managed MongoDB service, and the multi-tenant policy model.

## 1. High-Availability Architecture Diagram

This diagram shows the complete architecture deployed across two datacenters for high availability and disaster recovery.

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
            APISIX1["APISIX Gateway"]
            CMS1[CMS Microservice]
            OPA1[OPA Microservice]
            RAG_APP1[RAG Application Service]
        end

        subgraph "Data Node 1 (VM)"
            ETCD1[(etcd)]
            VAULT1[(Vault)]
            VECTOR_DB1[(Vector DB)]
        end
    end

    subgraph "Datacenter 2"
        subgraph "App Node 2 (VM)"
            APISIX2["APISIX Gateway"]
            CMS2[CMS Microservice]
            OPA2[OPA Microservice]
            RAG_APP2[RAG Application Service]
        end

        subgraph "Data Node 2 (VM)"
            ETCD2[(etcd)]
            VAULT2[(Vault)]
            VECTOR_DB2[(Vector DB)]
        end
    end
    
    subgraph "External & Managed Services"
        LLM["Large Language Models"]
        MANAGED_MONGO["MongoDB Atlas<br/>(Managed Service)"]
    end

    %% --- Connections ---
    CMS_USER --> LB
    TEAM_ADMIN --> LB
    RAG_USER --> LB
    LB --> APISIX1 & APISIX2

    %% App to Self-Hosted Data Connections
    APISIX1 & APISIX2 --> VAULT1 & VAULT2
    CMS1 & CMS2 --> ETCD1 & ETCD2
    OPA1 & OPA2 --> ETCD1 & ETCD2
    RAG_APP1 & RAG_APP2 --> VECTOR_DB1 & VECTOR_DB2
    
    %% Secure Connection to Managed Service
    CMS1 & CMS2 -- "Secure Connection" --> MANAGED_MONGO
    RAG_APP1 & RAG_APP2 -- "Secure Connection" --> MANAGED_MONGO
    
    %% Hairpin and External LLM
    RAG_APP1 & RAG_APP2 --> APISIX1 & APISIX2
    APISIX1 & APISIX2 -.->|Proxies to| LLM

    %% Data Replication
    ETCD1 <-.->|Replication| ETCD2
    VAULT1 <-.->|Replication| VAULT2
    VECTOR_DB1 <-.->|Replication| VECTOR_DB2
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

*(This flow remains unchanged)*

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

This diagram shows how a **Team Admin** updates a policy for their specific team.

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
