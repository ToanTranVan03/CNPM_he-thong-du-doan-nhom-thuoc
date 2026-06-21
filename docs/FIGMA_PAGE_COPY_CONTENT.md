# Nội dung copy vào Figma để hoàn thiện 90-95%

> File này dùng để copy nội dung sang các frame trong Figma. Không ảnh hưởng code.

## Frame 01 - Wireframe

Tiêu đề: Wireframe - PharmaPredict AI

Các màn hình cần vẽ:
1. Login
2. Dashboard / Nhập bệnh án
3. Quản lý thuốc
4. Lịch sử dự đoán
5. Hồ sơ cá nhân

Ghi chú đặt dưới frame:
Wireframe được sử dụng để xác định bố cục, vị trí thành phần và luồng thao tác chính trước khi thiết kế mockup chi tiết.

## Frame 02 - User Flow

Tiêu đề: User Flow - Luồng sử dụng hệ thống

Luồng người dùng:
Start -> Login -> Dashboard -> Nhập bệnh án -> Dự đoán -> Xem kết quả -> Lưu lịch sử -> Xem lịch sử -> Logout -> End

Luồng Admin:
Start -> Admin Login -> Quản lý nhóm thuốc -> Quản lý thuốc -> Upload Excel/CSV -> Kiểm tra dữ liệu -> Logout -> End

Luồng lỗi:
Sai tài khoản -> Hiển thị lỗi -> Nhập lại
Bệnh án rỗng -> Validate -> Yêu cầu nhập nội dung
Kết quả không đủ tin cậy -> Hiển thị cảnh báo -> Không gợi ý chắc chắn

## Frame 03 - Mockup

Tiêu đề: Mockup - Giao diện hoàn chỉnh

Màn hình mockup chính:
- Login
- Dashboard nhập bệnh án
- Quản lý thuốc / nhóm thuốc
- Lịch sử dự đoán
- Hồ sơ cá nhân

Ghi chú:
Mockup sử dụng tông màu xanh y khoa, bố cục sidebar, card bo góc, input rõ ràng và trạng thái bảo mật phù hợp với hệ thống hỗ trợ lâm sàng.

## Frame 04 - Prototype

Tiêu đề: Prototype - Tương tác màn hình

Các liên kết cần gắn:
- Login -> Dashboard
- Dashboard -> History
- Dashboard -> Medicines
- Dashboard -> Profile
- Medicines -> Modal thêm/sửa thuốc
- Profile -> Cập nhật thông tin
- Logout -> Login

Ghi chú:
Prototype giúp kiểm tra luồng thao tác trước khi hiện thực bằng code, giảm rủi ro sửa giao diện trong Sprint.

## Frame 05 - Design System

Tiêu đề: Design System - PharmaPredict AI

Typography:
- Font: Inter
- Heading: 32px / 40px, Bold
- Body: 16px / 24px, Regular
- Label: 14px / 20px, Medium

Colors:
- Primary: #0B5FB5
- Primary Hover: #0A4F97
- Background: #F5F7FB
- Surface: #FFFFFF
- Text: #0E1B2B
- Success: #1B8A5A
- Warning: #B7791F
- Danger: #C0392B

Components:
- Button Primary
- Button Secondary
- Input
- Textarea
- Card
- Sidebar item
- Status pill
- Modal
- Table

Ghi chú:
Design System giúp giao diện thống nhất giữa Figma và frontend, hỗ trợ tái sử dụng component trong các User Story sau.
