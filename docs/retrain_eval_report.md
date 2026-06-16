# Báo cáo eval retrain — baseline vs candidate (2026-06-16)

> Candidate: `models_retrain_vi/` (templated + natural EN + **natural VI dịch máy NLLB**), serving hybrid raw-VI.
> Baseline: `models/` (production hiện tại). KHÔNG promote — xem kết luận.

## Bảng so sánh

| Phép đo | Baseline `models/` | Candidate `models_retrain_vi/` | Đánh giá |
|---|---|---|---|
| **test_vi_cases (VN viết tay, độc lập)** ⭐ | **74.0%** | **70.0%** | 🔻 regression |
| QA độc lập — group_accuracy | 94.1% | 88.2% | 🔻 regression |
| QA độc lập — abstain_accuracy | 93.8% | 75.0% | 🔻 regression |
| QA độc lập — safety_recall | 100% | **100%** | ✅ giữ |
| QA — red_flag_drug / false_emergency / contract | 0 / 0 / 0 | **0 / 0 / 0** | ✅ giữ |
| stress 500 | 459/500 | 459/500 | ✅ giữ |
| gretel EN held-out | 92.6% | 93.1% | ✅ ~ |
| VN holdout (gretel_test **dịch máy**) end-to-end | 14.9% | **42.1%** | 🟢 tăng (nhưng in-style) |
| Candidate raw-direct trên VN holdout (dịch máy) | — | **92.1%** | (in-style) |
| Candidate raw-direct trên test_vi (viết tay) | — | **53.3%** | 🔻 KHÔNG tổng quát |

## Phát hiện cốt lõi

1. **Model HỌC được tiếng Việt** khi đo trực tiếp: 8.4% → 92.1% trên VN holdout (dịch máy).
2. **Nhưng chỉ học VĂN PHONG DỊCH MÁY**, không tổng quát sang tiếng Việt viết tay thật:
   raw-direct 92.1% (holdout dịch) vs **53.3%** (test_vi viết tay). Hai văn phong khác hẳn nhau.
3. **Serving hybrid raw-VI hoạt động đúng** (đã sửa `backend/app.py`): kéo VN holdout end-to-end
   14.9% → 42.1%. Nhưng vì model không tổng quát, end-to-end vẫn xa trần 92%.
4. **Trên benchmark độc lập (test_vi, QA 48 ca) candidate THUA baseline**: 74→70%, group_acc 94→88%.
   Lý do: trộn data VN làm lệch đường cụm-triệu-chứng-EN (vốn là thứ tạo ra 74%), trong khi
   năng lực VN mới chỉ áp dụng cho input câu-tự-nhiên dạng dịch máy.
5. **An toàn KHÔNG tụt**: safety_recall 100%, red_flag/false_emergency/contract = 0, stress 459/500.

## Kết luận & khuyến nghị

**KHÔNG promote `models_retrain_vi` → `models/`.** Trượt gate promote: test_vi phải >74% (đạt 70%),
và group_accuracy regression. `models/` production GIỮ NGUYÊN, chưa bị đụng.

**Trả lời câu hỏi gốc (retrain / thêm data / train lại từ đầu):**
- Retrain rất khả thi & rẻ (vài phút), nhưng **thêm data DỊCH MÁY KHÔNG cải thiện độ chính xác VN thật.**
  Model chỉ học văn phong dịch, không khớp tiếng Việt người dùng gõ.
- Đòn bẩy thật, theo bằng chứng:
  1. **Data tiếng Việt VIẾT TAY thật** (không phải dịch máy) — nguồn khan hiếm `docs/DATA_SOURCES.md` đã nêu.
  2. **Cải thiện tầng trích triệu chứng VN→EN** — chính nó tạo ra 74% baseline; vá nó nâng trần cho input ngắn.
  3. Hybrid raw-VI (đã code, dormant) sẽ phát huy NẾU có model raw-capable tổng quát tốt.

## Phát hiện cuối: "74%" là lỗi ĐO, không phải lỗi năng lực

Phân tích 13 ca "sai" của baseline trên `test_vi_cases`: **toàn bộ là NÉ (422) nhóm kê đơn/rủi ro
cao**, KHÔNG phải đoán sai. Tầng trích triệu chứng hoạt động tốt; hệ né **theo đúng thiết kế an
toàn** (P2.3/P4: kháng sinh/tim mạch/tuyến giáp/kháng virus → "đi khám").

Đo lại bằng thước đo safety-aware mới (`scripts/eval_vietnamese.py`, báo cáo CẢ hai số):

| Chỉ số | Baseline `models/` |
|---|---|
| **Độ chính xác GỢI Ý** (né nhóm kê đơn = chưa gợi ý) | **74.0%** (37/50) |
| **Độ chính xác NHẬN DIỆN** (tính cả né-an-toàn-ĐÚNG-nhóm) | **90.0%** (45/50) |
| Né an toàn đúng nhóm kê đơn (hành vi ĐÚNG) | 8 ca |
| Sai thật còn lại | 5 ca — đều là `tuyến giáp` / `kháng virus` / `đau thần kinh` (lớp ít data), và đều né AN TOÀN |
| safety_recall | 100% |

→ **Năng lực thật ~90%**, an toàn 100%. "74%" thấp vì `eval_vietnamese.py` cũ tính một lần
từ-chối-an-toàn-thuốc-kê-đơn thành "sai". Cải thiện extraction/model KHÔNG kéo được số này lên
vì 8/13 ca hệ ĐÃ nhận đúng rồi chủ động từ chối. 5 ca còn lại là lớp khó ít data (cần data thật),
nhưng output vẫn an toàn.

## Trạng thái code (an toàn để giữ hoặc revert)

- `backend/app.py`: nhánh hybrid raw-VI bị **gate bằng cờ `trained_on_raw_text`**. Model `models/` không
  có cờ → hybrid là **no-op** (đã regression-test: số liệu y hệt baseline). An toàn để giữ làm scaffold,
  hoặc revert nếu muốn nhánh sạch.
- `scripts/train_model.py`: thêm cờ `--raw-text-capable` (mặc định tắt) — không ảnh hưởng train cũ.
- Artefact thử nghiệm: `models_retrain_vi/`, `data/*_vi*.csv`, `data/translation_cache.jsonl`.
