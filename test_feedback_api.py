#!/usr/bin/env python
"""
Test script for Feedback Statistics API
Demonstrates the functionality of:
  - POST /api/feedback (submit feedback)
  - GET /api/feedback/statistics (get statistics)
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

def test_feedback_api():
    print("=" * 70)
    print("FEEDBACK STATISTICS API TEST")
    print("=" * 70)
    print()
    
    # Test 1: Submit multiple feedback entries
    print("TEST 1: Submitting feedback entries...")
    print("-" * 70)
    
    feedback_data = [
        {
            "prediction_id": 1,
            "user_id": 1,
            "feedback_type": "agree",
            "comment": "Kết quả chính xác, triệu chứng khớp với chẩn đoán"
        },
        {
            "prediction_id": 2,
            "user_id": 1,
            "feedback_type": "agree",
            "comment": None
        },
        {
            "prediction_id": 3,
            "user_id": 2,
            "feedback_type": "agree",
            "comment": "Đúng hướng điều trị"
        },
        {
            "prediction_id": 4,
            "user_id": 2,
            "feedback_type": "disagree",
            "comment": "Nên gợi ý nhóm thuốc khác"
        },
        {
            "prediction_id": 5,
            "user_id": 3,
            "feedback_type": "disagree",
            "comment": "Triệu chứng không khớp"
        },
    ]
    
    for i, feedback in enumerate(feedback_data, 1):
        try:
            response = requests.post(
                f"{BASE_URL}/api/feedback",
                json=feedback,
                timeout=10
            )
            
            if response.status_code == 201:
                data = response.json()
                print(f"✓ Feedback {i}: {feedback['feedback_type'].upper()} - Thành công")
            else:
                print(f"✗ Feedback {i}: Lỗi HTTP {response.status_code}")
        except Exception as e:
            print(f"✗ Feedback {i}: {str(e)}")
    
    print()
    
    # Test 2: Get feedback statistics
    print("TEST 2: Getting feedback statistics...")
    print("-" * 70)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/feedback/statistics",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print("✓ API Response: SUCCESS")
                print()
                print("STATISTICS RESULT:")
                print(f"  • Total Feedback:        {data['total']}")
                print(f"  • Agree Count:           {data['agree_count']}")
                print(f"  • Disagree Count:        {data['disagree_count']}")
                print(f"  • Agree Percentage:      {data['agree_percentage']}%")
                print(f"  • Disagree Percentage:   {data['disagree_percentage']}%")
                print()
                
                # Validation
                print("VALIDATION:")
                total = data['total']
                agree = data['agree_count']
                disagree = data['disagree_count']
                
                if agree + disagree == total:
                    print("✓ Count validation: PASS (agree + disagree = total)")
                else:
                    print("✗ Count validation: FAIL")
                
                if data['agree_percentage'] + data['disagree_percentage'] == 100.0 and total > 0:
                    print("✓ Percentage validation: PASS (percentages sum to 100%)")
                elif total == 0 and data['agree_percentage'] == 0 and data['disagree_percentage'] == 0:
                    print("✓ Percentage validation: PASS (zero case handled correctly)")
                else:
                    print("✗ Percentage validation: FAIL")
                    
            else:
                print(f"✗ API returned error: {data.get('message')}")
        else:
            print(f"✗ HTTP Error {response.status_code}")
            
    except Exception as e:
        print(f"✗ Request failed: {str(e)}")
    
    print()
    
    # Test 3: Test edge cases
    print("TEST 3: Testing edge cases...")
    print("-" * 70)
    
    # Invalid feedback type
    print("Testing invalid feedback_type...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/feedback",
            json={
                "prediction_id": 100,
                "feedback_type": "invalid_type",
                "comment": "Test"
            },
            timeout=10
        )
        if response.status_code == 400:
            print("✓ Invalid feedback_type correctly rejected (HTTP 400)")
        else:
            print(f"✗ Expected HTTP 400, got {response.status_code}")
    except Exception as e:
        print(f"✗ Request failed: {str(e)}")
    
    print()
    
    # Test 4: Empty database edge case
    print("TEST 4: Empty data handling...")
    print("-" * 70)
    print("This test would need a separate database state.")
    print("When total = 0, the API should return:")
    print("  - agree_count: 0")
    print("  - disagree_count: 0")
    print("  - agree_percentage: 0")
    print("  - disagree_percentage: 0")
    print("  - No division by zero errors")
    
    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    test_feedback_api()
