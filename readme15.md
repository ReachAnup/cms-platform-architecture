# Definitive Platform Architecture & Core Workflows

## Overview

This document provides the definitive, comprehensive guide to the Configuration Management System (CMS) and its surrounding RAG (Retrieval-Augmented Generation) platform architecture. It is designed to be a single source of truth for engineering teams, detailing not only the components and their connections but also the strategic rationale behind key design decisions.

The primary goals of this architecture are:
- **High Availability:** Ensure system resilience and uptime through a dual-datacenter deployment and use of managed services.
- **Scalability:** Allow individual components to scale independently to meet demand.
- **Security:** Enforce a robust, centralized security model for all operations, leveraging a managed secrets platform.
- **Multi-Tenancy:** Enable different teams to use the platform securely and in isolation.
- **Extensibility:** Provide a flexible foundation for adding new features and services.

---

## 1. High-Availability Architecture Diagram

This diagram illustrates the complete, production-grade architecture. It shows the physical deployment across two datacenters and the clear separation between self-hosted services and fully managed cloud services, including the managed Vault service.

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
            VECTOR_DB_DC2[(Vector DB)]
        end
    end
    
    subgraph "External & Managed Services"
        LLM["Large Language Models"]
        MANAGED_MONGO["MongoDB Atlas<br/>(Platform Data)"]
        COSMOS_DB["Azure Cosmos DB<br/>(RAG App Data)"]
        MANAGED_VAULT["Managed Vault Service<br/>(e.g., HCP Vault)"]
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

    %% Backend Services to Self-Hosted Data Stores
    CMS_DC1 & CMS_DC2 --> ETCD_DC1 & ETCD_DC2
    OPA_DC1 & OPA_DC2 --> ETCD_DC1 & ETCD_DC2
    RAG_APP_DC1 & RAG_APP_DC2 --> VECTOR_DB_DC1 & VECTOR_DB_DC2
    
    %% Secure Connections to Managed Services
    APISIX_DC1 & APISIX_DC2 -- "Secure Connection" --> MANAGED_VAULT
    CMS_DC1 & CMS_DC2 -- "Secure Connection" --> MANAGED_MONGO
    RAG_APP_DC1 & RAG_APP_DC2 -- "Secure Connection" --> COSMOS_DB
    
    %% Hairpin and External LLM
    RAG_APP_DC1 & RAG_APP_DC2 --> APISIX_DC1 & APISIX_DC2
    APISIX_DC1 & APISIX_DC2 -.->|Proxies to| LLM

    %% Data Replication for Self-Hosted Components
    ETCD_DC1 -->|Replication| ETCD_DC2
    ETCD_DC2 -->|Replication| ETCD_DC1
    VECTOR_DB_DC1 -->|Replication| VECTOR_DB_DC2
    VECTOR_DB_DC2 -->|Replication| VECTOR_DB_DC1
```

---

## 2. Component Descriptions & Rationale

This section details each component's role and the reasoning behind its inclusion in the architecture.

#### Network & Gateway
-   **Load Balancer (HA Pair):** The single entry point to the system. Deployed as an Active-Passive High-Availability pair to prevent it from being a single point of failure. It distributes traffic across the APISIX gateways in both datacenters.
-   **APISIX Gateway:** The core of the request management and security enforcement layer. Its responsibilities include routing, security enforcement (JWT validation, OPA delegation), and acting as a centralized "hairpin" proxy for all outbound LLM traffic.

#### Core Platform Services
-   **CMS Microservice:** The "control plane" for managing policies. It provides APIs for teams to manage their Rego policies, writing metadata to MongoDB and raw policy content to `etcd`.
-   **OPA Microservice (Open Policy Agent):** The stateless "decision engine" for authorization. It loads all policies from `etcd` into memory and uses its `watch` feature to receive instant updates, providing "Allow" or "Deny" decisions to APISIX.

#### RAG Application
-   **RAG Application Service:** Contains the business logic for the RAG functionality, handling document ingestion, pre-filtering, context enrichment, and communication with the LLM.

#### Self-Hosted Data Stores
-   **etcd:** A consistent key-value store used exclusively for **live, watchable configuration data**, primarily OPA policies. Its `watch` capability is critical for near real-time policy propagation.
-   **Vector DB (e.g., Milvus, Weaviate):** A specialized database for efficient similarity searching on vector embeddings. It stores the vectorized chunks of ingested documents.

#### Managed Services
-   **Managed Vault Service (e.g., HCP Vault):** A dedicated, centralized secrets management service provided by a cloud vendor. This is a critical strategic choice to **offload the significant operational burden** of managing, securing, and maintaining a highly available Vault cluster. It stores all sensitive data, including database credentials and API keys. Services authenticate to the managed service endpoint to retrieve secrets at runtime.
-   **MongoDB Atlas (Platform Data):** A managed NoSQL database used by the **core platform services** (CMS, APISIX) for data that does not need to be "watched," such as policy metadata, user roles, and gateway plugin configurations.
-   **Azure Cosmos DB (RAG App Data):** A managed NoSQL database used exclusively by the **RAG Application Service**. This clear separation of concerns allows the RAG team to manage their own data schema for document metadata, pre-filtering attributes, and user chat history.
-   **Large Language Models (LLM):** External, third-party AI services that provide the generative capabilities for the RAG system.

---

## 3. Scalability and High Availability

-   **High Availability:** The architecture achieves HA through a multi-layered strategy:
    -   **Managed Services:** The availability and disaster recovery of Vault, MongoDB, and Cosmos DB are handled by their respective cloud providers.
    -   **Self-Hosted Replication:** The stateful components that we manage (`etcd`, `Vector DB`) have their data replicated across both datacenters.
    -   **Stateless Services:** The "App Nodes" are stateless, allowing the Load Balancer to redirect traffic to the healthy datacenter in a disaster scenario.
-   **Scalability:** The stateless "App Nodes" allow for horizontal scaling. If any service comes under heavy load, new App Node VMs can be provisioned and added to the Load Balancer's pool to increase capacity.

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
This flow details how a user query is answered, correctly showing the interaction with the **Managed Vault Service**.

```mermaid
sequenceDiagram
    autonumber

    participant USER as End User
    participant APISIX as APISIX Gateway
    participant RAG as RAG Service
    participant COSMOS as "Azure Cosmos DB (RAG Data)"
    participant VDB as Vector DB
    participant VAULT as "Managed Vault Service"
    participant LLM as External LLM

    USER->>+APISIX: 1. User sends query
    APISIX->>+RAG: 2. Route to RAG Service
    RAG->>+COSMOS: 3. Fetch app data/metadata for pre-filtering
    COSMOS-->>-RAG: 4. Return filtered document IDs & context
    RAG->>+VDB: 5. Get context from Vector DB (using filtered IDs)
    VDB-->>-RAG: 6. Return context documents
    RAG->>+APISIX: 7. "Hairpin Call" with enriched prompt
    APISIX->>+VAULT: 8. Fetch LLM API Key from Managed Vault
    VAULT-->>-APISIX: 9. Return secret API Key
    APISIX->>+LLM: 10. Proxy to external LLM
    LLM-->>-APISIX: 11. LLM sends response back
    APISIX-->>-RAG: 12. Forward response to RAG
    RAG-->>-APISIX: 13. Send final polished answer
    APISIX-->>-USER: 14. Deliver final answer
```
