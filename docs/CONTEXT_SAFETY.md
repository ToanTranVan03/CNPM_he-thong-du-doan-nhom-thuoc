# Tầng NGỮ CẢNH - AN TOÀN (+ vòng học)

Vá điểm mù "túi triệu chứng": đọc CẢ CÂU để bắt yếu tố quyết định an toàn (bệnh nền, tuổi, thai kỳ,
thuốc đang dùng, dị ứng thuốc, phản vệ) và CHẶN gợi ý chống chỉ định.

## 3 lớp (phòng thủ chồng)
1. **Lexicon** (`backend/context_safety.py`) — LUÔN bật, deterministic, nhanh. Từ khóa tiếng Việt cho
   bệnh nền/thuốc/tuổi/thai kỳ. Bệnh gan/thận dò GIỮ DẤU (tránh va chạm `gân≠gan`, `thân≠thận`).
2. **LLM trích ngữ cảnh** (`backend/llm_context_extract.py`) — TÙY CHỌN (gated `LLM_CONTEXT_ENABLED`).
   Đọc semantic để bắt CÁCH NÓI MỚI lexicon sót (vd "bao tử"≈loét dạ dày, "ông nội"≈người già,
   "thuốc loãng máu"≈chống đông). Dùng OpenAI SDK (Groq/Gemini...). Lỗi/thiếu key -> bỏ qua, lexicon vẫn chạy.
3. **Vòng HỌC** — khi LLM bắt được cụm chữ mà lexicon SÓT, lưu vào `data/learned_context.jsonl`
   (gitignored, trạng thái runtime). Lần sau lexicon TỰ bắt cụm đó (không cần LLM) -> hệ giỏi dần.

## Logic an toàn (sau khi gộp cờ lexicon + LLM)
- NSAID × {loét dạ dày, suy thận, bệnh gan, hen, suy tim, rối loạn đông máu, đang dùng chống đông} -> CHẶN.
- Paracetamol × bệnh gan -> CHẶN (độc gan).
- Thai kỳ -> cảnh báo hỏi bác sĩ sản (NSAID -> chặn).
- Trẻ sơ sinh -> chặn (khám nhi); trẻ em/người già -> cảnh báo.
- "sau khi uống/tiêm thuốc + nổi mề đay" -> DỊ ỨNG THUỐC (ngừng thuốc nghi ngờ).
- Sưng môi/lưỡi/họng + khó thở, hoặc "phản vệ" -> CẤP CỨU.

## Bật LLM trích ngữ cảnh (+ học)
```
LLM_CONTEXT_ENABLED=1
LLM_API_KEY=<key>           # Groq: gsk_... | Gemini: AIza...
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile
```
Cài: `pip install openai`. Mặc định TẮT -> chỉ lexicon + learned (không gọi mạng).

## Kiểm chứng (2026-06-16)
- `scripts/test_context_safety.py`: 14/14 PASS. Antigravity v9: 12/12 PASS.
- LLM off (mặc định) + learned: benchmark 100/100/92.5%, safety_recall 100%, stress 459/500.
- Vòng học: "đau bao tử" -> peptic_ulcer, "Ông nội" -> elderly tự bắt sau khi học.
