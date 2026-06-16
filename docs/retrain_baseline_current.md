# Baseline hiện tại (A0.1) — model `models/` trước retrain

> Khóa ngày 2026-06-16. Đây là mốc tham chiếu BẮT BUỘC để so sánh sau retrain.
> Chạy lại bằng đúng các lệnh dưới với `MODEL_DIR` mặc định (`models/`).

## Lệnh đã chạy

```powershell
python scripts/eval_natural_descriptions.py --model models --split test
python scripts/eval_vietnamese.py --cases data/test_vi_cases.csv
python scripts/score_independent_probe.py --split all
python scripts/stress_test_user_cases.py
```

## Kết quả

| Bộ đo | Con số | Ghi chú |
|---|---|---|
| **gretel held-out (EN, in-style)** | **92.6%** (187/202) | Lạc quan — cùng văn phong train |
| **test_vi_cases (VN thật, qua backend)** | **74.0%** (37/50) | ⬅️ **CON SỐ TRUNG THỰC** |
| — theo loại: hard | 2/5 (40%) | |
| — normal | 30/40 (75%) | |
| — safety | 3/3 (100%) | |
| — vague | 2/2 (100%) | |
| **QA độc lập (48 ca)** | group_acc 94.1%, abstain_acc 93.8% | |
| — safety_recall | 100.0% | red_flag_drug=0, false_emergency=0, bad_label=0, contract_fail=0 |
| **Stress 500 ca** | 459/500 pass (41 fail) | |
| — issue: should_request_more_info | 32 | chủ yếu nhóm `headache_dizzy` |
| — issue: missing_summary_* / matched | 9 mỗi loại | nhóm `chest_red_flag` (422 emergency) |

## Chẩn đoán từ baseline (khớp giả thuyết bottleneck)

1. **Khoảng cách EN→VN rất lớn**: 92.6% (gretel) vs **74.0%** (VN thật). Đây là bằng chứng số cho việc thiếu data tiếng Việt tự nhiên.
2. **Model OVER-ABSTAIN trên VN**: phần lớn ca VN sai là `NEEDS_MORE_INFO` ở các ca lẽ ra gợi ý được (sốt rét/kháng sinh, tim mạch, tuyến giáp, kháng virus, zona). Nguyên nhân: model thiếu tín hiệu VN → độ tin cậy thấp → cổng an toàn né. Bơm data VN tự nhiên kỳ vọng kéo 74% lên mà KHÔNG hạ safety_recall.
3. **Cổng an toàn vững**: safety_recall 100%, false_emergency 0 — retrain KHÔNG được làm tụt các chỉ số này (gate chốt A8/B4).
4. Stress fail `chest_red_flag` (missing_summary_* trên 422) là hành vi chặn khẩn cấp đúng đắn bị test contract bắt — xử lý ở Hạng mục B3, không phải lỗi model.

## Mục tiêu sau retrain (định lượng)

- test_vi_cases: **> 74.0%** (kỳ vọng giảm over-abstain ở normal/hard).
- gretel held-out: không tụt dưới ~90%.
- Giữ nguyên: red_flag_drug_count=0, safety_recall=100%, false_emergency=0, contract_failure=0.
- Lớp nhỏ/nguy hiểm (chống đông, ung thư, tuyến giáp, vắc-xin): không xấu hơn baseline.
