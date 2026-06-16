"""Trích NGỮ CẢNH AN TOÀN bằng LLM (semantic) để bắt cách nói MỚI mà lexicon sót:
bệnh nền, thuốc đang dùng, tuổi, thai kỳ, dị ứng thuốc.

LLM chỉ TRÍCH (không quyết định, không gợi thuốc) -> context_safety (rule) quyết định an toàn.
Trả kèm CỤM CHỮ kích hoạt để vòng học lưu lại (data/learned_context.jsonl).

Dùng OpenAI SDK (tránh Cloudflare 1010 của Groq). Mặc định TẮT (LLM_CONTEXT_ENABLED).
Mọi lỗi -> None (im lặng, pipeline lexicon vẫn chạy).
"""
from __future__ import annotations

import json
import os
import re

FLAGS = ("renal", "hepatic", "peptic_ulcer", "asthma", "heart_failure", "bleeding")


def _truthy(v: str) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes"}


def enabled() -> bool:
    return _truthy(os.environ.get("LLM_CONTEXT_ENABLED", "0"))


def _env_any(*names: str, default: str = "") -> str:
    for n in names:
        v = os.environ.get(n)
        if v and v.strip():
            return v.strip()
    return default


_SYSTEM = (
    "Bạn là bộ TRÍCH XUẤT thông tin an toàn từ mô tả triệu chứng tiếng Việt. CHỈ trích, KHÔNG "
    "chẩn đoán, KHÔNG gợi ý thuốc. Trả về DUY NHẤT một JSON object theo schema, mỗi mục kèm 'phrase' "
    "là CỤM CHỮ NGẮN nguyên văn trong mô tả đã kích hoạt (để hệ học). Nếu không có thì để mảng rỗng/false.\n"
    "Schema:\n"
    '{\n'
    '  "comorbidities": [{"flag": "renal|hepatic|peptic_ulcer|asthma|heart_failure|bleeding", "phrase": "..."}],\n'
    '  "on_anticoagulant": {"value": true/false, "phrase": "..."},\n'
    '  "pregnant": {"value": true/false, "phrase": "..."},\n'
    '  "age_group": {"value": "infant|child|elderly|adult", "phrase": "..."},\n'
    '  "drug_allergy": {"value": true/false, "phrase": "..."}\n'
    "}\n"
    "Quy ước flag bệnh nền: renal=bệnh/suy thận; hepatic=bệnh gan/xơ gan; peptic_ulcer=loét/viêm dạ dày tá tràng; "
    "asthma=hen suyễn; heart_failure=suy tim; bleeding=rối loạn đông máu. "
    "drug_allergy=triệu chứng (mề đay/ngứa/phát ban) xuất hiện SAU khi dùng/tiêm thuốc. "
    "Chỉ trả JSON, không markdown, không giải thích."
)


def _parse_json(raw: str) -> dict | None:
    s = re.sub(r"^```(?:json)?|```$", "", (raw or "").strip(), flags=re.MULTILINE).strip()
    if not s.startswith("{"):
        l, r = s.find("{"), s.rfind("}")
        if l >= 0 and r > l:
            s = s[l:r + 1]
    try:
        d = json.loads(s)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def extract(notes: str) -> dict | None:
    if not enabled() or not notes or not notes.strip():
        return None
    key = _env_any("LLM_API_KEY", "DEEPSEEK_API_KEY")
    base = _env_any("LLM_BASE_URL", "DEEPSEEK_BASE_URL").rstrip("/")
    model = _env_any("LLM_MODEL", "DEEPSEEK_MODEL")
    if not (key and base and model):
        return None
    try:
        timeout = min(max(float(os.environ.get("LLM_TIMEOUT", "15")), 1.0), 30.0)
    except ValueError:
        timeout = 15.0
    try:
        from openai import OpenAI

        cli = OpenAI(api_key=key, base_url=base, timeout=timeout)
        resp = cli.chat.completions.create(
            model=model, temperature=0, max_tokens=500,
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": f'Mô tả: "{notes.strip()}"'}],
        )
        return _parse_json(resp.choices[0].message.content)
    except Exception:
        return None
