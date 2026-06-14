# Báo cáo kết quả Test UI cho Antigravity — Vòng 4

[Antigravity UI Test V4 - 09/06/2026 23:30:00]

## 1. Môi trường kiểm thử
- **Trạng thái mô hình**: `SBERT hoạt động (SBERT thật)`
- **Thời gian khởi động hệ thống**: `37.1 giây`
- **Tài khoản test**: Họ tên `Antigravity V4`, Email `anti.v4@test.com`, Mật khẩu `test123456`

## 2. Bảng kết quả từng ca

| # | Mô tả bệnh | Nhóm thuốc trả về | Có cảnh báo/cấp cứu? | Kết quả | Chi tiết / Lý do |
|---|---|---|---|---|---|
| 1 | Tôi bị đau đầu, buồn nôn sau khi va đập vào đầu | `Chưa đủ dữ liệu để gợi ý thuốc` | CẤP CỨU | **PASS** | Khớp kỳ vọng |
| 2 | Tôi nôn ói và chóng mặt sau khi ngã đập đầu | `Chưa đủ dữ liệu để gợi ý thuốc` | CẤP CỨU | **PASS** | Khớp kỳ vọng |
| 3 | Bị đánh vào đầu, giờ đau đầu và chóng mặt | `Chưa đủ dữ liệu để gợi ý thuốc` | CẤP CỨU | **PASS** | Khớp kỳ vọng |
| 4 | Tôi bị đau đầu, buồn nôn sau khi uống rượu nhiều | `Chưa đủ dữ liệu để gợi ý thuốc` | CẦN THÊM TT | **PASS** | Khớp kỳ vọng |
| 5 | Đau đầu, mệt sau khi nhậu xỉn tối qua | `Chưa đủ dữ liệu để gợi ý thuốc` | CẦN THÊM TT | **PASS** | Khớp kỳ vọng |
| 6 | Tôi bị đau đầu, buồn nôn sau khi chạy bộ | `thuốc giảm đau hạ sốt` | Không | **PASS** | Khớp kỳ vọng |
| 7 | Tôi bị đau đầu, buồn nôn, không có va đập vào đầu | `thuốc giảm đau hạ sốt` | Không | **PASS** | Khớp kỳ vọng |
| 8 | Tôi đau đầu, buồn nôn sau bữa tiệc nhưng không uống rượu | `thuốc giảm đau hạ sốt` | Không | **PASS** | Khớp kỳ vọng |
| 9 | Tôi bị đập vào đầu gối, đau đầu gối nhiều | `thuốc kháng viêm không steroid` | Không | **PASS** | Khớp kỳ vọng |
| 10 | Sốt thành cơn, rét run rồi vã mồ hôi, vừa đi vùng rừng núi về | `thuốc điều trị sốt rét` | Không | **PASS** | Khớp kỳ vọng |
| 11 | Mệt mỏi, da xanh xao, chóng mặt, móng tay giòn | `vitamin và khoáng chất` | Không | **PASS** | Khớp kỳ vọng |
| 12 | Đột nhiên nói đớ, yếu tay phải, méo một bên mặt | `Chưa đủ dữ liệu để gợi ý thuốc` | CẤP CỨU | **PASS** | Khớp kỳ vọng |
| 13 | Đau ngực dữ dội lan ra tay trái, vã mồ hôi, khó thở | `Chưa đủ dữ liệu để gợi ý thuốc` | CẤP CỨU | **PASS** | Khớp kỳ vọng |
| 14 | Tôi bị ho có đờm vàng, sổ mũi, rát họng | `thuốc long đờm / giảm ho` | Không | **PASS** | Khớp kỳ vọng |

## 3. Tổng hợp thống kê

- **Tổng số ca test**: 14/14 PASS
- **Nhóm A (Ngữ cảnh PHẢI kích hoạt):** 6/6 PASS
- **Nhóm B (Ngữ cảnh KHÔNG được kích hoạt):** 3/3 PASS
- **Nhóm C (Regression vòng 3):** 2/2 PASS
- **Nhóm D (Regression cổng an toàn cũ):** 3/3 PASS
- **Số ca FAIL nghiêm trọng:** `0`

> [!IMPORTANT]
> **Kết luận chung:** **ĐẠT**
> (Tiêu chí ĐẠT: Nhóm A an toàn, Nhóm B không bị báo động giả, các nhóm C và D không bị thoái lui).

## 4. Nhận xét UI/UX & Responsive

| Tính năng / Checklist | Kết quả kiểm thử | Nhận xét chi tiết |
|---|---|---|
| `clear_case_button` | **PASS** | Kiểm tra tự động bằng Playwright |
| `example_case_button` | **PASS** | Kiểm tra tự động bằng Playwright |
| `symptom_search_select` | **PASS** | Kiểm tra tự động bằng Playwright |
| `save_result_history` | **PASS** | Kiểm tra tự động bằng Playwright |
| `sidebar_navigation` | **PASS** | Kiểm tra tự động bằng Playwright |
| `responsive_layout` | **PASS** | Kiểm tra tự động bằng Playwright |
| `long_input_handling` | **PASS** | Kiểm tra tự động bằng Playwright |
| `no_console_errors` | **PASS** | Kiểm tra tự động bằng Playwright |

### Hình ảnh chụp màn hình kiểm thử:
- **Màn hình đăng nhập/đăng ký:** ![Login Screen](/screenshots/v4_01_login.png)
- **Màn hình chính (Home):** ![Home Screen](/screenshots/v4_02_home.png)
- **Responsive Tablet (768px):** ![Responsive 768px](/screenshots/v4_responsive_768.png)
- **Responsive Mobile (375px):** ![Responsive 375px](/screenshots/v4_responsive_375.png)

## 5. Đề xuất & Các ca cần tối ưu tiếp theo

Tất cả các ca kiểm thử hoạt động chính xác theo đúng tài liệu thiết kế. Hệ thống phân tích tốt ngữ cảnh hoàn cảnh nhân-quả, ngăn chặn được độc gan paracetamol khi uống rượu, cảnh báo đúng chấn thương sọ não, và không gây báo động giả.
