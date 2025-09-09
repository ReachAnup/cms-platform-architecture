# Definitive Architecture & Core Workflows

This document provides the definitive, comprehensive view of the system architecture. It details the multi-datacenter HA setup, the multi-tenant policy model, and the core operational workflows of the platform.

## 1. High-Availability Architecture Diagram

This diagram shows the complete architecture, including the correct request routing from the APISIX gateway to the backend services. This version is safe to import into `diagrams.net`.

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

    %% Gateway to Backend Services
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

---
## 2. Component Descriptions & Rationale
*(Unchanged from previous version)*

---
## 3. Multi-Tenant Policy Model
*(Unchanged from previous version)*

---
## 4. Core Workflow Sequence Diagrams

This section details the key operational flows within the platform.

### 4.1 Authorization Flow (JWT Validation)

This workflow shows how every incoming API request is authorized. It assumes the user has already authenticated and possesses a valid JWT.

```mermaid
sequenceDiagram
    autonumber

    participant USER as User
    participant APISIX as APISIX Gateway
    participant OPA as OPA Service
    participant Backend as Backend Service (CMS/RAG)

    USER->>+APISIX: 1. API Request with JWT in 'Authorization' header

    APISIX->>APISIX: 2. Validate JWT signature & expiration
    note right of APISIX: This is a fast, local operation using the public key.

    APISIX->>+OPA: 3. Authorization check: "Can this user perform this action?"
    note right of APISIX: Sends JWT claims (user, team, roles), path, and HTTP method to OPA.

    OPA-->>-APISIX: 4. Decision: "Allow" or "Deny"
    
    alt Allow
        APISIX->>+Backend: 5. Forward request to the appropriate backend service
        Backend-->>-APISIX: 6. Return response
    else Deny
        APISIX-->>USER: 7. Return 403 Forbidden error
    end

    APISIX-->>-USER: 8. Return final response
```

### 4.2 CMS Team-Specific Policy Update Flow

*(Unchanged from previous version)*

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

### 4.3 RAG Document Ingestion Flow

This high-level workflow shows how new documents are added to the RAG platform. It highlights the intersection points with our core architecture.

```mermaid
sequenceDiagram
    autonumber

    participant ADMIN as Team Admin
    participant APISIX as APISIX Gateway
    participant RAG as RAG Service
    participant MONGO as "MongoDB Atlas (Managed)"
    participant VDB as Vector DB

    ADMIN->>+APISIX: 1. Upload new document(s)
    note left of ADMIN: Intersection Point: All traffic enters via the Gateway.

    APISIX->>+RAG: 2. Route request to RAG Service

    RAG->>RAG: 3. Process Document: Chunk text into smaller pieces

    loop For Each Chunk
        RAG->>RAG: 4. Generate vector embedding for the chunk
        RAG->>+VDB: 5. Store chunk's embedding and a reference ID
        note right of RAG: Intersection Point: Uses the platform's self-hosted Vector DB.
        VDB-->>-RAG: 6. Confirm storage
    end

    RAG->>+MONGO: 7. Store document metadata (filename, source, etc.)
    note right of RAG: Intersection Point: Uses the platform's managed MongoDB.
    MONGO-->>-RAG: 8. Confirm metadata saved

    RAG-->>-APISIX: 9. Return "Ingestion Complete"
    APISIX-->>-ADMIN: 10. Display "Ingestion Complete"
```

### 4.4 RAG Data Retrieval Flow

This workflow details how a user query is answered using the RAG platform.

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
    RAG->>+MONGO: 3. Fetch app data/metadata
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
