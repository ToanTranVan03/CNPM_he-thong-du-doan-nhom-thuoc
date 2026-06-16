# Kế hoạch test UI cho Antigravity — Vòng 7 (UX TỪ CHỐI nhóm kê đơn)

> Dành cho **Antigravity** chạy độc lập trên browser. Mục tiêu vòng này: xác nhận thay đổi #1 —
> khi hệ NHẬN ĐÚNG một nhóm thuốc KÊ ĐƠN (rủi ro cao) rồi chủ động chuyển khám, giao diện phải
> **nêu rõ tên nhóm + cảnh báo kê đơn**, thay vì câu chung chung "Chưa đủ dữ liệu".
> Đồng thời regression: nhóm "không bao giờ gợi ý" (ung thư), cấp cứu, và ca OTC vẫn đúng như cũ.
>
> Bối cảnh kỹ thuật: phản hồi 422 nay trả `display_title` = "Cần đi khám bác sĩ — có thể liên quan
> nhóm X", `error` nêu "thuốc KÊ ĐƠN: cần bác sĩ khám và chỉ định", và field mới `suggested_group`.
> Frontend `renderInsufficientInput` đã đổi để render `display_title` (trước đây hardcode).
> **Quan trọng:** đây vẫn là TỪ CHỐI an toàn — KHÔNG được hiện hoạt chất/thuốc cụ thể cho nhóm kê đơn.

---

## 1. Khởi động + tài khoản

```powershell
$env:LLM_CONTEXT_ENABLED="0"
python backend/app.py
```
- Chờ `http://127.0.0.1:5000/api/health` trả 200. (App có thể đang chạy sẵn — nếu kẹt port thì dùng instance đang chạy.)
- Đăng ký/đăng nhập: `Antigravity V7` / `anti.v7@test.com` / `test123456`.
- **Lưu ý:** gõ tiếng Việt CÓ DẤU trực tiếp vào ô nhập (browser gửi UTF-8 đúng).

## 2. Quy trình mỗi ca
Home → **Xóa** (`#clear-case`) → nhập vào `#case-description` → submit (`#diagnosis-form button[type='submit']`)
→ đọc: tiêu đề `#result-title`, ghi chú/cảnh báo `#result-note`, nhóm `#summary-drug-group`,
danh sách thuốc `#medication-list`, cảnh báo `#warning-text`. Chụp `screenshots/v7_*.png`.

---

## 3. NHÓM A — Nhóm KÊ ĐƠN: phải NÊU TÊN NHÓM + cảnh báo (trọng tâm vòng 7)

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 1 | Tiểu buốt, tiểu rắt, nước tiểu đục, đau bụng dưới | `#result-title` ≈ **"Cần đi khám bác sĩ — có thể liên quan nhóm thuốc kháng sinh"**; `#result-note` nêu **"KÊ ĐƠN: cần bác sĩ khám và chỉ định, KHÔNG tự mua dùng"**; `#medication-list` **KHÔNG** liệt kê kháng sinh cụ thể |
| 2 | Đau ngực trái, khó thở khi gắng sức, hồi hộp đánh trống ngực | Title nêu nhóm **tim mạch/huyết áp**; cảnh báo kê đơn; không hoạt chất cụ thể |
| 3 | Đau họng dữ dội, nuốt đau, sốt, amidan sưng có mủ trắng | Title nêu nhóm **kháng sinh**; cảnh báo kê đơn |
| 4 | Mất ngủ kéo dài nhiều tuần, lo âu, bồn chồn, khó tập trung | Title nêu nhóm **thần kinh/tâm thần**; cảnh báo kê đơn |

**PASS khi:** tiêu đề nêu ĐÚNG tên nhóm kê đơn + có chữ "đi khám/bác sĩ", ghi chú có "KÊ ĐƠN",
và **không** lộ tên thuốc cụ thể của nhóm đó.

## 4. NHÓM B — "Không bao giờ gợi ý" (ung thư/miễn dịch): KHÔNG nêu như gợi ý

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 5 | Sụt cân nhiều, mệt mỏi kéo dài, nổi hạch, ho ra máu | `#result-title` **KHÔNG** dạng "có thể liên quan nhóm thuốc/điều trị ung thư"; giữ chung chung "Chưa đủ dữ liệu..." + chuyển khám chuyên khoa; tuyệt đối không hoạt chất |

## 5. NHÓM C — Cấp cứu (regression, không đụng)

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 6 | Đau ngực dữ dội lan tay trái, vã mồ hôi, khó thở | **CẤP CỨU (422)**, title "⚠️ Cần hỗ trợ y tế khẩn cấp", KHÔNG nêu nhóm thuốc, KHÔNG hoạt chất |
| 7 | Sốt cao, đau đầu dữ dội, cứng gáy, nôn, sợ ánh sáng | Cảnh báo dấu hiệu thần kinh nguy hiểm/đi cấp cứu; không gợi thuốc |

## 6. NHÓM D — Ca OTC (regression: vẫn gợi ý trực tiếp như cũ)

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 8 | Da nổi mẩn đỏ, ngứa nhiều, hắt hơi sổ mũi | Gợi ý TRỰC TIẾP nhóm **kháng histamin** (200), title "Nhóm thuốc gợi ý: ..."; có hoạt chất (cetirizin/loratadin); **không** bị đổi sang câu "cần đi khám" |
| 9 | Sốt cao, đau mỏi người | Nhóm **giảm đau hạ sốt** trực tiếp (paracetamol/ibuprofen) |

## 7. Review UI/UX
- [ ] Ca nhóm A: tiêu đề `#result-title` hiển thị ĐÚNG tên nhóm kê đơn + "đi khám" (không còn câu generic).
- [ ] Ghi chú `#result-note` đọc rõ ràng, có cụm "KÊ ĐƠN / cần bác sĩ"; không tràn layout.
- [ ] Ca nhóm B/C: KHÔNG lộ nhóm như gợi ý / giữ cảnh báo cấp cứu.
- [ ] Ca nhóm D (OTC): vẫn hiển thị nhóm + hoạt chất bình thường, KHÔNG bị "đi khám" nhầm.
- [ ] Responsive 768px/375px; không lỗi console.
- [ ] Chụp screenshot mỗi ca `screenshots/v7_*.png`.

---

## 8. Báo cáo: `docs/ANTIGRAVITY_REPORT_v7.md`
Bảng #1–#9 (title hiển thị | có nêu tên nhóm? | có "KÊ ĐƠN"? | có lộ thuốc cụ thể? | PASS/FAIL) +
tổng hợp A/B/C/D + nhận xét UI + ảnh.

> **Tiêu chí ĐẠT (merge):**
> - Nhóm A: title nêu đúng tên nhóm kê đơn + "đi khám", ghi chú có "KÊ ĐƠN", KHÔNG lộ thuốc cụ thể.
> - Nhóm B: ung thư KHÔNG bị nêu như gợi ý (giữ chuyển khám chuyên khoa).
> - Nhóm C: cấp cứu/cờ đỏ không regress.
> - Nhóm D: ca OTC vẫn gợi ý trực tiếp bình thường (không bị đổi nhầm sang "đi khám").
