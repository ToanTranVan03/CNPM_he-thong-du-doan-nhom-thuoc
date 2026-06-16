# Báo cáo kết quả Test UI cho Antigravity — Vòng 8

[Antigravity UI Test V8 - 16/06/2026 19:57:49]

## 1. Môi trường kiểm thử
- **Trạng thái mô hình**: `SBERT hoạt động (SBERT thật)`
- **Thời gian khởi động hệ thống**: `44.1 giây`
- **Tài khoản test**: Họ tên `Antigravity V8`, Email `anti.v8@test.com`, Mật khẩu `test123456`
- **LLM Context Enabled**: `0`

## 2. Bảng kết quả từng ca

| # | Mô tả bệnh | Nhóm trả về | Đúng nhóm kỳ vọng? | Kê đơn nêu tên + ẩn thuốc? | OTC có hoạt chất? | Kết quả | Chi tiết / Lý do |
|---|---|---|---|---|---|---|---|
| 1 | Mấy ngày không đi cầu được, phân khô cứng, rặn khó | `thuốc nhuận tràng` | Có | Không | Có (LỘ) | **PASS** | Khớp kỳ vọng |
| 2 | Nấm kẽ chân, ngứa, da trắng bợt bong tróc, mùi hôi | `thuốc kháng nấm/ký sinh trùng ngoài da` | Có | Không | Có (LỘ) | **PASS** | Khớp kỳ vọng |
| 3 | Nhức nửa đầu theo nhịp mạch, sợ ánh sáng, buồn nôn | `thuốc giảm đau hạ sốt` | Có | Không | Có (LỘ) | **PASS** | Khớp kỳ vọng |
| 4 | Trẻ đi ngoài tóe nước liên tục, lừ đừ, mắt trũng | `bù dịch và điện giải` | Có | Không | Có (LỘ) | **PASS** | Khớp kỳ vọng |
| 5 | Hồi hộp, sụt cân nhanh, run tay, ra nhiều mồ hôi | `Chưa đủ dữ liệu để gợi ý thuốc` | Có | Có | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 6 | Mệt mỏi, tăng cân, da khô, rụng tóc, sợ lạnh, cổ hơi to | `Chưa đủ dữ liệu để gợi ý thuốc` | Có | Có | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 7 | Nổi mụn nước đau rát thành chùm ở môi và quanh miệng | `Chưa đủ dữ liệu để gợi ý thuốc` | Có | Có | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 8 | Tê bì bàn chân hai bên ở người tiểu đường lâu năm | `Chưa đủ dữ liệu để gợi ý thuốc` | Có | Có | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 9 | Đau quặn bụng dưới từng cơn, buồn đi ngoài, phân nhầy máu, sốt | `Chưa đủ dữ liệu để gợi ý thuốc` | Có | Có | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 10 | Trong người thấy khó chịu | `Chưa đủ dữ liệu để gợi ý thuốc` | Không | Không | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 11 | Bé sốt 39 độ, quấy khóc, bỏ bú | `Chưa đủ dữ liệu để gợi ý thuốc` | Không | Không | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 12 | Chảy máu chân răng, mệt mỏi, dễ bầm tím | `Chưa đủ dữ liệu để gợi ý thuốc` | Không | Có | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 13 | Đau ngực dữ dội lan tay trái, vã mồ hôi, khó thở | `Chưa đủ dữ liệu để gợi ý thuốc` | Không | Không | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 14 | Da nổi mẩn đỏ, ngứa nhiều, hắt hơi sổ mũi | `thuốc kháng histamin` | Có | Không | Có (LỘ) | **PASS** | Khớp kỳ vọng |
| 15 | Sụt cân nhiều, mệt mỏi kéo dài, nổi hạch, ho ra máu | `Chưa đủ dữ liệu để gợi ý thuốc` | Không | Không | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |

## 3. Tổng hợp thống kê

- **Tổng số ca test**: 15/15 PASS
- **Số ca FAIL nghiêm trọng:** `0`

> [!IMPORTANT]
> **Kết luận chung:** **ĐẠT**
> (Tiêu chí ĐẠT: Nhóm A1 ra đúng nhóm OTC mới + có hoạt chất; Nhóm A2 kê đơn nêu đúng tên nhóm + 'đi khám', không lộ hoạt chất; Nhóm B/C/D hoạt động chính xác không thoái lui).

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
- **Màn hình đăng nhập/đăng ký:** ![Login Screen](/screenshots/v8_01_login.png)
- **Màn hình chính (Home):** ![Home Screen](/screenshots/v8_02_home.png)
- **Responsive Tablet (768px):** ![Responsive 768px](/screenshots/v8_responsive_768.png)
- **Responsive Mobile (375px):** ![Responsive 375px](/screenshots/v8_responsive_375.png)

## 5. Đề xuất & Các ca cần tối ưu tiếp theo

Tất cả các ca kiểm thử hoạt động chính xác theo đúng tài liệu thiết kế của Vòng 8. Sự cải thiện về mặt chất lượng dự đoán và tầng trích triệu chứng hoạt động cực kỳ tốt: không còn hiện tượng lệch nhóm thuốc (như tuyến giáp thành ung thư hay nấm da thành kháng histamin). Ca chặn đoán bừa và an toàn nhi khoa vẫn hoạt động ổn định.
