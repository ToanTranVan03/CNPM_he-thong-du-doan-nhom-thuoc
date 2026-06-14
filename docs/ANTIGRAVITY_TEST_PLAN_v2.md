# Kế hoạch test UI cho Antigravity — Vòng 2 (lớp hiểu ngữ nghĩa tiếng Việt)

> Dành cho **Antigravity** chạy độc lập. Mục tiêu: (A) xác nhận hệ thống hiểu **câu tiếng Việt
> lạ** (khác từ điển) nhờ lớp SBERT, (B) **review giao diện/UX** — phần con mắt độc lập mà chỉ
> Antigravity làm. So với vòng 1, hệ thống đã thêm: lớp ngữ nghĩa, nhiều rule lâm sàng, cảnh báo
> dấu hiệu đỏ đa cách diễn đạt.

---

## 1. Khởi động ứng dụng (LƯU Ý: chậm hơn vòng trước)

```powershell
# Dùng ĐÚNG Python đã cài torch + sentence-transformers (Python 3.11 global của máy này)
python backend/app.py
```

- Lần đầu khởi động sẽ **tải model SBERT (~500MB)** rồi nạp + dựng index → có thể mất **30s–3 phút**.
  Các lần sau nhanh (~10–40s vì model đã cache).
- **CHỜ** tới khi `http://127.0.0.1:5000/api/health` trả **200** rồi mới test.
- Kiểm tra log thấy dòng `Running on http://127.0.0.1:5000` là server đã lên.
- Nếu thiếu `torch`/`sentence-transformers`: app vẫn chạy nhưng **tự lùi về khớp từ khóa** (kém
  robust hơn). Khi đó ghi rõ trong báo cáo "chạy chế độ fallback (không có SBERT)".

## 2. Tài khoản
Đăng ký mới qua UI: bấm **"Đăng ký"** → Họ tên `Antigravity V2`, Email `anti.v2@test.com`,
Mật khẩu `test123456` → bấm **"Tạo tài khoản"**. (Nếu email đã tồn tại thì đăng nhập lại.)

## 3. Cách test mỗi ca (trang Home → Kết quả)
1. Vào Home, bấm **"Xóa"** (`#clear-case`).
2. Nhập mô tả vào ô `#case-description`.
3. Bấm **"Gợi ý nhóm thuốc"** (`#diagnosis-form button[type='submit']`).
4. Đọc **Nhóm thuốc gợi ý** (`#result-title` / `#summary-drug-group`). Nếu hệ thống trả
   "Chưa đủ dữ liệu để gợi ý thuốc" → coi là **CẦN-THÊM-THÔNG-TIN/CẢNH-BÁO**.

> Có sẵn script tự động: `python run_ui_tests_semantic.py` (cần server đang chạy). Nó tự đăng
> nhập, chạy 12 ca câu lạ, chụp `screenshots/sem_*.png`, ghi `screenshots/sem_test_report.txt`.
> Antigravity có thể chạy script này HOẶC tự thao tác tay theo bảng dưới.

### 3a. Ca câu LẠ — kỳ vọng đúng (PASS nếu khớp cột kỳ vọng)

| # | Mô tả (tiếng Việt, phrasing lạ) | Nhóm thuốc kỳ vọng |
|---|---|---|
| 1 | Mũi tắc tịt, hắt xì cả buổi sáng, chảy nước mũi trong | thuốc kháng histamin (hoặc thông mũi) |
| 2 | Bụng trên đau cồn cào lúc đói, hay ợ chua | thuốc điều trị dạ dày |
| 3 | Khớp gối sưng đau, đi lại khó, sáng dậy cứng khớp | thuốc kháng viêm không steroid |
| 4 | Lên cơn hen, thở rít, nặng ngực khó thở | thuốc giãn phế quản |
| 5 | Răng sâu nhức buốt, lợi sưng đau | thuốc giảm đau nha khoa |
| 6 | Mẩn ngứa nổi khắp người sau khi uống thuốc lạ | thuốc kháng histamin |
| 7 | Hay khát, tiểu nhiều, mờ mắt, sụt cân, mệt mỏi | thuốc điều trị đái tháo đường |
| 8 | Cổ to, mắt lồi, sút cân, tay run, hồi hộp | thuốc nội tiết tuyến giáp |

### 3b. Ca AN TOÀN — kỳ vọng CẢNH BÁO/không gợi ý thuốc (PASS nếu hệ thống KHÔNG đưa thuốc, mà nhắc đi khám)

| # | Mô tả | Kỳ vọng |
|---|---|---|
| 9 | Đột nhiên nói đớ, yếu tay phải, méo một bên mặt | Cảnh báo cấp cứu (đột quỵ) |
| 10 | Sốt cao, đau đầu nhiều, cổ cứng, sợ ánh sáng | Cảnh báo (viêm màng não) |
| 11 | Khó thở dữ dội, tím tái, lơ mơ | Cảnh báo cấp cứu |
| 12 | Trong người thấy oải oải khó tả (mơ hồ) | Cần thêm thông tin, KHÔNG đoán bừa |

> Ghi chú: một số ca "khó" (tim mạch, sốt rét, thiếu máu, đau thần kinh) hiện vẫn có thể sai —
> **không tính là lỗi chặn merge**; chỉ cần ghi lại kết quả.

## 4. ★ Review GIAO DIỆN / UX (phần quan trọng nhất chỉ Antigravity làm)
Chụp và nhận xét từng màn, nêu rõ lỗi visual nếu có:
- [ ] **Đăng nhập/Đăng ký**: bố cục cân đối, chữ rõ, nút bấm đúng, thông báo lỗi thân thiện.
- [ ] **Home**: ô nhập mô tả, ô tìm triệu chứng, nút "Gợi ý nhóm thuốc"/"Ví dụ"/"Xóa" hiển thị đúng.
- [ ] **Kết quả**: tiêu đề nhóm thuốc, độ tin cậy, danh sách thuốc tham khảo, chăm sóc, **cảnh báo
      an toàn** có nổi bật không; bố cục không vỡ, không tràn chữ.
- [ ] **Lịch sử**: lưu kết quả, tìm kiếm, xem chi tiết.
- [ ] **Responsive (mobile)**: thu nhỏ ~375px → bottom-nav hiện, bố cục không vỡ.
- [ ] **Tiếng Việt**: dấu hiển thị đúng, không lỗi font/mojibake.
- [ ] Bắt lỗi console (F12) nghiêm trọng nếu có.

## 5. Tiêu chí kết luận
- **ĐẠT**: ≥6/8 ca mục 3a đúng, **4/4 ca an toàn mục 3b cảnh báo đúng**, checklist UI mục 4 không
  có lỗi nghiêm trọng/không crash.
- **CHƯA ĐẠT**: bất kỳ ca an toàn (3b) KHÔNG cảnh báo, hoặc UI crash/nút hỏng/không lưu lịch sử,
  hoặc tiếng Việt lỗi font.

## 6. Mẫu báo cáo (ghi vào `screenshots/anti_v2_report.md`)
```
[Antigravity UI Test V2 - <ngày>]
Khởi động: OK / fallback không SBERT / lỗi (...)
Mục 3a: _/8  (liệt kê ca sai: # -> nhận được gì)
Mục 3b (an toàn): _/4  (ca nào không cảnh báo?)
Mục 4 (UI/UX): nhận xét từng màn + lỗi visual + screenshot
Lỗi console/crash: ...
Kết luận: ĐẠT / CHƯA ĐẠT
```

## 7. Ngữ cảnh kỹ thuật
- Backend Flask `backend/app.py`; endpoint `POST /api/predict` (body `{notes, symptoms}`), không cần token.
- Lớp ngữ nghĩa: `backend/semantic_matcher.py` (SBERT VN) — chạy fallback khi khớp từ khóa <2 triệu chứng.
- Model nhóm thuốc: `models/disease_model.joblib` (TF-IDF + LinearSVM, 24 nhóm).
- Pipeline: mô tả VN → trích triệu chứng (từ khóa + ngữ nghĩa) → rule lâm sàng/model → nhóm thuốc + cảnh báo.
