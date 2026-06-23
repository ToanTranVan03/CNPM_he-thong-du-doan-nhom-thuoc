"""Test tầng LLM ngữ cảnh (vòng 5) bằng MOCK/STUB — KHÔNG gọi mạng thật.

Gồm 2 phần:
1. Unit test backend/llm_context.py: mock requests.post (disabled, thiếu key, JSON hợp lệ/hỏng,
   sai schema, timeout, 401).
2. Integration test /api/predict: stub A.llm_context.extract_context để kiểm augment triệu chứng,
   phủ định, cổng an toàn head_trauma, cảnh báo rượu — mà không cần API key/mạng.

Chạy: python scripts/test_llm_context_mock.py
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

os.environ["DB_DISABLED"] = "1"  # test logic, JSON-mode — không ghi lịch sử vào Postgres
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")


class FakeResp:
    def __init__(self, status_code, payload=None, raise_json=False):
        self.status_code = status_code
        self._payload = payload
        self._raise_json = raise_json

    def json(self):
        if self._raise_json:
            raise ValueError("not json")
        return self._payload


def _content(obj_str):
    return {"choices": [{"message": {"content": obj_str}}]}


VALID_JSON = (
    '{"symptoms_vi": ["đau đầu", "buồn nôn"], '
    '"contexts": [{"type": "head_trauma", "text": "va đập vào đầu"}], '
    '"red_flags": ["head_trauma"], "negated_vi": ["sốt"]}'
)


def unit_tests():
    print("== UNIT: llm_context ==")
    import llm_context as L

    # 1. Disabled -> None, không gọi mạng.
    os.environ["LLM_CONTEXT_ENABLED"] = "0"
    with patch.object(L, "requests") as rq:
        check("disabled -> None", L.extract_context("đau đầu") is None)
        check("disabled -> không gọi requests", not rq.post.called)

    # Bật cho các test còn lại.
    os.environ["LLM_CONTEXT_ENABLED"] = "1"

    # 2. Thiếu API key -> None, không gọi mạng.
    os.environ["DEEPSEEK_API_KEY"] = ""
    with patch.object(L, "requests") as rq:
        check("thiếu key -> None", L.extract_context("đau đầu") is None)
        check("thiếu key -> không gọi requests", not rq.post.called)

    os.environ["DEEPSEEK_API_KEY"] = "test-key"

    # 3. JSON hợp lệ -> dict đủ 4 key.
    with patch.object(L.requests, "post", return_value=FakeResp(200, _content(VALID_JSON))):
        out = L.extract_context("Tôi đau đầu sau va đập")
        check("JSON hợp lệ -> dict", isinstance(out, dict))
        check("đủ 4 key", out and set(out) == {"symptoms_vi", "contexts", "red_flags", "negated_vi"})
        check("red_flag head_trauma", out and out["red_flags"] == ["head_trauma"])

    # 4. content không phải JSON -> None.
    with patch.object(L.requests, "post", return_value=FakeResp(200, _content("xin chào không phải json"))):
        check("content không JSON -> None", L.extract_context("x") is None)

    # 5. Sai schema (enum red_flag lạ) -> None.
    bad = _content('{"symptoms_vi": [], "contexts": [], "red_flags": ["xxx"], "negated_vi": []}')
    with patch.object(L.requests, "post", return_value=FakeResp(200, bad)):
        check("enum lạ -> None", L.extract_context("x") is None)

    # 6. Thiếu key trong schema -> None.
    miss = _content('{"symptoms_vi": []}')
    with patch.object(L.requests, "post", return_value=FakeResp(200, miss)):
        check("thiếu key schema -> None", L.extract_context("x") is None)

    # 7. drug_group thừa bị bỏ qua, vẫn hợp lệ nếu đủ 4 key.
    extra = _content('{"symptoms_vi": ["ho"], "contexts": [], "red_flags": [], "negated_vi": [], "drug_group": "kháng sinh"}')
    with patch.object(L.requests, "post", return_value=FakeResp(200, extra)):
        out = L.extract_context("x")
        check("bỏ qua drug_group thừa", isinstance(out, dict) and "drug_group" not in out)

    # 8. Timeout/RequestException -> None (sau retry).
    with patch.object(L.requests, "post", side_effect=Exception("timeout")):
        check("exception mạng -> None", L.extract_context("x") is None)

    # 9. 401 -> None.
    with patch.object(L.requests, "post", return_value=FakeResp(401, {})):
        check("401 -> None", L.extract_context("x") is None)


def integration_tests():
    print("== INTEGRATION: /api/predict (stub extract_context) ==")
    os.environ["LLM_CONTEXT_ENABLED"] = "1"
    os.environ["DEEPSEEK_API_KEY"] = "test-key"
    import app as A
    client = A.app.test_client()

    def with_stub(payload):
        return patch.object(A.llm_context, "extract_context", lambda notes: payload)

    # A. Augment triệu chứng: notes nghèo keyword nhưng LLM trả triệu chứng map được.
    with with_stub({"symptoms_vi": ["đau đầu", "buồn nôn"], "contexts": [], "red_flags": [], "negated_vi": []}):
        r = client.post("/api/predict", json={"notes": "Trong người khó chịu", "symptoms": []})
        d = r.get_json() or {}
        matched = " ".join(d.get("matched_symptoms_vi", [])).lower()
        check("augment: có triệu chứng map từ LLM", r.status_code in (200, 422) and ("đau đầu" in matched or "buồn nôn" in matched))

    # B. Negation: LLM phủ định 'sốt' -> không xuất hiện trong matched.
    with with_stub({"symptoms_vi": ["sốt", "ho"], "contexts": [], "red_flags": [], "negated_vi": ["sốt"]}):
        r = client.post("/api/predict", json={"notes": "mô tả chung", "symptoms": []})
        d = r.get_json() or {}
        matched = " ".join(d.get("matched_symptoms_vi", [])).lower()
        check("negation: 'sốt' bị loại", "sốt" not in matched)

    # C. Head trauma red flag -> 422 emergency.
    with with_stub({"symptoms_vi": ["đau đầu", "buồn nôn"], "contexts": [{"type": "head_trauma", "text": "va đập vào đầu"}], "red_flags": ["head_trauma"], "negated_vi": []}):
        r = client.post("/api/predict", json={"notes": "Tôi thấy choáng sau cú va", "symptoms": []})
        d = r.get_json() or {}
        check("head_trauma -> 422 emergency", r.status_code == 422 and d.get("score_type") == "emergency")
        check("head_trauma -> không gợi ý thuốc", not d.get("disease_vi"))

    # D. Alcohol context + giảm đau hạ sốt -> chặn (422 needs_more).
    with with_stub({"symptoms_vi": ["đau đầu"], "contexts": [{"type": "alcohol", "text": "vừa uống rượu nhiều"}], "red_flags": [], "negated_vi": []}):
        r = client.post("/api/predict", json={"notes": "Tôi đau đầu", "symptoms": []})
        d = r.get_json() or {}
        err = (d.get("error") or "") + (d.get("quality_message") or "")
        check("alcohol -> không kê vô điều kiện", r.status_code == 422 or "rượu" in err.lower())

    # E. suicide red flag -> thông điệp khủng hoảng.
    with with_stub({"symptoms_vi": [], "contexts": [], "red_flags": ["suicide_self_harm"], "negated_vi": []}):
        r = client.post("/api/predict", json={"notes": "tâm trạng tệ", "symptoms": []})
        d = r.get_json() or {}
        check("suicide -> 422 + thông điệp hỗ trợ", r.status_code == 422 and "115" in (d.get("error") or ""))

    # F. LLM trả None -> hành vi như cũ (không crash).
    with patch.object(A.llm_context, "extract_context", lambda notes: None):
        r = client.post("/api/predict", json={"notes": "Tôi bị ho có đờm, sổ mũi", "symptoms": []})
        check("LLM None -> không crash", r.status_code in (200, 422))


def main():
    unit_tests()
    integration_tests()
    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
