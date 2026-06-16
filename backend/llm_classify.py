"""Lớp DỰ PHÒNG: phân loại nhóm thuốc bằng LLM khi pipeline rule/extraction KHÔNG trích
được triệu chứng (đúng lỗ hổng "diễn đạt lạ").

Tách khỏi llm_context (vai trò chỉ TRÍCH XUẤT, cấm gợi thuốc). Module này CÓ đề xuất nhóm,
nhưng output LUÔN đi qua cổng an toàn ở app.py (cấp cứu đã chặn trước; high-risk -> chuyển khám;
fallback chỉ trả "tham khảo", không bao giờ là gợi ý chắc chắn).

Dùng OpenAI SDK (fingerprint chuẩn -> tránh Cloudflare 1010 của một số endpoint như Groq).
Mặc định TẮT (LLM_FALLBACK_ENABLED); mọi lỗi -> None (fallback im lặng, không crash pipeline).
"""
from __future__ import annotations

import os

ABSTAIN = "CAN_THEM_THONG_TIN"


def _truthy(v: str) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes"}


def fallback_enabled() -> bool:
    return _truthy(os.environ.get("LLM_FALLBACK_ENABLED", "0"))


def _env_any(*names: str, default: str = "") -> str:
    for n in names:
        v = os.environ.get(n)
        if v and v.strip():
            return v.strip()
    return default


def classify_group(notes: str, groups: list[str]) -> str | None:
    """Trả về 1 nhóm thuốc trong `groups`, hoặc None (né/cấp cứu/lỗi/chưa cấu hình/tắt)."""
    if not fallback_enabled() or not notes or not notes.strip() or not groups:
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
        sysp = (
            "Bạn là công cụ phân loại nhóm thuốc tham khảo cho dược sĩ. Đọc mô tả triệu chứng tiếng Việt "
            "và chọn DUY NHẤT 1 nhóm phù hợp nhất từ DANH SÁCH. Nếu có dấu hiệu CẤP CỨU (đau ngực dữ dội, "
            "khó thở nặng, yếu liệt, co giật, lơ mơ...) hoặc mô tả QUÁ MƠ HỒ, trả về đúng: " + ABSTAIN + ".\n"
            "Chỉ in tên nhóm (hoặc " + ABSTAIN + "), KHÔNG giải thích.\n\nDANH SÁCH NHÓM:\n- " + "\n- ".join(groups)
        )
        resp = cli.chat.completions.create(
            model=model, temperature=0, max_tokens=40,
            messages=[{"role": "system", "content": sysp},
                      {"role": "user", "content": f'Mô tả: "{notes.strip()}"\nNhóm:'}],
        )
        out = (resp.choices[0].message.content or "").strip().strip('"').strip()
        up = out.upper().replace(" ", "_")
        if ABSTAIN in up or "CẦN_THÊM" in up or "CAN_THEM" in up:
            return None
        for g in groups:
            if g.lower() in out.lower() or out.lower() in g.lower():
                return g
        return None
    except Exception:
        return None
