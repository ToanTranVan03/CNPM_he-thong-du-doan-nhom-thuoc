# 📁 Hướng Dẫn Sử Dụng Tính Năng Kéo Thả Upload File

## 🎯 Tổng Quan

Tính năng **Drag & Drop Upload** cho phép bạn nhập dữ liệu thuốc hàng loạt từ file CSV hoặc Excel. Thay vì thêm từng thuốc một, bạn có thể nhập hàng chục hoặc hàng trăm thuốc cùng lúc.

---

## ✨ Tính Năng Chính

✅ **Kéo thả file** trực tiếp vào vùng upload  
✅ **Hỗ trợ CSV & Excel** (.csv, .xlsx, .xls)  
✅ **Tự động mapping cột** - Hệ thống tự nhận dạng cột từ tiêu đề  
✅ **Xử lý hàng loạt** - Thêm nhiều thuốc cùng lúc  
✅ **Báo cáo chi tiết** - Hiển thị số lượng thành công/lỗi  
✅ **Hỗ trợ tiếng Việt** - Tất cả thông báo bằng tiếng Việt  

---

## 🚀 Cách Sử Dụng

### Bước 1: Vào trang Quản lý Thuốc
- Đăng nhập vào hệ thống
- Chọn **"Quản Lý Thuốc"** từ menu chính
- Nhấn nút **"Nhập từ file"** (upload_file icon)

### Bước 2: Chuẩn Bị File
File của bạn phải có các cột **bắt buộc**:
- **Tên thuốc** (name, tên, medicine_name, ...)
- **Nhóm thuốc** (group, nhom, drug_group, ...)

**Các cột tùy chọn:**
- Hoạt chất (active_substance, hoạt chất, ...)
- Hàm lượng (strength, dose, hàm lượng, ...)
- Dạng bào chế (form, dạng, ...)
- Đơn vị tính (unit, đơn vị, ...)
- Hãng sản xuất (manufacturer, hang, ...)
- Nước sản xuất (country, nuoc, ...)
- Số đăng ký (registration, so_dk, ...)
- Giá (price, gia, ...)
- Mô tả (description, mo_ta, ...)

### Bước 3: Upload File
**Cách 1: Kéo thả**
- Kéo file từ máy tính
- Thả vào vùng upload
- Hệ thống tự xử lý

**Cách 2: Chọn từ máy**
- Nhấn **"chọn từ máy tính"** trong vùng upload
- Chọn file từ thư mục
- Nhấn mở (Open)

### Bước 4: Kiểm Tra Kết Quả
- Hệ thống sẽ hiển thị tiến trình xử lý
- Sau khi hoàn thành, bạn sẽ thấy báo cáo:
  - ✅ Số thuốc thêm thành công
  - ❌ Số lỗi (nếu có)
  - Chi tiết lỗi từng hàng

---

## 📋 Ví Dụ File CSV

**File: thuoc_import.csv**
```csv
Tên thuốc,Hoạt chất,Hàm lượng,Dạng bào chế,Nhóm thuốc,Hãng sản xuất,Giá
Paracetamol 500mg,Paracetamol,500mg,Viên nén,Hạ sốt - Giảm đau,Dược Hậu Giang,8000
Amoxicillin 500mg,Amoxicillin,500mg,Viên nén,Kháng sinh,Dược Hậu Giang,15000
Vitamin C 1000mg,Vitamin C,1000mg,Viên nén,Vitamin và khoáng chất,Dược Hậu Giang,5000
```

**Yêu cầu:**
- Hàng đầu tiên là tiêu đề cột
- Mỗi hàng = 1 thuốc
- Giá trị để trống nếu không có dữ liệu

---

## 📊 Ví Dụ File Excel (.xlsx)

File Excel có cấu trúc tương tự CSV:

| Tên thuốc | Hoạt chất | Hàm lượng | Dạng bào chế | Nhóm thuốc | Hãng sản xuất | Giá |
|-----------|-----------|----------|--------------|-----------|--------------|-----|
| Paracetamol 500mg | Paracetamol | 500mg | Viên nén | Hạ sốt - Giảm đau | Dược Hậu Giang | 8000 |
| Amoxicillin 500mg | Amoxicillin | 500mg | Viên nén | Kháng sinh | Dược Hậu Giang | 15000 |

---

## ⚠️ Lưu Ý Quan Trọng

### Lỗi Thường Gặp

**❌ Nhóm thuốc không tồn tại**
- **Nguyên nhân:** Tên nhóm thuốc trong file không khớp với hệ thống
- **Giải pháp:** 
  - Kiểm tra tên nhóm trong bảng "Quản lý Danh mục Nhóm thuốc"
  - Đảm bảo đánh vần chính xác
  - Chú ý chữ hoa/thường

**❌ Thiếu tên thuốc hoặc nhóm**
- **Nguyên nhân:** Hàng nào đó không có dữ liệu bắt buộc
- **Giải pháp:** 
  - Kiểm tra file, điền đủ 2 cột bắt buộc
  - Xóa hàng trống

**❌ Định dạng file không hỗ trợ**
- **Nguyên nhân:** File không phải CSV, XLSX hoặc XLS
- **Giải pháp:** 
  - Chuyển đổi file sang CSV hoặc XLSX
  - Sử dụng Excel hoặc Google Sheets để lưu lại

---

## 🔧 Cấu Trúc Code

### HTML Elements
```html
<!-- Nút bật/tắt upload -->
<button id="btn-toggle-upload">Nhập từ file</button>

<!-- Vùng kéo thả -->
<div id="file-upload-zone">
  <!-- Nội dung, file input, tiến trình, kết quả -->
</div>
```

### JavaScript Functions
- `handleFileUpload(file)` - Xử lý file được chọn
- `parseCSV(text)` - Phân tích CSV
- `parseXLSX(file)` - Phân tích Excel
- `mapColumnName(name, possibleNames)` - Tự động mapping cột

### CSS Classes
- `.file-upload-zone` - Vùng kéo thả chính
- `.upload-progress` - Thanh tiến trình
- `.upload-result` - Kết quả cuối cùng

---

## 💡 Mẹo Sử Dụng

### Tối ưu hóa file
1. **Làm sạch dữ liệu** - Xóa hàng trống, cột thừa
2. **Chuẩn hóa tên** - Tên nhóm phải đúng chính xác
3. **Kiểm tra kiểu dữ liệu** - Giá phải là số, không có chữ
4. **Mã hóa UTF-8** - Đảm bảo tiếng Việt hiển thị đúng

### Xử lý lỗi
- Nếu có lỗi một vài hàng, hệ thống vẫn thêm những hàng khác
- Kiểm tra báo cáo lỗi để sửa lại
- Upload lại file sau khi sửa

### Batch processing
- Nếu file quá lớn (>500 hàng), chia thành nhiều file nhỏ
- Upload từng file để dễ theo dõi

---

## 🔐 An Toàn & Quyền Hạn

- **Yêu cầu đăng nhập** - Chỉ người dùng đã đăng nhập mới có thể upload
- **Xác thực token** - Tất cả yêu cầu đều được xác thực qua Bearer token
- **Dữ liệu riêng tư** - Dữ liệu nhập vào chỉ lưu trong cơ sở dữ liệu

---

## 📞 Hỗ Trợ

Nếu có vấn đề:
1. Kiểm tra lại file CSV/Excel
2. Đảm bảo nhóm thuốc đã tồn tại
3. Xem báo cáo lỗi chi tiết từ hệ thống
4. Liên hệ admin nếu cần hỗ trợ thêm

---

## 🔄 Các Cập Nhật Trong Tương Lai

- [ ] Hỗ trợ định dạng JSON
- [ ] Xem trước dữ liệu trước khi nhập
- [ ] Tải template Excel có sẵn
- [ ] Nhập dữ liệu từ URL hoặc Google Drive
- [ ] Lịch sử nhập file

---

**Phiên bản:** 1.0  
**Cập nhật lần cuối:** 2026-06-19  
**Trạng thái:** ✅ Hoạt động
