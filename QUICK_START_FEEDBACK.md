# Feedback Statistics API - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Step 1: Start the Flask Backend
```bash
cd backend
python app.py
```
✓ Server runs on http://127.0.0.1:5000
✓ Database automatically initialized
✓ API endpoints ready

### Step 2: Open the Application
Navigate to: `http://127.0.0.1:5000`
- Login with test account
- Or create new account

### Step 3: View Dashboard
Click navigation: **"Thống Kê"** (Statistics)
- See loading skeleton
- Wait for data to load
- View stat cards and chart

### Step 4: Submit Feedback
From prediction result page:
1. Click **"👍 Đồng ý"** or **"👎 Không đồng ý"**
2. Optionally add comment
3. Submit
4. Return to dashboard to see updated stats

---

## 📊 Dashboard Overview

### Three Stat Cards
```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ 👍 Đồng ý        │  │ 👎 Không đồng ý  │  │ 📊 Tổng đánh giá │
│ 120 (80.0%)      │  │ 30  (20.0%)      │  │ 150              │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

### Doughnut Chart
- Visual representation of feedback ratio
- Green for agree, Red for disagree
- Hover for detailed tooltip

---

## 🔌 API Usage

### Submit Feedback
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

### Get Statistics
```bash
curl http://127.0.0.1:5000/api/feedback/statistics
```

Response:
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

---

## 🧪 Running Tests

```bash
# From project root
python test_feedback_api.py
```

Expected output:
```
✓ Feedback 1: AGREE - Thành công
✓ Feedback 2: AGREE - Thành công
✓ Feedback 3: AGREE - Thành công
✓ Feedback 4: DISAGREE - Thành công
✓ Feedback 5: DISAGREE - Thành công
✓ API Response: SUCCESS
  • Total Feedback:        5
  • Agree Count:           3
  • Disagree Count:        2
  • Agree Percentage:      60.0%
  • Disagree Percentage:   40.0%
```

---

## 📁 Key Files

### Backend
- `backend/models.py` - Feedback model (15 lines)
- `backend/app.py` - API endpoints (90 lines)

### Frontend
- `frontend/index.html` - Dashboard page (60 lines)
- `frontend/script.js` - JavaScript functions (100 lines)
- `frontend/styles.css` - Dashboard styles (50 lines)

### Tests & Documentation
- `test_feedback_api.py` - Test suite
- `FEEDBACK_STATISTICS_API.md` - API documentation
- `FEEDBACK_IMPLEMENTATION_SUMMARY.md` - Implementation guide

---

## 🎨 Colors & Design

| Element | Color | Usage |
|---------|-------|-------|
| Agree | #22c55e (Green) | Positive feedback |
| Disagree | #ef4444 (Red) | Negative feedback |
| Total | var(--primary) | Neutral stat |
| Background | var(--surface) | Page background |
| Border | var(--border) | Card borders |

---

## ⚙️ Configuration

### Database
- Type: SQLite
- Path: `instance/pharma_predict.db`
- Auto-created on startup

### API Endpoints
- Base: `http://127.0.0.1:5000`
- POST: `/api/feedback`
- GET: `/api/feedback/statistics`

### Frontend
- No configuration needed
- Chart.js loaded from CDN
- Responsive design automatic

---

## 🆘 Troubleshooting

### Issue: "Chart not loading"
**Solution:** Check Chart.js CDN is accessible
```html
<!-- In frontend/index.html -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
```

### Issue: "API returns 500 error"
**Solution:** Check Flask backend logs
```bash
python app.py  # View error messages
```

### Issue: "Dashboard shows no data"
**Solution:** Submit feedback first, then refresh dashboard

### Issue: "Statistics not updating"
**Solution:** 
1. Check API status: http://127.0.0.1:5000/api/feedback/statistics
2. Try refresh button on error state
3. Check browser console for errors

---

## 📝 API Response Codes

| Code | Status | Meaning |
|------|--------|---------|
| 200 | OK | GET statistics success |
| 201 | Created | POST feedback success |
| 400 | Bad Request | Invalid input |
| 500 | Server Error | Database/server error |

---

## 🔒 Security Notes

✓ Input validation on feedback_type
✓ SQL injection prevention (SQLAlchemy)
✓ Error messages don't expose secrets
✓ Proper HTTP status codes
✓ No hardcoded credentials

---

## 📚 Documentation Structure

```
project/
├── FEEDBACK_STATISTICS_API.md .............. Full API reference
├── FEEDBACK_IMPLEMENTATION_SUMMARY.md ...... Implementation guide
├── IMPLEMENTATION_CHECKLIST.md ............ Verification checklist
├── QUICK_START.md ........................ This file
├── backend/
│   ├── models.py ......................... Feedback model
│   └── app.py ........................... API endpoints
├── frontend/
│   ├── index.html ........................ Dashboard page
│   ├── script.js ......................... Dashboard logic
│   └── styles.css ........................ Dashboard styles
└── test_feedback_api.py .................. Test suite
```

---

## 🎯 Next Steps

1. ✅ Start backend server
2. ✅ Open application
3. ✅ Navigate to dashboard
4. ✅ Submit test feedback
5. ✅ View statistics
6. ✅ Run test suite (optional)

---

## 📞 Support

For issues or questions:
1. Check troubleshooting section above
2. Review error message carefully
3. Check API logs in Flask output
4. Check browser console (F12)
5. Read full documentation in FEEDBACK_STATISTICS_API.md

---

## 🎉 Success!

If you can see the dashboard with:
- ✓ Three stat cards
- ✓ Loading skeleton animation
- ✓ Doughnut chart
- ✓ Error state with retry button

**Congratulations! The API is working correctly.**

---

**Last Updated:** 2026-06-21  
**Version:** 1.0  
**Status:** Ready for Production
