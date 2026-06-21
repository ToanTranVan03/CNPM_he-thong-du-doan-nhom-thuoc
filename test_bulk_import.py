#!/usr/bin/env python
"""
Test script for Bulk Import API
"""
import requests
import json
import os

BASE_URL = "http://localhost:5000"

def test_bulk_import_nhom_thuoc():
    """Test bulk import nhóm thuốc"""
    print("\n=== Testing Bulk Import Nhóm Thuốc ===")
    
    csv_file = "data/sample_nhom_thuoc.csv"
    if not os.path.exists(csv_file):
        print(f"Error: File {csv_file} not found")
        return False
    
    with open(csv_file, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            f"{BASE_URL}/api/bulk-import/nhom-thuoc",
            files=files
        )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200


def test_bulk_import_thuoc():
    """Test bulk import thuốc"""
    print("\n=== Testing Bulk Import Thuốc ===")
    
    csv_file = "data/sample_thuoc.csv"
    if not os.path.exists(csv_file):
        print(f"Error: File {csv_file} not found")
        return False
    
    with open(csv_file, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            f"{BASE_URL}/api/bulk-import/thuoc",
            files=files
        )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200


def test_download_templates():
    """Test downloading templates"""
    print("\n=== Testing Download Templates ===")
    
    endpoints = [
        ("/api/bulk-import/template/nhom-thuoc", "nhom_thuoc_template.csv"),
        ("/api/bulk-import/template/thuoc", "thuoc_template.csv")
    ]
    
    for endpoint, filename in endpoints:
        print(f"\nDownloading {endpoint}...")
        response = requests.get(f"{BASE_URL}{endpoint}")
        
        if response.status_code == 200:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"✓ Downloaded: {filename}")
            print(f"Content preview:\n{response.text[:200]}...")
        else:
            print(f"✗ Failed: {response.status_code}")
            print(f"Response: {response.text}")


if __name__ == "__main__":
    print("Starting Bulk Import API Tests...")
    print(f"Base URL: {BASE_URL}")
    
    try:
        # Download templates first
        test_download_templates()
        
        # Test bulk import
        test_bulk_import_nhom_thuoc()
        test_bulk_import_thuoc()
        
        print("\n✓ All tests completed!")
    except Exception as e:
        print(f"\n✗ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
