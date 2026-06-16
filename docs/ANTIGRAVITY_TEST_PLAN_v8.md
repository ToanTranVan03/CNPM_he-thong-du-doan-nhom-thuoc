# Kế hoạch test UI cho Antigravity — Vòng 8 (CHẤT LƯỢNG DỰ ĐOÁN: vá ca lệch đề)

> Dành cho **Antigravity** chạy độc lập trên browser. Mục tiêu vòng này: xác nhận các ca trước đây
> hệ **dự đoán lệch nhóm** (vd tuyến giáp→ung thư, herpes→kháng nấm, táo bón→dạ dày) nay **nhận đúng
> nhóm**, NHỜ vá rule + tầng trích triệu chứng (commit c271e30, 62384e9).
> Đồng thời regression: cổng an toàn, ca cố-ý-né, ca cấp cứu và ca OTC vẫn đúng như cũ.
>
> Nguyên tắc vẫn giữ: nhóm KÊ ĐƠN (kháng sinh/tim mạch/tuyến giáp/kháng virus/chống co giật) → nêu tên
> nhóm + "cần bác sĩ", KHÔNG lộ hoạt chất. Nhóm OTC (nhuận tràng/kháng nấm/giảm đau/bù dịch/kháng histamin)
> → gợi ý trực tiếp kèm hoạt chất.

---

## 1. Khởi động + tài khoản

```powershell
$env:LLM_CONTEXT_ENABLED="0"
python backend/app.py
```
- Chờ `http://127.0.0.1:5000/api/health` trả 200.
- Đăng ký/đăng nhập: `Antigravity V8` / `anti.v8@test.com` / `test123456`.
- Gõ tiếng Việt CÓ DẤU trực tiếp vào ô nhập.

## 2. Quy trình mỗi ca
Home → **Xóa** (`#clear-case`) → nhập `#case-description` → submit (`#diagnosis-form button[type='submit']`)
→ đọc tiêu đề `#result-title`, ghi chú `#result-note`, nhóm `#summary-drug-group`, thuốc `#medication-list`,
cảnh báo `#warning-text`. Chụp `screenshots/v8_*.png`.

---

## 3. NHÓM A1 — Ca OTC đã vá: phải GỢI Ý TRỰC TIẾP đúng nhóm + có hoạt chất

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 1 | Mấy ngày không đi cầu được, phân khô cứng, rặn khó | Nhóm **nhuận tràng** (200, gợi ý trực tiếp), có hoạt chất; KHÔNG ra "dạ dày" |
| 2 | Nấm kẽ chân, ngứa, da trắng bợt bong tróc, mùi hôi | Nhóm **kháng nấm/ký sinh trùng ngoài da**; KHÔNG ra "kháng histamin" |
| 3 | Nhức nửa đầu theo nhịp mạch, sợ ánh sáng, buồn nôn | Nhóm **giảm đau hạ sốt** (migraine); KHÔNG ra "thuốc chống nôn" |
| 4 | Trẻ đi ngoài tóe nước liên tục, lừ đừ, mắt trũng | Nhóm **bù dịch và điện giải** (ORS); KHÔNG ra "kháng virus" |

**PASS khi:** đúng nhóm OTC nêu trên, có hoạt chất minh hoạ, không lệch sang nhóm cũ sai.

## 4. NHÓM A2 — Ca KÊ ĐƠN đã vá: nêu ĐÚNG TÊN NHÓM + cảnh báo (422, không lộ thuốc)

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 5 | Hồi hộp, sụt cân nhanh, run tay, ra nhiều mồ hôi | `#result-title` nêu nhóm **nội tiết tuyến giáp** + "đi khám/kê đơn"; KHÔNG ra "ung thư" |
| 6 | Mệt mỏi, tăng cân, da khô, rụng tóc, sợ lạnh, cổ hơi to | Nêu nhóm **nội tiết tuyến giáp** + cảnh báo kê đơn; KHÔNG ra "tim mạch" |
| 7 | Nổi mụn nước đau rát thành chùm ở môi và quanh miệng | Nêu nhóm **kháng virus** + cảnh báo kê đơn; KHÔNG ra "kháng nấm" |
| 8 | Tê bì bàn chân hai bên ở người tiểu đường lâu năm | Nêu nhóm **chống co giật/đau thần kinh** + cảnh báo; KHÔNG ra "corticosteroid" |
| 9 | Đau quặn bụng dưới từng cơn, buồn đi ngoài, phân nhầy máu, sốt | Nêu nhóm **kháng sinh** + cảnh báo kê đơn |

**PASS khi:** tiêu đề nêu ĐÚNG tên nhóm kê đơn + "cần bác sĩ/đi khám", KHÔNG liệt kê hoạt chất cụ thể.

## 5. NHÓM B — Chặn đoán bừa (không lệch đề kiểu "tự tin sai")

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 10 | Trong người thấy khó chịu | **Cần thêm thông tin** (không gợi ý nhóm cụ thể); tuyệt đối KHÔNG ra "thuốc điều trị đái tháo đường" |

## 6. NHÓM C — Cố ý NÉ an toàn (hành vi ĐÚNG, regression)

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 11 | Bé sốt 39 độ, quấy khóc, bỏ bú | Cần thêm thông tin / chuyển khám; KHÔNG tự kê thuốc cho trẻ |
| 12 | Chảy máu chân răng, mệt mỏi, dễ bầm tím | Cần thêm thông tin / đi khám (nghi huyết học); KHÔNG khẳng định "vitamin" như chỉ định |

## 7. NHÓM D — Regression an toàn lõi (không đụng)

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 13 | Đau ngực dữ dội lan tay trái, vã mồ hôi, khó thở | **CẤP CỨU (422)**, title "⚠️ Cần hỗ trợ y tế khẩn cấp", không thuốc |
| 14 | Da nổi mẩn đỏ, ngứa nhiều, hắt hơi sổ mũi | Gợi ý TRỰC TIẾP nhóm **kháng histamin** (200) + hoạt chất |
| 15 | Sụt cân nhiều, mệt mỏi kéo dài, nổi hạch, ho ra máu | Nhóm ung thư KHÔNG bị nêu như gợi ý; chuyển khám chuyên khoa |

## 8. Review UI/UX
- [ ] Ca A1: hiển thị đúng nhóm OTC mới + hoạt chất, không tràn layout.
- [ ] Ca A2: tiêu đề nêu đúng tên nhóm kê đơn + "đi khám"; KHÔNG lộ hoạt chất.
- [ ] Ca B/C: không đoán bừa / giữ chuyển khám.
- [ ] Ca D: cấp cứu, OTC, ung thư vẫn đúng như vòng trước.
- [ ] Responsive 768px/375px; không lỗi console. Chụp `screenshots/v8_*.png`.

---

## 9. Báo cáo: `docs/ANTIGRAVITY_REPORT_v8.md`
Bảng #1–#15 (nhóm trả về | đúng nhóm kỳ vọng? | kê đơn nêu tên + ẩn thuốc? | OTC có hoạt chất? | PASS/FAIL)
+ tổng hợp A1/A2/B/C/D + nhận xét UI + ảnh.

> **Tiêu chí ĐẠT (merge):**
> - Nhóm A1: 4 ca OTC ra ĐÚNG nhóm mới + có hoạt chất (không lệch sang nhóm cũ sai).
> - Nhóm A2: 5 ca kê đơn nêu ĐÚNG tên nhóm + "đi khám", KHÔNG lộ hoạt chất.
> - Nhóm B: "khó chịu" không bị đoán thành tiểu đường.
> - Nhóm C: 2 ca cố-ý-né vẫn chuyển khám (không tự kê thuốc).
> - Nhóm D: cấp cứu/OTC/ung thư không regress.
