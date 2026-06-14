# Kế hoạch test UI — PharmaPredict (model mới, 2026-06-08)

> File này dành cho **Antigravity** (browser agent) chạy test UI/UX. Mục tiêu: xác nhận
> hệ thống "dự đoán nhóm thuốc từ mô tả bệnh án ngắn" hoạt động đúng với **model vừa retrain**
> (accuracy thật trên mô tả tự nhiên đã tăng 26,2% → 92,6%).

---

## 1. Khởi động ứng dụng

```powershell
# Tại thư mục d:\CNPM, dùng đúng Python đã cài deps (Python 3.11 global)
python backend/app.py
```

- Mở trình duyệt: **http://127.0.0.1:5000**
- Nếu gặp lỗi thiếu thư viện: `pip install -r requirements.txt` (cần `scikit-learn`, `flask`,
  `flask-cors`, `joblib`).
- Lưu ý: model đã train trên scikit-learn 1.9.x nên **không còn** cảnh báo version khi khởi động.

## 2. Tài khoản đăng nhập

App có màn hình đăng nhập chặn trước. Tài khoản cũ không rõ mật khẩu → **đăng ký tài khoản mới**:

- Ở màn hình đăng nhập, bấm link **"Đăng ký"**.
- Điền: Họ tên `Antigravity Test`, Email `antigravity@test.com`, Mật khẩu `test123456` (≥6 ký tự).
- Bấm nút **"Tạo tài khoản"** → hệ thống tự đăng nhập và vào trang chính.

## 3. Luồng chính cần test (trang Home → Kết quả)

Với mỗi case dưới đây:
1. Vào trang **Home**.
2. Nhập mô tả vào ô textarea `#case-description` ("Mô tả bệnh án").
3. Bấm nút **"Gợi ý nhóm thuốc"** (nút primary có icon `analytics` trong form).
4. Đọc kết quả: **Nhóm thuốc gợi ý** (`display_title`), độ tin cậy, triệu chứng nhận diện,
   thuốc tham khảo, lời khuyên chăm sóc.

### 3a. Case KỲ VỌNG ĐÚNG (phải PASS)

| # | Mô tả nhập (tiếng Việt) | Nhóm thuốc kỳ vọng |
|---|---|---|
| 1 | `Tôi bị ho, sốt và đau họng mấy ngày nay` | thuốc giảm đau hạ sốt |
| 2 | `Ngứa da, nổi mẩn đỏ, hắt hơi liên tục` | thuốc kháng histamin |
| 3 | `Sốt cao, rét run, đau cơ, vừa đi vùng sốt rét về` | thuốc điều trị sốt rét |
| 4 | `Ợ chua, nóng rát vùng thượng vị, đau dạ dày sau ăn` | thuốc điều trị dạ dày |
| 5 | `Bệnh nhân sốt cao, ho có đờm, đau ngực, khó thở` | thuốc kháng sinh |

✅ **PASS** nếu nhóm thuốc hiển thị khớp cột "kỳ vọng" (hoặc rất sát về mặt y khoa).

### 3b. Case ĐÃ BIẾT LỖI (xác nhận có tái hiện không)

Đây là lỗi của **tầng dịch triệu chứng Việt→Anh** (chưa map đủ 330/582 triệu chứng), KHÔNG
phải lỗi model. Antigravity chỉ cần **xác nhận hiện tượng** để nhóm ưu tiên vá sau:

| # | Mô tả nhập | Hiện ra (sai) | Đúng phải là |
|---|---|---|---|
| 6 | `Tiểu buốt, tiểu rắt, đau bụng dưới` | thuốc điều trị dạ dày | thuốc kháng sinh (nhiễm khuẩn tiết niệu) |
| 7 | `Đau đầu dữ dội từng cơn, buồn nôn, sợ ánh sáng` | thuốc chống nôn | thuốc giảm đau hạ sốt (migraine) |

📝 Ghi lại: case 6,7 ra nhóm nào, có đúng như "hiện ra (sai)" không.

## 4. Test UI/UX tổng quát (mỗi mục PASS/FAIL)

- [ ] **Nút "Ví dụ"** (`#example-case`): bấm → tự điền mô tả mẫu vào ô nhập.
- [ ] **Nút "Xóa"** (`#clear-case`): bấm → xóa sạch ô nhập + kết quả.
- [ ] **Tìm triệu chứng** (`#symptom-search`): gõ "ho" → ra danh sách triệu chứng tiếng Việt;
      chọn 1-2 triệu chứng rồi dự đoán → vẫn ra kết quả.
- [ ] **Lưu kết quả** (`#save-result`): sau khi có kết quả, bấm lưu → vào trang **Lịch sử** thấy bản ghi.
- [ ] **Trang Lịch sử**: tìm kiếm (`#history-search`), mở xem chi tiết 1 bản ghi.
- [ ] **Điều hướng**: chuyển qua lại các tab Home / Kết quả / Lịch sử / Giới thiệu (menu trên + bottom-nav) không lỗi.
- [ ] **Đăng xuất** (`#logout-button`): bấm → quay về màn đăng nhập; đăng nhập lại được.
- [ ] **Validate**: để trống ô mô tả rồi bấm dự đoán → hiện thông báo lỗi thân thiện (không crash).
- [ ] **Mô tả vô nghĩa** (vd `aaaa bbbb`): hiện thông báo "không nhận diện được triệu chứng",
      không trả kết quả bừa.
- [ ] **Responsive**: thu nhỏ cửa sổ / chế độ mobile → bố cục không vỡ, bottom-nav hiển thị.

## 5. Tiêu chí kết luận

- **ĐẠT (sẵn sàng merge)** nếu: 5/5 case mục 3a PASS, toàn bộ checklist mục 4 PASS, không có
  lỗi JS console nghiêm trọng / không crash backend.
- **CHƯA ĐẠT** nếu: bất kỳ case 3a sai, hoặc UI crash / nút không hoạt động / không lưu được lịch sử.
- Case mục 3b **không tính là fail merge** (đã biết, thuộc backlog vá tầng dịch VN→EN).

## 6. Mẫu báo cáo gửi lại

```
[PharmaPredict UI Test - 2026-06-08]
Khởi động: OK / Lỗi (...)
Đăng ký/đăng nhập: OK / Lỗi
Mục 3a: _/5 PASS  (liệt kê case sai nếu có: # ... ra nhóm ...)
Mục 3b: case6 -> ... | case7 -> ...  (có tái hiện lỗi không)
Mục 4 (UI/UX): _/11 PASS  (liệt kê mục FAIL)
Lỗi console/crash: (mô tả + screenshot)
Kết luận: ĐẠT / CHƯA ĐẠT
```

## 7. Ngữ cảnh kỹ thuật (để hiểu hệ thống)

- Backend Flask: `backend/app.py`; endpoint dự đoán `POST /api/predict` (body `{notes, symptoms}`),
  không yêu cầu token.
- Model: TF-IDF + Linear SVM (calibrated), 24 nhóm thuốc, file `models/disease_model.joblib`
  (đã đổi sang bản mới; bản cũ backup ở `models_old/`).
- Pipeline suy luận: mô tả tiếng Việt → trích & dịch triệu chứng sang tiếng Anh → model dự đoán
  nhóm thuốc → tra thuốc tham khảo + lời khuyên. (Lỗi mục 3b nằm ở bước "trích & dịch".)
