# Lớp dự phòng LLM (LLM fallback) — tùy chọn

> Mặc định **TẮT**. Khi bật, chỉ kích hoạt lúc pipeline rule/extraction **không trích được
> triệu chứng nào** (vá "diễn đạt lạ" / người dùng nêu thẳng tên bệnh). Output luôn là
> **tham khảo** (422), không phải gợi ý chắc chắn. Cấp cứu đã chặn TRƯỚC fallback; nhóm kê đơn → chuyển khám.

## Cơ chế
- Module `backend/llm_classify.py` (OpenAI-compatible, dùng `openai` SDK).
- Gọi trong `/api/predict` tại nhánh `if not active_symptoms` — chỉ khi extraction rỗng.
- Thất bại/thiếu key/thiếu gói `openai` → trả `None` → app chạy như cũ (no-op, không crash).

## Bật

Đặt các biến môi trường (vd qua `.env` hoặc `settings.json` env):

```
LLM_FALLBACK_ENABLED=1
LLM_API_KEY=<key>
LLM_BASE_URL=https://api.groq.com/openai/v1     # Groq (nhanh, free tier)
LLM_MODEL=llama-3.3-70b-versatile
# hoặc Gemini: LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/ , LLM_MODEL=gemini-2.5-flash
LLM_TIMEOUT=15
```

Để vừa tự động trích/chuẩn hóa ngữ cảnh tiếng Việt vừa dùng gợi ý dự phòng, phải bật
**cả hai** cờ `LLM_CONTEXT_ENABLED=1` và `LLM_FALLBACK_ENABLED=1`. Chỉ bật
`LLM_CONTEXT_ENABLED` không cho phép LLM tự chọn nhóm thuốc.

Admin có thể kiểm tra cấu hình đã được backend nạp (không trả API key) qua:

```text
GET /api/admin/integrations/llm
Authorization: Bearer <admin-token>
```

Cài client: `pip install openai`.

## Kiểm chứng (đã đo 2026-06-16)
- Cờ TẮT: no-op — `score_independent_probe` safety_recall 100%, stress 459/500 (y baseline).
- Cờ BẬT: safety suite vẫn 100%/459; ca extraction-rỗng có nghĩa rõ được nhận đúng nhóm
  (vd "cường giáp Basedow" → tuyến giáp; "nấm candida" → kháng nấm), cấp cứu vẫn chặn trước.
- Provider khuyến nghị: **Groq** (Llama-3.3-70B, ~1–2s) hoặc **Gemini Flash**. Tránh NVIDIA NIM Kimi
  (đo được ~160s + output thoái hóa — không dùng được).

## Lưu ý
- Free tier có rate limit (Groq ~30 req/phút) + có thể dùng dữ liệu để train → production thật nên dùng tier trả phí.
- Đây là lớp DỰ PHÒNG, không thay pipeline chính (rule/extraction vẫn xử lý mọi ca trích được).
