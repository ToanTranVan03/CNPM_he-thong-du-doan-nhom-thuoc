# API Thống Kê Phản Hồi Đánh Giá Nhóm Thuốc

## Mục Tiêu
Xây dựng API thống kê số lượng đánh giá **Đồng ý (agree)** và **Không đồng ý (disagree)** từ người dùng về kết quả dự đoán nhóm thuốc. Dữ liệu này được sử dụng để hiển thị trên Dashboard, biểu đồ thống kê và báo cáo của hệ thống.

---

## 1. DATABASE MODEL (Backend)

### Feedback Table
```python
class Feedback(db.Model):
    """Phản hồi Đồng ý / Không đồng ý của người dùng về kết quả dự đoán nhóm thuốc."""
    __tablename__ = 'feedback'

    id                = db.Column(db.Integer, primary_key=True)
    prediction_id     = db.Column(db.Integer, nullable=True)   # ID của dự đoán
    user_id           = db.Column(db.Integer, nullable=True)   # ID của người dùng
    feedback_type     = db.Column(db.String(20), nullable=False)  # 'agree' hoặc 'disagree'
    comment           = db.Column(db.Text, nullable=True)      # Ghi chú bổ sung
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
```

**Giải thích các cột:**
- `id`: Khóa chính, ID duy nhất của mỗi phản hồi
- `prediction_id`: Tham chiếu đến ID của dự đoán mà người dùng đánh giá
- `user_id`: Tham chiếu đến ID của người dùng thực hiện đánh giá
- `feedback_type`: Loại phản hồi - chỉ nhận hai giá trị:
  - `"agree"` - Người dùng đồng ý với kết quả dự đoán
  - `"disagree"` - Người dùng không đồng ý với kết quả dự đoán
- `comment`: Ghi chú bổ sung từ người dùng (tuỳ chọn)
- `created_at`: Thời gian tạo bản ghi

---

## 2. API ENDPOINTS

### 2.1 Gửi Phản Hồi

**Endpoint:**
```
POST /api/feedback
```

**Mô Tả:**
Ghi lại phản hồi Đồng ý/Không đồng ý từ người dùng.

**Request Body:**
```json
{
  "prediction_id": 123,
  "user_id": 45,
  "feedback_type": "agree",
  "comment": "Kết quả chính xác, triệu chứng khớp với chẩn đoán"
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prediction_id` | Integer | No | ID của dự đoán được đánh giá |
| `user_id` | Integer | No | ID của người dùng |
| `feedback_type` | String | **Yes** | `"agree"` hoặc `"disagree"` |
| `comment` | String | No | Ghi chú bổ sung |

**Response (Success - 201):**
```json
{
  "success": true,
  "message": "Phản hồi đã được ghi nhận thành công.",
  "feedback": {
    "id": 1,
    "prediction_id": 123,
    "user_id": 45,
    "feedback_type": "agree",
    "comment": "Kết quả chính xác, triệu chứng khớp với chẩn đoán",
    "created_at": "2026-06-21T14:29:02.373"
  }
}
```

**Response (Error - 400):**
```json
{
  "success": false,
  "message": "feedback_type phải là \"agree\" hoặc \"disagree\"."
}
```

**Response (Error - 500):**
```json
{
  "success": false,
  "message": "Không thể ghi nhận phản hồi.",
  "error": "Chi tiết lỗi từ server"
}
```

---

### 2.2 Lấy Thống Kê Phản Hồi

**Endpoint:**
```
GET /api/feedback/statistics
```

**Mô Tả:**
Lấy thống kê số lượng phản hồi Đồng ý / Không đồng ý.

**Request:**
- Không cần body
- Không cần tham số query

**Response (Success - 200):**
```json
{
  "success": true,
  "total": 150,
  "agree_count": 120,
  "disagree_count": 30,
  "agree_percentage": 80.0,
  "disagree_percentage": 20.0
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `success` | Boolean | `true` nếu thành công |
| `total` | Integer | Tổng số lượt đánh giá |
| `agree_count` | Integer | Số lượng phản hồi "agree" |
| `disagree_count` | Integer | Số lượng phản hồi "disagree" |
| `agree_percentage` | Float | Tỷ lệ phần trăm "agree" (làm tròn 2 chữ số thập phân) |
| `disagree_percentage` | Float | Tỷ lệ phần trăm "disagree" (làm tròn 2 chữ số thập phân) |

**Response (Trường Hợp Không Có Dữ Liệu - 200):**
```json
{
  "success": true,
  "total": 0,
  "agree_count": 0,
  "disagree_count": 0,
  "agree_percentage": 0.0,
  "disagree_percentage": 0.0
}
```
**Lưu ý:** API xử lý trường hợp chia cho 0 một cách an toàn, trả về giá trị 0 thay vì lỗi.

**Response (Error - 500):**
```json
{
  "success": false,
  "message": "Không thể lấy dữ liệu thống kê.",
  "error": "Chi tiết lỗi từ server"
}
```

---

## 3. FRONTEND IMPLEMENTATION

### 3.1 HTML Structure

**Dashboard Page:**
```html
<section class="page" id="page-dashboard" aria-labelledby="dashboard-title">
  <div class="container">
    <!-- Loading State -->
    <div id="feedback-stats-loading">
      <!-- Skeleton loading indicators -->
    </div>

    <!-- Stats Content -->
    <div id="feedback-stats-content" style="display: none;">
      <!-- Stat Cards (Agree, Disagree, Total) -->
      <div class="stat-card" id="stat-agree-count">...</div>
      <div class="stat-card" id="stat-disagree-count">...</div>
      <div class="stat-card" id="stat-total-count">...</div>

      <!-- Chart Section -->
      <canvas id="feedbackChart"></canvas>

      <!-- Error State -->
      <div id="feedback-stats-error" style="display: none;">...</div>
    </div>
  </div>
</section>
```

### 3.2 JavaScript Functions

**Main Function - Load Statistics:**
```javascript
async function loadFeedbackStatistics() {
  try {
    const response = await fetch('/api/feedback/statistics');
    const data = await response.json();
    
    if (data.success) {
      // Update stat cards
      document.getElementById('stat-agree-count').textContent = data.agree_count;
      document.getElementById('stat-disagree-count').textContent = data.disagree_count;
      document.getElementById('stat-total-count').textContent = data.total;
      
      // Render chart
      renderFeedbackChart(data);
    }
  } catch (error) {
    // Show error state
  }
}
```

**Chart Rendering (Using Chart.js):**
```javascript
function renderFeedbackChart(data) {
  const ctx = document.getElementById('feedbackChart').getContext('2d');
  
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['👍 Đồng ý', '👎 Không đồng ý'],
      datasets: [{
        data: [data.agree_count, data.disagree_count],
        backgroundColor: ['#22c55e', '#ef4444'],
      }]
    },
    options: {
      responsive: true,
      plugins: {
        tooltip: {
          callbacks: {
            label: function(context) {
              const value = context.parsed || 0;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = ((value / total) * 100).toFixed(1);
              return `${context.label}: ${value} (${percentage}%)`;
            }
          }
        }
      }
    }
  });
}
```

### 3.3 UI Components

**Stats Cards:**
```
┌─────────────────┐
│ 👍 Đồng ý       │
│ 120 (80.0%)     │
└─────────────────┘

┌─────────────────┐
│ 👎 Không đồng ý │
│ 30  (20.0%)     │
└─────────────────┘

┌─────────────────┐
│ 📊 Tổng đánh giá│
│ 150             │
└─────────────────┘
```

**Chart (Doughnut Chart):**
```
        ┌─────────────┐
        │  👍 Đồng ý  │
        │    80%      │
        └─────────────┘
       /
      /
    ◉─────────────────
      \
       \
        └─────────────┐
        │ 👎 Không đ.đ │
        │    20%      │
        └─────────────┘
```

---

## 4. COLOR SCHEME

| Element | Color | Hex Code |
|---------|-------|----------|
| Agree (Đồng ý) | Green | `#22c55e` |
| Disagree (Không đồng ý) | Red | `#ef4444` |
| Border/Accent | Primary | Từ theme |

---

## 5. TESTING

### Test Case 1: Normal Case (Có Dữ Liệu)
```
Input Database:
- 5 Feedback: agree, agree, disagree, agree, disagree

Expected Response:
{
  "success": true,
  "total": 5,
  "agree_count": 3,
  "disagree_count": 2,
  "agree_percentage": 60.0,
  "disagree_percentage": 40.0
}
```

### Test Case 2: Empty Case (Không Có Dữ Liệu)
```
Expected Response:
{
  "success": true,
  "total": 0,
  "agree_count": 0,
  "disagree_count": 0,
  "agree_percentage": 0.0,
  "disagree_percentage": 0.0
}
```

### Test Case 3: Invalid Input
```
POST /api/feedback
Body: {
  "feedback_type": "invalid_value"
}

Expected Response (400):
{
  "success": false,
  "message": "feedback_type phải là \"agree\" hoặc \"disagree\"."
}
```

---

## 6. LOADING & ERROR STATES

### Loading State
Hiển thị skeleton loading khi đang gọi API:
```html
<div class="loading-skeleton">
  <!-- Animated placeholder elements -->
</div>
```

### Error State
Hiển thị thông báo lỗi với nút thử lại:
```html
<div id="feedback-stats-error">
  <p>Không thể tải dữ liệu thống kê.</p>
  <button id="btn-retry-stats">Thử lại</button>
</div>
```

---

## 7. PERFORMANCE CONSIDERATIONS

### Backend
- **Optimization:** Sử dụng SQLAlchemy query thay vì SQL thuần
- **Index:** Nên thêm index trên cột `feedback_type` để tối ưu câu query đếm
- **Caching:** Có thể cache kết quả nếu dữ liệu thay đổi không thường xuyên

### Frontend
- **Chart.js:** Sử dụng CDN để giảm kích thước bundle
- **Lazy Loading:** Chỉ load chart khi người dùng vào trang dashboard
- **Error Handling:** Có retry logic nếu API fails

---

## 8. EXPANSION POSSIBILITIES

Hệ thống này dễ mở rộng để bổ sung:
1. **Feedback Types mới:** Thêm các loại đánh giá khác (neutral, useful, etc.)
2. **Filters:** Thống kê theo ngày, user, prediction group
3. **Export:** Xuất dữ liệu thành CSV/Excel
4. **Time Series:** Biểu đồ theo dõi xu hướng theo thời gian
5. **User Feedback Detail:** Chi tiết feedback từng user

---

## 9. API USAGE EXAMPLES

### Using cURL:

**Submit Feedback:**
```bash
curl -X POST http://127.0.0.1:5000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "prediction_id": 123,
    "user_id": 45,
    "feedback_type": "agree",
    "comment": "Chính xác"
  }'
```

**Get Statistics:**
```bash
curl http://127.0.0.1:5000/api/feedback/statistics
```

### Using JavaScript/Fetch:

```javascript
// Submit feedback
fetch('/api/feedback', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    prediction_id: 123,
    user_id: 45,
    feedback_type: 'agree',
    comment: 'Chính xác'
  })
})
.then(res => res.json())
.then(data => console.log(data));

// Get statistics
fetch('/api/feedback/statistics')
  .then(res => res.json())
  .then(data => console.log(data));
```

### Using Python:

```python
import requests

# Submit feedback
response = requests.post(
  'http://127.0.0.1:5000/api/feedback',
  json={
    'prediction_id': 123,
    'user_id': 45,
    'feedback_type': 'agree',
    'comment': 'Chính xác'
  }
)
print(response.json())

# Get statistics
response = requests.get('http://127.0.0.1:5000/api/feedback/statistics')
print(response.json())
```

---

## 10. STATUS CODES REFERENCE

| Code | Status | Meaning |
|------|--------|---------|
| 200 | OK | GET statistics thành công |
| 201 | Created | POST feedback thành công |
| 400 | Bad Request | Dữ liệu input không hợp lệ |
| 500 | Internal Server Error | Lỗi server khi xử lý |

---

## 11. IMPLEMENTATION CHECKLIST

- ✅ Database Model (Feedback table) - Created in `models.py`
- ✅ POST /api/feedback endpoint - Created in `app.py`
- ✅ GET /api/feedback/statistics endpoint - Created in `app.py`
- ✅ Frontend Dashboard Page - Added to `index.html`
- ✅ JavaScript Statistics Functions - Added to `script.js`
- ✅ Chart.js Integration - CDN link added to `index.html`
- ✅ Loading & Error States - Implemented
- ✅ Navigation Links - Added to top nav and bottom nav
- ✅ Error Handling & Validation - Implemented
- ✅ Test Script - Created in `test_feedback_api.py`

---

## 12. NOTES

- API trả về dữ liệu hợp lệ ngay cả khi không có dữ liệu (total = 0)
- Không có lỗi chia cho 0 (zero-safe calculation)
- Tỷ lệ phần trăm làm tròn đến 2 chữ số thập phân
- Cơ chế caching có thể được thêm vào nếu cần tối ưu hiệu suất
- Frontend có loading state và error state để UX tốt hơn
