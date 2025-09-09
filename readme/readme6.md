# Complete System Architecture and Workflows

This document provides a single, comprehensive view of the entire system, from the high-level component architecture to the detailed, step-by-step sequence of operations.

## 1. Integrated Architecture Diagram

This diagram shows the complete system, including the CMS and RAG Platform services, and illustrates the physical deployment across datacenters and VMs.

```mermaid
graph TD
    subgraph "End Users"
        CMS_USER[Platform Admin]
        RAG_USER[RAG Platform User]
    end

    subgraph "Network Layer"
        LB["Load Balancer (HA Pair)<br/>e.g., HAProxy with Keepalived"]
    end

    subgraph "Datacenter 1"
        subgraph "App Node 1 (VM)"
            APISIX1["APISIX Gateway<br/>(with AI Gateway plugins)"]
            CMS1[CMS Microservice]
            OPA1[OPA Microservice]
            RAG_APP1[RAG Application Service]
        end

        subgraph "Data Node 1 (VM)"
            ETCD1[(etcd Node 1)]
            VECTOR_DB1[(Vector Database)]
        end
    end

    subgraph "Datacenter 2"
        subgraph "App Node 2 (VM)"
            APISIX2["APISIX Gateway<br/>(with AI Gateway plugins)"]
            CMS2[CMS Microservice]
            OPA2[OPA Microservice]
            RAG_APP2[RAG Application Service]
        end

        subgraph "Data Node 2 (VM)"
            ETCD2[(etcd Node 2)]
            VECTOR_DB2[(Vector Database)]
        end
    end
    
    subgraph "External AI Services"
        LLM["Large Language Models<br/>(OpenAI, Anthropic, etc.)"]
    end

    %% Connections
    CMS_USER --> LB
    RAG_USER --> LB

    LB --> APISIX1 & APISIX2

    %% CMS Flow
    APISIX1 --> CMS1 & OPA1
    CMS1 & OPA1 --> ETCD1

    APISIX2 --> CMS2 & OPA2
    CMS2 & OPA2 --> ETCD2

    %% RAG App Flow
    APISIX1 --> RAG_APP1
    RAG_APP1 --> VECTOR_DB1

    APISIX2 --> RAG_APP2
    RAG_APP2 --> VECTOR_DB2

    %% LLM Request Flow (The Key Part)
    RAG_APP1 --> APISIX1
    RAG_APP2 --> APISIX2
    APISIX1 -.->|Proxies to| LLM
    APISIX2 -.->|Proxies to| LLM

    %% Data Replication
    ETCD1 <-.->|Replication| ETCD2
    VECTOR_DB1 <-.->|Replication| VECTOR_DB2
```

## 2. Component Descriptions

-   **RAG Application Service:** The backend for your RAG platform. It handles user queries, retrieves documents from the Vector DB, and orchestrates calls to the LLM.
-   **Vector Database:** A specialized database (e.g., Milvus, Weaviate) that stores document embeddings for fast similarity searches. It is a stateful service and resides on the **Data Nodes**.
-   **Large Language Models (LLMs):** External, third-party AI services that your platform will call via the APISIX gateway.

## 3. LLM Request Flow Explained

The flow for handling LLM requests is a critical pattern called a **"hairpin" or "reflexive" proxy**.

1.  A user's request arrives at the **RAG Application Service**.
2.  The RAG service queries the **Vector Database** to get relevant context.
3.  Crucially, instead of calling the external LLM directly, the RAG service makes a request back to its **local APISIX Gateway** (e.g., at `http://localhost:9080/llm/openai/...`).
4.  **APISIX's AI Gateway plugins** intercept this request to:
    *   Securely inject the required LLM API key.
    *   Enforce rate limits and budget controls.
    *   Log requests and token usage for observability.
    *   Potentially serve a response from its cache.
5.  APISIX then proxies the authenticated request to the actual **external LLM provider**.
6.  The response flows back through APISIX (where it can be logged and cached) to the RAG service, which then prepares the final, polished answer for the user.

This pattern provides centralized security, control, and cost management for all AI traffic.

---

## 4. Detailed Workflow Sequence Diagrams

### End-to-End RAG Query Flow

```mermaid
sequenceDiagram
    autonumber

    participant USER as End User
    participant LB as Load Balancer
    participant APISIX as APISIX Gateway
    participant RAG as RAG Service
    participant VDB as Vector DB
    participant LLM as External LLM

    USER->>+LB: 1. User sends query
    LB->>+APISIX: 2. Forward to Gateway
    APISIX->>+RAG: 3. Route to RAG Service

    RAG->>+VDB: 4. Get context from Vector DB
    VDB-->>-RAG: 5. Return context

    RAG->>+APISIX: 6. "Hairpin Call": Send enriched prompt to local APISIX
    APISIX->>+LLM: 7. Proxy to external LLM (adds key, logs)
    LLM-->>-APISIX: 8. LLM sends response back to APISIX
    APISIX-->>-RAG: 9. Forward response to RAG (caches)

    RAG-->>-APISIX: 10. Send final polished answer back out
    APISIX-->>-LB: 11. Forward final response
    LB-->>-USER: 12. Deliver final answer to user
```

### CMS Policy Update Flow

```mermaid
sequenceDiagram
    autonumber

    participant ADMIN as Platform Admin
    participant LB as Load Balancer
    participant APISIX as APISIX Gateway
    participant CMS as CMS Service
    participant OPA as OPA Service
    participant ETCD as etcd Cluster

    ADMIN->>+LB: 1. Submit request to update a policy
    LB->>+APISIX: 2. Forward request
    APISIX->>+CMS: 3. Route to CMS Service

    CMS->>+ETCD: 4. Write new policy version to etcd
    ETCD-->>-CMS: 5. Confirm write success

    note over OPA, ETCD: OPA service is watching etcd for changes and is notified instantly.

    OPA->>ETCD: 6. Read the new policy from etcd
    
    note over OPA: OPA loads the new policy into memory.

    CMS-->>-APISIX: 7. Return "Update Successful" message
    APISIX-->>-LB: 8. Forward success response
    LB-->>-ADMIN: 9. Display "Update Successful" to admin
```
