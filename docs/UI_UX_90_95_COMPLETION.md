# UI/UX Figma Completion 90-95% - PharmaPredict AI

> File này chỉ là tài liệu minh chứng UI/UX, không thay đổi code chạy hệ thống.
> Mục tiêu: đáp ứng yêu cầu 3.2 Thiết kế UI/UX: Wireframe, User Flow, Prototype, Mockup, Design System.

## 1. Link Figma chính

Figma Make / Prototype:
https://www.figma.com/make/N6QHloV4xVQyq5w5DHkegn/Review-and-fulfill-request?p=f&t=g3iLRQrvFzUoq8Qq-0&preview-route=%2Flogin

## 2. Các trang cần có trong Figma

Để đạt 90-95%, trong Figma nên có tối thiểu các Page/Frame sau:

```text
01_Wireframe
02_User_Flow
03_Mockup
04_Prototype
05_Design_System
06_Export_PDF
```

## 3. Wireframe cần có

Wireframe là bản khung đen trắng, chưa cần màu sắc chi tiết.

### 3.1 Login Wireframe

Thành phần:
- Logo / tên hệ thống MediPredict AI.
- Ô nhập tên đăng nhập.
- Ô nhập mật khẩu.
- Nút đăng nhập.
- Khu vực tài khoản demo.

Luồng:
```text
Người dùng mở website -> Trang đăng nhập -> Nhập tài khoản -> Nhấn đăng nhập
```

### 3.2 Dashboard / Nhập bệnh án Wireframe

Thành phần:
- Sidebar điều hướng.
- Khu vực nhập mô tả bệnh án / triệu chứng.
- Nút dự đoán.
- Card thống kê dữ liệu.
- Khu vực mẹo viết bệnh án.

Luồng:
```text
Dashboard -> Nhập triệu chứng -> Bấm dự đoán -> Xem kết quả
```

### 3.3 Quản lý thuốc / nhóm thuốc Wireframe

Thành phần:
- Bảng danh sách nhóm thuốc / thuốc.
- Nút thêm mới.
- Nút sửa.
- Nút xóa.
- Form hoặc modal nhập dữ liệu.

### 3.4 Hồ sơ cá nhân Wireframe

Thành phần:
- Thông tin người dùng.
- Form cập nhật hồ sơ.
- Nút lưu thay đổi.
- Khu vực đổi mật khẩu.

### 3.5 Lịch sử dự đoán Wireframe

Thành phần:
- Bảng lịch sử.
- Ngày dự đoán.
- Nội dung triệu chứng.
- Kết quả nhóm thuốc.
- Bộ lọc theo ngày.

## 4. User Flow cần có

### 4.1 Luồng người dùng thường

```text
Start
  ↓
Mở website
  ↓
Đăng nhập
  ↓
Dashboard
  ↓
Nhập triệu chứng / bệnh án
  ↓
Tiền xử lý văn bản
  ↓
Trích xuất triệu chứng
  ↓
Dự đoán nhóm thuốc
  ↓
Hiển thị Top nhóm thuốc phù hợp
  ↓
Lưu lịch sử dự đoán
  ↓
Xem lại lịch sử
  ↓
Logout
End
```

### 4.2 Luồng Admin

```text
Start
  ↓
Admin đăng nhập
  ↓
Vào trang quản lý thuốc
  ↓
Quản lý nhóm thuốc
  ↓
Thêm / sửa / xóa nhóm thuốc
  ↓
Quản lý thuốc
  ↓
Thêm / sửa / xóa thuốc
  ↓
Upload Excel/CSV dữ liệu từ điển
  ↓
Kiểm tra dữ liệu sau import
  ↓
Logout
End
```

### 4.3 Luồng xử lý lỗi

```text
Người dùng nhập sai tài khoản
  ↓
Hiển thị thông báo lỗi
  ↓
Cho nhập lại
```

```text
Người dùng để trống bệnh án
  ↓
Disable nút dự đoán hoặc hiển thị validate
  ↓
Yêu cầu nhập nội dung
```

```text
Dữ liệu không đủ tin cậy
  ↓
Hiển thị cảnh báo không đủ tin cậy
  ↓
Không gợi ý thuốc như kết quả chắc chắn
```

## 5. Prototype cần gắn trong Figma

Trong Figma, bật tab Prototype và nối các màn hình:

```text
Login.Button Đăng nhập -> Dashboard
Sidebar.Trang chủ -> Dashboard
Sidebar.Lịch sử dự đoán -> History
Sidebar.Quản lý thuốc -> Medicines
Sidebar.Hồ sơ của tôi -> Profile
Button.Logout -> Login
Dashboard.Button Dự đoán -> Result / Result Section
Medicines.Button Thêm -> Modal Thêm thuốc
Medicines.Button Sửa -> Modal Sửa thuốc
```

Yêu cầu tối thiểu:
- Bấm được từ Login sang Dashboard.
- Bấm sidebar chuyển được giữa các màn hình chính.
- Có đường quay lại hoặc logout.

## 6. Mockup hiện có

Mockup hiện tại đã thể hiện:
- Giao diện MediPredict AI.
- Tông màu xanh y khoa.
- Sidebar điều hướng.
- Form đăng nhập.
- Dashboard nhập bệnh án.
- Quản lý thuốc / nhóm thuốc.
- Hồ sơ người dùng.
- Lịch sử dự đoán.

## 7. Design System tóm tắt

Chi tiết xem thêm file:

```text
docs/DESIGN_SYSTEM.md
```

Các thành phần chính:
- Typography: Inter.
- Primary color: xanh y khoa.
- Button: bo góc, có trạng thái hover/disabled.
- Input/Textarea: border nhẹ, focus rõ.
- Card: bo góc, shadow nhẹ.
- Status: success/warning/danger.
- Layout: sidebar + content area.
- Dark/Light mode.

## 8. Mapping với backlog / Jira

Các hạng mục UI/UX này liên quan trực tiếp tới:

| Task | Nội dung | Liên quan |
|---|---|---|
| Task 1 | Thiết kế UI trang đăng nhập trên Figma | Login wireframe/mockup/prototype |
| Task 24 | Wireframe/Prototype khu vực nhập bệnh án trên Figma | Dashboard nhập bệnh án |
| Task 25 | UI Textarea nhập bệnh án | Form nhập bệnh án |
| Task 35 | UI hiển thị Top 3 nhóm thuốc | Khu vực kết quả dự đoán |
| Task 43 | UI bảng lịch sử | History screen |
| Task 47 | UI duyệt phản hồi Admin | Admin review screen nếu có |

## 9. Checklist trước khi nộp

- [ ] Figma có Page Wireframe.
- [ ] Figma có Page User Flow.
- [ ] Figma có Page Mockup.
- [ ] Figma có gắn Prototype click được.
- [ ] Figma có Page Design System.
- [ ] Đã export PDF/ảnh minh chứng nếu giảng viên yêu cầu.
- [ ] Link Figma được ghi trong README hoặc docs/UI_UX_FIGMA.md.
- [ ] Không thay đổi backend/API/database khi chỉ bổ sung UI/UX documentation.

## 10. Kết luận

Nhóm sử dụng Figma làm công cụ thiết kế UI/UX trước khi đưa User Story vào Sprint phát triển. Figma đóng vai trò là bản thiết kế chuẩn, bao gồm Wireframe, User Flow, Mockup, Prototype và Design System. Source code hiện tại giữ nguyên để đảm bảo không phá vỡ tiến độ các task đã hoàn thành trên GitHub/Jira.
