# Báo cáo kết quả Test UI cho Antigravity — Vòng 6
        
[Antigravity UI Test V6 - 10/06/2026 21:32:58]

## 1. Môi trường kiểm thử
- **Trạng thái mô hình**: `SBERT hoạt động (SBERT thật)`
- **Thời gian khởi động hệ thống**: `36.1 giây`
- **Tài khoản test**: Họ tên `Antigravity V6`, Email `anti.v6@test.com`, Mật khẩu `test123456`
- **LLM Context Enabled**: `0`

## 2. Bảng kết quả từng ca

| # | Mô tả bệnh | Nhóm thuốc trả về | Có cảnh báo/cấp cứu? | Kết quả | Chi tiết / Lý do |
|---|---|---|---|---|---|
| 1 | Da nổi mẩn đỏ, ngứa nhiều, có mảng tróc vảy | `thuốc kháng histamin` | Không | **PASS** | Khớp kỳ vọng |
| 2 | Đau bụng vùng thượng vị, ợ chua, đầy bụng | `thuốc điều trị dạ dày` | Không | **PASS** | Khớp kỳ vọng |
| 3 | Ho có đờm vàng, sổ mũi, rát họng | `thuốc long đờm / giảm ho` | Không | **PASS** | Khớp kỳ vọng |
| 4 | Sốt cao, đau mỏi người | `thuốc giảm đau hạ sốt` | Không | **PASS** | Khớp kỳ vọng |
| 5 | Hồi hộp, tim đập nhanh, huyết áp cao 160 | `thuốc tim mạch/huyết áp` | Không | **PASS** | Khớp kỳ vọng |
| 6 | Sốt cao, ho, nghi nhiễm khuẩn | `thuốc giảm đau hạ sốt` | Không | **PASS** | Đoán ra nhóm thường 'thuốc giảm đau hạ sốt' thay vì kháng sinh. Khớp kỳ vọng y tế. |
| 7 | Đau ngực dữ dội lan tay trái, vã mồ hôi, khó thở | `Chưa đủ dữ liệu để gợi ý thuốc` | CẤP CỨU | **PASS** | Khớp kỳ vọng |
| 8 | Trong người thấy oải oải khó tả | `Chưa đủ dữ liệu để gợi ý thuốc` | CẦN THÊM TT | **PASS** | Khớp kỳ vọng |
| 9 | Sốt thành cơn, rét run, vừa đi vùng rừng núi về | `thuốc điều trị sốt rét` | Không | **PASS** | Khớp kỳ vọng |
| 10 | Mệt mỏi, da xanh xao, chóng mặt, móng tay giòn | `vitamin và khoáng chất` | Không | **PASS** | Khớp kỳ vọng |

## 3. Tổng hợp thống kê

- **Tổng số ca test**: 10/10 PASS
- **Nhóm A (Output gọn cho ca thường):** 4/4 PASS
- **Nhóm B (Nhóm rủi ro/chuyên khoa):** 2/2 PASS
- **Nhóm C (An toàn không lộ thuốc):** 2/2 PASS
- **Nhóm D (Regression phán đoán cũ):** 2/2 PASS
- **Số ca FAIL nghiêm trọng:** `0`

> [!IMPORTANT]
> **Kết luận chung:** **ĐẠT**
> (Tiêu chí ĐẠT: Nhóm A output ngắn gọn, ≤3 hoạt chất tiếng Việt sạch, không dump thô; Nhóm B không có hoạt chất cụ thể, hiện note bác sĩ; Nhóm C và D hoạt động chính xác không thoái lui).

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
- **Màn hình đăng nhập/đăng ký:** ![Login Screen](/screenshots/v6_01_login.png)
- **Màn hình chính (Home):** ![Home Screen](/screenshots/v6_02_home.png)
- **Responsive Tablet (768px):** ![Responsive 768px](/screenshots/v6_responsive_768.png)
- **Responsive Mobile (375px):** ![Responsive 375px](/screenshots/v6_responsive_375.png)

## 5. Đề xuất & Các ca cần tối ưu tiếp theo

Tất cả các ca kiểm thử hoạt động chính xác theo đúng tài liệu thiết kế. Output gọn gàng, hoạt chất minh hoạ sạch bằng tiếng Việt, các nhóm nguy cơ cao được chuyển hướng khám bác sĩ an toàn, không còn dump thô trùng lặp tiếng Anh.
