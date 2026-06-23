# Loại bỏ tính năng bệnh án mẫu

## Bối cảnh

Bảng `benh_an_mau` hiện đứng độc lập, không có khóa ngoại tới `mo_ta_benh_an` hoặc `quan_tri_vien`. PostgreSQL đang có 5 bản ghi seed trong bảng này, 17 bản ghi `mo_ta_benh_an`, và chưa có bản ghi `quan_tri_vien`.

Sau khi cân nhắc bổ sung quan hệ, quyết định sản phẩm là ưu tiên người dùng tự nhập mô tả bệnh án. Vì vậy, hệ thống sẽ loại bỏ hoàn toàn tính năng bệnh án mẫu thay vì tiếp tục mở rộng mô hình dữ liệu cho tính năng này.

## Mục tiêu

- Loại bỏ bảng và toàn bộ mã phục vụ `benh_an_mau`.
- Giữ nguyên luồng người dùng tự nhập mô tả rồi gửi dự đoán.
- Giữ `mo_ta_benh_an` làm nơi lưu nội dung người dùng đã nhập khi ghi lịch sử dự đoán.
- Không để lại API, giao diện, CSS, script seed hoặc test chỉ phục vụ tính năng đã bỏ.

## Ngoài phạm vi

- Không thay đổi quan hệ hiện có của `mo_ta_benh_an`.
- Không thay đổi thuật toán dự đoán, lịch sử dự đoán hoặc phân quyền chung.
- Không xóa nút tĩnh **Dùng thử ví dụ**. Nút này chỉ hỗ trợ onboarding, không đọc hoặc ghi bảng bệnh án mẫu.
- Không thay đổi cấu hình PostgreSQL cục bộ trong `.env`.

## Thay đổi thiết kế

### Cơ sở dữ liệu

- Xóa bảng `benh_an_mau` bằng migration riêng với `DROP TABLE IF EXISTS benh_an_mau`.
- Không chuyển đổi 5 bản ghi hiện tại vì chúng đều là dữ liệu seed và không được bảng khác tham chiếu.
- Xóa `BenhAnMau` khỏi SQLAlchemy và khỏi `EXPECTED_TABLES` để `db.create_all()` không tạo lại bảng.

Migration phải chạy an toàn khi bảng đã bị xóa và không được tác động tới bảng khác.

### Backend

Xóa ba endpoint:

- `GET /api/benh-an-mau`
- `POST /api/admin/benh-an-mau`
- `DELETE /api/admin/benh-an-mau/<ma>`

Luồng `/api/predict` không thay đổi. Khi dự đoán được ghi vào PostgreSQL, backend tiếp tục tạo `MoTaBenhAn` từ trường `notes` do người dùng nhập.

### Frontend

- Xóa bộ chọn **Nạp bệnh án mẫu** trên Trang chủ.
- Xóa mục điều hướng và trang quản trị **Bệnh án mẫu**.
- Xóa trạng thái cache, lời gọi API, hàm render, xử lý thêm/xóa và CSS liên quan.
- Giữ ô nhập bệnh án, nút xóa nội dung và nút **Dùng thử ví dụ**.

### Script và tài liệu

- Xóa `scripts/seed_benh_an_mau.py`.
- Xóa `scripts/test_benh_an_mau.py`.
- Xóa `run_ui_tests_us29.py`.
- Xóa hướng dẫn chạy seed bệnh án mẫu trong README.

## Xử lý lỗi và tương thích

- Migration dùng `IF EXISTS` để có thể chạy lặp lại.
- Sau khi triển khai, các endpoint bệnh án mẫu cũ trả `404` vì không còn route.
- Không duy trì contract cũ vì tính năng bị loại bỏ hoàn toàn.
- Dữ liệu và quan hệ của `mo_ta_benh_an`, `ket_qua_du_doan` và `lich_su_du_doan` phải được giữ nguyên.

## Kiểm thử

- Chạy test schema để xác nhận `benh_an_mau` không còn trong danh sách bảng kỳ vọng.
- Kiểm tra PostgreSQL thật không còn bảng `benh_an_mau` sau migration.
- Chạy các test backend liên quan đến auth, dự đoán và lưu lịch sử phù hợp với phạm vi thay đổi.
- Kiểm tra frontend không còn selector hoặc điều hướng bệnh án mẫu.
- Kiểm tra người dùng vẫn có thể nhập tay, dùng ví dụ tĩnh, gửi dự đoán và xem kết quả.
- Tìm kiếm toàn repo để đảm bảo không còn tham chiếu chức năng tới `benh_an_mau`, ngoại trừ migration hoặc tài liệu lịch sử cần thiết.

## Tiêu chí hoàn thành

- Không còn bảng `benh_an_mau` trong PostgreSQL.
- Không còn model, API, giao diện quản trị hoặc bộ chọn bệnh án mẫu.
- Luồng nhập tay và dự đoán hoạt động như trước.
- Test hồi quy trong phạm vi đều đạt.
