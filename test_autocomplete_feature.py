#!/usr/bin/env python3
"""
Test cases for Autocomplete Symptoms Feature
Tests all aspects of the autocomplete functionality
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

class TestAutocomplete:
    def __init__(self):
        self.session = requests.Session()
        self.passed = 0
        self.failed = 0
    
    def log(self, test_name, passed, message=""):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"   → {message}")
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def test_api_health(self):
        """Test if API is running"""
        try:
            response = self.session.get(f"{BASE_URL}/api/symptoms/common?limit=5")
            self.log("API Health Check", response.status_code == 200, 
                    f"Status: {response.status_code}")
        except Exception as e:
            self.log("API Health Check", False, str(e))
    
    def test_autocomplete_empty_query(self):
        """Test autocomplete with empty query - should return common symptoms"""
        try:
            response = self.session.get(f"{BASE_URL}/api/symptoms/autocomplete")
            data = response.json()
            
            success = (
                data.get('success') == True and
                'data' in data and
                'total' in data
            )
            self.log("Autocomplete - Empty Query", success,
                    f"Returns {data.get('total', 0)} common symptoms")
        except Exception as e:
            self.log("Autocomplete - Empty Query", False, str(e))
    
    def test_autocomplete_fuzzy_search(self):
        """Test fuzzy search - Vietnamese query"""
        try:
            response = self.session.get(f"{BASE_URL}/api/symptoms/autocomplete?q=sot")
            data = response.json()
            
            success = (
                data.get('success') == True and
                data.get('query') == 'sot' and
                len(data.get('data', [])) > 0
            )
            
            # Check if "Sốt" is in results
            labels = [item.get('label_vi', '') for item in data.get('data', [])]
            has_sot = any('sốt' in label.lower() for label in labels)
            
            self.log("Autocomplete - Fuzzy Search (Việt)", success and has_sot,
                    f"Found {len(data.get('data', []))} results with 'Sốt' in results: {has_sot}")
        except Exception as e:
            self.log("Autocomplete - Fuzzy Search (Việt)", False, str(e))
    
    def test_autocomplete_english_search(self):
        """Test autocomplete with English query"""
        try:
            response = self.session.get(f"{BASE_URL}/api/symptoms/autocomplete?q=fever")
            data = response.json()
            
            success = (
                data.get('success') == True and
                data.get('query') == 'fever' and
                len(data.get('data', [])) > 0
            )
            
            # Check if "Fever" is in results
            labels = [item.get('label_en', '') for item in data.get('data', [])]
            has_fever = any('fever' in label.lower() for label in labels)
            
            self.log("Autocomplete - English Search", success and has_fever,
                    f"Found {len(data.get('data', []))} results with 'Fever': {has_fever}")
        except Exception as e:
            self.log("Autocomplete - English Search", False, str(e))
    
    def test_autocomplete_no_results(self):
        """Test autocomplete with query that has no results"""
        try:
            response = self.session.get(f"{BASE_URL}/api/symptoms/autocomplete?q=xyzabc123notexist")
            data = response.json()
            
            success = (
                data.get('success') == True and
                len(data.get('data', [])) == 0 and
                data.get('total') == 0
            )
            
            self.log("Autocomplete - No Results", success,
                    f"Correctly returns 0 results for non-existent symptom")
        except Exception as e:
            self.log("Autocomplete - No Results", False, str(e))
    
    def test_autocomplete_result_structure(self):
        """Test that autocomplete results have correct structure"""
        try:
            response = self.session.get(f"{BASE_URL}/api/symptoms/autocomplete?q=sot&limit=5")
            data = response.json()
            
            if not data.get('success'):
                self.log("Autocomplete - Result Structure", False, "Not successful")
                return
            
            items = data.get('data', [])
            if len(items) == 0:
                self.log("Autocomplete - Result Structure", False, "No items in response")
                return
            
            # Check first item structure
            item = items[0]
            required_fields = ['id', 'label_vi', 'label_en', 'score']
            has_all_fields = all(field in item for field in required_fields)
            
            score_valid = isinstance(item.get('score'), (int, float)) and 0 <= item.get('score', 0) <= 1
            
            self.log("Autocomplete - Result Structure", has_all_fields and score_valid,
                    f"Item has fields: {required_fields}, score valid: {score_valid}")
        except Exception as e:
            self.log("Autocomplete - Result Structure", False, str(e))
    
    def test_autocomplete_score_sorting(self):
        """Test that results are sorted by score (highest first)"""
        try:
            response = self.session.get(f"{BASE_URL}/api/symptoms/autocomplete?q=sot")
            data = response.json()
            items = data.get('data', [])
            
            if len(items) < 2:
                self.log("Autocomplete - Score Sorting", True,
                        "Only 1 or fewer items, cannot test sorting")
                return
            
            # Check if scores are in descending order
            scores = [item.get('score', 0) for item in items]
            is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
            
            self.log("Autocomplete - Score Sorting", is_sorted,
                    f"Scores in descending order: {[f'{s:.2f}' for s in scores[:3]]}...")
        except Exception as e:
            self.log("Autocomplete - Score Sorting", False, str(e))
    
    def test_autocomplete_limit_param(self):
        """Test limit parameter"""
        try:
            # Test with limit=5
            response = self.session.get(f"{BASE_URL}/api/symptoms/autocomplete?limit=5")
            data = response.json()
            count = len(data.get('data', []))
            
            success = count <= 5 and data.get('success') == True
            self.log("Autocomplete - Limit Parameter", success,
                    f"Requested limit=5, got {count} results")
        except Exception as e:
            self.log("Autocomplete - Limit Parameter", False, str(e))
    
    def test_autocomplete_threshold_param(self):
        """Test threshold parameter"""
        try:
            # High threshold (strict) - should return fewer results
            response1 = self.session.get(f"{BASE_URL}/api/symptoms/autocomplete?q=sot&threshold=0.9")
            data1 = response1.json()
            count1 = len(data1.get('data', []))
            
            # Low threshold (loose) - should return more results
            response2 = self.session.get(f"{BASE_URL}/api/symptoms/autocomplete?q=sot&threshold=0.3")
            data2 = response2.json()
            count2 = len(data2.get('data', []))
            
            # Low threshold should have >= high threshold results
            success = count2 >= count1
            
            self.log("Autocomplete - Threshold Parameter", success,
                    f"Threshold 0.9: {count1} results, Threshold 0.3: {count2} results")
        except Exception as e:
            self.log("Autocomplete - Threshold Parameter", False, str(e))
    
    def test_autocomplete_response_time(self):
        """Test API response time (should be < 500ms)"""
        try:
            start = time.time()
            response = self.session.get(f"{BASE_URL}/api/symptoms/autocomplete?q=sot")
            elapsed = (time.time() - start) * 1000  # Convert to ms
            
            success = elapsed < 500
            self.log("Autocomplete - Response Time", success,
                    f"Response time: {elapsed:.0f}ms (target: <500ms)")
        except Exception as e:
            self.log("Autocomplete - Response Time", False, str(e))
    
    def test_autocomplete_case_insensitive(self):
        """Test that search is case-insensitive"""
        try:
            # Test different cases
            queries = ['sot', 'SOT', 'Sot', 'sOt']
            results_count = []
            
            for query in queries:
                response = self.session.get(f"{BASE_URL}/api/symptoms/autocomplete?q={query}")
                data = response.json()
                count = len(data.get('data', []))
                results_count.append(count)
            
            # All should return same number of results (case-insensitive)
            all_same = all(c == results_count[0] for c in results_count)
            
            self.log("Autocomplete - Case Insensitive", all_same,
                    f"All queries returned {results_count[0]} results (consistent)")
        except Exception as e:
            self.log("Autocomplete - Case Insensitive", False, str(e))
    
    def test_common_symptoms_endpoint(self):
        """Test /api/symptoms/common endpoint"""
        try:
            response = self.session.get(f"{BASE_URL}/api/symptoms/common?limit=10")
            data = response.json()
            
            success = (
                data.get('success') == True and
                'data' in data and
                len(data.get('data', [])) <= 10
            )
            
            self.log("API - Common Symptoms", success,
                    f"Returns {len(data.get('data', []))} common symptoms")
        except Exception as e:
            self.log("API - Common Symptoms", False, str(e))
    
    def test_search_endpoint(self):
        """Test /api/symptoms/search endpoint"""
        try:
            response = self.session.get(f"{BASE_URL}/api/symptoms/search?q=sot&limit=10")
            data = response.json()
            
            success = (
                data.get('success') == True and
                'data' in data
            )
            
            self.log("API - Search Endpoint", success,
                    f"Found {len(data.get('data', []))} matching symptoms")
        except Exception as e:
            self.log("API - Search Endpoint", False, str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("🧪 AUTOCOMPLETE FEATURE TEST SUITE")
        print("="*60 + "\n")
        
        self.test_api_health()
        print()
        
        print("📊 Testing Autocomplete Endpoint:")
        self.test_autocomplete_empty_query()
        self.test_autocomplete_fuzzy_search()
        self.test_autocomplete_english_search()
        self.test_autocomplete_no_results()
        self.test_autocomplete_result_structure()
        self.test_autocomplete_score_sorting()
        self.test_autocomplete_limit_param()
        self.test_autocomplete_threshold_param()
        self.test_autocomplete_response_time()
        self.test_autocomplete_case_insensitive()
        print()
        
        print("📊 Testing Other Endpoints:")
        self.test_common_symptoms_endpoint()
        self.test_search_endpoint()
        print()
        
        print("="*60)
        print(f"📈 Test Results: {self.passed} passed, {self.failed} failed")
        print("="*60 + "\n")
        
        return self.failed == 0

if __name__ == '__main__':
    import sys
    
    print("⏳ Waiting for API server to be ready...")
    time.sleep(2)
    
    tester = TestAutocomplete()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
