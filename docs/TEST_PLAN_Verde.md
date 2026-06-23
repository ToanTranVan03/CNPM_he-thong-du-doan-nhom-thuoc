# Kế hoạch Test giao diện Verde — PharmaPredict

> Giao cho **Antigravity** (browser agent) chạy kiểm thử UI/UX sau khi redesign sang phong cách **Verde**.
> Mục tiêu: xác nhận (1) **giao diện** đúng Verde và khớp mockup Figma, (2) **chức năng** không vỡ sau khi đổi giao diện.

## 0. Chuẩn bị

| Mục | Giá trị |
|---|---|
| URL | http://127.0.0.1:5050/ |
| Trình duyệt | Chrome/Edge mới nhất, cửa sổ 1440×900 |
| Trước khi test | Mở DevTools (F12) → tab Console; **Ctrl+Shift+R** để xóa cache CSS |
| Tài khoản user | Đăng ký mới hoặc tài khoản sẵn có |
| Tài khoản admin | Cần tài khoản có quyền admin để hiện menu **"Quản Trị"** |
| Tiêu chí "đạt" về thị giác | Nền ngà ấm `#f3f1e9`, xanh dược liệu `#1f6b5c`, font **Be Vietnam Pro**, bo góc mềm, bóng dịu, animation chuyển trang mượt |

---

## A. Đăng nhập / Đăng ký (Auth)

| Mã | Bước thực hiện | Kết quả kỳ vọng | Ưu tiên |
|---|---|---|---|
| A1 | Mở URL khi chưa đăng nhập | Hiện màn Auth **1 cột, căn giữa màn**, có logo gradient xanh, tông Verde, font Be Vietnam Pro | Cao |
| A2 | Bấm tab "Đăng ký" → nhập họ tên/email/mật khẩu hợp lệ → gửi | Tạo tài khoản thành công, vào được app | Cao |
| A3 | Đăng xuất → "Đăng nhập" với sai mật khẩu | Hiện thông báo lỗi (chữ đỏ Verde), không vào app | Cao |
| A4 | Đăng nhập đúng | Vào app, top bar hiện, tên/email người dùng đúng góc phải | Cao |
| A5 | Luồng "Quên mật khẩu" → "Nhập mã đặt lại" | Form chuyển đúng, gửi được yêu cầu | Trung bình |

## B. Điều hướng & Giao diện chung

| Mã | Bước thực hiện | Kết quả kỳ vọng | Ưu tiên |
|---|---|---|---|
| B1 | Quan sát thanh trên cùng | **Top bar** (không phải sidebar): brand trái, nav giữa, theme + avatar phải | Cao |
| B2 | Bấm lần lượt Trang Chủ / Lịch Sử / Hồ Sơ | Chuyển trang có **animation fade-rise mượt**, mục nav active đổi màu primary-soft | Cao |
| B3 | (Admin) Di chuột/click vào **"Quản Trị ▾"** | Dropdown mở mượt, có nhãn "Khu quản trị" + 5 mục (Dashboard, Lịch Sử Hệ Thống, Từ Điển, Quản Lý Thuốc, Duyệt Phản Hồi); mũi tên xoay | Cao |
| B4 | (User thường) Quan sát nav | **Không** thấy menu "Quản Trị" (ẩn theo quyền) | Cao |
| B5 | Bấm nút **giao diện tối** | Toàn app chuyển dark Verde (nền đậm, xanh ngọc), không vỡ màu/chữ | Cao |
| B6 | Hover lên card/nút | Card nhấc nhẹ + đổ bóng tăng; nút nhích lên mượt | Trung bình |
| B7 | Kiểm tra **không còn** mục "Bệnh Án Mẫu" ở bất kỳ đâu | Không xuất hiện trong nav, dropdown, trang nào | Cao |

## C. Chẩn đoán (Trang chủ) & Kết quả

| Mã | Bước thực hiện | Kết quả kỳ vọng | Ưu tiên |
|---|---|---|---|
| C1 | Quan sát Trang chủ | Bố cục **căn giữa kiểu Console**, panel bệnh án là card nổi | Cao |
| C2 | Gõ mô tả vào ô lớn | Bộ đếm ký tự cập nhật; focus có viền + ring xanh | Cao |
| C3 | Tìm & bấm vài **chip triệu chứng** | Chip đổi sang trạng thái chọn (nền primary-soft, viền xanh); số "đã chọn" tăng | Cao |
| C4 | Bấm "Dùng thử ví dụ" | Ô nhập được điền sẵn nội dung mẫu | Trung bình |
| C5 | Bấm **"Gợi ý nhóm thuốc"** | Chuyển sang **Trang kết quả** mượt; hiện nhóm thuốc + độ tin cậy | Cao |
| C6 | Quan sát thanh độ tin cậy | Thanh gradient **chạy mượt**, màu theo mức (cao=xanh, TB=vàng, thấp=đỏ) + nhãn mức | Cao |
| C7 | Quan sát Top-3 nhóm thuốc | Các dòng `prediction` có thanh tỉ lệ gradient xanh, % tabular | Cao |
| C8 | Bấm 👍 / 👎 phản hồi | Ghi nhận phản hồi; chọn 👎 hiện ô nhập lý do | Cao |
| C9 | Bấm "Lưu kết quả" | Lưu thành công, xuất hiện ở Lịch sử | Cao |
| C10 | Trường hợp dữ liệu **không đủ tin cậy** | Hiển thị trạng thái cảnh báo rõ ràng, không gợi ý chắc chắn | Trung bình |

## D. Lịch sử dự đoán & Hồ sơ

| Mã | Bước thực hiện | Kết quả kỳ vọng | Ưu tiên |
|---|---|---|---|
| D1 | Vào "Lịch Sử Dự Đoán" | Danh sách thẻ ca đã lưu, pill "Đã lưu" xanh, có ngày/giờ | Cao |
| D2 | Gõ từ khóa ô tìm kiếm | Lọc thẻ theo nội dung; rỗng thì hiện empty-state | Trung bình |
| D3 | Vào "Hồ Sơ Của Tôi" | Thông tin tài khoản Verde; nút Đăng xuất hoạt động | Trung bình |

## E. Khu quản trị (Admin)

| Mã | Bước thực hiện | Kết quả kỳ vọng | Ưu tiên |
|---|---|---|---|
| E1 | Quản Trị → **Dashboard** | Stat card Verde; **biểu đồ Chart.js** vẽ được, không vỡ; feed/tóm tắt hiển thị | Cao |
| E2 | Quản Trị → **Quản Lý Thuốc** | Bảng/list Verde (header in hoa nhạt, hover dòng); thêm/sửa/xóa nhóm & thuốc chạy; import CSV ok | Cao |
| E3 | Quản Trị → **Từ Điển Triệu Chứng** | Bảng + tìm kiếm + phân trang; thêm/sửa/xóa ánh xạ chạy | Cao |
| E4 | Quản Trị → **Lịch Sử Hệ Thống** | Bảng toàn hệ thống; lọc theo trạng thái/email; bấm dòng → **modal chi tiết** mở (pop mượt); Xuất CSV | Cao |
| E5 | Quản Trị → **Duyệt Phản Hồi** | Danh sách phản hồi không đồng ý; lọc tab; nút duyệt/đã xử lý chạy | Cao |
| E6 | Mở modal bất kỳ (chi tiết/ánh xạ) | Nền mờ + blur, card bo góc Verde, nút đóng hoạt động | Trung bình |

## F. Responsive / Dark / Hiệu năng

| Mã | Bước thực hiện | Kết quả kỳ vọng | Ưu tiên |
|---|---|---|---|
| F1 | Thu nhỏ cửa sổ < 760px (mobile) | Bố cục dồn 1 cột; **bottom-nav** mobile hiện; không tràn ngang | Cao |
| F2 | Mobile: kiểm tra top bar | Nav cuộn ngang được hoặc gọn; không che nội dung | Trung bình |
| F3 | Bật "giảm chuyển động" của HĐH | Animation tự tắt (prefers-reduced-motion) | Thấp |
| F4 | Suốt phiên test, theo dõi Console (F12) | **Không có lỗi đỏ** JS/CSS/404 | Cao |

---

## Mẫu ghi kết quả

| Mã | Kết quả (Đạt/Lỗi) | Ảnh chụp | Ghi chú lệch so với Figma |
|---|---|---|---|
| A1 | | | |
| ... | | | |

> Gửi lại bảng này (kèm ảnh các mục **Lỗi/lệch**) để fix gọn trong một đợt.
