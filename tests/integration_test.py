#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite for CMS-OPA Bundle Architecture

This test suite validates the complete integration between:
- CMS (FastAPI service with policy management and bundle serving)
- etcd (Policy data storage)
- OPA (Open Policy Agent with bundle polling)

Test Coverage:
1. Service Health Checks
2. Policy CRUD Operations via CMS
3. Bundle Generation and ETag Caching
4. OPA Bundle Polling and Policy Loading
5. Policy Decision Validation
6. End-to-End Workflow Testing
"""

import requests
import time
import json
import tarfile
import io
import subprocess
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntegrationTestSuite:
    def __init__(self):
        self.cms_base_url = "http://localhost:8080"
        self.opa_base_url = "http://localhost:8181"
        self.test_policy_id = "test-policy-integration"
        self.test_data_key = "test-data-integration"
        
    def run_all_tests(self):
        """Run the complete integration test suite"""
        logger.info("Starting comprehensive integration test suite...")
        
        try:
            # Phase 1: Service Health Checks
            self.test_service_health()
            
            # Phase 2: Policy Management
            self.test_policy_crud_operations()
            
            # Phase 3: Bundle Generation and Caching
            self.test_bundle_generation()
            self.test_bundle_etag_caching()
            
            # Phase 4: OPA Integration
            self.test_opa_bundle_polling()
            self.test_policy_decisions()
            
            # Phase 5: End-to-End Workflow
            self.test_end_to_end_workflow()
            
            logger.info("✅ ALL TESTS PASSED! Integration is working correctly.")
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST FAILED: {e}")
            return False
    
    def test_service_health(self):
        """Test that all services are healthy and responding"""
        logger.info("Testing service health checks...")
        
        # Test CMS health
        response = requests.get(f"{self.cms_base_url}/health")
        assert response.status_code == 200, f"CMS health check failed: {response.status_code}"
        logger.info("✓ CMS service is healthy")
        
        # Test OPA health
        response = requests.get(f"{self.opa_base_url}/health")
        assert response.status_code == 200, f"OPA health check failed: {response.status_code}"
        logger.info("✓ OPA service is healthy")
        
        # Test OPA bundle status
        response = requests.get(f"{self.opa_base_url}/v1/status")
        assert response.status_code == 200, f"OPA status check failed: {response.status_code}"
        
        status_data = response.json()
        assert "result" in status_data, "No result in OPA status"
        assert "bundles" in status_data["result"], "No bundles in OPA status"
        logger.info("✓ OPA bundle system is active")
    
    def test_policy_crud_operations(self):
        """Test policy CRUD operations through CMS"""
        logger.info("Testing policy CRUD operations...")
        
        # Test CREATE/UPDATE policy (using PUT)
        policy_content = '''package demo

default allow = false

# Allow admins to do anything
allow if {
    input.user.role == "admin"
}

# Allow users to access their own resources
allow if {
    input.user.role == "user"
    input.resource.owner == input.user.id
}'''
        
        test_data = {"users": {"alice": {"role": "admin"}, "bob": {"role": "user"}}}
        
        response = requests.put(
            f"{self.cms_base_url}/policies/demo",
            json={"rego": policy_content, "data": test_data}
        )
        assert response.status_code == 200, f"Policy creation failed: {response.status_code}"
        logger.info("✓ Policy created successfully")
        
        # Test READ policy
        response = requests.get(f"{self.cms_base_url}/policies/demo")
        assert response.status_code == 200, f"Policy read failed: {response.status_code}"
        policy_data = response.json()
        assert "demo" in policy_data["rego"], "Policy content mismatch"
        assert "alice" in policy_data["data"]["users"], "Data content mismatch"
        logger.info("✓ Policy read successfully")
        
        # Test UPDATE policy (using PUT again)
        updated_policy = policy_content.replace('default allow = false', 'default allow = true')
        response = requests.put(
            f"{self.cms_base_url}/policies/demo",
            json={"rego": updated_policy}
        )
        assert response.status_code == 200, f"Policy update failed: {response.status_code}"
        logger.info("✓ Policy updated successfully")
    
    def test_bundle_generation(self):
        """Test bundle generation and content validation"""
        logger.info("Testing bundle generation...")
        
        # Get bundle
        response = requests.get(f"{self.cms_base_url}/bundles/demo")
        assert response.status_code == 200, f"Bundle generation failed: {response.status_code}"
        assert response.headers["content-type"] == "application/gzip", "Bundle content type incorrect"
        logger.info("✓ Bundle generated with correct content type")
        
        # Validate bundle content
        bundle_data = io.BytesIO(response.content)
        with tarfile.open(fileobj=bundle_data, mode='r:gz') as tar:
            members = tar.getnames()
            assert "demo.rego" in members, "Bundle missing rego file"
            assert "data.json" in members, "Bundle missing data file"
            logger.info("✓ Bundle contains required files")
            
            # Validate rego content
            rego_file = tar.extractfile("demo.rego")
            rego_content = rego_file.read().decode()
            assert "package demo" in rego_content, "Rego content incorrect"
            logger.info("✓ Bundle rego content is valid")
    
    def test_bundle_etag_caching(self):
        """Test ETag caching for bundle endpoint"""
        logger.info("Testing bundle ETag caching...")
        
        # First request
        response1 = requests.get(f"{self.cms_base_url}/bundles/demo")
        assert response1.status_code == 200, "First bundle request failed"
        etag1 = response1.headers.get("etag")
        assert etag1 is not None, "ETag not present in response"
        logger.info(f"✓ First request returned ETag: {etag1}")
        
        # Second request with ETag
        headers = {"If-None-Match": etag1}
        response2 = requests.get(f"{self.cms_base_url}/bundles/demo", headers=headers)
        assert response2.status_code == 304, f"Expected 304 Not Modified, got {response2.status_code}"
        logger.info("✓ ETag caching working correctly (304 Not Modified)")
        
        # Modify policy to change ETag
        new_policy = '''
        package demo
        default allow = false
        allow { input.user.role == "superadmin" }
        '''
        response = requests.put(
            f"{self.cms_base_url}/policies/demo",
            json={"rego": new_policy}
        )
        assert response.status_code == 200, "Policy update failed"
        
        # Request with old ETag should return new content
        response3 = requests.get(f"{self.cms_base_url}/bundles/demo", headers=headers)
        assert response3.status_code == 200, "Expected new content after policy change"
        etag2 = response3.headers.get("etag")
        assert etag2 != etag1, "ETag should change after policy modification"
        logger.info(f"✓ ETag changed after policy modification: {etag2}")
    
    def test_opa_bundle_polling(self):
        """Test that OPA successfully polls and loads bundles"""
        logger.info("Testing OPA bundle polling...")
        
        # Wait for OPA to poll (configured for 15 seconds, wait a bit longer)
        logger.info("Waiting for OPA to poll bundle (up to 20 seconds)...")
        time.sleep(20)
        
        # Check OPA bundle status
        response = requests.get(f"{self.opa_base_url}/v1/status")
        assert response.status_code == 200, "OPA status check failed"
        
        status_data = response.json()
        assert "result" in status_data, "No result in OPA status"
        assert "bundles" in status_data["result"], "No bundles in OPA status"
        
        demo_bundle = status_data["result"]["bundles"]["demo"]
        assert "last_successful_activation" in demo_bundle, "Bundle has no activation record"
        logger.info(f"✓ OPA loaded bundle successfully")
        
        # Check that policies are loaded
        response = requests.get(f"{self.opa_base_url}/v1/policies")
        assert response.status_code == 200, "Failed to get OPA policies"
        policies = response.json()["result"]
        
        # Look for our test policy (should be demo/demo.rego)
        found_policy = False
        for policy in policies:
            if "demo/" in policy.get("id", "") and "demo.rego" in policy.get("id", ""):
                found_policy = True
                logger.info(f"Found policy: {policy['id']}")
                break
        
        assert found_policy, f"Test policy not found in OPA. Available policies: {[p.get('id') for p in policies]}"
        logger.info("✓ Test policy loaded in OPA")
    
    def test_policy_decisions(self):
        """Test policy decision making through OPA"""
        logger.info("Testing policy decisions...")
        
        # Test admin access (should be allowed)
        admin_input = {
            "input": {
                "user": {"role": "admin", "id": "alice"},
                "resource": {"owner": "bob"}
            }
        }
        
        response = requests.post(
            f"{self.opa_base_url}/v1/data/demo/allow",
            json=admin_input
        )
        assert response.status_code == 200, "Admin decision request failed"
        result = response.json()
        assert result.get('result') is True, "Admin should be allowed access"
        logger.info(f"✓ Admin decision result: {result.get('result')}")
        
        # Test regular user access to own resource
        user_input = {
            "input": {
                "user": {"role": "user", "id": "bob"},
                "resource": {"owner": "bob"}
            }
        }
        
        response = requests.post(
            f"{self.opa_base_url}/v1/data/demo/allow",
            json=user_input
        )
        assert response.status_code == 200, "User decision request failed"
        result = response.json()
        assert result.get('result') is True, "User should access own resource"
        logger.info(f"✓ User own resource decision result: {result.get('result')}")
        
        # Test unauthorized access
        unauthorized_input = {
            "input": {
                "user": {"role": "user", "id": "bob"},
                "resource": {"owner": "alice"}
            }
        }
        
        response = requests.post(
            f"{self.opa_base_url}/v1/data/demo/allow",
            json=unauthorized_input
        )
        assert response.status_code == 200, "Unauthorized decision request failed"
        result = response.json()
        assert result.get("result") is False, "Unauthorized access should be denied"
        logger.info("✓ Unauthorized access correctly denied")
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow"""
        logger.info("Testing end-to-end workflow...")
        
        # Step 1: Create a new policy with specific rules
        policy_content = '''package demo

default allow = false

# Allow admins everything
allow if {
    input.user.role == "admin"
}

# Allow users to access their own resources
allow if {
    input.user.role == "user"
    input.user.id == input.resource.owner
}

# Allow managers to access team resources
allow if {
    input.user.role == "manager"
    input.user.team == input.resource.team
}'''
        
        # Step 2: Add supporting data
        team_data = {
            "teams": {
                "engineering": {"members": ["alice", "bob"]},
                "marketing": {"members": ["charlie", "diana"]}
            },
            "users": {
                "alice": {"role": "manager", "team": "engineering"},
                "bob": {"role": "user", "team": "engineering"},
                "charlie": {"role": "admin", "team": "marketing"},
                "diana": {"role": "user", "team": "marketing"}
            }
        }
        
        response = requests.put(
            f"{self.cms_base_url}/policies/demo",
            json={"rego": policy_content, "data": team_data}
        )
        assert response.status_code == 200, "E2E policy creation failed"
        logger.info("✓ E2E policy and data created")
        
        # Step 3: Wait for OPA to poll and load new bundle
        logger.info("Waiting for OPA to poll updated bundle...")
        time.sleep(20)
        
        # Step 4: Test various scenarios
        test_cases = [
            {
                "name": "Admin access",
                "input": {"user": {"role": "admin", "id": "charlie"}, "resource": {"owner": "anyone"}},
                "expected": True
            },
            {
                "name": "Manager team access",
                "input": {"user": {"role": "manager", "team": "engineering", "id": "alice"}, 
                         "resource": {"team": "engineering"}},
                "expected": True
            },
            {
                "name": "User own resource",
                "input": {"user": {"role": "user", "id": "bob"}, "resource": {"owner": "bob"}},
                "expected": True
            },
            {
                "name": "User cross-team access",
                "input": {"user": {"role": "user", "id": "bob"}, "resource": {"owner": "diana"}},
                "expected": False
            }
        ]
        
        for test_case in test_cases:
            response = requests.post(
                f"{self.opa_base_url}/v1/data/demo/allow",
                json={"input": test_case["input"]}
            )
            assert response.status_code == 200, f"Decision request failed for {test_case['name']}"
            result = response.json().get("result")
            assert result == test_case["expected"], \
                f"E2E test '{test_case['name']}' failed: expected {test_case['expected']}, got {result}"
            logger.info(f"✓ E2E test '{test_case['name']}': {result}")
        
        logger.info("✓ E2E workflow completed successfully")
    
    def _cleanup_test_policy(self):
        """Clean up test policy if it exists"""
        # For the demo CMS, we just reset to a clean state
        try:
            # Reset to a basic policy
            default_policy = '''
            package demo
            default allow = false
            '''
            requests.put(
                f"{self.cms_base_url}/policies/demo",
                json={"rego": default_policy, "data": {}}
            )
        except:
            pass  # Ignore cleanup errors
    
    def cleanup(self):
        """Clean up all test data"""
        logger.info("Cleaning up test data...")
        self._cleanup_test_policy()


def main():
    """Run the integration test suite"""
    print("=" * 80)
    print("CMS-OPA Bundle Architecture Integration Test Suite")
    print("=" * 80)
    
    test_suite = IntegrationTestSuite()
    
    try:
        success = test_suite.run_all_tests()
        if success:
            print("\n" + "=" * 80)
            print("🎉 ALL INTEGRATION TESTS PASSED!")
            print("Your CMS-OPA bundle architecture is working correctly.")
            print("=" * 80)
            return 0
        else:
            print("\n" + "=" * 80)
            print("❌ INTEGRATION TESTS FAILED!")
            print("Please check the logs above for details.")
            print("=" * 80)
            return 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    finally:
        test_suite.cleanup()


if __name__ == "__main__":
    exit(main())
