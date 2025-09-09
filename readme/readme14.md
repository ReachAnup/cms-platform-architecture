# Definitive Architecture & Core Workflows

## Overview

This document provides the definitive, comprehensive guide to the Configuration Management System (CMS) and its surrounding RAG (Retrieval-Augmented Generation) platform architecture. It is designed to be a single source of truth for engineering teams, detailing not only the components and their connections but also the strategic rationale behind key design decisions.

The primary goals of this architecture are:
- **High Availability:** Ensure system resilience and uptime through a dual-datacenter deployment.
- **Scalability:** Allow individual components to scale independently to meet demand.
- **Security:** Enforce a robust, centralized security model for all operations.
- **Multi-Tenancy:** Enable different teams to use the platform securely and in isolation.
- **Extensibility:** Provide a flexible foundation for adding new features and services.

---

## 1. High-Availability Architecture Diagram

This diagram illustrates the complete, production-grade architecture. It shows the physical deployment across two datacenters, the clear separation of services, and the full data flow.

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
        MANAGED_MONGO["MongoDB Atlas<br/>(Platform Data)"]
        COSMOS_DB["Azure Cosmos DB<br/>(RAG App Data)"]
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
    RAG_APP_DC1 & RAG_APP_DC2 -- "Secure Connection" --> COSMOS_DB
    
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

This section details each component's role and the reasoning behind its inclusion in the architecture.

#### Network & Gateway
-   **Load Balancer (HA Pair):** The single entry point to the system. Deployed as an Active-Passive High-Availability pair (using a Virtual IP via Keepalived/VRRP) to prevent it from being a single point of failure. It distributes traffic across the APISIX gateways in both datacenters.
-   **APISIX Gateway:** The core of the request management and security enforcement layer. Its responsibilities include:
    -   **Routing:** Directing incoming requests to the correct backend microservice.
    -   **Security:** Validating JWTs and delegating authorization decisions to OPA on every request.
    -   **Centralized Control:** Acts as a "hairpin" proxy for outbound calls to external LLMs, ensuring all traffic is monitored and controlled.
    -   **Plugin Execution:** Stores its configuration and plugin data in the platform's MongoDB instance.

#### Core Platform Services
-   **CMS Microservice:** The "control plane" for managing policies. It provides APIs for teams to create, update, and manage their specific Rego policies and data. It writes policy metadata to MongoDB and the raw policy content to `etcd`.
-   **OPA Microservice (Open Policy Agent):** The "decision engine" for authorization. It is completely stateless. It loads all policies from `etcd` into memory and uses its `watch` feature to receive instant updates. It evaluates requests against these policies to provide "Allow" or "Deny" decisions back to the APISIX gateway.

#### RAG Application
-   **RAG Application Service:** Contains the business logic for the Retrieval-Augmented Generation functionality. It handles document ingestion, pre-filtering, context enrichment, and communication with the LLM (via the hairpin proxy).

#### Data Stores
-   **etcd:** A consistent and highly-available key-value store used exclusively for **live, watchable configuration data**. Its primary role is to store OPA policies, where its `watch` capability allows OPA to update its rules in near real-time without polling.
-   **Vault:** A dedicated, centralized secrets management service. It stores all sensitive data, including database credentials, API keys for external services (like the LLM), and certificates. Services authenticate to Vault to retrieve the secrets they need at runtime.
-   **Vector DB (e.g., Milvus, Weaviate):** A specialized database designed for efficient similarity searching on high-dimensional vector embeddings. It stores the vectorized chunks of ingested documents, forming the "retrieval" backbone of the RAG system.
-   **MongoDB Atlas (Platform Data):** A managed NoSQL database used by the **core platform services**. It stores platform-level data that does not need to be "watched" in real-time, such as CMS policy metadata (author, version history), user roles, and gateway plugin configurations.
-   **Azure Cosmos DB (RAG App Data):** A managed NoSQL database used exclusively by the **RAG Application Service**. This clear separation of concerns allows the RAG team to manage their own data schema. It stores all RAG-specific application data, such as document metadata (source, owner), pre-filtering attributes, and user chat history.

---

## 3. Scalability and High Availability

-   **High Availability:** The architecture achieves HA by deploying across two independent datacenters. All stateful components (`etcd`, `Vault`, `Vector DB`) have their data replicated across both sites. In the event of a full datacenter failure, the Load Balancer can redirect all traffic to the remaining healthy datacenter.
-   **Scalability:** The "App Nodes" (containing APISIX, CMS, OPA, RAG) are designed to be **stateless**. This allows for horizontal scaling. If any service comes under heavy load, new App Node VMs can be provisioned and added to the Load Balancer's pool to increase capacity.

---

## 4. Multi-Tenant Policy Model

The system uses a hybrid policy model to provide both centralized control and delegated flexibility.

-   **Platform-Level Policies:** Managed by Platform Admins. These are global rules that apply to all teams and cannot be overridden. They enforce universal security and operational guardrails.
-   **Team-Level Policies:** Managed by individual teams via the CMS API. These define business logic and access control specific to that team's resources.

During an authorization check, OPA evaluates the request by combining the global platform policies with the specific policies of the team making the request, ensuring both sets of rules are satisfied.

---

## 5. Core Workflow Sequence Diagrams

This section details the key operational flows within the platform.

### 5.1 Authorization Flow (JWT Validation)
This workflow shows how every incoming API request is authorized. It assumes the user has already authenticated with a separate identity provider and possesses a valid JWT.

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

### 5.2 CMS Team-Specific Policy Update Flow
This flow shows how a Team Admin updates a policy for their specific team, correctly using MongoDB for platform metadata.

```mermaid
sequenceDiagram
    autonumber
    participant ADMIN as Team Admin
    participant APISIX as APISIX Gateway
    participant CMS as CMS Service
    participant MONGO as "MongoDB Atlas (Platform Data)"
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

### 5.3 RAG Document Ingestion Flow
This high-level workflow shows how new documents are added to the RAG platform, correctly using Cosmos DB for RAG-specific metadata.

```mermaid
sequenceDiagram
    autonumber

    participant ADMIN as Team Admin
    participant APISIX as APISIX Gateway
    participant RAG as RAG Service
    participant COSMOS as "Azure Cosmos DB (RAG Data)"
    participant VDB as Vector DB

    ADMIN->>+APISIX: 1. Upload new document(s)
    APISIX->>+RAG: 2. Route request to RAG Service
    RAG->>RAG: 3. Process Document: Chunk text into smaller pieces
    loop For Each Chunk
        RAG->>RAG: 4. Generate vector embedding for the chunk
        RAG->>+VDB: 5. Store chunk's embedding and a reference ID
        VDB-->>-RAG: 6. Confirm storage
    end
    RAG->>+COSMOS: 7. Store document metadata (filename, source, etc.)
    COSMOS-->>-RAG: 8. Confirm metadata saved
    RAG-->>-APISIX: 9. Return "Ingestion Complete"
    APISIX-->>-ADMIN: 10. Display "Ingestion Complete"
```

### 5.4 RAG Data Retrieval Flow
This flow details how a user query is answered, correctly using Cosmos DB for pre-filtering and metadata retrieval.

```mermaid
sequenceDiagram
    autonumber

    participant USER as End User
    participant APISIX as APISIX Gateway
    participant RAG as RAG Service
    participant COSMOS as "Azure Cosmos DB (RAG Data)"
    participant VDB as Vector DB
    participant VAULT as Vault
    participant LLM as External LLM

    USER->>+APISIX: 1. User sends query
    APISIX->>+RAG: 2. Route to RAG Service
    RAG->>+COSMOS: 3. Fetch app data/metadata for pre-filtering
    COSMOS-->>-RAG: 4. Return filtered document IDs & context
    RAG->>+VDB: 5. Get context from Vector DB (using filtered IDs)
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

