# Kế hoạch test UI cho Antigravity — Vòng 6 (OUTPUT trọng tâm)

> Dành cho **Antigravity** chạy độc lập trên browser. Mục tiêu vòng này: xác nhận output đã
> **gọn và trọng tâm** — chỉ 1 nhóm thuốc chính + 2-3 hoạt chất tiêu biểu (đã làm sạch, tiếng Việt)
> + lý do + độ tin cậy, **không còn dump danh sách thuốc thô tiếng Anh trùng lặp / đường dùng sai**.
> Đồng thời regression: các cổng an toàn và phán đoán vòng trước vẫn đúng.
>
> Bối cảnh: backend đã thêm mapping nhóm→2-3 hoạt chất sạch + field `reason`/`representative_active_ingredients`,
> ẩn dump thô; nhóm rủi ro/chuyên khoa hiện "cần bác sĩ"; thêm top-gap (model phân vân → xin thêm tt).
> LLM ngữ cảnh (vòng 5) **để TẮT** trong test này (không cần key).

---

## 1. Khởi động + tài khoản

```powershell
$env:LLM_CONTEXT_ENABLED="0"
python backend/app.py
```
- Chờ `http://127.0.0.1:5000/api/health` trả 200.
- Đăng ký/đăng nhập: `Antigravity V6` / `anti.v6@test.com` / `test123456`.

## 2. Quy trình mỗi ca
Home → **Xóa** (`#clear-case`) → nhập `#case-description` → submit (`#diagnosis-form button[type='submit']`)
→ đọc: `#result-title`/`#summary-drug-group`, độ tin cậy `#confidence-value`, danh sách thuốc (`#medication-list`),
ghi chú kết quả (có **lý do** ở đầu), cảnh báo `#warning-text`.

---

## 3. NHÓM A — Output gọn cho ca thường (trọng tâm vòng 6)

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 1 | Da nổi mẩn đỏ, ngứa nhiều, có mảng tróc vảy | 1 nhóm (kháng histamin); thuốc chỉ gồm **cetirizin/loratadin/fexofenadin**; **KHÔNG** có "eye drops"/tiếng Anh thô; có câu lý do + độ tin cậy |
| 2 | Đau bụng vùng thượng vị, ợ chua, đầy bụng | Nhóm dạ dày; hoạt chất **omeprazol/pantoprazol/antacid**; có lý do |
| 3 | Ho có đờm vàng, sổ mũi, rát họng | Nhóm long đờm/giảm ho; hoạt chất **acetylcystein/bromhexin/guaifenesin** |
| 4 | Sốt cao, đau mỏi người | Nhóm giảm đau hạ sốt; **paracetamol/ibuprofen** |

**PASS khi:** mỗi ca chỉ 1 nhóm chính, danh sách thuốc **ngắn (≤3 hoạt chất)** bằng tiếng Việt, có lý do, **không** còn danh sách dài/trùng/tiếng Anh thô.

## 4. NHÓM B — Nhóm rủi ro/chuyên khoa: KHÔNG gợi thuốc cụ thể

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 5 | Hồi hộp, tim đập nhanh, huyết áp cao 160 | Nhóm tim mạch/huyết áp; phần thuốc hiện **"cần bác sĩ đánh giá/kê đơn"**, KHÔNG có hoạt chất cụ thể |
| 6 | Sốt cao, ho, nghi nhiễm khuẩn (nếu ra nhóm kháng sinh) | Nếu nhóm = kháng sinh → hiện note "cần bác sĩ kê", KHÔNG liệt kê kháng sinh cụ thể |

## 5. NHÓM C — An toàn không lộ thuốc (regression)

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 7 | Đau ngực dữ dội lan tay trái, vã mồ hôi, khó thở | CẤP CỨU (422), **không** hoạt chất/thuốc |
| 8 | Trong người thấy oải oải khó tả | Cần thêm thông tin, không gợi thuốc |

## 6. NHÓM D — Regression phán đoán vòng trước

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 9 | Sốt thành cơn, rét run, vừa đi vùng rừng núi về | Nhóm **thuốc điều trị sốt rét** (note "cần xét nghiệm", không kê cụ thể) |
| 10 | Mệt mỏi, da xanh xao, chóng mặt, móng tay giòn | Nhóm **vitamin và khoáng chất** (sắt/acid folic/B12) |

## 7. Review UI/UX
- [ ] Danh sách thuốc gọn, dễ đọc, không tràn; không còn dòng tiếng Anh trùng lặp.
- [ ] Câu **lý do** hiển thị rõ ở ghi chú kết quả; độ tin cậy (`#confidence-value`) khớp.
- [ ] Nhóm rủi ro hiện ghi chú "cần bác sĩ" thay vì thuốc.
- [ ] Responsive 768px/375px; không lỗi console.
- [ ] Chụp screenshot mỗi ca `screenshots/v6_*.png`.

---

## 8. Báo cáo: `docs/ANTIGRAVITY_REPORT_v6.md`
Bảng kết quả #1–#10 (nhóm trả về | số hoạt chất | có lý do? | có dump thô? | PASS/FAIL) + tổng hợp A/B/C/D + nhận xét UI + ảnh.

> **Tiêu chí ĐẠT (merge):**
> - Nhóm A: output gọn, ≤3 hoạt chất tiếng Việt, không dump thô/đường dùng sai.
> - Nhóm B: nhóm rủi ro KHÔNG liệt kê thuốc cụ thể (hiện note bác sĩ).
> - Nhóm C & D: không regress (cấp cứu/không-lộ-thuốc/sốt rét/thiếu máu vẫn đúng).
