# Kế hoạch test UI cho Antigravity — Vòng 4 (hiểu NGỮ CẢNH "sau khi X")

> Dành cho **Antigravity** chạy độc lập trên browser. Mục tiêu vòng này: xác nhận hệ thống đã
> xử lý **ngữ cảnh nhân–quả/hoàn cảnh** trong câu (không chỉ nhặt từ khóa triệu chứng) cho 3 nhóm
> NGUY HIỂM, VÀ không tự "báo động giả" với câu phủ định. Đồng thời **regression**: xác nhận các
> ca vòng 3 (#9 sốt rét, #10 thiếu máu) và các ca an toàn cũ vẫn đúng.
>
> Bối cảnh: backend đã thêm tầng lexicon ngữ cảnh notes-aware + cổng phủ định. Smoke test code
> 8/8 đúng; eval chính 96%, eval v3 75%, stress 500 = 459/500 (không regress so với HEAD).

---

## 1. Khởi động ứng dụng

```powershell
python backend/app.py
```

- Lần đầu tải/nạp SBERT có thể mất **30s–3 phút**. CHỜ `http://127.0.0.1:5000/api/health` trả **200**.
- Nếu log báo thiếu `torch`/`sentence-transformers` → app chạy fallback; **ghi rõ trong báo cáo**.

## 2. Tài khoản

Đăng ký qua UI: **"Tạo tài khoản"** → Họ tên `Antigravity V4`, Email `anti.v4@test.com`,
Mật khẩu `test123456`. Nếu email đã tồn tại thì đăng nhập lại.

## 3. Quy trình test mỗi ca (Home → Kết quả)

1. Home → bấm **"Xóa"** (`#clear-case`).
2. Nhập mô tả vào `#case-description`.
3. Bấm submit (`#diagnosis-form button[type='submit']`).
4. Đọc: `#result-title` / `#summary-drug-group`, độ tin cậy `#confidence-value`, cảnh báo `#warning-text`.
5. Quy ước trạng thái:
   - **CẤP CỨU**: tiêu đề kiểu "⚠️ Cần hỗ trợ y tế khẩn cấp", có thông điệp gọi 115/đi khám ngay.
   - **CẦN THÊM THÔNG TIN**: "Chưa đủ dữ liệu để gợi ý thuốc".
   - **GỢI Ý NHÓM**: hiện một nhóm thuốc bình thường (+ có thể kèm cảnh báo trong phần lưu ý).

---

## 4. NHÓM A — Ngữ cảnh PHẢI kích hoạt (trọng tâm vòng 4)

| # | Mô tả nhập | Kỳ vọng | PASS khi |
|---|---|---|---|
| 1 | Tôi bị đau đầu, buồn nôn sau khi va đập vào đầu | CẤP CỨU (nghi chấn thương sọ não) | Hiện cảnh báo cấp cứu, **KHÔNG** gợi ý thuốc giảm đau |
| 2 | Tôi nôn ói và chóng mặt sau khi ngã đập đầu | CẤP CỨU | Cảnh báo cấp cứu |
| 3 | Bị đánh vào đầu, giờ đau đầu và chóng mặt | CẤP CỨU | Cảnh báo cấp cứu |
| 4 | Tôi bị đau đầu, buồn nôn sau khi uống rượu nhiều | CẦN THÊM THÔNG TIN | **KHÔNG** gợi ý paracetamol/giảm đau; thông điệp nhắc độc gan do rượu |
| 5 | Đau đầu, mệt sau khi nhậu xỉn tối qua | CẦN THÊM THÔNG TIN | Không kê giảm đau vô điều kiện; nhắc rượu/gan |
| 6 | Tôi bị đau đầu, buồn nôn sau khi chạy bộ | GỢI Ý NHÓM (không cấp cứu) | Phần **Lưu ý/Chăm sóc** có nội dung nghỉ, **bù nước/oresol**, theo dõi mất nước |

## 5. NHÓM B — Ngữ cảnh KHÔNG được kích hoạt (chống báo động giả — RẤT QUAN TRỌNG)

> Đây là phần kiểm tra cổng phủ định và bẫy "đầu gối". FAIL nếu hệ báo cấp cứu/chặn sai.

| # | Mô tả nhập | Kỳ vọng | FAIL khi |
|---|---|---|---|
| 7 | Tôi bị đau đầu, buồn nôn, không có va đập vào đầu | KHÔNG cấp cứu | Bị báo cấp cứu chấn thương đầu |
| 8 | Tôi đau đầu, buồn nôn sau bữa tiệc nhưng không uống rượu | Bình thường | Bị chặn vì rượu |
| 9 | Tôi bị đập vào đầu gối, đau đầu gối nhiều | KHÔNG cấp cứu (đây là chân, không phải đầu) | Bị báo cấp cứu chấn thương đầu |

## 6. NHÓM C — Regression vòng 3 (phải vẫn đúng)

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 10 | Sốt thành cơn, rét run rồi vã mồ hôi, vừa đi vùng rừng núi về | Nhóm **thuốc điều trị sốt rét** (KHÔNG phải kháng sinh) |
| 11 | Mệt mỏi, da xanh xao, chóng mặt, móng tay giòn | Nhóm **vitamin và khoáng chất** (KHÔNG phải tim mạch) |

## 7. NHÓM D — Regression cổng an toàn cũ (phải vẫn đúng)

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 12 | Đột nhiên nói đớ, yếu tay phải, méo một bên mặt | CẤP CỨU (đột quỵ) |
| 13 | Đau ngực dữ dội lan ra tay trái, vã mồ hôi, khó thở | CẤP CỨU (tim mạch) |
| 14 | Tôi bị ho có đờm vàng, sổ mũi, rát họng | Gợi ý nhóm long đờm/giảm ho (không cấp cứu) |

## 8. Review giao diện / UX

- [ ] Khối cảnh báo (`#warning-text`) nổi bật rõ khi cấp cứu (màu/icon).
- [ ] Phần Lưu ý/Chăm sóc hiển thị đủ nội dung động (bù nước cho ca chạy bộ; cảnh báo rượu nếu có).
- [ ] Responsive ~768px và ~375px không vỡ.
- [ ] Không có lỗi `console` đỏ khi submit.
- [ ] Chụp screenshot mỗi ca vào `screenshots/v4_*.png`.

---

## 9. Định dạng báo cáo: `docs/ANTIGRAVITY_REPORT_v4.md`

1. **Môi trường**: SBERT thật/fallback, thời gian khởi động.
2. **Bảng kết quả** từng ca #1–#14: mô tả | trạng thái trả về (cấp cứu / cần thêm tt / nhóm thuốc) | nhóm | cảnh báo? | PASS/FAIL.
3. **Tổng hợp** theo nhóm A/B/C/D, nêu rõ FAIL nghiêm trọng.
4. **Nhận xét UI/UX** + ảnh.
5. **Đề xuất** ca cần Claude fix.

> **Tiêu chí ĐẠT (cho phép merge):**
> - Nhóm A: #1–#5 phải đúng trạng thái an toàn (cấp cứu / cần thêm tt), #6 có guidance bù nước.
> - Nhóm B: **không ca nào** bị báo động giả (đây là điều kiện cứng).
> - Nhóm C & D: không regress.
