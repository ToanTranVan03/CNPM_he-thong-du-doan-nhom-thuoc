import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

import app as app_module


class SymptomSuggestionsApiTest(unittest.TestCase):
    def setUp(self):
        self.original_cache = app_module.SYMPTOM_DICTIONARY_CACHE
        app_module.SYMPTOM_DICTIONARY_CACHE = [
            {
                "id": "headache",
                "label_vi": "Đau đầu",
                "label_en": "Headache",
                "keywords": ["đau đầu", "nhức đầu", "headache"],
                "source": "model",
            },
            {
                "id": "high_fever",
                "label_vi": "Sốt cao",
                "label_en": "High fever",
                "keywords": ["sốt cao", "nóng sốt"],
                "source": "database",
            },
            {
                "id": "cough",
                "label_vi": "Ho",
                "label_en": "Cough",
                "keywords": ["ho", "cough"],
                "source": "model",
            },
        ]
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.SYMPTOM_DICTIONARY_CACHE = self.original_cache

    def test_suggests_without_requiring_vietnamese_accents(self):
        response = self.client.get("/api/symptoms/suggestions?q=dau")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["suggestions"][0]["id"], "headache")

    def test_suggests_by_english_keyword(self):
        response = self.client.get("/api/symptoms/suggestions?q=head")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["suggestions"][0]["label_vi"], "Đau đầu")

    def test_suggests_from_keyword_inside_typing_sentence(self):
        response = self.client.get("/api/symptoms/suggestions?q=toi bi dau dau va met")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["suggestions"][0]["id"], "headache")

    def test_empty_keyword_returns_empty_list(self):
        response = self.client.get("/api/symptoms/suggestions?q=")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["suggestions"], [])

    def test_limit_is_applied(self):
        response = self.client.get("/api/symptoms/suggestions?q=h&limit=1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["suggestions"]), 1)

    def test_invalid_limit_returns_400(self):
        response = self.client.get("/api/symptoms/suggestions?q=ho&limit=abc")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
