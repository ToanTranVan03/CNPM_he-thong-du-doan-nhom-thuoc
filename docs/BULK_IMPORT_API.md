# Bulk Import API Documentation

## Giới thiệu

API Bulk Import cho phép nhập dữ liệu hàng loạt từ file Excel/CSV vào cơ sở dữ liệu. Hỗ trợ nhập:
- **Nhóm thuốc** (Drug Groups)
- **Thuốc** (Drugs)

## Endpoints

### 1. Import Nhóm Thuốc

**Endpoint:** `POST /api/bulk-import/nhom-thuoc`

**Mô tả:** Nhập danh sách nhóm thuốc từ file Excel/CSV

**Content-Type:** `multipart/form-data`

**Parameters:**
- `file` (required): File CSV hoặc Excel (.csv, .xlsx, .xls)

**Định dạng file:**
```
ten_nhom,mo_ta
Thuốc kháng sinh,Dùng để điều trị nhiễm khuẩn
Thuốc giảm đau hạ sốt,Làm giảm đau và hạ sốt
Vitamin và khoáng chất,Bổ sung dinh dưỡng
```

**Cột yêu cầu:**
- `ten_nhom` (hoặc `tên_nhóm`): Tên nhóm thuốc

**Cột tùy chọn:**
- `mo_ta` (hoặc `mô_tả`): Mô tả nhóm thuốc

**Response (200):**
```json
{
  "message": "Import thành công",
  "imported": 5,
  "skipped": 1,
  "errors": [
    {
      "row": 3,
      "message": "Nhóm thuốc 'Thuốc kháng sinh' đã tồn tại"
    }
  ]
}
```

**Error Response (400/500):**
```json
{
  "error": "Định dạng file không hợp lệ. Vui lòng sử dụng CSV hoặc Excel"
}
```

---

### 2. Import Thuốc

**Endpoint:** `POST /api/bulk-import/thuoc`

**Mô tả:** Nhập danh sách thuốc từ file Excel/CSV

**Content-Type:** `multipart/form-data`

**Parameters:**
- `file` (required): File CSV hoặc Excel

**Định dạng file:**
```
ten_thuoc,nhom_thuoc_id,hoat_chat,ham_luong,dang_bao_che,hang_san_xuat,nuoc_san_xuat,so_dang_ky,gia_tham_khao,don_vi_tinh,mo_ta
Amoxicillin 500mg,1,Amoxicillin,500mg,Viên nén,Công ty A,Việt Nam,123456,5000,Hộp,Kháng sinh
Paracetamol 500mg,2,Paracetamol,500mg,Viên nén,Công ty B,Việt Nam,123457,3000,Hộp,Giảm đau hạ sốt
```

**Cột yêu cầu:**
- `ten_thuoc` (hoặc `tên_thuốc`): Tên thuốc **[BẮT BUỘC]**
- `nhom_thuoc_id` (hoặc `nhóm_thuốc_id` hoặc `nhom_thuoc`): ID hoặc tên nhóm thuốc **[BẮT BUỘC]**

**Cột tùy chọn:**
- `hoat_chat` (hoặc `hoạt_chất`): Hoạt chất chính
- `ham_luong` (hoặc `hàm_lượng`): Hàm lượng (ví dụ: 500mg, 250mg/5ml)
- `dang_bao_che` (hoặc `dạng_bào_chế`): Dạng bào chế (ví dụ: viên nén, siro, thuốc bôi)
- `hang_san_xuat` (hoặc `hãng_sản_xuất`): Hãng sản xuất
- `nuoc_san_xuat` (hoặc `nước_sản_xuất`): Nước sản xuất
- `so_dang_ky` (hoặc `số_đăng_ký`): Số đăng ký lưu hành
- `gia_tham_khao` (hoặc `giá_tham_khảo`): Giá tham khảo (VNĐ)
- `don_vi_tinh` (hoặc `đơn_vị_tính`): Đơn vị tính (ví dụ: hộp, lọ, tuýp)
- `mo_ta` (hoặc `mô_tả`): Mô tả chi tiết

**Response (200):**
```json
{
  "message": "Import thành công",
  "imported": 10,
  "skipped": 2,
  "errors": [
    {
      "row": 5,
      "message": "Nhóm thuốc ID 99 không tồn tại"
    },
    {
      "row": 8,
      "message": "Hàng 8: Thiếu tên thuốc"
    }
  ]
}
```

---

### 3. Tải Template Nhóm Thuốc

**Endpoint:** `GET /api/bulk-import/template/nhom-thuoc`

**Mô tả:** Tải file template CSV để import nhóm thuốc

**Response:** File CSV với các cột mẫu

---

### 4. Tải Template Thuốc

**Endpoint:** `GET /api/bulk-import/template/thuoc`

**Mô tả:** Tải file template CSV để import thuốc

**Response:** File CSV với các cột mẫu

---

## Hướng dẫn sử dụng

### Bước 1: Chuẩn bị dữ liệu

**Tùy chọn A: Sử dụng template**
1. Tải file template từ API endpoint
2. Mở file trong Excel hoặc Text Editor
3. Điền dữ liệu theo từng hàng
4. Lưu file dưới định dạng CSV hoặc Excel

**Tùy chọn B: Tạo file từ đầu**
1. Tạo file CSV/Excel với headers tương ứng
2. Điền dữ liệu
3. Lưu file

### Bước 2: Import dữ liệu

**Sử dụng cURL:**
```bash
# Import nhóm thuốc
curl -X POST http://localhost:5000/api/bulk-import/nhom-thuoc \
  -F "file=@nhom_thuoc.csv"

# Import thuốc
curl -X POST http://localhost:5000/api/bulk-import/thuoc \
  -F "file=@thuoc.csv"
```

**Sử dụng Python:**
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

**Sử dụng JavaScript/Fetch:**
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
.then(data => console.log(data));
```

---

## Tính năng

✅ **Hỗ trợ nhiều định dạng:** CSV, Excel (.xlsx, .xls)

✅ **Validation dữ liệu:** Kiểm tra trường bắt buộc, kiểu dữ liệu

✅ **Bulk insert:** Nhập hàng loạt với performance tối ưu

✅ **Error reporting:** Chi tiết lỗi từng hàng

✅ **Rollback on error:** Nếu lỗi, toàn bộ transaction được rollback

✅ **Vietnamese support:** Hỗ trợ tên cột tiếng Việt

✅ **Flexible field mapping:** Hỗ trợ cả tên cột tiếng Anh và Việt

✅ **Template download:** Tải file template sẵn sàng

---

## Ví dụ đầy đủ

### Import Nhóm Thuốc

**File: nhom_thuoc.csv**
```csv
ten_nhom,mo_ta
Kháng sinh,Dùng để điều trị nhiễm khuẩn
Giảm đau hạ sốt,Làm giảm đau và hạ sốt
Vitamin,Bổ sung vi chất dinh dưỡng
Mỡ ngoài da,Điều trị các bệnh ngoài da
```

**Request:**
```bash
curl -X POST http://localhost:5000/api/bulk-import/nhom-thuoc \
  -F "file=@nhom_thuoc.csv"
```

**Response:**
```json
{
  "message": "Import thành công",
  "imported": 4,
  "skipped": 0,
  "errors": []
}
```

---

### Import Thuốc

**File: thuoc.csv**
```csv
ten_thuoc,nhom_thuoc_id,hoat_chat,ham_luong,dang_bao_che,hang_san_xuat,nuoc_san_xuat,so_dang_ky,gia_tham_khao,don_vi_tinh,mo_ta
Amoxicillin 500mg,1,Amoxicillin,500mg,Viên nén,Dược phẩm A,Việt Nam,ĐK001,5000,Hộp,Kháng sinh phổ rộng
Paracetamol 500mg,2,Paracetamol,500mg,Viên nén,Dược phẩm B,Việt Nam,ĐK002,3000,Hộp,Giảm đau hạ sốt
```

**Request:**
```bash
curl -X POST http://localhost:5000/api/bulk-import/thuoc \
  -F "file=@thuoc.csv"
```

**Response:**
```json
{
  "message": "Import thành công",
  "imported": 2,
  "skipped": 0,
  "errors": []
}
```

---

## Lưu ý quan trọng

⚠️ **Yêu cầu nhóm thuốc tồn tại:** Trước khi import thuốc, phải nhập nhóm thuốc tương ứng hoặc đảm bảo nhóm đã tồn tại

⚠️ **Nhóm trùng lặp:** Không thể import nhóm thuốc với tên đã tồn tại

⚠️ **Kích thước file:** Giới hạn 50MB

⚠️ **Encoding:** File CSV phải sử dụng encoding UTF-8

⚠️ **Tên cột:** Headers phải chính xác (không phân biệt hoa thường nhưng phải đủ tên cột)

---

## Troubleshooting

**Lỗi: "Định dạng file không hợp lệ"**
- Kiểm tra phần mở rộng file (.csv, .xlsx, .xls)
- Đảm bảo file không bị hỏng

**Lỗi: "File CSV trống hoặc không hợp lệ"**
- Kiểm tra file có dữ liệu
- Kiểm tra headers có chính xác

**Lỗi: "Nhóm thuốc không tồn tại"**
- Kiểm tra giá trị nhom_thuoc_id có đúng
- Đảm bảo nhóm thuốc đã được tạo trước

**Lỗi: "Thiếu tên thuốc"**
- Kiểm tra cột ten_thuoc có giá trị
- Kiểm tra không có khoảng trắng trước/sau

---

## Constraints

| Parameter | Limit | Note |
|-----------|-------|------|
| File size | 50 MB | Giới hạn kích thước file upload |
| Rows per file | Unlimited | Phụ thuộc vào memory server |
| Batch insert | All at once | Tất cả dữ liệu được insert trong 1 transaction |
| Field length | Database limits | Xem schema trong models.py |

---

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Thông báo kết quả |
| `imported` | integer | Số dòng được import thành công |
| `skipped` | integer | Số dòng bị bỏ qua |
| `errors` | array | Chi tiết lỗi của các dòng |
| `error` | string | Thông báo lỗi (nếu có) |

---

## Support

Nếu gặp vấn đề, vui lòng kiểm tra:
1. Log của server Flask
2. Cấu trúc file CSV/Excel
3. Dữ liệu nhóm thuốc đã tồn tại

Để báo cáo lỗi, cung cấp:
- File import (hoặc sample)
- Thông báo lỗi từ API
- Log server
