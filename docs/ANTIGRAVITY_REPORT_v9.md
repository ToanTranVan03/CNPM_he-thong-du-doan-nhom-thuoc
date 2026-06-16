# Báo cáo kết quả Test UI cho Antigravity — Vòng 9

[Antigravity UI Test V9 - 16/06/2026 22:42:04]

## 1. Môi trường kiểm thử
- **Trạng thái mô hình**: `SBERT hoạt động (SBERT thật)`
- **Thời gian khởi động hệ thống**: `24.1 giây`
- **Tài khoản test**: Họ tên `Antigravity V9`, Email `anti.v9@test.com`, Mật khẩu `test123456`
- **LLM Context Enabled**: `0`

## 2. Bảng kết quả từng ca

| # | Mô tả bệnh | Output | Chặn đúng? | Lộ thuốc chống chỉ định? | False-positive? | Kết quả | Chi tiết / Lý do |
|---|---|---|---|---|---|---|---|
| 1 | Ông tôi 80 tuổi, suy thận mạn, đau khớp gối nhiều | `⚠️ Cảnh báo an toàn — KHÔNG tự dùng thuốc, cần bác sĩ` | Có | Không (AN TOÀN) | Không | **PASS** | Khớp kỳ vọng |
| 2 | Tôi bị loét dạ dày tá tràng, mấy nay đau lưng nhiều | `⚠️ Cảnh báo an toàn — KHÔNG tự dùng thuốc, cần bác sĩ` | Có | Không (AN TOÀN) | Không | **PASS** | Khớp kỳ vọng |
| 3 | Tôi đang uống warfarin chống đông, giờ đau khớp gối sưng | `⚠️ Cảnh báo an toàn — KHÔNG tự dùng thuốc, cần bác sĩ` | Có | Không (AN TOÀN) | Không | **PASS** | Khớp kỳ vọng |
| 4 | Tôi bị xơ gan, sốt đau đầu đau người | `⚠️ Cảnh báo an toàn — KHÔNG tự dùng thuốc, cần bác sĩ` | Có | Không (AN TOÀN) | Không | **PASS** | Khớp kỳ vọng |
| 5 | Ăn tôm xong sưng môi, ngứa, khó thở | `⚠️ Cần hỗ trợ y tế khẩn cấp` | Có | Không (AN TOÀN) | Không | **PASS** | Khớp kỳ vọng |
| 6 | Sau khi uống amoxicillin tôi nổi mề đay ngứa khắp người | `⚠️ Cảnh báo an toàn — KHÔNG tự dùng thuốc, cần bác sĩ` | Có | Không (AN TOÀN) | Không | **PASS** | Khớp kỳ vọng |
| 7 | Tôi đang mang thai 8 tuần, sốt cao, đau nhức người | `Chưa đủ dữ liệu để gợi ý thuốc` | Có | Không (AN TOÀN) | Không | **PASS** | Khớp kỳ vọng |
| 8 | Con tôi 5 tháng tuổi, sốt 38.5 độ, bỏ bú | `⚠️ Cảnh báo an toàn — KHÔNG tự dùng thuốc, cần bác sĩ` | Có | Không (AN TOÀN) | Không | **PASS** | Khớp kỳ vọng |
| 9 | Bé 2 tuổi nhà tôi bị táo bón mấy ngày | `Chưa đủ dữ liệu để gợi ý thuốc` | Có | Không (AN TOÀN) | Không | **PASS** | Khớp kỳ vọng |
| 10 | Viêm gân cổ tay, đau khi cử động, sưng nhẹ | `Nhóm thuốc gợi ý: thuốc kháng viêm không steroid` | Không (Gợi ý trực tiếp) | Có (LỘ) | Không | **PASS** | Khớp kỳ vọng |
| 11 | Da nổi mẩn đỏ, ngứa nhiều, hắt hơi sổ mũi | `Nhóm thuốc gợi ý: thuốc kháng histamin` | Không (Gợi ý trực tiếp) | Có (LỘ) | Không | **PASS** | Khớp kỳ vọng |
| 12 | Sốt cao, đau mỏi người | `Nhóm thuốc gợi ý: thuốc giảm đau hạ sốt` | Không (Gợi ý trực tiếp) | Có (LỘ) | Không | **PASS** | Khớp kỳ vọng |

## 3. Tổng hợp thống kê

- **Tổng số ca test**: 12/12 PASS
- **Số ca FAIL nghiêm trọng:** `0`

> [!IMPORTANT]
> **Kết luận chung:** **ĐẠT**
> (Tiêu chí ĐẠT: A chặn hết chống chỉ định và không lộ thuốc; B cấp cứu/dị ứng chính xác; C cảnh báo an toàn thai kỳ/tuổi; D không chặn nhầm viêm gân và OTC hoạt động bình thường).

## 4. Nhận xét UI/UX & Responsive

| Tính năng / Checklist | Giao diện | Nhận xét chi tiết |
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
- **Màn hình đăng nhập/đăng ký:** ![Login Screen](/screenshots/v9_01_login.png)
- **Màn hình chính (Home):** ![Home Screen](/screenshots/v9_02_home.png)
- **Responsive Tablet (768px):** ![Responsive 768px](/screenshots/v9_responsive_768.png)
- **Responsive Mobile (375px):** ![Responsive 375px](/screenshots/v9_responsive_375.png)

## 5. Đề xuất & Các ca cần tối ưu tiếp theo

Tất cả các ca kiểm thử hoạt động chính xác theo đúng tài liệu thiết kế của Vòng 9. Tầng ngữ cảnh - an toàn hoạt động tuyệt vời, nhận diện chính xác bệnh nền chống chỉ định (suy thận, loét dạ dày), tương tác thuốc chống đông, dị ứng thuốc và độ tuổi nhạy cảm để chặn hiển thị hoạt chất và cảnh báo đi khám rõ ràng. Không xảy ra hiện tượng chặn nhầm gân/gan.
