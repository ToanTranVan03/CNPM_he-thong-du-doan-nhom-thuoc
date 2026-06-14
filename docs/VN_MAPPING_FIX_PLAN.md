# Plan: Vá tầng dịch triệu chứng VN→EN + rule ưu tiên (Codex lập, Claude review)

> Nguồn: Codex (read-only planner) 2026-06-08. Claude đã review & xác minh với code thật.
> Gốc rễ 2 case lỗi nằm ở **lớp rule ghi đè model** trong `backend/app.py` (dòng 2098-2106),
> KHÔNG phải thiếu mapping đơn thuần. `gastrointestinal_rule_drug_group` bắt "đau bụng"→dạ dày
> và "buồn nôn"→chống nôn, fire trước nên đè kết quả đúng.

## Phạm vi
- Chỉ sửa `backend/app.py` (mapping + rule). KHÔNG retrain model, KHÔNG đổi pipeline TF-IDF.
- Giữ encoding UTF-8, không gây mojibake.

## 1. Bổ sung mapping VI→EN trong `VI_SYMPTOM_KEYWORDS` (tăng độ phủ)
Chỉ thêm key có thật trong `metadata["features"]`; ưu tiên key atomic, tránh feature composite dài.
- [ ] Tiết niệu: `tiểu rắt`, `tiểu lắt nhắt`, `mắc tiểu liên tục`, `đau bàng quang`, `đau hạ vị`,
  `nước tiểu đục`, `bí tiểu` (lưu ý "tiểu buốt"→`burning micturition` ĐÃ map sẵn).
- [ ] Thần kinh/đau đầu: `đau nửa đầu`, `đau đầu từng cơn`, `sợ ánh sáng`, `nhạy cảm ánh sáng`,
  `sợ tiếng ồn` → map vào `visual disturbances` nếu không có feature photophobia riêng.
- [ ] Hô hấp: `thở rít`, `khò khè`, `tức ngực`, `nặng ngực`, `khạc đờm`, `nghẹt ngực`.
- [ ] Tiêu hóa: `phân đen`, `nôn ra máu`, `ợ nóng`, `đau thượng vị`, `chướng bụng`.
- [ ] Phrase quan trọng nhưng không có feature → thêm vào `UNSUPPORTED_SYMPTOM_KEYWORDS`, không ép map sai.

## 2. ★ FIX CỐT LÕI: rule cluster + thứ tự ưu tiên (dòng ~1487-1531, 2098-2106)
- [ ] Thêm `urinary_rule_drug_group(active_symptoms)`: nếu có cụm tiết niệu
  (`burning micturition`/`bladder discomfort`/`foul smell of urine`/`continuous feel of urine`/
  `spotting urination`... ) → trả `"thuốc kháng sinh"` (tên khớp `metadata["classes"]`).
- [ ] Thêm `migraine_rule_drug_group(active_symptoms)`: nếu có `headache` + (≥1 trong
  `visual disturbances`/`nausea`/`vomiting`/`dizziness`) → trả `"thuốc giảm đau hạ sốt"`.
  - [ ] Loại trừ dấu hiệu đỏ (yếu/liệt, lú lẫn, co giật, cứng cổ + sốt cao) → KHÔNG force giảm đau,
    chuyển `needs_more_input`/cảnh báo đi khám.
- [ ] Đặt thứ tự trong chuỗi `rule_group`: `urinary` và `migraine` **TRƯỚC** `gastrointestinal`.
- [ ] Sửa `gastrointestinal_rule_drug_group`: không trả `thuốc chống nôn` khi đang ở migraine cluster;
  không trả `thuốc điều trị dạ dày` khi đang ở urinary cluster (phòng hờ).

## 3. Kiểm thử
- [ ] Baseline: `python scripts/eval_natural_descriptions.py --model models` (giữ ~92,6%).
- [ ] Sau sửa: `python scripts/audit_symptom_mapping.py` → kỳ vọng `mapped > 252`.
- [ ] `python scripts/eval_natural_descriptions.py --model models` → accuracy KHÔNG được giảm.
- [ ] Cập nhật `run_ui_tests.py`: case 6 phải ra **kháng sinh**, case 7 phải ra **giảm đau** (đổi 3b từ
  "expected_fail" sang expected đúng).
- [ ] Chạy `python run_ui_tests.py` (cần backend đang chạy) → case 3a không regression, 3b pass.

## 4. File cần sửa
- [ ] `backend/app.py`: `VI_SYMPTOM_KEYWORDS`, `UNSUPPORTED_SYMPTOM_KEYWORDS` (nếu cần),
  2 helper rule mới, chuỗi `rule_group`, điều kiện trong `gastrointestinal_rule_drug_group`.
- [ ] `run_ui_tests.py`: đổi kỳ vọng case 3b.
- [ ] `docs/symptom_mapping_audit*.{csv,json}`: KHÔNG sửa tay, regenerate bằng `audit_symptom_mapping.py`.

## 5. Rủi ro
- Mapping quá rộng kích hoạt nhầm feature composite → chỉ thêm key atomic.
- Rule kháng sinh có rủi ro y khoa → chỉ là "nhóm tham khảo", giữ cảnh báo không tự dùng.
- Rule migraine có thể che ca thần kinh nguy hiểm → bắt buộc loại trừ dấu hiệu đỏ trước.
- Tên label phải khớp tuyệt đối `metadata["classes"]`.
- `NORMALIZED_KEYWORDS` build lúc import → phải restart app/test sau khi sửa.
