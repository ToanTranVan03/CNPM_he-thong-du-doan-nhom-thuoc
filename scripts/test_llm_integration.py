"""Kiểm thử tích hợp LLM không gọi provider thật và không cần API key thật."""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.update({
    "DB_DISABLED": "1",
    "SEMANTIC_MATCH": "0",
    "LLM_CONTEXT_ENABLED": "1",
    "LLM_FALLBACK_ENABLED": "1",
    "LLM_API_KEY": "test-key-not-real",
    "LLM_BASE_URL": "https://provider.invalid/openai/v1",
    "LLM_MODEL": "test-model",
})

from backend import app as A  # noqa: E402
from backend import stats_source  # noqa: E402


def main() -> None:
    assert A.llm_context is not None
    assert A.llm_classify is not None
    assert A.llm_context_extract is not None
    assert A.context_safety is not None

    temp_dir = Path(tempfile.mkdtemp(prefix="llm_integration_"))
    stats_source.PREDICTION_LOG_PATH = temp_dir / "predictions.jsonl"
    expires = A.iso_utc(datetime.now(timezone.utc) + timedelta(hours=1))
    A.USERS_PATH = temp_dir / "users.json"
    A.USERS_PATH.write_text(json.dumps({"users": [{
        "id": "admin-test",
        "name": "Admin Test",
        "email": "admin@test.local",
        "password_hash": "unused",
        "role": "admin",
        "session_token": "ADMIN-TEST",
        "session_expires_at": expires,
    }]}), encoding="utf-8")

    original_context = A.llm_context.extract_context
    original_safety_extract = A.llm_context_extract.extract
    original_classify = A.llm_classify.classify_group
    try:
        A.llm_context_extract.extract = lambda _notes: None
        A.llm_context.extract_context = lambda _notes: {
            "symptoms_vi": ["buồn nôn", "tiêu chảy"],
            "contexts": [],
            "red_flags": [],
            "negated_vi": [],
        }
        with A.app.test_client() as client:
            response = client.post("/api/predict", json={
                "symptoms": [],
                "notes": "Bụng dạ cứ réo liên hồi, người nao nao sau bữa ăn.",
            })
            body = response.get_json() or {}
            assert response.status_code in (200, 422), body
            assert body.get("llm_context_used") is True, body
            assert body.get("suggestion_source") == "model_with_llm_context", body
            assert body.get("matched_symptoms"), body

            A.llm_context.extract_context = lambda _notes: {
                "symptoms_vi": [], "contexts": [], "red_flags": [], "negated_vi": [],
            }
            A.llm_classify.classify_group = lambda _notes, _groups: "bù dịch và điện giải"
            fallback = client.post("/api/predict", json={
                "symptoms": [],
                "notes": "Cách diễn đạt hoàn toàn mới mà từ điển chưa biết.",
            })
            fallback_body = fallback.get_json() or {}
            assert fallback.status_code == 422, fallback_body
            assert fallback_body.get("suggestion_source") == "llm_fallback", fallback_body
            assert fallback_body.get("suggested_group") == "bù dịch và điện giải", fallback_body

            status = client.get(
                "/api/admin/integrations/llm",
                headers={"Authorization": "Bearer ADMIN-TEST"},
            )
            status_body = status.get_json() or {}
            assert status.status_code == 200, status_body
            assert status_body["context"]["ready"] is True, status_body
            assert status_body["fallback_suggestion"]["ready"] is True, status_body
            assert "test-key-not-real" not in status.get_data(as_text=True)
    finally:
        A.llm_context.extract_context = original_context
        A.llm_context_extract.extract = original_safety_extract
        A.llm_classify.classify_group = original_classify

    print("LLM context + fallback suggestion integration: PASS")


if __name__ == "__main__":
    main()
