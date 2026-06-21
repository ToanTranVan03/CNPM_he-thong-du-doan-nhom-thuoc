#!/usr/bin/env python3
"""
Test script for new Symptom Suggester APIs
"""
import requests
import json
from time import sleep

BASE_URL = "http://127.0.0.1:5000"

def test_common_symptoms():
    """Test /api/symptoms/common endpoint"""
    print("\n" + "="*80)
    print("TEST: /api/symptoms/common")
    print("="*80)
    
    try:
        response = requests.get(f"{BASE_URL}/api/symptoms/common?limit=5")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ SUCCESS - Total symptoms: {data.get('total')}")
            print(f"Sample symptoms:")
            for symptom in data.get('data', [])[:3]:
                print(f"  - {symptom.get('label_vi')} ({symptom.get('label_en')})")
        else:
            print(f"✗ ERROR: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"✗ EXCEPTION: {e}")

def test_search_symptoms():
    """Test /api/symptoms/search endpoint"""
    print("\n" + "="*80)
    print("TEST: /api/symptoms/search")
    print("="*80)
    
    test_queries = ["sốt", "ho", "fever", "cough"]
    
    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        try:
            response = requests.get(f"{BASE_URL}/api/symptoms/search?q={query}&limit=5")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✓ Found {data.get('total')} results")
                    for symptom in data.get('data', [])[:2]:
                        print(f"  - {symptom.get('label_vi')} ({symptom.get('label_en')})")
                else:
                    print(f"✗ API returned success=false")
            else:
                print(f"✗ HTTP Error: {response.status_code}")
        except Exception as e:
            print(f"✗ EXCEPTION: {e}")

def test_empty_search():
    """Test search with no query"""
    print("\n" + "="*80)
    print("TEST: /api/symptoms/search (no query)")
    print("="*80)
    
    try:
        response = requests.get(f"{BASE_URL}/api/symptoms/search")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 400:
            print(f"✓ Correctly rejected empty query")
            print(f"Response: {response.json()}")
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"✗ EXCEPTION: {e}")

def main():
    """Run all tests"""
    print("Starting Symptom Suggester API Tests...")
    print(f"Base URL: {BASE_URL}")
    
    # Give server time to start
    sleep(2)
    
    test_common_symptoms()
    test_search_symptoms()
    test_empty_search()
    
    print("\n" + "="*80)
    print("All tests completed!")
    print("="*80)

if __name__ == "__main__":
    main()
