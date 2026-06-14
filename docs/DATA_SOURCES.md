# Nguồn dữ liệu chất lượng cho PharmaPredict

> Cập nhật: 2026-06-08. Mục tiêu: dữ liệu để train "dự đoán nhóm thuốc từ mô tả bệnh án ngắn".

## 0. Phát hiện quan trọng (đọc trước)

Model hiện tại đạt **accuracy 93,4% trên tập test nội bộ**, nhưng đó là con số **ảo** vì
data train là câu khuôn mẫu `Patient has symptoms: X; Y; Z` (hoán vị của cùng bộ triệu chứng).

Khi đánh giá trên **1065 câu mô tả tự nhiên** (`gretelai/symptom_to_diagnosis`):

```
ACCURACY THẬT = 22,8% (243/1065)
```

(chạy lại bằng `python scripts/eval_natural_descriptions.py`)

➡️ Kết luận: vấn đề số 1 **không phải thiếu công cụ crawl**, mà là **data không tự nhiên +
mất cân bằng lớp + một số mapping chẩn đoán→nhóm thuốc bị sai** (vd `varicose veins` đang
map sang `thuốc nội tiết tuyến giáp`, `typhoid` map sang `vắc-xin`). Cần ưu tiên data tự
nhiên + làm sạch mapping trước khi crawl thêm.

### Kết quả Bước 1 (2026-06-08): sửa mapping + bơm data tự nhiên + retrain

| Đo trên gretel TEST (212 câu, held-out) | Model cũ `models/` | Model mới `models_v2/` |
|---|---|---|
| **Accuracy THẬT trên mô tả tự nhiên** | **26,2%** | **92,6%** |

- Pipeline: `fix_mappings.py` → `build_natural_dataset.py` → `build_combined_dataset.py` →
  `train_model.py --out models_v2` → `eval_natural_descriptions.py --model models_v2`.
- Đã sửa: dengue (kháng sinh→giảm đau hạ sốt), typhoid (vắc-xin→kháng sinh); loại `varicose veins`
  (không nhóm thuốc phù hợp). Khử trùng + cap 3000/lớp + nhân bản data tự nhiên x3.
- **Lưu ý trung thực:** gretel test cùng văn phong với gretel train, nên 92,6% phản ánh khả năng
  tổng quát trong *phong cách gretel*; mô tả lâm sàng tiếng Việt thật (sau dịch) có thể khác. Đây
  vẫn là bước nhảy lớn vì model giờ hiểu *câu tự nhiên* thay vì chỉ token khuôn mẫu.

---

## 1. Dataset MÔ TẢ TỰ NHIÊN (đã tải về `data/raw/`)

Đây là loại data đúng nhất cho bài toán "mô tả bệnh án ngắn".

| Dataset | File | Mô tả | Dùng cho |
|---|---|---|---|
| `gretelai/symptom_to_diagnosis` | `gretel_symptom_to_diagnosis_{train,test}.jsonl` | 1065 câu mô tả tự nhiên của bệnh nhân → 22 bệnh | **Test thật + augment train** |
| `QuyenAnhDE/Diseases_Symptoms` | `QuyenAnhDE_Diseases_Symptoms.csv` | 400+ bệnh kèm cột Symptoms **và Treatments** | Map bệnh → điều trị / nhóm thuốc |
| `celikmus/symptom_text_to_disease_01` | `celikmus_train.parquet` | Câu mô tả triệu chứng → bệnh | Augment train |

Tải lại (HuggingFace, không cần token):
```powershell
curl -sL -o data/raw/gretel_symptom_to_diagnosis_train.jsonl "https://huggingface.co/datasets/gretelai/symptom_to_diagnosis/resolve/main/train.jsonl"
```

## 2. Nguồn tải trực tiếp khác (tiếng Anh, chất lượng cao)

| Nguồn | Link | Ghi chú |
|---|---|---|
| Kaggle — Symptom2Disease | `kaggle datasets download niyarrbarman/symptom2disease` | 1200 câu mô tả tự nhiên, 24 bệnh |
| Kaggle — Disease Symptom Prediction | `kaggle datasets download kaushil268/disease-symptom-prediction` | Chính là nguồn gốc data hiện tại (dạng triệu chứng rời) |
| Kaggle — Drugs, Side Effects & Conditions | `kaggle datasets download jithinanievarghese/drugs-side-effects-and-medical-conditions` | Map thuốc → bệnh/điều kiện (cào từ drugs.com) |
| HuggingFace — `shanover/disease_symptoms_prec_full` | `.../disease_sympts_prec_full.csv` | Bệnh + triệu chứng + phòng ngừa |
| MIMIC-IV / MIMIC-IV-Note | physionet.org | Bệnh án LÂM SÀNG thật (tiếng Anh) — **cần đăng ký credentialed access + khóa học CITI** |

> Kaggle cần API token: tải `kaggle.json` từ trang Account → đặt vào `~/.kaggle/kaggle.json`.

## 3. Nguồn DƯỢC TIẾNG VIỆT (cần crawl — dùng scraper)

Không có dataset tải sẵn → đây là lúc dùng `scripts/scrape_vn_drugs.py` (requests/BS4)
hoặc `scripts/browser_use_vn_drugs.py` (browser-use) nếu trang chặn/nặng JS.

| Trang | URL | Nội dung |
|---|---|---|
| Thuốc biệt dược | https://www.thuocbietduoc.com.vn | Tên thuốc, hoạt chất, nhóm thuốc, chỉ định |
| DrugBank VN | https://drugbank.vn | CSDL thuốc chính thức (Bộ Y tế) |
| Nhà thuốc Long Châu | https://nhathuoclongchau.com.vn/thuoc | Thuốc + công dụng + nhóm |
| Trung tâm thuốc Central Pharmacy | https://trungtamthuoc.com | Bài viết dược, hoạt chất |
| Dược thư Quốc gia VN | (PDF Bộ Y tế) | Chuẩn nhất để map hoạt chất → nhóm dược lý |

> Lưu ý pháp lý/kỹ thuật: kiểm tra `robots.txt`, đặt delay ≥1s/req, set User-Agent thật,
> chỉ lấy dữ liệu công khai phục vụ học tập. Không cào ồ ạt.

## 4. Dữ liệu lâm sàng / NLP TIẾNG VIỆT

| Bộ | Nguồn | Ghi chú |
|---|---|---|
| ViMQ | github.com/vinairesearch (Vietnamese Medical Question) | Câu hỏi y khoa tiếng Việt có annotation |
| ViHealthBERT | HuggingFace `demdecuong/vihealthbert-base-word` | Pretrained model y tế tiếng Việt (để embed, không phải dataset) |
| PhoBERT | `vinai/phobert-base` | Encoder tiếng Việt mạnh, thay TF-IDF khi nâng cấp model |
| COVID-19 Vietnamese NER | github | Văn bản y tế tiếng Việt có nhãn |

> Phần lớn dataset lâm sàng tiếng Việt khan hiếm và cần email xin tác giả / ký thỏa thuận.

---

## 5. Lộ trình đề xuất (ưu tiên giảm dần)

1. **Làm sạch mapping** chẩn đoán→nhóm thuốc trong data hiện tại (sửa các map sai như
   varicose veins, typhoid, jaundice).
2. **Trộn data tự nhiên** (gretel + Symptom2Disease + celikmus) vào train để model học
   ngôn ngữ tự nhiên, không chỉ token khuôn mẫu.
3. **Cân bằng lớp**: gộp lớp quá nhỏ hoặc dùng `class_weight='balanced'` / oversample.
4. **Nâng encoder**: TF-IDF → PhoBERT/ViHealthBERT cho tiếng Việt thật.
5. **Crawl dược VN** để map nhóm thuốc tiếng Việt chuẩn theo Dược thư Quốc gia.
6. Re-evaluate bằng `scripts/eval_natural_descriptions.py` sau mỗi bước.
