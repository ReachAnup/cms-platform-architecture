#!/usr/bin/env python3
"""
Simple Debug Test for Integration Issues
"""
import requests
import time

def debug_integration():
    print('=== Integration Test Debug ===')

    # Test 1: Check if we can create a proper policy
    policy_data = {
        'rego': '''package demo

default allow = false

# Allow admins to do anything
allow if {
    input.user.role == "admin"
}

# Allow users to access their own resources  
allow if {
    input.user.role == "user"
    input.user.id == input.resource.owner
}'''
    }

    print('1. Creating policy...')
    try:
        resp = requests.put('http://localhost:8080/policies/demo', json=policy_data)
        print(f'   Status: {resp.status_code}')
        if resp.status_code == 200:
            print(f'   Response: {resp.json()}')
        else:
            print(f'   Error: {resp.text}')
    except Exception as e:
        print(f'   Exception: {e}')

    print('\n2. Waiting 25 seconds for OPA polling...')
    time.sleep(25)

    print('3. Checking OPA policies...')
    try:
        resp = requests.get('http://localhost:8181/v1/policies')
        if resp.status_code == 200:
            policies = resp.json()['result']
            print(f'   Found {len(policies)} policies')
            for p in policies:
                print(f'   - {p["id"]}')
                content = p['raw']
                if len(content) > 200:
                    print(f'     Content: {content[:200]}...')
                else:
                    print(f'     Content: {content}')
        else:
            print(f'   Error: {resp.status_code}')
    except Exception as e:
        print(f'   Exception: {e}')

    print('\n4. Testing policy decision...')
    try:
        test_input = {
            'input': {
                'user': {'role': 'admin', 'id': 'alice'},
                'resource': {'owner': 'bob'}
            }
        }
        resp = requests.post('http://localhost:8181/v1/data/demo/allow', json=test_input)
        if resp.status_code == 200:
            result = resp.json()
            print(f'   Decision: {result.get("result", "unknown")}')
        else:
            print(f'   Error: {resp.status_code} - {resp.text}')
    except Exception as e:
        print(f'   Exception: {e}')

if __name__ == "__main__":
    debug_integration()
