# Configuration Management System (CMS) Architecture

## Overview

This document outlines the architecture for a production-grade, highly scalable Configuration Management System designed to manage OPA policies and API keys for a RAG-based platform using microservices architecture with FastAPI on Linux.

## System Requirements

### Users & Access Levels
1. **CMS Admin**: Full access to Configuration Management System
2. **Platform Admin**: Full access to RAG platform with project-level and platform-level policy management
3. **Project Users**: Read-only access to their specific project policies
4. **Multiple Projects**: Support for onboarding multiple project teams

### Core Features
- Secure storage of OPA policies and API keys
- Project team onboarding capabilities
- Policy modification workflows
- Active-active configuration support
- Stateless design for easy migration to Kubernetes
- Integration with APISIX API Gateway and AI Gateway

## High-Level Architecture

The system architecture is designed for high availability, scalability, and security. To make it easier to understand, we've broken down the single complex diagram into several focused views.

### 1. Overall Request Flow

This diagram shows the path of a typical request from an external user or service into the system's application layer.

```mermaid
graph TD
    subgraph "External Users & Services"
        UI[Web UI - Future]
        CLI[CLI Tools]
        EXT[External Services]
    end

    subgraph "Network Entry Point"
        LB[Load Balancer<br/>HAProxy/Nginx]
    end

    subgraph "API Gateway Layer"
        APISIX["APISIX API Gateway<br/>(with AI Gateway plugins)"]
    end

    subgraph "Application Layer (Microservices)"
        direction LR
        AUTH[Auth Service]
        POLICY[Policy Service]
        PROJECT[Project Service]
        SECRET[Secret Service]
        AUDIT[Audit Service]
    end

    UI & CLI & EXT --> LB
    LB --> APISIX
    APISIX --> AUTH & POLICY & PROJECT & SECRET & AUDIT
```

### 2. Datacenter Internal Architecture

This diagram shows the components within a single datacenter, illustrating how the microservices interact with the data layer. Both datacenters (DC1 and DC2) follow this same structure.

```mermaid
graph TD
    subgraph "CMS Microservices"
        AUTH[Auth Service]
        POLICY[Policy Service]
        PROJECT[Project Service]
        SECRET[Secret Service]
        AUDIT[Audit Service]
    end
    
    subgraph "Data Layer"
        ETCD[(etcd Cluster)]
        VAULT[(HashiCorp Vault)]
        REDIS[(Redis Cache)]
    end

    AUTH --> REDIS & ETCD
    POLICY --> ETCD
    PROJECT --> ETCD
    SECRET --> VAULT
    AUDIT --> ETCD
```

### 3. Cross-Datacenter Replication

For high availability and disaster recovery, the data layer is replicated across both datacenters.

```mermaid
graph LR
    subgraph "Datacenter 1"
        ETCD1[(etcd)]
        VAULT1[(Vault)]
        REDIS1[(Redis)]
    end

    subgraph "Datacenter 2"
        ETCD2[(etcd)]
        VAULT2[(Vault)]
        REDIS2[(Redis)]
    end

    ETCD1 <-.->|Replication| ETCD2
    VAULT1 <-.->|Replication| VAULT2
    REDIS1 <-.->|Replication| REDIS2
```

### 4. External Dependencies & Observability

This diagram shows how the CMS interacts with external storage and the monitoring stack.

```mermaid
graph TD
    subgraph "CMS Microservices"
        direction LR
        SERVICES[Auth, Policy, Project, etc.]
    end

    subgraph "External Storage"
        GIT[(Git Repository<br/>Policy Backup)]
        OBJ[(Object Storage<br/>S3/MinIO)]
    end

    subgraph "Monitoring & Observability"
        PROM[Prometheus]
        GRAF[Grafana]
        ELK[ELK Stack]
        JAEGER[Jaeger Tracing]
    end

    SERVICES --> GIT
    SERVICES --> OBJ
    SERVICES --> PROM
    SERVICES --> JAEGER
    SERVICES --> ELK

    PROM --> GRAF
```

## Microservices Architecture

### Core Services

#### 1. Authentication & Authorization Service
- **Purpose**: Handle user authentication, JWT token management, RBAC
- **Technology**: FastAPI, JWT, OAuth2
- **Database**: Redis (sessions), etcd (user roles)
- **Features**:
  - Multi-tenant authentication
  - Role-based access control (CMS Admin, Platform Admin, Project User)
  - JWT token validation and refresh
  - Rate limiting

#### 2. Policy Management Service
- **Purpose**: Manage OPA policies (CRUD operations)
- **Technology**: FastAPI, OPA integration
- **Storage**: etcd (primary), Git (backup/versioning)
- **Features**:
  - Policy validation and testing
  - Version control integration
  - Policy deployment workflows
  - Rollback capabilities

#### 3. Project Management Service
- **Purpose**: Handle project onboarding and team management
- **Technology**: FastAPI
- **Storage**: etcd
- **Features**:
  - Project creation and configuration
  - Team member management
  - Project-level policy assignment
  - Multi-tenancy support

#### 4. Secret Management Service
- **Purpose**: Secure storage and retrieval of API keys
- **Technology**: FastAPI, HashiCorp Vault
- **Storage**: Vault (encrypted), etcd (metadata)
- **Features**:
  - Encrypted secret storage
  - Key rotation capabilities
  - Audit logging
  - Access policies

#### 5. Audit & Logging Service
- **Purpose**: Track all system activities and changes
- **Technology**: FastAPI, ELK Stack
- **Storage**: etcd, Elasticsearch
- **Features**:
  - Comprehensive audit trails
  - Policy change tracking
  - Access logging
  - Compliance reporting

## Data Architecture

### Primary Storage Strategy

```mermaid
graph LR
    subgraph "Data Storage Strategy"
        subgraph "etcd Cluster"
            ETCD_META[Policy Metadata]
            ETCD_PROJ[Project Config]
            ETCD_USER[User Roles]
            ETCD_AUDIT[Audit Logs]
        end
        
        subgraph "HashiCorp Vault"
            VAULT_API[API Keys]
            VAULT_CERT[Certificates]
            VAULT_DB[DB Credentials]
        end
        
        subgraph "Git Repository"
            GIT_POLICY[OPA Policy Files]
            GIT_VERSION[Version Control]
            GIT_BACKUP[Backup & Recovery]
        end
        
        subgraph "Redis Cache"
            REDIS_SESSION[User Sessions]
            REDIS_CACHE[Policy Cache]
            REDIS_RATE[Rate Limiting]
        end
        
        subgraph "Object Storage"
            OBJ_BACKUP[Configuration Backups]
            OBJ_LOGS[Long-term Logs]
            OBJ_REPORTS[Audit Reports]
        end
    end
```

### Data Flow & Consistency

1. **etcd**: Primary storage for configuration metadata, project settings, and user roles
2. **Git**: Version-controlled storage for OPA policies with full history
3. **Vault**: Encrypted storage for sensitive data (API keys, certificates)
4. **Redis**: Caching layer for performance and session management
5. **Object Storage**: Long-term backup and archival

## Security Architecture

### Multi-Layer Security

```mermaid
graph TB
    subgraph "Security Layers"
        subgraph "Network Security"
            TLS[TLS 1.3 Encryption]
            VPN[VPN/Private Networks]
            FW[Firewall Rules]
        end
        
        subgraph "Application Security"
            JWT[JWT Authentication]
            RBAC[Role-Based Access Control]
            RATE[Rate Limiting]
            VALID[Input Validation]
        end
        
        subgraph "Data Security"
            ENCRYPT[Encryption at Rest]
            VAULT_SEC[Vault Encryption]
            BACKUP_ENC[Encrypted Backups]
        end
        
        subgraph "Infrastructure Security"
            SCAN[Vulnerability Scanning]
            SECRETS[Secret Rotation]
            AUDIT_SEC[Security Auditing]
        end
    end
```

## Workflow Diagrams

### 1. Policy Management Workflow

```mermaid
sequenceDiagram
    participant PA as Platform Admin
    participant AUTH as Auth Service
    participant POLICY as Policy Service
    participant ETCD as etcd
    participant GIT as Git Repository
    participant OPA as OPA Engine

    PA->>AUTH: Login Request
    AUTH->>PA: JWT Token
    
    PA->>POLICY: Create/Update Policy Request
    POLICY->>AUTH: Validate Token & Permissions
    AUTH->>POLICY: Authorization Granted
    
    POLICY->>POLICY: Validate OPA Policy Syntax
    POLICY->>ETCD: Store Policy Metadata
    POLICY->>GIT: Commit Policy File
    POLICY->>OPA: Deploy Policy
    
    POLICY->>PA: Policy Updated Successfully
    
    Note over POLICY,GIT: Version control maintains history
    Note over ETCD,OPA: Real-time policy activation
```

### 2. Project Onboarding Workflow

```mermaid
sequenceDiagram
    participant PA as Platform Admin
    participant AUTH as Auth Service
    participant PROJ as Project Service
    participant POLICY as Policy Service
    participant SECRET as Secret Service
    participant ETCD as etcd

    PA->>AUTH: Authenticate
    AUTH->>PA: JWT Token
    
    PA->>PROJ: Create New Project
    PROJ->>AUTH: Verify Admin Permissions
    AUTH->>PROJ: Permission Granted
    
    PROJ->>ETCD: Create Project Configuration
    PROJ->>POLICY: Assign Default Policies
    PROJ->>SECRET: Create Project API Keys
    
    PA->>PROJ: Add Team Members
    PROJ->>AUTH: Create User Roles
    PROJ->>ETCD: Update Project Team
    
    PROJ->>PA: Project Onboarding Complete
    
    Note over PROJ,SECRET: Each project gets isolated resources
```

### 3. API Key Management Workflow

```mermaid
sequenceDiagram
    participant USER as Project User
    participant AUTH as Auth Service
    participant SECRET as Secret Service
    participant VAULT as HashiCorp Vault
    participant AUDIT as Audit Service

    USER->>AUTH: Request API Key Access
    AUTH->>SECRET: Validate User & Project
    SECRET->>AUTH: Authorization Check
    AUTH->>SECRET: Access Granted
    
    SECRET->>VAULT: Retrieve Encrypted API Key
    VAULT->>SECRET: Return Decrypted Key
    SECRET->>AUDIT: Log Access Event
    
    SECRET->>USER: Return API Key (Masked)
    
    Note over SECRET,VAULT: Keys never stored in plaintext
    Note over AUDIT: All access logged for compliance
```

### 4. Policy Request & Approval Workflow

```mermaid
sequenceDiagram
    participant PU as Project User
    participant PA as Platform Admin
    participant AUTH as Auth Service
    participant POLICY as Policy Service
    participant WORKFLOW as Workflow Engine
    participant ETCD as etcd

    PU->>WORKFLOW: Submit Policy Change Request
    WORKFLOW->>AUTH: Validate User Identity
    WORKFLOW->>ETCD: Store Request Details
    
    WORKFLOW->>PA: Notify Policy Change Request
    PA->>WORKFLOW: Review Request
    
    alt Request Approved
        PA->>POLICY: Approve & Implement Policy
        POLICY->>ETCD: Update Policy
        POLICY->>PU: Notify Policy Updated
    else Request Rejected
        PA->>WORKFLOW: Reject Request
        WORKFLOW->>PU: Notify Rejection with Reason
    end
    
    Note over WORKFLOW: Maintains audit trail of all requests
```

## Deployment Architecture

### Multi-Datacenter Setup

```mermaid
graph TB
    subgraph "Datacenter 1 (Primary)"
        subgraph "Compute Tier"
            VM1[VM1: Auth + Policy Services]
            VM2[VM2: Project + Secret Services]
            VM3[VM3: Audit + Monitoring]
        end
        
        subgraph "Data Tier"
            ETCD1[etcd Node 1]
            VAULT1[Vault Node 1]
            REDIS1[Redis Node 1]
        end
    end
    
    subgraph "Datacenter 2 (Secondary)"
        subgraph "Compute Tier"
            VM4[VM4: Auth + Policy Services]
            VM5[VM5: Project + Secret Services]
            VM6[VM6: Audit + Monitoring]
        end
        
        subgraph "Data Tier"
            ETCD2[etcd Node 2]
            VAULT2[Vault Node 2]
            REDIS2[Redis Node 2]
        end
    end
    
    subgraph "External Services"
        GIT_EXT[Git Repository]
        MONITOR[External Monitoring]
        BACKUP[Backup Storage]
    end
    
    ETCD1 -.->|Replication| ETCD2
    VAULT1 -.->|Replication| VAULT2
    REDIS1 -.->|Replication| REDIS2
    
    VM1 --> ETCD1
    VM2 --> VAULT1
    VM3 --> REDIS1
    
    VM4 --> ETCD2
    VM5 --> VAULT2
    VM6 --> REDIS2
```

## Technology Stack

### Core Technologies
- **Framework**: FastAPI (Python)
- **Authentication**: OAuth2 + JWT
- **API Gateway**: APISIX + AI Gateway
- **Container**: Docker (future Kubernetes migration)
- **Service Discovery**: etcd
- **Load Balancing**: HAProxy/Nginx

### Data Storage
- **Primary Config Store**: etcd cluster
- **Secret Management**: HashiCorp Vault
- **Version Control**: Git (GitLab/GitHub)
- **Caching**: Redis
- **Long-term Storage**: MinIO/S3

### Monitoring & Observability
- **Metrics**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Tracing**: Jaeger
- **Health Checks**: Custom FastAPI endpoints

### Security
- **Encryption**: TLS 1.3, AES-256
- **Secret Rotation**: Vault automatic rotation
- **Vulnerability Scanning**: Trivy/Anchore
- **Compliance**: SOC2, ISO 27001 ready

## Scalability Considerations

### Horizontal Scaling
- **Stateless Services**: All microservices designed stateless
- **Database Clustering**: etcd and Vault in cluster mode
- **Cache Distribution**: Redis Cluster for high availability
- **Load Distribution**: APISIX for intelligent routing

### Performance Optimization
- **Caching Strategy**: Multi-level caching (Redis, Application-level)
- **Connection Pooling**: Database connection optimization
- **Async Processing**: FastAPI async capabilities
- **Content Delivery**: CDN for static content

## Migration Strategy (VM to Kubernetes)

### Phase 1: VM Deployment (Current)
- Docker containers on VMs
- Manual orchestration
- File-based configuration

### Phase 2: Kubernetes Migration (Future)
- **Containerization**: All services containerized
- **Service Mesh**: Istio for advanced networking
- **Config Management**: Kubernetes ConfigMaps/Secrets
- **Auto-scaling**: HPA (Horizontal Pod Autoscaler)

### Migration Readiness
- Stateless design enables seamless migration
- Configuration externalization
- Health check endpoints for Kubernetes probes
- Graceful shutdown handling

## API Design Principles

### RESTful API Structure
```
/api/v1/auth/         # Authentication endpoints
/api/v1/policies/     # Policy management
/api/v1/projects/     # Project management
/api/v1/secrets/      # Secret management
/api/v1/audit/        # Audit and logging
/api/v1/health/       # Health checks
```

### API Standards
- **Versioning**: URL-based versioning (/api/v1/)
- **Authentication**: Bearer token (JWT)
- **Error Handling**: Standardized error responses
- **Rate Limiting**: Per-user and per-service limits
- **Documentation**: OpenAPI/Swagger integration

## Security Best Practices

### Access Control
- **Principle of Least Privilege**: Minimal required permissions
- **Multi-Factor Authentication**: Required for admin access
- **Session Management**: Secure session handling
- **API Rate Limiting**: Prevent abuse and DoS

### Data Protection
- **Encryption**: All data encrypted in transit and at rest
- **Key Management**: Automated key rotation
- **Backup Security**: Encrypted backups with retention policies
- **Audit Logging**: Comprehensive activity logging

## Monitoring & Alerting

### Key Metrics
- **Service Health**: Uptime, response times, error rates
- **Resource Usage**: CPU, memory, storage utilization
- **Security Events**: Authentication failures, unauthorized access
- **Business Metrics**: Policy changes, user activity

### Alert Categories
- **Critical**: Service outages, security breaches
- **Warning**: High resource usage, slow responses
- **Info**: Normal operational events

## Disaster Recovery

### Backup Strategy
- **Automated Backups**: Daily incremental, weekly full
- **Cross-Datacenter Replication**: Real-time data sync
- **Point-in-Time Recovery**: Policy and configuration rollback
- **Disaster Recovery Testing**: Regular DR drills

### Recovery Objectives
- **RTO (Recovery Time Objective)**: < 30 minutes
- **RPO (Recovery Point Objective)**: < 5 minutes
- **Data Integrity**: Zero data loss tolerance

## Conclusion

This architecture provides a robust, scalable, and secure foundation for the Configuration Management System. The design emphasizes:

1. **Scalability**: Horizontal scaling capabilities
2. **Security**: Multi-layer security approach
3. **Reliability**: High availability across datacenters
4. **Maintainability**: Modular microservices design
5. **Future-Proof**: Easy migration to Kubernetes

The stateless design and containerization strategy ensure smooth transition from VM-based deployment to Kubernetes orchestration, providing flexibility for future infrastructure evolution.
