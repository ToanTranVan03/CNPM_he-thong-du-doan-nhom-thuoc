# Brief cho Codex — Plan NÂNG CHẤT LƯỢNG & AN TOÀN chẩn đoán PharmaPredict

> Codex output plan dạng checklist Markdown ra `docs/CODEX_QUALITY_PLAN.md`. Claude review rồi mới code.
> KHÔNG sửa code trong lần lập plan này. Mức suy luận: xhigh.

## Bối cảnh — vấn đề đã ĐO được (không phải phỏng đoán)

Test cũ tạo an toàn giả: `scripts/stress_test_user_cases.py` sinh 500 ca từ **12 template cố định** mà các rule trong `backend/app.py` đã được tinh chỉnh sẵn → 459/500 (91.8%) là **vòng tròn**, không phản ánh thực tế.

Đo trên bộ ĐỘC LẬP `scripts/independent_probe.py` (14 ca thật) lộ ra lỗi nghiêm trọng:

| Ca | Hệ thống trả về | Vấn đề |
|----|------------------|--------|
| Đau cơ sau đá bóng | rule → NSAID, chẩn đoán **"spinal stenosis"** | nhãn bệnh vô lý, trình bày như chắc chắn |
| Mất ngủ, lo âu | 64% → **thuốc tim mạch/huyết áp** | sai nhóm, tự tin |
| Ho khan 3 tuần + sụt cân | 77% → **thuốc điều trị ung thư** | **NGUY HIỂM**: phải là cờ đỏ tầm soát |
| Đau hố chậu phải (nghi ruột thừa) | rule → **chống nôn**, "viêm hô hấp trên" | **NGUY HIỂM**: bỏ sót cấp cứu |
| Táo bón | rule → nhuận tràng, chẩn đoán **"trĩ"** | nhãn bệnh sai |
| Sốt cao + co giật (trẻ) | 422, chẩn đoán "hypoglycemia" | chặn được nhưng nhãn sai |

### 3 lỗi hệ thống
1. **Nhãn chẩn đoán (disease_vi/diagnosis) thường vô nghĩa** dù nhóm thuốc đôi khi tạm đúng — nhưng vẫn hiển thị tự tin.
2. **Nhánh "rule"** (`*_rule_drug_group` trong app.py, dòng ~1706–2200, gọi ở ~2850) áp đặt kết quả dứt khoát + nhãn bệnh sai; frontend hiển thị "Theo rule" = 100%.
3. **An toàn bị đảo/bỏ sót**: red flag (ho mạn + sụt cân, đau hố chậu phải, sốt cao co giật) không được chặn đúng → vẫn kê thuốc tự tin.

## Mục tiêu (ƯU TIÊN AN TOÀN, theo thứ tự)

- **P0 — An toàn (chặn nguy hiểm):** mở rộng phát hiện cờ đỏ/cấp cứu để các ca nguy hiểm KHÔNG BAO GIỜ nhận gợi ý thuốc tự tin → luôn trả "cần đi khám". Tối thiểu: ho mạn tính + sụt cân/ra mồ hôi đêm; đau bụng khu trú dữ dội (hố chậu phải); sốt cao + co giật; bất kỳ tổ hợp đã liệt kê ở bảng trên. Mục tiêu đo được: **0 red flag bị kê thuốc** trên `independent_probe.py`.
- **P1 — Trình bày trung thực:** không hiển thị rule/heuristic như chắc chắn 100%. Nhãn chẩn đoán (disease) chỉ hiển thị khi đủ tin cậy; nếu không, ẩn hoặc ghi rõ "nhãn tham khảo, có thể không chính xác". Recalibrate cách hiển thị confidence/score_type ở frontend `script.js` (giữ id contract).
- **P2 — Độ tin cậy nhãn bệnh:** quyết định cơ chế: ẩn disease label khi model top-gap/confidence thấp, hoặc chỉ trả nhóm thuốc + "cần bổ sung triệu chứng". Tránh nhãn bệnh vô nghĩa.
- **P3 — Bộ QA THẬT:** chuẩn hóa & MỞ RỘNG `scripts/independent_probe.py` thành bộ test độc lập (≥40 ca đa dạng, có nhãn kỳ vọng + cờ an toàn), không vòng tròn. Tạo script chấm điểm đo: (a) tỉ lệ đúng nhóm, (b) số red flag bị kê thuốc (phải = 0). Thay/bổ sung cho stress test cũ. Ghi báo cáo có số liệu.
- **P4 — Cải thiện độ chính xác:** siết rule (yêu cầu tổ hợp triệu chứng đặc hiệu hơn để giảm dương tính giả), nâng ngưỡng model (`MIN_RELIABLE_CONFIDENCE`, top-gap), cải thiện trích triệu chứng/phủ định, phủ thêm nhóm còn thiếu (cơ xương khớp). Thành thật về giới hạn dataset.

## Ràng buộc bắt buộc
1. Giữ API contract mà frontend dùng: response fields `case_summary{diagnosis,medication_name,drug_group}`, `confidence`, `score_type`, `display_title`, `top_predictions`, `matched_symptoms_vi`, `needs_more_input`, `warning`, status 200/400/422. Đổi *ngữ nghĩa hiển thị* được, nhưng không xoá field khiến `frontend/script.js` (53+ id) vỡ.
2. Vanilla, chạy local (`python backend/app.py`). Tiếng Việt.
3. Mọi thay đổi phải đo được bằng `scripts/independent_probe.py` (mở rộng) — không quay lại test vòng tròn.
4. Không hứa "chính xác như bác sĩ"; ưu tiên AN TOÀN > tỏ ra thông minh.

## Yêu cầu với PLAN (Codex output)
Checklist Markdown theo giai đoạn P0→P4. Mỗi mục: file đụng tới (backend/app.py vùng nào, frontend/script.js, scripts/), mô tả ngắn, **tiêu chí nghiệm thu ĐO ĐƯỢC** (vd "0 red flag kê thuốc", "≥X% đúng nhóm trên bộ độc lập"), và rủi ro. Ưu tiên P0 an toàn trước.

## Tham chiếu
- `backend/app.py`: rules ~1706–2200, predict() ~2736–3070, ngưỡng dòng 69–72, emergency `emergency_red_flag_from_notes`.
- `scripts/independent_probe.py` (bộ đo độc lập — mở rộng cái này).
- `scripts/stress_test_user_cases.py` (test cũ vòng tròn — biết để không lặp lại).

---
## Task (dán cho Codex / mình tự chạy)
```
Đọc docs/CODEX_QUALITY_BRIEF.md, backend/app.py, scripts/independent_probe.py, scripts/stress_test_user_cases.py.
Lập plan NÂNG CHẤT LƯỢNG & AN TOÀN chẩn đoán theo giai đoạn P0->P4 trong brief, ưu tiên an toàn.
Mỗi mục ghi file đụng tới + tiêu chí nghiệm thu ĐO ĐƯỢC + rủi ro. Ghi ra docs/CODEX_QUALITY_PLAN.md (tiếng Việt).
KHÔNG sửa code, chỉ tạo file plan.
```
