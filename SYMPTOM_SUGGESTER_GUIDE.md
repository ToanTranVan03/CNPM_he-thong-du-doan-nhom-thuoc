# 🎯 Hướng dẫn Chức năng Gợi ý và Chọn nhanh Triệu chứng

## 📋 Mục đích
Chức năng này giúp người dùng (bác sĩ, nhân viên y tế) bổ sung thông tin triệu chứng một cách nhanh chóng và thuận tiện thông qua giao diện "chip/tag" hiện đại. Thay vì phải gõ tất cả các triệu chứng bằng tay, người dùng có thể:

- Xem danh sách các triệu chứng phổ biến (top 30)
- Tìm kiếm triệu chứng theo từ khóa Tiếng Việt hoặc Tiếng Anh
- Chọn/bỏ chọn triệu chứng bằng một cú nhấp chuột
- Tự động cập nhật danh sách triệu chứng vào nội dung bệnh án
- Giới hạn số lượng chọn tối đa (max 15 triệu chứng)

## 🚀 Tính năng chính

### 1. **Danh sách Triệu chứng Phổ biến**
- Khi mở trang tạo bệnh án, hệ thống tự động tải 30 triệu chứng phổ biến nhất
- Các triệu chứng được hiển thị dưới dạng chip/tag
- Có thể click trực tiếp để chọn/bỏ chọn

### 2. **Tìm kiếm Động (Real-time Search)**
- Nhập từ khóa vào ô tìm kiếm
- Hệ thống sẽ tìm kiếm động dựa trên:
  - Tên tiếng Việt của triệu chứng
  - Tên tiếng Anh (Symptom name)
  - Từ khóa đồng nghĩa (synonyms)
- Kết quả được sắp xếp ưu tiên: khớp chính xác → khớp bắt đầu → khớp chứa

### 3. **Trạng thái Giao diện (UI States)**
- **Loading**: Đang tải danh sách triệu chứng từ máy chủ
- **Empty**: Không tìm thấy triệu chứng nào phù hợp với từ khóa
- **Error**: Lỗi khi tải dữ liệu từ API (hiển thị thông báo lỗi)
- **Loaded**: Danh sách triệu chứng đã sẵn sàng

### 4. **Giới hạn Selection**
- Tối đa **15 triệu chứng** có thể chọn
- Khi đạt giới hạn, các chip chưa được chọn sẽ bị vô hiệu (disabled)
- Có thể bỏ chọn bất kỳ triệu chứng nào để chọn thêm

### 5. **Dark Mode Support**
- Toàn bộ component tương thích với Dark Mode của hệ thống
- Các màu sắc tự động điều chỉnh theo theme

### 6. **Responsive Design**
- Desktop (1920x1080): Chip hiển thị kích thước đầy đủ
- Tablet (768x1024): Chip nhỏ hơn, spacing giảm
- Mobile (375x667): Chip cực nhỏ, tối ưu cho cảm ứng

## 📊 Cấu trúc API

### Endpoint 1: Lấy Triệu chứng Phổ biến
```
GET /api/symptoms/common?limit=30
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "fever",
      "label_vi": "Sốt",
      "label_en": "Fever"
    },
    ...
  ],
  "total": 30
}
```

### Endpoint 2: Tìm kiếm Triệu chứng
```
GET /api/symptoms/search?q=sốt&limit=30
```

**Response:**
```json
{
  "success": true,
  "query": "sốt",
  "data": [
    {
      "id": "fever",
      "label_vi": "Sốt",
      "label_en": "Fever"
    },
    {
      "id": "high_fever",
      "label_vi": "Sốt cao",
      "label_en": "High Fever"
    }
  ],
  "total": 2
}
```

## 🎨 CSS Classes

### Container
- `.symptom-picker` - Container chính
- `.symptom-list-container` - Container danh sách
- `.symptom-state` - Container cho các state khác nhau
- `.symptom-chips` - Wrapper cho các chip

### Chip States
- `.symptom-chip` - Chip bình thường
- `.symptom-chip:hover` - Chip khi hover chuột
- `.symptom-chip:focus` - Chip khi focus (keyboard navigation)
- `.symptom-chip.selected` - Chip đã được chọn (có dấu ✓)
- `.symptom-chip.disabled` - Chip bị vô hiệu (khi đạt limit)

### States
- `.loading-state` - Trạng thái đang tải
- `.empty-state` - Trạng thái không có kết quả
- `.error-state` - Trạng thái lỗi
- `.selected-badge` - Badge hiển thị số lượng đã chọn

## 🔧 JavaScript Functions

### Main Functions
- `loadSymptoms()` - Tải danh sách triệu chứng phổ biến từ API
- `renderSymptoms(filter)` - Render danh sách triệu chứng với filter tìm kiếm
- `renderSymptomChips(symptomsData)` - Tạo các chip UI từ dữ liệu
- `updateSelectedCount()` - Cập nhật số lượng triệu chứng đã chọn

### Helper Functions
- `showSymptomState(state, errorMessage)` - Hiển thị các state khác nhau
- `canSelectMore()` - Kiểm tra có thể chọn thêm không (< 15)
- `getSelectedSymptomLabels()` - Lấy danh sách tên triệu chứng đã chọn

### Constants
- `MAX_SELECTED_SYMPTOMS = 15` - Số lượng tối đa
- `SYMPTOM_SEARCH_DELAY = 300` - Debounce delay (ms)

## 📝 Hướng dẫn sử dụng

### Bước 1: Đăng nhập
1. Mở ứng dụng trên trình duyệt
2. Đăng nhập bằng email và mật khẩu

### Bước 2: Mở trang tạo bệnh án
1. Nhấp vào "Mô tả ca lâm sàng" trên trang chủ
2. Hệ thống tự động tải danh sách triệu chứng phổ biến

### Bước 3: Chọn triệu chứng
**Cách 1 - Chọn từ danh sách phổ biến:**
1. Tìm triệu chứng cần thiết trong danh sách
2. Nhấp vào chip triệu chứng
3. Chip sẽ chuyển sang trạng thái "selected" (nền xanh, có dấu ✓)

**Cách 2 - Tìm kiếm:**
1. Nhập từ khóa vào ô "Tìm triệu chứng..."
   - Ví dụ: "sốt", "fever", "ho", "cough"
2. Hệ thống sẽ lọc kết quả theo từ khóa
3. Nhấp vào chip kết quả để chọn

### Bước 4: Xem triệu chứng đã chọn
- Số lượng triệu chứng đã chọn hiển thị trên badge "X đã chọn"
- Tất cả các chip đã chọn sẽ có nền xanh với dấu ✓

### Bước 5: Bỏ chọn triệu chứng
1. Nhấp lại vào chip đã chọn
2. Chip sẽ quay về trạng thái bình thường (không chọn)

### Bước 6: Gửi dự đoán
1. Nhấp nút "Gợi ý nhóm thuốc"
2. Hệ thống sẽ phân tích triệu chứng đã chọn + mô tả ca lâm sàng
3. Hiển thị kết quả dự đoán nhóm thuốc

## ⚠️ Lưu ý quan trọng

### Giới hạn Selection
- **Tối đa 15 triệu chứng** có thể chọn cùng lúc
- Nếu đạt giới hạn, các chip chưa chọn sẽ bị vô hiệu (disabled)
- Bỏ chọn một triệu chứng để có thể chọn thêm

### Xử lý Lỗi
- **Lỗi tải dữ liệu**: Kiểm tra kết nối internet, thử tải lại trang
- **Tìm kiếm không có kết quả**: Thử từ khóa khác, kiểm tra chính tả

### Dark Mode
- Giao diện tự động thích ứng với Dark Mode
- Nhấp vào icon "🌙" ở góc trên phải để bật/tắt Dark Mode

## 🔍 Các ví dụ Tìm kiếm

| Từ khóa | Kết quả |
|---------|---------|
| sốt | Sốt, Sốt cao, Sốt nhẹ |
| fever | Fever, High Fever, Mild Fever |
| ho | Ho, Ho có đờm, Ho khan |
| cough | Cough, Coughing Up Sputum |
| đau | Đau đầu, Đau lưng, Đau cơ |
| headache | Headache |

## 📱 Hỗ trợ Đa thiết bị

### Desktop
- Chip kích thước 14px, padding 8-12px
- Khoảng cách giữa chip: 8px
- Transition mượt mà khi hover

### Tablet
- Chip kích thước 13px, padding 8px
- Khoảng cách giữa chip: 4px
- Tối ưu cho cảm ứng

### Mobile
- Chip kích thước 13px, padding 8px
- Khoảng cách giữa chip: 4px
- Full-width layout
- Dễ dàng tap bằng ngón tay

## 🐛 Troubleshooting

### Vấn đề: Danh sách triệu chứng không tải
**Giải pháp:**
1. Kiểm tra kết nối internet
2. Thử tải lại trang (F5)
3. Kiểm tra console (F12) xem có lỗi gì không

### Vấn đề: Chip không phản ứng khi click
**Giải pháp:**
1. Kiểm tra browser hỗ trợ JavaScript không
2. Bật JavaScript nếu đã vô hiệu
3. Xóa cache browser và tải lại

### Vấn đề: Tìm kiếm quá chậm
**Giải pháp:**
1. Bình thường: có debounce 300ms, nên không quá chậm
2. Kiểm tra kết nối internet
3. Thử nhập từ khóa ngắn hơn

## 📚 Tài liệu liên quan
- Backend API: `/backend/app.py` (dòng 4442+)
- Frontend HTML: `/frontend/index.html` (dòng 216-251)
- Frontend CSS: `/frontend/styles.css` (dòng 3115+)
- Frontend JS: `/frontend/script.js` (dòng 310+)

## ✅ Danh sách Kiểm tra (Checklist)

- [x] API `/api/symptoms/common` hoạt động
- [x] API `/api/symptoms/search` hoạt động
- [x] HTML structure với các state (Loading, Empty, Error, Loaded)
- [x] CSS styling cho chip và các state
- [x] JavaScript functions để tải và render symptoms
- [x] Debounce cho search input (300ms)
- [x] Giới hạn selection (max 15)
- [x] Dark Mode support
- [x] Responsive design (Desktop, Tablet, Mobile)
- [x] Error handling

---

**Version:** 1.0.0  
**Date:** 2026-06-21  
**Last Updated:** 2026-06-21 18:25
