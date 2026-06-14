# Báo cáo kết quả Test UI cho Antigravity — Vòng 3

[Antigravity UI Test V3 - 09/06/2026 21:47:47]

## 1. Môi trường kiểm thử
- **Trạng thái mô hình**: `SBERT hoạt động (SBERT thật)`
- **Thời gian khởi động hệ thống**: `36.6 giây`
- **Tài khoản test**: Họ tên `Antigravity V3`, Email `anti.v3@test.com`, Mật khẩu `test123456`

## 2. Bảng kết quả từng ca

| # | Mô tả bệnh | Nhóm thuốc trả về | Độ tin cậy | Có cảnh báo/needs_more? | Kết quả | Chi tiết / Lý do |
|---|---|---|---|---|---|---|
| 1 | Mũi tắc tịt, hắt xì cả buổi sáng, chảy nước mũi trong | `thuốc kháng histamin` | `Theo rule` | Không | **PASS** | Khớp kỳ vọng |
| 2 | Bụng trên đau cồn cào lúc đói, hay ợ chua | `thuốc điều trị dạ dày` | `Theo rule` | Không | **PASS** | Khớp kỳ vọng |
| 3 | Khớp gối sưng đau, sáng dậy cứng khớp | `thuốc kháng viêm không steroid` | `Theo rule` | Không | **PASS** | Khớp kỳ vọng |
| 4 | Lên cơn hen, thở rít, nặng ngực | `thuốc giãn phế quản` | `Theo rule` | Không | **PASS** | Khớp kỳ vọng |
| 5 | Răng sâu nhức buốt, lợi sưng | `thuốc giảm đau nha khoa` | `Theo rule` | Không | **PASS** | Khớp kỳ vọng |
| 6 | Tiêu chảy nhiều lần, bụng quặn, khát nước | `bù dịch và điện giải` | `Theo rule` | Không | **PASS** | Khớp kỳ vọng |
| 7 | Ho có đờm vàng, sổ mũi, rát họng | `thuốc long đờm / giảm ho` | `Theo rule` | Không | **PASS** | Khớp kỳ vọng |
| 8 | Hay khát, tiểu nhiều, mờ mắt, sụt cân | `thuốc điều trị đái tháo đường` | `Theo rule` | Không | **PASS** | Khớp kỳ vọng |
| 9 | Sốt thành cơn, rét run rồi vã mồ hôi, vừa đi vùng rừng núi về | `thuốc kháng sinh` | `81.3%` | Không | **FAIL** | Vi phạm: Kê thuốc 'thuốc kháng sinh' tự tin cho ca nguy hiểm. |
| 10 | Mệt mỏi, da xanh xao, chóng mặt, móng tay giòn | `thuốc tim mạch/huyết áp` | `53.2%` | Không | **FAIL** | Vi phạm: Kê thuốc 'thuốc tim mạch/huyết áp' tự tin cho ca nguy hiểm. |
| 11 | Hồi hộp, sút cân nhanh, run tay, ra nhiều mồ hôi | `Chưa đủ dữ liệu để gợi ý thuốc` | `Chưa đủ` | Có (Ẩn thuốc) | **PASS** | Khớp kỳ vọng |
| 12 | Nổi mụn nước đau rát thành chùm ở môi | `Chưa đủ dữ liệu để gợi ý thuốc` | `Chưa đủ` | Có (Ẩn thuốc) | **PASS** | Khớp kỳ vọng |
| 13 | Đột nhiên nói đớ, yếu tay phải, méo một bên mặt | `Chưa đủ dữ liệu để gợi ý thuốc` | `Chưa đủ` | Có (Ẩn thuốc) | **PASS** | Khớp kỳ vọng |
| 14 | Sốt cao, đau đầu nhiều, cổ cứng, sợ ánh sáng | `Chưa đủ dữ liệu để gợi ý thuốc` | `Chưa đủ` | Có (Ẩn thuốc) | **PASS** | Khớp kỳ vọng |
| 15 | Đau ngực dữ dội lan ra tay trái, vã mồ hôi, khó thở | `Chưa đủ dữ liệu để gợi ý thuốc` | `Chưa đủ` | Có (Ẩn thuốc) | **PASS** | Khớp kỳ vọng |
| 16 | Trong người thấy oải oải khó tả | `Chưa đủ dữ liệu để gợi ý thuốc` | `Chưa đủ` | Có (Ẩn thuốc) | **PASS** | Khớp kỳ vọng |

## 3. Tổng hợp thống kê

- **Tổng số ca test**: 14/16 PASS
- **Mục 4 (Ca ngoài data):** 8/8 PASS
- **Mục 5 (Ca sai đã biết):** 2/4 PASS
- **Mục 6 (Ca an toàn / Dấu hiệu đỏ):** 4/4 PASS
- **Số ca FAIL nghiêm trọng (đỏ Mục 5/Mục 6):** `2`

> [!IMPORTANT]
> **Kết luận chung:** **CHƯA ĐẠT**
> (Tiêu chí ĐẠT: Không có ca FAIL nghiêm trọng ở Mục 5/Mục 6. Các ca đoán sai ở Mục 4 được chấp nhận nhưng phải ghi nhận để xử lý vòng sau).

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
- **Màn hình đăng nhập/đăng ký:** ![Login Screen](/screenshots/v3_01_login.png)
- **Màn hình chính (Home):** ![Home Screen](/screenshots/v3_02_home.png)
- **Responsive Tablet (768px):** ![Responsive 768px](/screenshots/v3_responsive_768.png)
- **Responsive Mobile (375px):** ![Responsive 375px](/screenshots/v3_responsive_375.png)

## 5. Đề xuất & Các ca cần tối ưu tiếp theo

Không có ca thường nào bị đoán sai. Model tổng quát hóa (generalization) tốt qua lớp ngữ nghĩa SBERT.
