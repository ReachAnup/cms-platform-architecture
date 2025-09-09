# API Design Specification

## API Overview

This document details the REST API design for the Configuration Management System (CMS).

## Base URL Structure
```
https://api.cms.yourdomain.com/api/v1/
```

## Authentication
All API endpoints require JWT authentication via Bearer token.

```http
Authorization: Bearer <jwt_token>
```

## Common Response Format

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "message": "Operation completed successfully",
  "timestamp": "2025-09-03T10:00:00Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {}
  },
  "timestamp": "2025-09-03T10:00:00Z"
}
```

## API Endpoints

### Authentication Service (`/api/v1/auth/`)

#### POST /auth/login
Authenticate user and return JWT token.

**Request:**
```json
{
  "username": "admin@company.com",
  "password": "secure_password",
  "mfa_token": "123456"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": "user_123",
      "username": "admin@company.com",
      "role": "platform_admin",
      "projects": ["project_1", "project_2"]
    }
  }
}
```

#### POST /auth/refresh
Refresh JWT token using refresh token.

#### POST /auth/logout
Logout user and invalidate tokens.

#### GET /auth/me
Get current user information.

### Policy Management Service (`/api/v1/policies/`)

#### GET /policies/
List all policies (filtered by user permissions).

**Query Parameters:**
- `project_id`: Filter by project
- `limit`: Number of items per page (default: 20)
- `offset`: Pagination offset
- `search`: Search in policy names/descriptions

**Response:**
```json
{
  "success": true,
  "data": {
    "policies": [
      {
        "id": "policy_123",
        "name": "project_access_policy",
        "description": "Controls access to project resources",
        "project_id": "project_1",
        "version": "1.2.0",
        "status": "active",
        "created_at": "2025-09-01T10:00:00Z",
        "updated_at": "2025-09-02T15:30:00Z",
        "created_by": "admin@company.com"
      }
    ],
    "total": 50,
    "limit": 20,
    "offset": 0
  }
}
```

#### GET /policies/{policy_id}
Get specific policy details.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "policy_123",
    "name": "project_access_policy",
    "description": "Controls access to project resources",
    "project_id": "project_1",
    "content": {
      "package": "authz",
      "rules": {
        "allow_read": {
          "condition": "input.user.role == 'project_user'",
          "resources": ["documents", "models"]
        }
      }
    },
    "version": "1.2.0",
    "status": "active",
    "metadata": {
      "tags": ["access_control", "project"],
      "category": "authorization"
    },
    "created_at": "2025-09-01T10:00:00Z",
    "updated_at": "2025-09-02T15:30:00Z",
    "created_by": "admin@company.com"
  }
}
```

#### POST /policies/
Create new policy.

**Request:**
```json
{
  "name": "new_project_policy",
  "description": "New policy for project access",
  "project_id": "project_1",
  "content": {
    "package": "authz",
    "rules": {
      "allow_read": {
        "condition": "input.user.role == 'project_user'",
        "resources": ["documents"]
      }
    }
  },
  "metadata": {
    "tags": ["access_control"],
    "category": "authorization"
  }
}
```

#### PUT /policies/{policy_id}
Update existing policy.

#### DELETE /policies/{policy_id}
Delete policy (soft delete with audit trail).

#### POST /policies/{policy_id}/validate
Validate policy syntax and test scenarios.

**Request:**
```json
{
  "test_cases": [
    {
      "input": {
        "user": {"role": "project_user", "id": "user_123"},
        "resource": "document_456",
        "action": "read"
      },
      "expected_result": true
    }
  ]
}
```

#### GET /policies/{policy_id}/versions
Get policy version history.

#### POST /policies/{policy_id}/rollback
Rollback to previous policy version.

### Project Management Service (`/api/v1/projects/`)

#### GET /projects/
List all projects (filtered by user access).

**Response:**
```json
{
  "success": true,
  "data": {
    "projects": [
      {
        "id": "project_1",
        "name": "AI Research Project",
        "description": "Machine learning research initiative",
        "status": "active",
        "team_count": 15,
        "policy_count": 8,
        "created_at": "2025-08-01T10:00:00Z",
        "admin": "project_admin@company.com"
      }
    ],
    "total": 10
  }
}
```

#### GET /projects/{project_id}
Get specific project details.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "project_1",
    "name": "AI Research Project",
    "description": "Machine learning research initiative",
    "status": "active",
    "settings": {
      "max_team_members": 50,
      "storage_quota": "10GB",
      "api_rate_limit": 1000
    },
    "team_members": [
      {
        "user_id": "user_123",
        "email": "researcher@company.com",
        "role": "project_user",
        "joined_at": "2025-08-05T10:00:00Z"
      }
    ],
    "policies": ["policy_123", "policy_456"],
    "api_keys": ["key_123"],
    "created_at": "2025-08-01T10:00:00Z",
    "admin": "project_admin@company.com"
  }
}
```

#### POST /projects/
Create new project.

**Request:**
```json
{
  "name": "New AI Project",
  "description": "Description of the new project",
  "admin_email": "admin@company.com",
  "settings": {
    "max_team_members": 20,
    "storage_quota": "5GB",
    "api_rate_limit": 500
  }
}
```

#### PUT /projects/{project_id}
Update project settings.

#### DELETE /projects/{project_id}
Archive project (soft delete).

#### POST /projects/{project_id}/members
Add team member to project.

**Request:**
```json
{
  "email": "newuser@company.com",
  "role": "project_user",
  "permissions": ["read_documents", "query_models"]
}
```

#### DELETE /projects/{project_id}/members/{user_id}
Remove team member from project.

#### PUT /projects/{project_id}/members/{user_id}
Update team member role/permissions.

### Secret Management Service (`/api/v1/secrets/`)

#### GET /secrets/
List secrets (metadata only, not values).

**Response:**
```json
{
  "success": true,
  "data": {
    "secrets": [
      {
        "id": "secret_123",
        "name": "openai_api_key",
        "type": "api_key",
        "project_id": "project_1",
        "created_at": "2025-09-01T10:00:00Z",
        "last_rotated": "2025-09-01T10:00:00Z",
        "expires_at": "2026-09-01T10:00:00Z",
        "status": "active"
      }
    ]
  }
}
```

#### GET /secrets/{secret_id}
Get secret value (with proper authorization).

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "secret_123",
    "name": "openai_api_key",
    "value": "sk-1234567890abcdef...",
    "type": "api_key",
    "metadata": {
      "provider": "openai",
      "usage": "rag_queries"
    }
  }
}
```

#### POST /secrets/
Create new secret.

**Request:**
```json
{
  "name": "new_api_key",
  "value": "secret_value_here",
  "type": "api_key",
  "project_id": "project_1",
  "metadata": {
    "provider": "anthropic",
    "usage": "model_queries"
  },
  "expires_at": "2026-09-01T10:00:00Z"
}
```

#### PUT /secrets/{secret_id}
Update secret value or metadata.

#### DELETE /secrets/{secret_id}
Delete secret (with confirmation).

#### POST /secrets/{secret_id}/rotate
Rotate secret value.

### Audit Service (`/api/v1/audit/`)

#### GET /audit/logs
Get audit logs with filtering.

**Query Parameters:**
- `user_id`: Filter by user
- `project_id`: Filter by project
- `action`: Filter by action type
- `start_date`: Start date filter
- `end_date`: End date filter
- `limit`: Items per page
- `offset`: Pagination offset

**Response:**
```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": "log_123",
        "timestamp": "2025-09-03T10:00:00Z",
        "user_id": "user_123",
        "action": "policy_update",
        "resource_type": "policy",
        "resource_id": "policy_123",
        "project_id": "project_1",
        "details": {
          "old_version": "1.1.0",
          "new_version": "1.2.0",
          "changes": ["added new rule for document access"]
        },
        "ip_address": "192.168.1.100",
        "user_agent": "CMS-CLI/1.0"
      }
    ],
    "total": 1000,
    "limit": 50,
    "offset": 0
  }
}
```

#### GET /audit/reports
Generate compliance reports.

**Query Parameters:**
- `report_type`: Type of report (compliance, security, usage)
- `project_id`: Filter by project
- `start_date`: Report start date
- `end_date`: Report end date
- `format`: Report format (json, pdf, csv)

### Health Check Service (`/api/v1/health/`)

#### GET /health/
Overall system health status.

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2025-09-03T10:00:00Z",
    "version": "1.0.0",
    "services": {
      "auth_service": "healthy",
      "policy_service": "healthy",
      "project_service": "healthy",
      "secret_service": "healthy",
      "audit_service": "healthy"
    },
    "dependencies": {
      "etcd": "healthy",
      "vault": "healthy",
      "redis": "healthy",
      "git": "healthy"
    }
  }
}
```

#### GET /health/detailed
Detailed health check with metrics.

#### GET /health/ready
Readiness probe for load balancers.

#### GET /health/live
Liveness probe for container orchestration.

## Error Codes

| Code | Description |
|------|-------------|
| AUTH_001 | Invalid credentials |
| AUTH_002 | Token expired |
| AUTH_003 | Insufficient permissions |
| POLICY_001 | Policy validation failed |
| POLICY_002 | Policy not found |
| POLICY_003 | Policy syntax error |
| PROJECT_001 | Project not found |
| PROJECT_002 | Project limit exceeded |
| SECRET_001 | Secret not found |
| SECRET_002 | Secret access denied |
| SYSTEM_001 | Internal server error |
| SYSTEM_002 | Service unavailable |

## Rate Limiting

### Default Limits
- **Authentication**: 10 requests/minute per IP
- **Policy Operations**: 100 requests/minute per user
- **Secret Access**: 50 requests/minute per user
- **Project Management**: 200 requests/minute per user

### Rate Limit Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1625097600
```

## Pagination

### Query Parameters
- `limit`: Number of items per page (default: 20, max: 100)
- `offset`: Number of items to skip

### Response Format
```json
{
  "data": {
    "items": [...],
    "total": 150,
    "limit": 20,
    "offset": 40,
    "has_more": true
  }
}
```

## Versioning Strategy

- **URL Versioning**: `/api/v1/`, `/api/v2/`
- **Backward Compatibility**: Maintained for at least 2 major versions
- **Deprecation Notice**: 6 months notice via headers and documentation

## SDK Support

### Python SDK Example
```python
from cms_client import CMSClient

client = CMSClient(
    base_url="https://api.cms.yourdomain.com",
    api_key="your_api_key"
)

# Get policies
policies = client.policies.list(project_id="project_1")

# Create policy
new_policy = client.policies.create({
    "name": "test_policy",
    "content": {...}
})
```

### CLI Tool Example
```bash
# Login
cms auth login --username admin@company.com

# List policies
cms policies list --project project_1

# Create policy
cms policies create --file policy.json

# Get secret
cms secrets get openai_api_key --project project_1
```
