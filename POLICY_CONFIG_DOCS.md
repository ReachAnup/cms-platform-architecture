# Policy Configuration Files Documentation

This directory contains JSON configuration files used for policy management in the CMS system.

## Files Overview

### 1. `corrected_policy.json`
**Purpose**: Policy configuration for CMS API endpoint `PUT /policies/demo`
**API Endpoint**: `http://localhost:8080/policies/demo`

```json
{
    "rego": "<policy_content>",  // OPA Rego policy content with proper 'if' syntax
    "data": null                 // Optional policy data (null if not needed)
}
```

**Field Descriptions**:
- `rego`: Contains the OPA policy written in Rego language with proper syntax for OPA v1.7+
- `data`: Optional field for policy-specific data structures

**Usage**: 
```bash
curl -X PUT http://localhost:8080/policies/demo \
     -H "Content-Type: application/json" \
     -d @corrected_policy.json
```

### 2. `updated_policy.json`
**Purpose**: Legacy format (kept for reference)
**Status**: This format was initially used but incorrect for the CMS API

```json
{
    "content": "<policy_content>"  // Incorrect field name for CMS API
}
```

**Note**: This file uses `content` field which was incorrect. The CMS API expects `rego` field.

## Policy Syntax Notes

The policy content uses OPA Rego v1.7+ syntax which requires:
- `if` keyword before rule bodies
- Proper package declaration
- Structured access control rules

## Integration with System

1. **Policy Storage**: Policies are stored in etcd key-value store
2. **Bundle Generation**: CMS generates OPA bundles from stored policies  
3. **OPA Polling**: OPA polls CMS every 15-20 seconds for bundle updates
4. **Policy Evaluation**: OPA evaluates policies for authorization decisions

## Testing

Run integration tests to verify the complete workflow:
```bash
python tests/integration_test.py
```
