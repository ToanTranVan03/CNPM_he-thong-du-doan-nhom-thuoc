# 🎯 Hướng dẫn Chi tiết: Tính năng Autocomplete Triệu chứng

## 📋 Mục đích
Tính năng **Autocomplete** hỗ trợ người dùng (bác sĩ, nhân viên y tế) nhập triệu chứng **nhanh hơn và chính xác hơn** thông qua:
- ⚡ **Tìm kiếm động (Real-time Search)** - Gợi ý triệu chứng khi đang nhập
- 🔍 **Fuzzy Match** - Tìm kiếm gần đúng, không phân biệt chữ hoa/thường
- 📱 **Responsive Design** - Hoạt động trên Desktop, Tablet, Mobile
- ♿ **Accessibility** - Hỗ trợ keyboard navigation, screen reader
- 🌙 **Dark Mode** - Tự động thích ứng với theme hệ thống
- 💾 **Recently Used** - Ghi nhớ triệu chứng vừa dùng
- ✅ **Tránh trùng lặp** - Không thêm triệu chứng trùng vào textarea

## 🚀 Tính năng chính

### 1. **Autocomplete Dropdown**
- Hiển thị dropdown dưới input search khi người dùng nhập từ khóa
- Hiện thị kết quả gợi ý dựa trên độ phù hợp (relevance score)
- Áp dụng animation smooth khi render items

### 2. **Tìm kiếm Động (Real-time Search)**
- **Min query length**: 1 ký tự
- **Debounce delay**: 300ms (tối ưu hóa performance)
- **Max results**: 15 triệu chứng
- **Fuzzy threshold**: 0.6 (60%)

Ví dụ:
```
Query: "đau"     → Kết quả: "Đau đầu", "Đau bụng", "Đau lưng", "Đau cơ", ...
Query: "sot"     → Kết quả: "Sốt", "Sốt cao", "Sốt nhẹ", ...
Query: "cough"   → Kết quả: "Ho", "Ho có đờm", "Ho khan", ...
Query: "fever"   → Kết quả: "Sốt", "Sốt cao", "Sốt nhẹ", ...
```

### 3. **Tự động Thêm vào Textarea**
Khi người dùng chọn triệu chứng từ autocomplete:
- ✅ Tự động thêm vào textarea `case-description`
- ✅ Phân cách bằng dấu phẩy (`,`)
- ✅ Tránh trùng lặp (kiểm tra trước khi thêm)
- ✅ Cập nhật character count

Ví dụ:
```
Textarea trước: "Bệnh nhân sốt cao"
Người dùng chọn "Ho có đờm"
Textarea sau: "Bệnh nhân sốt cao, Ho có đờm"
```

### 4. **Recently Used Symptoms**
- Ghi nhớ triệu chứng vừa chọn (chuỗi 10 cái gần nhất)
- Lưu vào localStorage
- Dùng cho feature future (suggestions based on history)

### 5. **Trạng thái Giao diện (UI States)**
- **Loading** ⏳ - Đang tải kết quả từ API
- **Empty** 🔍 - Không tìm thấy triệu chứng phù hợp
- **Error** ⚠️ - Lỗi khi gọi API (hiển thị thông báo lỗi)
- **List** ✅ - Danh sách triệu chứng gợi ý

### 6. **Keyboard Navigation**
- ⬇️ **ArrowDown** - Di chuyển xuống item tiếp theo
- ⬆️ **ArrowUp** - Di chuyển lên item trước đó
- ⏎ **Enter** - Chọn item được focus
- 🚫 **Escape** - Đóng dropdown

### 7. **Accessibility (A11y)**
- ♿ **ARIA roles** - `listbox`, `option`, `region`, `status`, `alert`
- 🔊 **aria-label** - Mô tả chi tiết cho screen reader
- ✅ **aria-expanded** - Cho biết dropdown mở/đóng
- 📢 **aria-live** - Thông báo loading/error states

### 8. **Dark Mode Support**
- Tự động áp dụng theme tối (dark) hoặc sáng (light)
- Bảng màu tự điều chỉnh:
  - Light mode: Nền sáng, text tối
  - Dark mode: Nền tối, text sáng

### 9. **Responsive Design**
#### Desktop (1920px+)
- Dropdown max-height: 400px
- Item padding: 12px
- Font size: 14px

#### Tablet (768px - 1023px)
- Dropdown max-height: 300px
- Item padding: 8px
- Font size: 13px

#### Mobile (480px - 767px)
- Dropdown max-height: 250px
- Item padding: 8px
- Item min-height: 44px (easy to tap)
- Font size: 12px

#### Very Small Mobile (<480px)
- Position: absolute, full-width
- Item min-height: 44px
- Tối ưu cho cảm ứng

## 📊 API Endpoints

### 1. Autocomplete Endpoint
```
GET /api/symptoms/autocomplete?q=keyword&limit=15&threshold=0.6
```

**Query Parameters:**
- `q` (string): Từ khóa tìm kiếm (bắt buộc)
- `limit` (int): Số lượng kết quả (default: 15, min: 1, max: 50)
- `threshold` (float): Ngưỡng fuzzy match (default: 0.6, range: 0.0-1.0)

**Response:**
```json
{
  "success": true,
  "query": "đau",
  "data": [
    {
      "id": "headache",
      "label_vi": "Đau đầu",
      "label_en": "Headache",
      "score": 1.0
    },
    {
      "id": "stomach_pain",
      "label_vi": "Đau bụng",
      "label_en": "Stomach Pain",
      "score": 0.95
    }
  ],
  "total": 2
}
```

### 2. Common Symptoms Endpoint (Danh sách phổ biến)
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

## 🎨 Component Structure

### HTML
```html
<!-- Search Input -->
<input 
  id="symptom-search" 
  type="search" 
  placeholder="Tìm triệu chứng..."
  aria-expanded="false"
  aria-controls="autocomplete-dropdown"
  aria-label="Tìm kiếm triệu chứng"
/>

<!-- Autocomplete Dropdown -->
<div id="autocomplete-dropdown" role="region">
  <!-- Loading State -->
  <div id="autocomplete-loading-state" role="status" aria-live="polite">...</div>
  
  <!-- Empty State -->
  <div id="autocomplete-empty-state" role="status" aria-live="polite">...</div>
  
  <!-- Error State -->
  <div id="autocomplete-error-state" role="alert" aria-live="assertive">...</div>
  
  <!-- Suggestions List -->
  <ul id="autocomplete-list" role="listbox">
    <!-- Items generated dynamically -->
  </ul>
</div>
```

### CSS Classes
- `.autocomplete-dropdown` - Container
- `.autocomplete-list` - List container
- `.autocomplete-item` - Individual item
- `.autocomplete-item-label` - Label text
- `.autocomplete-item-en` - English translation
- `.autocomplete-item-score` - Relevance score
- `.autocomplete-state` - State indicator (loading/empty/error)
- `.visible` - Show element

### JavaScript Variables
```javascript
const selectedSymptoms = new Set();           // Track selected symptom IDs
const selectedSymptomLabels = new Map();      // Track symptom labels
const recentlyUsedSymptoms = [];              // Track recently used symptoms

const AUTOCOMPLETE_CONFIG = {
  DEBOUNCE_DELAY: 300,      // Delay before API call
  MIN_QUERY_LENGTH: 1,      // Min characters to trigger search
  MAX_RESULTS: 15,          // Max items in dropdown
  THRESHOLD: 0.6            // Fuzzy match threshold
};
```

## 🔧 Key Functions

### Frontend JavaScript

**1. `fetchAutocomplete(query)`**
- Fetch suggestions từ API dựa trên query
- Handle loading, empty, error states
- Return array of results

**2. `renderAutocompleteList(items)`**
- Render dropdown list từ items
- Add event listeners cho click/keyboard
- Build accessible labels (aria-label)

**3. `handleAutocompleteItemSelect(item)`**
- Toggle selection state (select/deselect)
- Add to selectedSymptoms Set
- Append to textarea (tránh trùng lặp)
- Add to recently used
- Re-fetch autocomplete to update visual

**4. `appendSymptomToTextarea(symptomLabel)`**
- Kiểm tra triệu chứng đã tồn tại (regex word boundary)
- Thêm vào textarea nếu chưa tồn tại
- Cập nhật character count
- Dispatch input event

**5. `setupAutocompleteKeyboardNavigation()`**
- Setup arrow keys (up/down)
- Setup Enter (select item)
- Setup Escape (close dropdown)
- Track current focus index

**6. `showAutocompleteState(state, errorMessage)`**
- Show/hide states (loading/empty/error/list)
- Update aria-expanded attribute
- Clear previous states

**7. `hideAutocompleteDropdown()`**
- Hide all autocomplete elements
- Reset aria-expanded attribute

### Backend Python

**1. `/api/symptoms/autocomplete` (GET)**
```python
def autocomplete_symptoms():
    """
    - Lấy query string parameter 'q'
    - Validate input (limit 1-50, threshold 0.0-1.0)
    - Nếu không có query: trả về danh sách phổ biến
    - Nếu có query: fuzzy search trong readable_symptoms + database
    - Sắp xếp theo score (descending)
    - Trả về JSON response
    """
```

**2. Fuzzy Match Algorithm**
```python
def fuzzy_match(query, target, threshold=0.6):
    """
    - Normalize text (remove accents, lowercase, remove spaces)
    - Use SequenceMatcher để tính similarity ratio
    - Return ratio nếu >= threshold, else 0.0
    """
```

## 📝 Hướng dẫn sử dụng

### Bước 1: Mở trang tạo bệnh án
1. Đăng nhập vào hệ thống
2. Nhấp vào "Mô tả ca lâm sàng" trên trang chủ

### Bước 2: Chọn triệu chứng từ Autocomplete
1. Nhập vào ô "Tìm triệu chứng..." (min 1 ký tự)
2. Chờ dropdown hiển thị gợi ý (300ms debounce)
3. Nhấp vào triệu chứng cần thiết
4. Triệu chứng tự động thêm vào textarea
5. Tiếp tục nhập để chọn thêm

### Bước 3: Keyboard Navigation
1. Nhập từ khóa vào input
2. Nhấp ArrowDown để chọn item đầu tiên
3. Nhấp ArrowUp/ArrowDown để di chuyển
4. Nhấp Enter để chọn
5. Nhấp Escape để đóng dropdown

### Bước 4: Xem triệu chứng đã chọn
- Badge "X đã chọn" hiển thị số lượng
- Triệu chứng hiển thị trong textarea
- Max 15 triệu chứng

### Bước 5: Gửi dự đoán
1. Nhấp nút "Gợi ý nhóm thuốc"
2. API sẽ gửi cả `selectedSymptoms` (IDs) và `textarea value` (text)
3. Hiển thị kết quả dự đoán

## ⚡ Performance Optimizations

### 1. **Debounce (300ms)**
```javascript
// Tránh gọi API quá nhiều khi người dùng đang gõ
symptomSearchTimeout = setTimeout(() => {
  fetchAutocomplete(query);
}, AUTOCOMPLETE_CONFIG.DEBOUNCE_DELAY);
```

### 2. **Fuzzy Matching (Backend)**
- Server-side fuzzy match (Levenshtein-like)
- Tránh transfer dữ liệu không cần thiết
- Cache readable_symptoms in memory

### 3. **Lazy Loading**
- Recently used symptoms load from localStorage
- Common symptoms load on page load
- Autocomplete items render on demand

### 4. **Efficient DOM Updates**
- Clear innerHTML once per render
- Use classList for fast style changes
- Avoid reflows (batch DOM operations)

## 🐛 Error Handling

### Loading State
- Hiển thị spinner nhỏ
- aria-live="polite" để screen reader đọc

### Empty State
- "Không tìm thấy triệu chứng phù hợp"
- Gợi ý người dùng thử từ khóa khác
- Icon search_off

### Error State
- Hiển thị thông báo lỗi chi tiết
- aria-live="assertive" để screen reader thông báo ngay
- Button retry (future feature)

### Network Errors
- Try-catch wrapping API calls
- Fallback to empty state
- Console error logging

## 🔒 Security

### Input Sanitization
- Escape HTML để tránh XSS
- Trim whitespace
- Remove special characters từ search query (nếu cần)

### SQL Injection Prevention
- Use SQLAlchemy ORM (parameterized queries)
- Input validation (limit, threshold ranges)

## 📱 Testing Checklist

### Desktop (1920x1080)
- [ ] Autocomplete dropdown hiển thị đúng
- [ ] Arrow keys hoạt động
- [ ] Enter để chọn item
- [ ] Escape để đóng dropdown
- [ ] Triệu chứng thêm vào textarea
- [ ] Không trùng lặp
- [ ] Dark mode hoạt động
- [ ] Character count cập nhật

### Tablet (768x1024)
- [ ] Dropdown responsive (max-height 300px)
- [ ] Item padding tối ưu (8px)
- [ ] Font size 13px dễ đọc
- [ ] Touch interaction hoạt động
- [ ] Không scroll ngang

### Mobile (375x667)
- [ ] Dropdown full-width
- [ ] Item min-height 44px (dễ tap)
- [ ] Font size 12px đủ nhỏ nhưng vẫn đọc được
- [ ] Scroll dropdown không scroll page
- [ ] Không overflow

### Accessibility
- [ ] Screen reader đọc ARIA labels
- [ ] Keyboard navigation đầy đủ
- [ ] Contrast ratio ≥ 4.5:1
- [ ] Focus visible rõ ràng
- [ ] aria-expanded tự cập nhật

### Error Scenarios
- [ ] API offline → Error state
- [ ] Query = "" → Không call API
- [ ] Query = "xyz" (không tồn tại) → Empty state
- [ ] Max 15 triệu chứng → Chỉ hiển thị top 15

## 📚 Tài liệu liên quan
- [Symptom Suggester Guide](./SYMPTOM_SUGGESTER_GUIDE.md)
- [Backend API Documentation](./backend/app.py) (dòng 4476+)
- [Frontend Code](./frontend/script.js) (dòng 329+)
- [Frontend Styles](./frontend/styles.css) (dòng 3305+)

## 🎓 Ví dụ Thực tế

### Ví dụ 1: Nhập "đau"
```
1. User gõ "đ" → API gọi fuzzy match → Dropdown hiển thị
2. User gõ "đa" → Debounce 300ms → API gọi lại
3. User gõ "đau" → Kết quả: "Đau đầu", "Đau bụng", "Đau lưng", ...
4. User click "Đau đầu" → Textarea: "Đau đầu"
5. User gõ "ho" → Kết quả: "Ho", "Ho có đờm", "Ho khan"
6. User click "Ho có đờm" → Textarea: "Đau đầu, Ho có đờm"
```

### Ví dụ 2: Keyboard Navigation
```
1. User gõ "fever" → Autocomplete hiển thị
2. User nhấp ArrowDown → Focus vào "Fever" (Sốt)
3. User nhấp ArrowDown → Focus vào "High Fever" (Sốt cao)
4. User nhấp Enter → "Sốt cao" được chọn, thêm vào textarea
5. User nhấp Escape → Dropdown đóng
6. User click vào textarea → Thấy "Sốt cao"
```

### Ví dụ 3: Tránh Trùng lặp
```
1. Textarea: "Sốt cao, Ho có đờm"
2. User gõ "sot" → Autocomplete hiển thị "Sốt cao" (đã có)
3. User click "Sốt cao" → Không thêm (regex match tìm thấy)
4. Textarea vẫn: "Sốt cao, Ho có đờm"
5. System log: "Triệu chứng 'Sốt cao' đã tồn tại"
```

## ❓ FAQ

**Q: Tại sao debounce 300ms?**
A: 300ms là sweet spot - nhanh đủ để responsive, chậm đủ để tránh quá nhiều API calls khi user gõ nhanh.

**Q: Fuzzy threshold 0.6 có nghĩa gì?**
A: Tìm kiếm sẽ chỉ hiển thị kết quả có độ tương đồng ≥60%. Cao hơn → kết quả chính xác hơn nhưng thiếu, thấp hơn → kết quả nhiều nhưng có noise.

**Q: Tại sao max 15 triệu chứng?**
A: UX: Quá nhiều chọn sẽ làm người dùng phối mất. 15 là balanced - đủ cho phần lớn use cases mà không quá phức tạp.

**Q: Recently used symptoms lưu ở đâu?**
A: localStorage của browser. Dữ liệu không được gửi lên server, chỉ lưu cục bộ.

**Q: Sao dropdown position absolute?**
A: Để nó overlay trên các element khác, không làm thay đổi layout. Có thể customize bằng CSS nếu cần.

## 🚀 Future Enhancements

- [ ] Recently used section tại đầu dropdown
- [ ] Pinned favorites symptoms
- [ ] Smart suggestions based on case history
- [ ] Multi-language support (Tiếng Anh, Tiếng Trung)
- [ ] Voice input (dictation)
- [ ] Synonym expansion
- [ ] Gesture support (swipe, pinch)
- [ ] Offline mode (cached results)

---

**Version:** 2.0.0  
**Date:** 2026-06-21  
**Last Updated:** 2026-06-21 20:00  
**Author:** Copilot AI Assistant
