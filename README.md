# PharmaPredict

Ứng dụng Flask + giao diện tĩnh để dự đoán nhóm thuốc tham khảo từ mô tả triệu chứng tiếng Việt bằng model TF-IDF + Linear SVM.

## Cấu trúc thư mụccc

```text
CNPM/
  backend/                 API Flask và các module xử lý
    app.py                 Entry point backend
    symptom_search_model.py
    translations.py
  frontend/                Giao diện web tĩnh
    index.html
    styles.css
    script.js
  data/
    train_ready_mapped_drug_groups.csv
    disease_guidance.json  Bảng treatment_groups/care/precautions/warning_signs theo disease
  models/                  Model đã train và metadata
    disease_model.joblib
    metadata.json
    classification_report.json
  scripts/
    train_model.py         Script train/retrain model
  docs/                    Tài liệu bổ sung
  requirements.txt
```

## Cách chạy tai terminal : pip install -r requirements.txt

```powershell
python backend/app.py
```

Sau đó mở:

```text
http://127.0.0.1:5000
```

Nếu muốn chạy port khác:

```powershell
$env:PORT="5001"
python backend/app.py
```

## Train model

```powershell
python scripts/train_model.py --data "data\train_ready_mapped_drug_groups.csv"
```

Mặc định model sẽ được ghi vào thư mục `models/`. Với CSV mới, script tự chọn `trieu_chung` làm text input và `nhom_thuoc` làm target; có thể đổi bằng `--text-column` và `--target-column`.

### Train trên tập đã trộn data tự nhiên (khuyến nghị)

Pipeline đầy đủ: làm sạch mapping → dựng data tự nhiên → gộp/cân bằng → train.

```powershell
python scripts/fix_mappings.py
python scripts/build_natural_dataset.py
python scripts/build_combined_dataset.py
python scripts/train_model.py --data "data\train_combined.csv" --features-data "data\train_ready_mapped_drug_groups.csv"
```

> `--features-data` bắt buộc khi train trên tập đã khử trùng/cap (`train_combined.csv`): danh sách
> features (từ vựng triệu chứng cho bộ chọn + tầng dịch VN→EN) được lấy từ data GỐC đầy đủ để
> không bị thiếu triệu chứng. Đánh giá lại bằng `python scripts/eval_natural_descriptions.py --model models`.

## Luồng xử lý

1. Người dùng nhập mô tả triệu chứng tiếng Việt.
2. Backend map triệu chứng sang cụm triệu chứng tiếng Anh.
3. Model TF-IDF + Linear SVM dự đoán `nhom_thuoc`.
4. Backend lấy nhóm thuốc dự đoán và danh sách thuốc tham khảo từ CSV mới.
5. API trả nhóm thuốc gợi ý, độ tin cậy, chăm sóc, phòng ngừa và cảnh báo an toàn.

## Mở rộng hướng dẫn bệnh

Thêm entry mới vào:

```text
data/disease_guidance.json
```

Tên key nên khớp với tên disease model trả về, ví dụ:

```json
"Acute Pharyngitis": {
  "treatment_groups": ["..."],
  "care": ["..."],
  "precautions": ["..."],
  "warning_signs": ["..."],
  "source": "structured_guidance"
}
```
