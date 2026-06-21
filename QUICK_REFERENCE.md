# Bulk Import API - Quick Reference

## 📦 Files Created/Modified

### New Files:
1. **backend/route_bulk_import.py** - Main API implementation
2. **docs/BULK_IMPORT_API.md** - Detailed API documentation
3. **BULK_IMPORT_README.md** - Feature overview and guide
4. **test_bulk_import.py** - Test script
5. **data/sample_nhom_thuoc.csv** - Sample drug group data
6. **data/sample_thuoc.csv** - Sample drug data

### Modified Files:
1. **backend/app.py** - Added blueprint registration
2. **requirements.txt** - Added dependencies (flask-sqlalchemy, openpyxl)

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Server
```bash
cd backend
python app.py
```

### 3. Upload Data

**Import Drug Groups:**
```bash
curl -X POST http://localhost:5000/api/bulk-import/nhom-thuoc \
  -F "file=@data/sample_nhom_thuoc.csv"
```

**Import Drugs:**
```bash
curl -X POST http://localhost:5000/api/bulk-import/thuoc \
  -F "file=@data/sample_thuoc.csv"
```

---

## 📋 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/bulk-import/nhom-thuoc` | Import drug groups |
| POST | `/api/bulk-import/thuoc` | Import drugs |
| GET | `/api/bulk-import/template/nhom-thuoc` | Download group template |
| GET | `/api/bulk-import/template/thuoc` | Download drug template |

---

## 📊 CSV Format

### Drug Groups (nhom_thuoc.csv)
```csv
ten_nhom,mo_ta
Kháng sinh,Dùng để điều trị nhiễm khuẩn
Giảm đau hạ sốt,Làm giảm đau và hạ sốt
```

### Drugs (thuoc.csv)
```csv
ten_thuoc,nhom_thuoc_id,hoat_chat,ham_luong,dang_bao_che,hang_san_xuat,nuoc_san_xuat,so_dang_ky,gia_tham_khao,don_vi_tinh,mo_ta
Amoxicillin 500mg,1,Amoxicillin,500mg,Viên nén,Công ty A,Việt Nam,123456,5000,Hộp,Kháng sinh
```

---

## ✨ Features

✅ Support for CSV and Excel formats  
✅ Automatic data validation  
✅ Bulk insert with transaction safety  
✅ Detailed error reporting per row  
✅ Vietnamese language support  
✅ Flexible column name mapping  
✅ Template download  
✅ File size limit: 50MB  
✅ Rollback on error  

---

## 🔍 Response Format

**Success (200):**
```json
{
  "message": "Import thành công",
  "imported": 10,
  "skipped": 2,
  "errors": []
}
```

**Partial Success with Errors:**
```json
{
  "message": "Import thành công",
  "imported": 8,
  "skipped": 2,
  "errors": [
    {
      "row": 3,
      "message": "Nhóm thuốc 'Kháng sinh' đã tồn tại"
    }
  ]
}
```

---

## 📝 Usage Examples

### Python
```python
import requests

# Upload drug groups
with open('nhom_thuoc.csv', 'rb') as f:
    resp = requests.post(
        'http://localhost:5000/api/bulk-import/nhom-thuoc',
        files={'file': f}
    )
    print(resp.json())

# Upload drugs
with open('thuoc.csv', 'rb') as f:
    resp = requests.post(
        'http://localhost:5000/api/bulk-import/thuoc',
        files={'file': f}
    )
    print(resp.json())
```

### JavaScript/Fetch
```javascript
const file = document.getElementById('fileInput').files[0];
const formData = new FormData();
formData.append('file', file);

fetch('http://localhost:5000/api/bulk-import/thuoc', {
  method: 'POST',
  body: formData
})
.then(r => r.json())
.then(data => console.log(data));
```

### cURL
```bash
# Download template
curl http://localhost:5000/api/bulk-import/template/thuoc \
  -o thuoc_template.csv

# Upload file
curl -X POST http://localhost:5000/api/bulk-import/thuoc \
  -F "file=@thuoc.csv"
```

---

## ⚠️ Important Notes

1. **Import order matters:** Always import drug groups first, then drugs
2. **No duplicate groups:** Cannot import group with existing name
3. **UTF-8 encoding:** CSV files must use UTF-8 encoding
4. **Group references:** Drug nhom_thuoc_id must reference existing group
5. **File size:** Maximum 50MB per file
6. **Column names:** Must match exactly (case-insensitive)

---

## 🧪 Testing

Run the test script:
```bash
python test_bulk_import.py
```

This will:
- Download templates
- Test group import
- Test drug import
- Print detailed results

---

## 📖 Documentation

- **Full API docs:** See `docs/BULK_IMPORT_API.md`
- **Feature guide:** See `BULK_IMPORT_README.md`
- **Sample data:** See `data/sample_*.csv`

---

## 🛠️ Architecture

```
Request
   ↓
route_bulk_import.py
   ├─ read_csv_file() / read_excel_file()
   ├─ validate_*_row()
   ├─ Create ORM objects
   ├─ db.session.add()
   └─ db.session.commit()
   ↓
Database (SQLite)
```

---

## 📌 Key Implementation Details

### File Reading
- **CSV:** Python csv.DictReader with UTF-8-sig encoding
- **Excel:** pandas with openpyxl backend

### Validation
- Required fields checked
- Data types validated
- Foreign keys verified (nhom_thuoc_id)
- Duplicate groups prevented

### Error Handling
- Row-level error capture
- Transaction rollback on failure
- Detailed error messages per row
- Graceful partial failure handling

### Performance
- Batch insert in single transaction
- Memory-efficient file streaming
- Supports files with thousands of rows

---

## 🤝 Integration

### With Frontend
POST form with file input:
```html
<form id="importForm">
  <input type="file" name="file" accept=".csv,.xlsx,.xls" required>
  <button type="submit">Import</button>
</form>
<script>
document.getElementById('importForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData(this);
  const resp = await fetch('/api/bulk-import/thuoc', {
    method: 'POST',
    body: formData
  });
  const result = await resp.json();
  console.log(result);
});
</script>
```

### With Database
Data is inserted directly into:
- `nhom_thuoc` table for drug groups
- `thuoc` table for drugs
- Relationships maintained via foreign keys

---

## 📞 Support

For issues or questions:
1. Check error message row numbers
2. Verify CSV format matches template
3. Ensure groups exist before importing drugs
4. Check file encoding is UTF-8
5. Review detailed logs in response

---

## Version Info

- **Created:** 2026-06-19
- **API Version:** 1.0
- **Python:** 3.8+
- **Flask:** 4.0+
- **Database:** SQLite (compatible with other SQL databases)

---

Generated on: 2026-06-19
