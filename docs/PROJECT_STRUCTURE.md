# Project Structure

## backend/

Chứa Flask API và logic xử lý:

- `app.py`: load model, nhận request, dự đoán bệnh, tra guidance và serve frontend.
- `symptom_search_model.py`: model TF-IDF cosine search dùng khi train từ `disease_database_en.json`.
- `translations.py`: ánh xạ tên bệnh/nội dung tham khảo sang tiếng Việt khi có dữ liệu.

## frontend/

Chứa giao diện web tĩnh:

- `index.html`: layout các màn hình nhập liệu, kết quả, lịch sử, hướng dẫn.
- `styles.css`: giao diện responsive.
- `script.js`: gọi API, render kết quả, lưu lịch sử localStorage.

## data/

Chứa dữ liệu cấu hình nghiệp vụ:

- `disease_guidance.json`: bảng hướng dẫn theo disease, gồm `treatment_groups`, `care`, `precautions`, `warning_signs`.

## models/

Chứa artifact sau train:

- `disease_model.joblib`: model đã train.
- `metadata.json`: metadata model, danh sách disease/features.
- `classification_report.json`: report hoặc ghi chú train.

## scripts/

Chứa script vận hành:

- `train_model.py`: train/retrain model từ archive có `Training.csv` hoặc `disease_database_en.json`.

## docs/

Chứa tài liệu bổ sung cho project.
