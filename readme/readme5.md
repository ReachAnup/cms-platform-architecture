# System Workflows Explained (Corrected)

This document provides explicit, step-by-step diagrams for the key data flows within the CMS and RAG platform architecture. This version uses a simplified and validated diagram syntax to ensure it renders correctly.

## 1. End-to-End RAG Query Flow

This is the complete lifecycle of a query from a RAG platform user.

### RAG Query Sequence Diagram

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

### Step-by-Step Explanation

1.  **User Sends Query:** The end-user sends a request from their browser.
2.  **Forward to Gateway:** The Load Balancer forwards the request to a healthy Application Node.
3.  **Route to RAG Service:** The APISIX Gateway on the App Node routes the request to the RAG Application Service.
4.  **Get Context:** The RAG service queries the Vector Database to find relevant documents.
5.  **Return Context:** The Vector DB returns the relevant text snippets.
6.  **Hairpin Call:** The RAG service sends its enriched prompt to its **local APISIX Gateway**.
7.  **Proxy to LLM:** APISIX's AI Gateway plugins process the request, add API keys, and securely proxy it to the external LLM.
8.  **LLM Responds:** The LLM generates a response and sends it back to APISIX.
9.  **Forward to RAG:** APISIX receives the LLM's response, logs usage, and forwards it back to the RAG service.
10. **Send Final Answer:** The RAG service polishes the final answer and sends it back out through the established connection.
11. **Forward Final Response:** The response travels back through APISIX and the Load Balancer.
12. **Deliver to User:** The final, complete answer is delivered to the user's browser.

---

## 2. CMS Policy Update Flow

This diagram shows how a Platform Admin updates a policy in the system.

### Policy Update Sequence Diagram

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
