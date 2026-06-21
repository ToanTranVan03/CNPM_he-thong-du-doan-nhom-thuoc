# Bulk Import Feature

## Tổng quan

Tính năng Bulk Import cho phép nhập dữ liệu hàng loạt từ file Excel/CSV vào hệ thống quản lý dữ liệu thuốc. Tính năng này giúp:

- ✅ Nhập nhanh danh sách nhóm thuốc
- ✅ Nhập nhanh danh sách thuốc chi tiết
- ✅ Validate dữ liệu tự động
- ✅ Xử lý lỗi từng hàng một cách rõ ràng
- ✅ Rollback transaction nếu có lỗi

## Cấu trúc thư mục

```
backend/
├── route_bulk_import.py       # API endpoints cho bulk import
├── models.py                  # Database models
└── app.py                     # Main app (đã thêm blueprint)

data/
├── sample_nhom_thuoc.csv      # Sample data for drug groups
└── sample_thuoc.csv           # Sample data for drugs

docs/
└── BULK_IMPORT_API.md         # Detailed API documentation

test_bulk_import.py             # Test script
```

## Các file được tạo/chỉnh sửa

### 1. **backend/route_bulk_import.py** (NEW)
Chứa toàn bộ logic bulk import:
- `bulk_import_thuoc()` - Nhập thuốc từ file
- `bulk_import_nhom_thuoc()` - Nhập nhóm thuốc từ file
- `download_thuoc_template()` - Tải template import thuốc
- `download_nhom_thuoc_template()` - Tải template import nhóm thuốc
- Các hàm helper cho đọc file, validate dữ liệu

**Tính năng:**
- Hỗ trợ CSV và Excel (.xlsx, .xls)
- Validate dữ liệu tự động
- Xử lý lỗi chi tiết
- Rollback on error
- Hỗ trợ tiếng Việt

### 2. **backend/app.py** (MODIFIED)
Bổ sung:
```python
from route_bulk_import import bulk_import_bp
app.register_blueprint(bulk_import_bp)
```

### 3. **requirements.txt** (MODIFIED)
Thêm dependencies:
```
flask-sqlalchemy      # Database ORM
openpyxl              # Excel support
```

## Cách sử dụng

### Quick Start

1. **Chuẩn bị dữ liệu:**
   ```bash
   # Tải template
   curl -X GET http://localhost:5000/api/bulk-import/template/nhom-thuoc -o nhom_thuoc.csv
   curl -X GET http://localhost:5000/api/bulk-import/template/thuoc -o thuoc.csv
   
   # Chỉnh sửa file CSV với dữ liệu của bạn
   ```

2. **Import nhóm thuốc trước:**
   ```bash
   curl -X POST http://localhost:5000/api/bulk-import/nhom-thuoc \
     -F "file=@nhom_thuoc.csv"
   ```

3. **Import thuốc:**
   ```bash
   curl -X POST http://localhost:5000/api/bulk-import/thuoc \
     -F "file=@thuoc.csv"
   ```

### Sử dụng Python

```python
import requests

# Import nhóm thuốc
with open('nhom_thuoc.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/api/bulk-import/nhom-thuoc',
        files={'file': f}
    )
    print(response.json())

# Import thuốc
with open('thuoc.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/api/bulk-import/thuoc',
        files={'file': f}
    )
    print(response.json())
```

### Sử dụng JavaScript/Frontend

```javascript
const fileInput = document.getElementById('fileInput');
const file = fileInput.files[0];

const formData = new FormData();
formData.append('file', file);

fetch('http://localhost:5000/api/bulk-import/thuoc', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => {
  console.log('Import result:', data);
  console.log(`Imported: ${data.imported}, Skipped: ${data.skipped}`);
  if (data.errors.length > 0) {
    console.log('Errors:', data.errors);
  }
});
```

## API Endpoints

### 1. POST /api/bulk-import/nhom-thuoc
Nhập danh sách nhóm thuốc từ file

**Request:**
- Content-Type: multipart/form-data
- Field: file (CSV/Excel)

**Response:**
```json
{
  "message": "Import thành công",
  "imported": 5,
  "skipped": 1,
  "errors": [
    {
      "row": 3,
      "message": "Nhóm thuốc 'Kháng sinh' đã tồn tại"
    }
  ]
}
```

### 2. POST /api/bulk-import/thuoc
Nhập danh sách thuốc từ file

**Request:**
- Content-Type: multipart/form-data
- Field: file (CSV/Excel)

**Response:**
```json
{
  "message": "Import thành công",
  "imported": 10,
  "skipped": 2,
  "errors": [...]
}
```

### 3. GET /api/bulk-import/template/nhom-thuoc
Tải file template CSV

### 4. GET /api/bulk-import/template/thuoc
Tải file template CSV

## Định dạng File

### Nhóm Thuốc (nhom_thuoc.csv)
```csv
ten_nhom,mo_ta
Kháng sinh,Dùng để điều trị nhiễm khuẩn
Giảm đau hạ sốt,Làm giảm đau và hạ sốt
Vitamin,Bổ sung vi chất dinh dưỡng
```

**Cột:**
- `ten_nhom` (required): Tên nhóm thuốc
- `mo_ta` (optional): Mô tả nhóm

### Thuốc (thuoc.csv)
```csv
ten_thuoc,nhom_thuoc_id,hoat_chat,ham_luong,dang_bao_che,hang_san_xuat,nuoc_san_xuat,so_dang_ky,gia_tham_khao,don_vi_tinh,mo_ta
Amoxicillin 500mg,1,Amoxicillin,500mg,Viên nén,Công ty A,Việt Nam,123456,5000,Hộp,Kháng sinh
Paracetamol 500mg,2,Paracetamol,500mg,Viên nén,Công ty B,Việt Nam,123457,3000,Hộp,Giảm đau
```

**Cột:**
- `ten_thuoc` (required): Tên thuốc
- `nhom_thuoc_id` (required): ID hoặc tên nhóm thuốc
- `hoat_chat` (optional): Hoạt chất chính
- `ham_luong` (optional): Hàm lượng
- `dang_bao_che` (optional): Dạng bào chế
- `hang_san_xuat` (optional): Hãng sản xuất
- `nuoc_san_xuat` (optional): Nước sản xuất
- `so_dang_ky` (optional): Số đăng ký
- `gia_tham_khao` (optional): Giá tham khảo
- `don_vi_tinh` (optional): Đơn vị tính
- `mo_ta` (optional): Mô tả

## Features

✅ **Multi-format Support** - CSV, Excel (.xlsx, .xls)

✅ **Automatic Validation** - Kiểm tra trường bắt buộc, kiểu dữ liệu

✅ **Batch Insert** - Nhập hàng loạt với performance tối ưu

✅ **Detailed Error Reporting** - Chi tiết lỗi từng hàng

✅ **Transaction Safety** - Rollback on error

✅ **Vietnamese Support** - Hỗ trợ tên cột tiếng Việt

✅ **Flexible Column Mapping** - Tên cột tiếng Anh hoặc Việt

✅ **Template Download** - Tải file template sẵn sàng

✅ **Large File Support** - Hỗ trợ file tới 50MB

✅ **Progress Feedback** - Báo cáo số dòng thành công/thất bại

## Ví dụ đầy đủ

### Step 1: Tải template
```bash
curl http://localhost:5000/api/bulk-import/template/nhom-thuoc -o nhom.csv
curl http://localhost:5000/api/bulk-import/template/thuoc -o thuoc.csv
```

### Step 2: Chỉnh sửa file
Mở file CSV trong Excel, chỉnh sửa dữ liệu

### Step 3: Import dữ liệu
```bash
# Import nhóm thuốc trước
curl -X POST http://localhost:5000/api/bulk-import/nhom-thuoc \
  -F "file=@nhom.csv"

# Sau đó import thuốc
curl -X POST http://localhost:5000/api/bulk-import/thuoc \
  -F "file=@thuoc.csv"
```

### Step 4: Kiểm tra kết quả
Response sẽ hiển thị:
- Số dòng import thành công
- Số dòng bị skip
- Chi tiết lỗi (nếu có)

## Testing

### Chạy test script
```bash
cd /path/to/project
python test_bulk_import.py
```

Script sẽ:
1. Tải templates
2. Test import nhóm thuốc
3. Test import thuốc
4. In kết quả

### Manual testing
```bash
# Test upload nhóm thuốc
curl -X POST http://localhost:5000/api/bulk-import/nhom-thuoc \
  -F "file=@data/sample_nhom_thuoc.csv"

# Test upload thuốc
curl -X POST http://localhost:5000/api/bulk-import/thuoc \
  -F "file=@data/sample_thuoc.csv"

# Test template download
curl http://localhost:5000/api/bulk-import/template/nhom-thuoc
```

## Lưu ý

⚠️ **Nhóm thuốc phải tồn tại** trước khi import thuốc

⚠️ **Không thể import nhóm trùng lặp** với tên đã tồn tại

⚠️ **Encoding phải là UTF-8** cho file CSV

⚠️ **Tối đa 50MB** cho mỗi file

⚠️ **Headers phải chính xác** (tên cột không được sai)

## Troubleshooting

### Lỗi: "File không được chọn"
Đảm bảo file được upload đúng

### Lỗi: "Nhóm thuốc không tồn tại"
- Nhập nhóm thuốc trước
- Hoặc kiểm tra ID nhóm có đúng

### Lỗi: "Thiếu tên thuốc"
- Kiểm tra cột ten_thuoc có giá trị
- Không có khoảng trắng thừa

### Lỗi: "Database error"
- Kiểm tra server Flask đang chạy
- Kiểm tra database accessible

## Performance

- **Small files** (< 1000 rows): < 1 second
- **Medium files** (1000-10000 rows): 1-5 seconds
- **Large files** (10000-50000 rows): 5-30 seconds

Tốc độ phụ thuộc vào:
- Kích thước file
- Số lượng validations
- Tốc độ database
- Tài nguyên server

## License

Same as main project

## Support

Xem chi tiết tại `docs/BULK_IMPORT_API.md`
