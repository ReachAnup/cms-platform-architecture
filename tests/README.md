# Integration Test Suite

This directory contains comprehensive integration tests for the CMS-OPA bundle architecture.

## Running the Tests

### Prerequisites

1. Ensure Docker and Docker Compose are installed
2. Navigate to the project root directory
3. Start all services:
   ```bash
   docker-compose up -d
   ```
4. Wait for all services to be healthy (about 30 seconds)

### Execute Tests

```bash
# Install test dependencies
pip install requests

# Run the integration test suite
python tests/integration_test.py
```

## Test Coverage

The integration test suite covers:

### 1. Service Health Checks
- ✅ CMS service health endpoint
- ✅ OPA service health endpoint  
- ✅ OPA bundle system status

### 2. Policy CRUD Operations
- ✅ Create policies via CMS
- ✅ Read policies from CMS
- ✅ Update existing policies
- ✅ List all policies
- ✅ Policy content validation

### 3. Bundle Generation & Caching
- ✅ Bundle endpoint returns valid tar.gz
- ✅ Bundle contains manifest, policies, and data
- ✅ Manifest structure validation
- ✅ ETag caching behavior
- ✅ ETag changes on policy updates

### 4. OPA Integration
- ✅ OPA polls CMS bundle endpoint
- ✅ Bundle loading and activation
- ✅ Policy compilation and availability
- ✅ Bundle status reporting

### 5. Policy Decision Validation
- ✅ Admin role decisions
- ✅ User role decisions  
- ✅ Resource ownership checks
- ✅ Unauthorized access denial

### 6. End-to-End Workflow
- ✅ Complete policy lifecycle
- ✅ Multi-user scenarios
- ✅ Team-based access control
- ✅ Real-world authorization patterns

## Test Scenarios

### Basic Authorization Test
```json
{
  "user": {"role": "admin", "id": "alice"},
  "resource": {"owner": "bob"}
}
```

### Team-Based Access Test  
```json
{
  "user": {"role": "manager", "team": "engineering", "id": "alice"},
  "resource": {"team": "engineering"}
}
```

### Resource Ownership Test
```json
{
  "user": {"role": "user", "id": "bob"},
  "resource": {"owner": "bob"}
}
```

## Expected Results

When all tests pass, you should see:

```
🎉 ALL INTEGRATION TESTS PASSED!
Your CMS-OPA bundle architecture is working correctly.
```

## Troubleshooting

### Common Issues

1. **Services not ready**
   - Wait longer for service startup
   - Check `docker-compose logs` for errors

2. **Connection refused**
   - Verify services are running: `docker-compose ps`
   - Check port conflicts

3. **Bundle polling not working**
   - Verify OPA configuration in `services/opa/config.yaml`
   - Check OPA logs: `docker-compose logs opa`

4. **Policy decisions incorrect**
   - Verify policy syntax in Rego
   - Check OPA compilation: `curl http://localhost:8181/v1/policies`

### Debug Commands

```bash
# Check service health
curl http://localhost:8080/health
curl http://localhost:8181/health

# Check OPA bundle status
curl http://localhost:8181/v1/status/bundles

# Get current bundle
curl http://localhost:8080/bundles/demo > bundle.tar.gz

# Test policy decision manually
curl -X POST http://localhost:8181/v1/data/demo/authz/allow \
  -H "Content-Type: application/json" \
  -d '{"input": {"user": {"role": "admin"}, "resource": {}}}'
```

## Test Environment

- **CMS**: http://localhost:8080
- **OPA**: http://localhost:8181  
- **etcd**: localhost:2379 (internal)
- **Bundle polling**: Every 15 seconds
- **ETag caching**: Enabled for efficiency

## Extending Tests

To add new test cases:

1. Add test methods to `IntegrationTestSuite` class
2. Follow naming convention: `test_feature_name()`
3. Use assertions with descriptive messages
4. Include cleanup in `cleanup()` method
5. Document new scenarios in this README
