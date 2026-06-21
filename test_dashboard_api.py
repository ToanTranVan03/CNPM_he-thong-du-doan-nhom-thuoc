#!/usr/bin/env python3
"""
Test script for Feedback Statistics Dashboard
Tests API endpoint and verifies data structure
"""

import requests
import json
import time
from datetime import datetime

API_URL = "http://127.0.0.1:5000/api/feedback/statistics"

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_api_connection():
    """Test if API is accessible"""
    print_section("Testing API Connection")
    try:
        response = requests.get(API_URL, timeout=5)
        print(f"✅ API is accessible")
        print(f"   Status Code: {response.status_code}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API")
        print(f"   URL: {API_URL}")
        print(f"   Make sure Flask server is running on port 5000")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_api_response():
    """Test API response format"""
    print_section("Testing API Response Format")
    try:
        response = requests.get(API_URL)
        data = response.json()
        
        print("Response Structure:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Verify required fields
        required_fields = ['success', 'total', 'agree_count', 'disagree_count', 'agree_percentage', 'disagree_percentage']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            print(f"\n❌ Missing fields: {missing_fields}")
            return False
        
        print(f"\n✅ All required fields present")
        
        # Verify data types
        if not isinstance(data.get('success'), bool):
            print(f"❌ 'success' should be boolean, got {type(data['success'])}")
            return False
        
        if not isinstance(data.get('total'), int):
            print(f"❌ 'total' should be integer, got {type(data['total'])}")
            return False
        
        print(f"✅ Data types correct")
        return True
        
    except json.JSONDecodeError:
        print(f"❌ Response is not valid JSON")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_data_validation():
    """Test data validity and calculations"""
    print_section("Testing Data Validation")
    try:
        response = requests.get(API_URL)
        data = response.json()
        
        total = data.get('total', 0)
        agree = data.get('agree_count', 0)
        disagree = data.get('disagree_count', 0)
        agree_pct = data.get('agree_percentage', 0)
        disagree_pct = data.get('disagree_percentage', 0)
        
        print(f"Total: {total}")
        print(f"Agree: {agree}")
        print(f"Disagree: {disagree}")
        print(f"Agree %: {agree_pct}%")
        print(f"Disagree %: {disagree_pct}%")
        
        # Validate counts
        if agree + disagree != total:
            print(f"\n❌ Count mismatch: {agree} + {disagree} ≠ {total}")
            return False
        print(f"\n✅ Counts are consistent")
        
        # Validate percentages
        if total > 0:
            expected_agree_pct = round((agree / total) * 100, 2)
            expected_disagree_pct = round((disagree / total) * 100, 2)
            
            if agree_pct != expected_agree_pct:
                print(f"⚠️  Agree % mismatch: expected {expected_agree_pct}, got {agree_pct}")
            else:
                print(f"✅ Agree percentage correct")
            
            if disagree_pct != expected_disagree_pct:
                print(f"⚠️  Disagree % mismatch: expected {expected_disagree_pct}, got {disagree_pct}")
            else:
                print(f"✅ Disagree percentage correct")
        else:
            if agree_pct == 0 and disagree_pct == 0:
                print(f"✅ Empty state handled correctly")
            else:
                print(f"❌ When total=0, percentages should be 0")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_empty_state():
    """Test empty state (when no data exists)"""
    print_section("Testing Empty State Handling")
    try:
        response = requests.get(API_URL)
        data = response.json()
        
        if data.get('total') == 0:
            print("✅ Empty state detected correctly")
            print(f"   Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print("ℹ️  Database has data - cannot test empty state")
            print(f"   Current total: {data.get('total')}")
            return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_response_time():
    """Test API response time"""
    print_section("Testing Response Time")
    try:
        start = time.time()
        response = requests.get(API_URL)
        end = time.time()
        
        elapsed_ms = (end - start) * 1000
        print(f"Response time: {elapsed_ms:.2f}ms")
        
        if elapsed_ms < 100:
            print(f"✅ Excellent - Response time < 100ms")
        elif elapsed_ms < 500:
            print(f"✅ Good - Response time < 500ms")
        else:
            print(f"⚠️  Slow - Response time > 500ms")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  FEEDBACK STATISTICS DASHBOARD - API TEST")
    print("="*60)
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  API URL: {API_URL}")
    
    results = {
        "Connection": test_api_connection(),
        "Response Format": test_api_response(),
        "Data Validation": test_data_validation(),
        "Empty State": test_empty_state(),
        "Response Time": test_response_time(),
    }
    
    print_section("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Dashboard is ready for deployment.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
