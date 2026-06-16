# Báo cáo kết quả Test UI cho Antigravity — Vòng 7

[Antigravity UI Test V7 - 16/06/2026 17:41:38]

## 1. Môi trường kiểm thử
- **Trạng thái mô hình**: `SBERT hoạt động (SBERT thật)`
- **Thời gian khởi động hệ thống**: `24.0 giây`
- **Tài khoản test**: Họ tên `Antigravity V7`, Email `anti.v7@test.com`, Mật khẩu `test123456`
- **LLM Context Enabled**: `0`

## 2. Bảng kết quả từng ca

| # | Mô tả bệnh | Title hiển thị | Có nêu tên nhóm? | Có "KÊ ĐƠN"? | Có lộ thuốc cụ thể? | Kết quả | Chi tiết / Lý do |
|---|---|---|---|---|---|---|---|
| 1 | Tiểu buốt, tiểu rắt, nước tiểu đục, đau bụng dưới | `Cần đi khám bác sĩ — có thể liên quan nhóm thuốc kháng sinh` | Có | Có | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 2 | Đau ngực trái, khó thở khi gắng sức, hồi hộp đánh trống ngực | `Cần đi khám bác sĩ — có thể liên quan nhóm thuốc tim mạch/huyết áp` | Có | Có | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 3 | Đau họng dữ dội, nuốt đau, sốt, amidan sưng có mủ trắng | `Cần đi khám bác sĩ — có thể liên quan nhóm thuốc kháng sinh` | Có | Có | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 4 | Mất ngủ kéo dài nhiều tuần, lo âu, bồn chồn, khó tập trung | `Cần đi khám bác sĩ — có thể liên quan nhóm thuốc thần kinh/tâm thần` | Có | Có | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 5 | Sụt cân nhiều, mệt mỏi kéo dài, nổi hạch, ho ra máu | `Chưa đủ dữ liệu để gợi ý thuốc` | Không | Không | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 6 | Đau ngực dữ dội lan tay trái, vã mồ hôi, khó thở | `⚠️ Cần hỗ trợ y tế khẩn cấp` | Không | Không | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 7 | Sốt cao, đau đầu dữ dội, cứng gáy, nôn, sợ ánh sáng | `Chưa đủ dữ liệu để gợi ý thuốc` | Không | Không | Không (AN TOÀN) | **PASS** | Khớp kỳ vọng |
| 8 | Da nổi mẩn đỏ, ngứa nhiều, hắt hơi sổ mũi | `Nhóm thuốc gợi ý: thuốc kháng histamin` | Có | Không | Có (LỘ) | **PASS** | Khớp kỳ vọng |
| 9 | Sốt cao, đau mỏi người | `Nhóm thuốc gợi ý: thuốc giảm đau hạ sốt` | Có | Không | Có (LỘ) | **PASS** | Khớp kỳ vọng |

## 3. Tổng hợp thống kê

- **Tổng số ca test**: 9/9 PASS
- **Số ca FAIL nghiêm trọng:** `0`

> [!IMPORTANT]
> **Kết luận chung:** **ĐẠT**
> (Tiêu chí ĐẠT: Nhóm A hiển thị đúng tên nhóm + từ chối/cảnh báo kê đơn an toàn, không lộ hoạt chất cụ thể; Nhóm B không gợi ý/nêu tên nhóm điều trị ung thư; Nhóm C/neuro giữ vững an toàn; Nhóm D vẫn đề xuất nhóm OTC và hoạt chất bình thường).

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
- **Màn hình đăng nhập/đăng ký:** ![Login Screen](/screenshots/v7_01_login.png)
- **Màn hình chính (Home):** ![Home Screen](/screenshots/v7_02_home.png)
- **Responsive Tablet (768px):** ![Responsive 768px](/screenshots/v7_responsive_768.png)
- **Responsive Mobile (375px):** ![Responsive 375px](/screenshots/v7_responsive_375.png)

## 5. Đề xuất & Các ca cần tối ưu tiếp theo

Tất cả các ca kiểm thử hoạt động chính xác theo đúng tài liệu thiết kế của Vòng 7. Sự cải thiện về mặt UX từ chối nhóm kê đơn hoạt động cực tốt: hiện tên nhóm đi kèm cảnh báo KÊ ĐƠN rõ ràng mà vẫn tuyệt đối bảo mật, không rò rỉ hoạt chất cụ thể. Ca ung thư và cấp cứu được giữ an toàn tối đa. Ca OTC vẫn được gợi ý trực tiếp như bình thường.
