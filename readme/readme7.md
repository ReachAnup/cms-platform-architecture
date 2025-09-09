# Complete Architecture with MongoDB and Vault

This document provides a comprehensive view of the system architecture, incorporating MongoDB for general application data and HashiCorp Vault for secrets management.

## 1. Integrated Architecture Diagram

This diagram shows the complete system with the clear separation of data stores based on their function.

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
            MONGO1[(MongoDB)]
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
            MONGO2[(MongoDB)]
            VAULT2[(Vault)]
            VECTOR_DB2[(Vector DB)]
        end
    end
    
    subgraph "External AI Services"
        LLM["Large Language Models"]
    end

    %% --- Connections ---
    USER_INTERACTION[CMS_USER & RAG_USER] --> LB
    LB --> APISIX1 & APISIX2

    %% App to Data Connections
    APISIX1 & APISIX2 --> VAULT1 & VAULT2
    CMS1 & CMS2 --> MONGO1 & MONGO2
    CMS1 & CMS2 --> ETCD1 & ETCD2
    OPA1 & OPA2 --> ETCD1 & ETCD2
    RAG_APP1 & RAG_APP2 --> MONGO1 & MONGO2
    RAG_APP1 & RAG_APP2 --> VECTOR_DB1 & VECTOR_DB2
    
    %% Hairpin and External
    RAG_APP1 & RAG_APP2 --> APISIX1 & APISIX2
    APISIX1 & APISIX2 -.->|Proxies to| LLM

    %% Data Replication
    ETCD1 <-.->|Replication| ETCD2
    MONGO1 <-.->|Replication| MONGO2
    VAULT1 <-.->|Replication| VAULT2
    VECTOR_DB1 <-.->|Replication| VECTOR_DB2
```

## 2. Component Descriptions

-   **etcd:** A distributed key-value store used exclusively for **live configuration data** and **OPA policies**. Its `watch` feature allows for instant propagation of policy changes.
-   **MongoDB:** A general-purpose document database used for all other **application data**. This includes user profiles, document metadata, chat histories, and policy metadata (like version history and author).
-   **HashiCorp Vault:** A dedicated **secrets management** tool. It securely stores, controls, and audits access to all secrets, including API keys for LLMs and credentials for the databases.
-   **Vector Database:** A specialized database for storing and querying vector embeddings for the RAG platform.

---

## 3. Detailed Workflow Sequence Diagrams

### End-to-End RAG Query Flow (with Vault and MongoDB)

```mermaid
sequenceDiagram
    autonumber

    participant USER as End User
    participant APISIX as APISIX Gateway
    participant RAG as RAG Service
    participant MONGO as MongoDB
    participant VDB as Vector DB
    participant VAULT as Vault
    participant LLM as External LLM

    USER->>+APISIX: 1. User sends query
    APISIX->>+RAG: 2. Route to RAG Service

    RAG->>+MONGO: 3. Fetch user profile or chat history
    MONGO-->>-RAG: 4. Return application data

    RAG->>+VDB: 5. Get context from Vector DB
    VDB-->>-RAG: 6. Return context documents

    RAG->>+APISIX: 7. "Hairpin Call" with enriched prompt
    
    APISIX->>+VAULT: 8. Fetch LLM API Key for the request
    VAULT-->>-APISIX: 9. Return secret API Key

    APISIX->>+LLM: 10. Proxy to external LLM (with key)
    LLM-->>-APISIX: 11. LLM sends response back
    APISIX-->>-RAG: 12. Forward response to RAG

    RAG->>+MONGO: 13. (Optional) Save chat history to MongoDB
    MONGO-->>-RAG: 14. Confirm save

    RAG-->>-APISIX: 15. Send final polished answer back out
    APISIX-->>-USER: 16. Deliver final answer to user
```

### CMS Policy Update Flow (with MongoDB and etcd)

```mermaid
sequenceDiagram
    autonumber

    participant ADMIN as Platform Admin
    participant APISIX as APISIX Gateway
    participant CMS as CMS Service
    participant MONGO as MongoDB
    participant ETCD as etcd Cluster
    participant OPA as OPA Service

    ADMIN->>+APISIX: 1. Submit request to update a policy
    APISIX->>+CMS: 2. Route to CMS Service

    CMS->>+MONGO: 3. Write policy metadata (e.g., author, version, description)
    MONGO-->>-CMS: 4. Confirm metadata saved

    CMS->>+ETCD: 5. Write the raw policy content to etcd
    ETCD-->>-CMS: 6. Confirm policy content saved

    note over OPA, ETCD: OPA service is watching etcd and is notified instantly.

    OPA->>ETCD: 7. Read the new policy content from etcd
    
    note over OPA: OPA loads the new policy into memory.

    CMS-->>-APISIX: 8. Return "Update Successful" message
    APISIX-->>-ADMIN: 9. Display "Update Successful" to admin
```
