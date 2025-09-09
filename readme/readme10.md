# Final Architecture with Multi-Datacenter HA

This document provides the definitive, comprehensive view of the system architecture. It shows the high-availability setup across two datacenters, the use of a managed MongoDB service, and includes detailed workflow diagrams.

## 1. High-Availability Architecture Diagram

This diagram shows the complete architecture deployed across two datacenters for high availability and disaster recovery.

```mermaid
graph TD
    subgraph "End Users"
        CMS_USER[Platform Admin]
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

-   **etcd:** Used for live configuration and OPA policies that require instant propagation via its `watch` feature.
-   **MongoDB (Managed):** Used for all general application data (user profiles, document metadata, etc.). A managed service is used to reduce operational overhead.
-   **HashiCorp Vault:** A dedicated secrets management tool for all API keys and credentials.
-   **Vector Database:** A specialized database for storing and querying vector embeddings.

---

## 3. Detailed Workflow Sequence Diagrams

### End-to-End RAG Query Flow

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

    RAG->>+MONGO: 3. Fetch app data via secure connection
    MONGO-->>-RAG: 4. Return application data

    RAG->>+VDB: 5. Get context from self-hosted Vector DB
    VDB-->>-RAG: 6. Return context documents

    RAG->>+APISIX: 7. "Hairpin Call" with enriched prompt
    
    APISIX->>+VAULT: 8. Fetch LLM API Key from self-hosted Vault
    VAULT-->>-APISIX: 9. Return secret API Key

    APISIX->>+LLM: 10. Proxy to external LLM
    LLM-->>-APISIX: 11. LLM sends response back
    APISIX-->>-RAG: 12. Forward response to RAG

    RAG-->>-APISIX: 13. Send final polished answer back out
    APISIX-->>-USER: 14. Deliver final answer to user
```

### CMS Policy Update Flow

```mermaid
sequenceDiagram
    autonumber

    participant ADMIN as Platform Admin
    participant APISIX as APISIX Gateway
    participant CMS as CMS Service
    participant MONGO as "MongoDB Atlas (Managed)"
    participant ETCD as "etcd Cluster (Self-Hosted)"
    participant OPA as OPA Service

    ADMIN->>+APISIX: 1. Submit request to update a policy
    APISIX->>+CMS: 2. Route to CMS Service

    CMS->>+MONGO: 3. Write policy metadata (author, version, etc.)
    MONGO-->>-CMS: 4. Confirm metadata saved

    CMS->>+ETCD: 5. Write raw policy content to etcd
    ETCD-->>-CMS: 6. Confirm policy content saved

    note over OPA, ETCD: OPA service is watching etcd and is notified instantly.

    OPA->>ETCD: 7. Read the new policy content from etcd
    
    note over OPA: OPA loads the new policy into memory.

    CMS-->>-APISIX: 8. Return "Update Successful" message
    APISIX-->>-ADMIN: 9. Display "Update Successful" to admin
```
