# Architecture with a Managed MongoDB Service

This document provides a comprehensive view of the system architecture, updated to reflect the use of a managed MongoDB service (e.g., MongoDB Atlas). This is a common and highly recommended pattern for production systems.

## 1. Architecture with Managed Database

This diagram visually separates the self-hosted infrastructure from external managed services, providing a clear architectural boundary.

```mermaid
graph TD
    subgraph "End Users"
        CMS_USER[Platform Admin]
        RAG_USER[RAG Platform User]
    end

    subgraph "Self-Hosted Infrastructure (Datacenters 1 & 2)"
        subgraph "Network Layer"
            LB["Load Balancer (HA Pair)"]
        end

        subgraph "App Nodes (VMs)"
            APISIX["APISIX Gateway"]
            CMS[CMS Microservice]
            OPA[OPA Microservice]
            RAG_APP[RAG Application Service]
        end

        subgraph "Data Nodes (VMs)"
            ETCD[(etcd)]
            VAULT[(Vault)]
            VECTOR_DB[(Vector DB)]
        end
    end
    
    subgraph "External & Managed Services"
        LLM["Large Language Models"]
        MANAGED_MONGO["MongoDB Atlas<br/>(Managed Service)"]
    end

    %% --- Connections ---
    USER_INTERACTION[CMS_USER & RAG_USER] --> LB
    LB --> APISIX

    %% App to Self-Hosted Data
    APISIX --> VAULT
    CMS --> ETCD
    OPA --> ETCD
    RAG_APP --> VECTOR_DB
    
    %% Secure Connection to Managed Service
    CMS & RAG_APP -- "Secure Connection<br/>(VPC Peering / Private Link)" --> MANAGED_MONGO
    
    %% Hairpin and External LLM
    RAG_APP --> APISIX
    APISIX -.->|Proxies to| LLM
```

## 2. Rationale for Using a Managed Database

Using a managed service for MongoDB is a strategic decision that offers significant advantages:
-   **Reduced Operational Overhead:** Your team is freed from the responsibility of database installation, patching, backups, replication, and scaling.
-   **Enhanced Reliability:** Managed services typically come with a high uptime Service Level Agreement (SLA), often higher than what can be achieved in-house without a dedicated database team.
-   **Simplified Internal Infrastructure:** Your on-premise Data Nodes become leaner, more focused, and easier to manage.
-   **Focus on Core Business:** It allows your development team to focus on building features for your RAG platform, not on becoming expert database administrators.

---

## 3. Detailed Workflow Sequence Diagrams

### End-to-End RAG Query Flow (with Managed MongoDB)

This diagram shows the RAG service communicating with the managed MongoDB endpoint over a secure connection.

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

### CMS Policy Update Flow (with Managed MongoDB)

This diagram illustrates the separation of concerns: the raw policy goes to the self-hosted `etcd` for instant watching, while the policy's metadata goes to the managed MongoDB for long-term storage and querying.

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
