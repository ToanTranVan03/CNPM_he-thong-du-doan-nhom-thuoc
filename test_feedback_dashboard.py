#!/usr/bin/env python
"""
Test script for Feedback Statistics API endpoint
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import app, db
from models import Feedback
import json

def test_feedback_api():
    """Test feedback statistics endpoint"""
    print("=" * 60)
    print("Testing Feedback Statistics API")
    print("=" * 60)
    
    with app.app_context():
        # Create tables
        db.create_all()
        print("✓ Database initialized")
        
        # Clear existing feedback
        Feedback.query.delete()
        db.session.commit()
        print("✓ Cleared existing feedback")
        
        # Test 1: Empty state
        print("\n--- Test 1: Empty State ---")
        with app.test_client() as client:
            response = client.get('/api/feedback/statistics')
            data = response.get_json()
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            assert response.status_code == 200
            assert data['success'] == True
            assert data['total'] == 0
            print("✓ Empty state test passed")
        
        # Test 2: Add some feedback
        print("\n--- Test 2: Adding Feedback ---")
        feedback_data = [
            {'feedback_type': 'agree', 'user_id': 1, 'comment': 'Chính xác'},
            {'feedback_type': 'agree', 'user_id': 2, 'comment': 'Cũng đúng'},
            {'feedback_type': 'agree', 'user_id': 3},
            {'feedback_type': 'disagree', 'user_id': 4, 'comment': 'Sai rồi'},
        ]
        
        with app.test_client() as client:
            for fb_data in feedback_data:
                response = client.post(
                    '/api/feedback',
                    json=fb_data,
                    content_type='application/json'
                )
                print(f"POST /api/feedback: {response.status_code}")
                assert response.status_code == 201
        
        print(f"✓ Added {len(feedback_data)} feedback records")
        
        # Test 3: Statistics with data
        print("\n--- Test 3: Statistics With Data ---")
        with app.test_client() as client:
            response = client.get('/api/feedback/statistics')
            data = response.get_json()
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            assert response.status_code == 200
            assert data['success'] == True
            assert data['total'] == 4
            assert data['agree_count'] == 3
            assert data['disagree_count'] == 1
            assert data['agree_percentage'] == 75.0
            assert data['disagree_percentage'] == 25.0
            print("✓ Statistics with data test passed")
        
        # Test 4: Invalid feedback
        print("\n--- Test 4: Invalid Feedback Type ---")
        with app.test_client() as client:
            response = client.post(
                '/api/feedback',
                json={'feedback_type': 'invalid'},
                content_type='application/json'
            )
            print(f"Status: {response.status_code}")
            data = response.get_json()
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            assert response.status_code == 400
            print("✓ Invalid feedback type test passed")
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)

if __name__ == '__main__':
    try:
        test_feedback_api()
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
