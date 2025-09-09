#!/usr/bin/env python3
"""
Quick test to validate CMS-OPA integration
"""

import requests
import time
import json

def main():
    cms_url = "http://localhost:8080"
    opa_url = "http://localhost:8181"
    
    print("=== Quick CMS-OPA Integration Test ===")
    
    # 1. Test service health
    print("1. Testing service health...")
    cms_health = requests.get(f"{cms_url}/health")
    opa_health = requests.get(f"{opa_url}/health")
    print(f"   CMS Health: {cms_health.status_code}")
    print(f"   OPA Health: {opa_health.status_code}")
    
    # 2. Update policy via CMS
    print("2. Updating policy via CMS...")
    policy = '''
package demo

default allow = false

allow {
    input.user.role == "admin"
}

allow {
    input.user.role == "user"
    input.user.id == input.resource.owner
}
'''
    
    data = {
        "users": {
            "alice": {"role": "admin"},
            "bob": {"role": "user"}
        }
    }
    
    response = requests.put(f"{cms_url}/policies/demo", json={"rego": policy, "data": data})
    print(f"   Policy update: {response.status_code}")
    
    # 3. Check bundle is generated
    print("3. Checking bundle generation...")
    bundle_resp = requests.get(f"{cms_url}/bundles/demo")
    print(f"   Bundle generation: {bundle_resp.status_code}")
    print(f"   Bundle size: {len(bundle_resp.content)} bytes")
    
    # 4. Wait for OPA to poll
    print("4. Waiting for OPA to poll (20 seconds)...")
    time.sleep(20)
    
    # 5. Check OPA status
    print("5. Checking OPA bundle status...")
    status_resp = requests.get(f"{opa_url}/v1/status")
    if status_resp.status_code == 200:
        status = status_resp.json()
        if "bundles" in status["result"]:
            print(f"   Bundles loaded: {list(status['result']['bundles'].keys())}")
        else:
            print("   No bundles found in status")
    
    # 6. Test policy decisions
    print("6. Testing policy decisions...")
    
    # Admin should be allowed
    admin_test = {
        "input": {
            "user": {"role": "admin", "id": "alice"},
            "resource": {"owner": "bob"}
        }
    }
    
    admin_resp = requests.post(f"{opa_url}/v1/data/demo/allow", json=admin_test)
    admin_result = admin_resp.json().get("result", False)
    print(f"   Admin access: {admin_result}")
    
    # User accessing own resource should be allowed
    user_test = {
        "input": {
            "user": {"role": "user", "id": "bob"},
            "resource": {"owner": "bob"}
        }
    }
    
    user_resp = requests.post(f"{opa_url}/v1/data/demo/allow", json=user_test)
    user_result = user_resp.json().get("result", False)
    print(f"   User own resource: {user_result}")
    
    # User accessing other's resource should be denied
    unauthorized_test = {
        "input": {
            "user": {"role": "user", "id": "bob"},
            "resource": {"owner": "alice"}
        }
    }
    
    unauth_resp = requests.post(f"{opa_url}/v1/data/demo/allow", json=unauthorized_test)
    unauth_result = unauth_resp.json().get("result", False)
    print(f"   User cross-access: {unauth_result}")
    
    # 7. Results
    print("\n=== Test Results ===")
    success = (
        cms_health.status_code == 200 and
        opa_health.status_code == 200 and
        response.status_code == 200 and
        bundle_resp.status_code == 200 and
        admin_result is True and
        user_result is True and
        unauth_result is False
    )
    
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ CMS service is healthy")
        print("✅ OPA service is healthy")
        print("✅ Policy updates work via CMS")
        print("✅ Bundle generation works")
        print("✅ OPA loads policies from bundles")
        print("✅ Policy decisions work correctly")
        print("\nYour CMS-OPA bundle architecture is working correctly!")
    else:
        print("❌ Some tests failed:")
        print(f"   CMS Health: {'✅' if cms_health.status_code == 200 else '❌'}")
        print(f"   OPA Health: {'✅' if opa_health.status_code == 200 else '❌'}")
        print(f"   Policy Update: {'✅' if response.status_code == 200 else '❌'}")
        print(f"   Bundle Generation: {'✅' if bundle_resp.status_code == 200 else '❌'}")
        print(f"   Admin Access: {'✅' if admin_result else '❌'}")
        print(f"   User Own Resource: {'✅' if user_result else '❌'}")
        print(f"   Unauthorized Denied: {'✅' if not unauth_result else '❌'}")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
