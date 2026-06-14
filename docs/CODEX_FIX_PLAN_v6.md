# Cải thiện output gợi ý nhóm thuốc Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` hoặc `superpowers:executing-plans` để triển khai task-by-task. Steps dùng checkbox (`- [ ]`) để tracking.

**Goal:** Output `/api/predict` chỉ hiển thị 1 nhóm thuốc chính, 2-3 hoạt chất tiêu biểu đã làm sạch, lý do triệu chứng -> nhóm, độ tin cậy, và vẫn giữ các cổng an toàn.

**Architecture:** Tách 2 việc độc lập: retrain/calibrate model để top-1 nhóm thuốc dứt khoát hơn, và curate danh sách hoạt chất sạch từ `ten_thuoc` để thay cho dump raw hiện tại. Retrain không được coi là giải pháp làm sạch thuốc; output cần mapping top-N riêng, có kiểm duyệt/allowlist và test Flask client.

**Tech Stack:** Python, Flask, scikit-learn TF-IDF + `LinearSVC`/`CalibratedClassifierCV`, CSV/JSON data artifacts, existing backend rule/LLM safety layers.

---

## Phân tích hiện trạng

- Scope: backend + data/model scripts. Không cần đổi frontend trừ khi UI đang render trực tiếp `medications` quá dài; nếu có, chỉ chỉnh sau khi API contract mới đã rõ.
- Model hiện hành: `models/disease_model.joblib`, metadata `models/metadata.json` ghi `model_type=tfidf_linear_svm`, `label_type=drug_group`, `accuracy=0.952994204764971`, `rows=46587`, `classes=24`, `source=data\train_combined.csv`, `text_column=trieu_chung`, `target_column=nhom_thuoc`.
- Data train hiện trong workspace: `data/train_ready_mapped_drug_groups.csv` đọc được `89869` dòng, 24 nhóm. Con số này khác metadata hiện hành và khác mô tả task `46587`; trước khi train phải chốt rõ file nguồn dùng thật và ghi vào metadata.
- Mất cân bằng thật trong metadata hiện hành: nhóm nhỏ gồm `thuốc chống đông/kháng tiểu cầu=10`, `thuốc/điều trị ung thư=15`, `vắc-xin=15`, `thuốc nội tiết tuyến giáp=18`, `thuốc điều hòa/ức chế miễn dịch=28`; nhóm lớn gồm `thuốc kháng sinh`, `thuốc kháng viêm không steroid`, `thuốc giảm đau hạ sốt`, `bù dịch và điện giải`, `thuốc corticosteroid/chống viêm`.
- Gốc rễ output "nhiều thuốc/chung chung": `backend/app.py:1204-1259` tạo `references["medications"][group]` bằng tối đa 8 dòng raw từ `ten_thuoc`; `backend/app.py:1611-1633` trả lại list đó; `backend/app.py:1636-1666` append vào `treatment`; `backend/app.py:2985-2987` trả `medications[:10]` và `dataset_treatment`.
- Các lớp phải giữ: emergency lexicon + LLM safety (`backend/app.py:2689-2753`), notes-aware rules (`backend/app.py:2788-2809`), ngưỡng scoped (`backend/app.py:2831-2866`), ngữ cảnh rượu/gắng sức (`backend/app.py:2867-2960`), LLM enrich trong `backend/llm_context.py`.

## Files sẽ sửa/tạo

- Modify `scripts/train_model.py:129-159`: cấu hình TF-IDF/SVM/calibration, thêm tùy chọn strategy imbalance, metadata class metrics.
- Modify `scripts/train_model.py:211-310`: split/eval/report, lưu thêm confusion/top-gap/calibration report nếu cần.
- Modify hoặc create script data audit, đề xuất `scripts/audit_drug_group_training.py`: thống kê class counts, overlap/confusion giữa nhóm, so sánh file nguồn `train_combined` vs `train_ready_mapped_drug_groups`.
- Create `data/drug_group_representatives.json`: mapping nhóm -> 2-3 hoạt chất tiêu biểu đã chuẩn hóa tiếng Việt, có nguồn từ `ten_thuoc` và cờ `manual_reviewed`.
- Create `scripts/build_drug_group_representatives.py`: sinh draft mapping từ `ten_thuoc`, dedupe/dịch/lọc đường dùng, xuất JSON để review.
- Modify `backend/app.py:1204-1259`: load thêm curated representatives, không đưa raw `raw_medication_or_treatment`/raw list dài vào output chính.
- Modify `backend/app.py:1611-1666`: thay `medication_reference_items_for_group()`/`drug_group_guidance()` để trả hoạt chất top-N sạch, giữ warning an toàn.
- Modify `backend/app.py:2485-2508`: `medication_names_for_group()` dùng cùng curated representatives, cap 2-3 thay vì 4 raw names.
- Modify `backend/app.py:2922-2998`: response thêm/chuẩn hóa field lý do, confidence/top-1/top_predictions; ẩn hoặc hạ `dataset_treatment` raw khỏi output người dùng.
- Modify `scripts/eval_vietnamese.py:21-79`: nếu cần, bổ sung per-class f1/confusion cho `data/test_vi_cases.csv` và `data/test_vi_cases_v3.csv` thay vì chỉ accuracy tổng.
- Modify `scripts/stress_test_user_cases.py:228-244`: nếu cần, lưu thêm `medications`, `top_predictions`, `quality_message` để kiểm tra output mới.

---

## PHẦN A - Retrain cho top-1 sắc hơn

### Task A1: Chụp baseline trước khi sửa

- [ ] Chạy và lưu output baseline model hiện tại:

```powershell
$env:LLM_CONTEXT_ENABLED="0"
python scripts/eval_vietnamese.py
python scripts/eval_vietnamese.py --cases data/test_vi_cases_v3.csv
python scripts/stress_test_user_cases.py
```

- [ ] Lưu lại accuracy theo loại ca, danh sách fail, `docs/stress_test_500_summary.json`, và class report hiện tại từ `models/classification_report.json`.
- [ ] Ghi rõ baseline đang dùng `models/metadata.json` rows `46587`; không được so sánh lẫn với file train mới nếu nguồn data đổi.

### Task A2: Audit dữ liệu train và lệch nguồn

- [ ] Tạo/hoàn thiện `scripts/audit_drug_group_training.py` để đọc `data/train_ready_mapped_drug_groups.csv`, `data/train_combined.csv` nếu còn tồn tại, và `models/metadata.json`.
- [ ] Report bắt buộc: số dòng, số nhóm, class counts, nhóm `<50`, nhóm `<200`, top 10 nhóm lớn, top cặp nhóm có nhiều `trieu_chung` overlap.
- [ ] Nếu `train_ready_mapped_drug_groups.csv` thật sự có `89869` dòng còn metadata model là `46587`, quyết định nguồn train mới phải được ghi vào metadata và PR notes. Không train "âm thầm" trên file khác.
- [ ] Kiểm tra nhãn gần trùng/đổi tên: ví dụ metadata có `thuốc/điều trị ung thư`, current data có thể đã đổi counts; không gộp nhãn bằng string heuristic nếu chưa audit.

### Task A3: Chiến lược nhóm hiếm, ưu tiên an toàn

- [ ] Phân loại nhóm hiếm thành 3 loại:
  - `rule-owned`: nhóm có dấu hiệu lâm sàng đặc hiệu và đang có rule an toàn, ví dụ sốt rét/thiếu máu/tuyến giáp nếu rule đủ rõ.
  - `high-risk-ask-more`: nhóm rủi ro cao hoặc quá ít mẫu như ung thư, chống đông/kháng tiểu cầu, ức chế miễn dịch; model không nên tự tin kê gợi ý khi không đủ tín hiệu.
  - `trainable-with-evidence`: nhóm có thể augment vì có mô tả triệu chứng/diagnosis rõ, không bịa y khoa.
- [ ] Với `high-risk-ask-more`, không oversample bằng câu tự chế. Giữ hoặc tăng ngưỡng `MIN_HIGH_RISK_MODEL_CONFIDENCE` tại `backend/app.py:68` và `HIGH_RISK_DRUG_GROUPS` tại `backend/app.py:69-74`; nếu top-1 thuộc nhóm này nhưng top-gap thấp thì trả `needs_more_input`.
- [ ] Với nhóm chỉ 10-28 mẫu, chọn một trong các hướng và ghi trade-off:
  - Tách khỏi model top-1 và để rule/triage hỏi thêm xử lý: giảm false positive, có thể giảm recall nhóm hiếm.
  - Gộp nhãn chỉ khi có cơ sở nghiệp vụ rõ và không làm mất cảnh báo an toàn: tăng ổn định, giảm độ chi tiết.
  - Augment có kiểm soát từ trường sẵn có (`mo_ta_benh_an`, `trieu_chung`, `chan_doan_du_kien`) bằng biến thể câu không thêm tri thức mới: tăng recall, rủi ro overfit nếu nhân bản quá nhiều.
- [ ] Không tạo dữ liệu y khoa mới kiểu "mẫu ung thư giả", không tự thêm hoạt chất/liều dùng vào train.

### Task A4: Giảm nhầm giữa nhóm chồng lấn

- [ ] Audit confusion trên split hiện tại và VN eval cho các cụm:
  - Da liễu: `thuốc kháng histamin`, `thuốc kháng nấm/ký sinh trùng ngoài da`, `thuốc corticosteroid/chống viêm`.
  - Tiêu hóa/nôn: `thuốc chống nôn`, `thuốc điều trị dạ dày`, `bù dịch và điện giải`.
  - Đau/viêm/sốt: `thuốc kháng viêm không steroid`, `thuốc giảm đau hạ sốt`, `thuốc corticosteroid/chống viêm`.
- [ ] Trong `scripts/train_model.py:150-155`, thử nghiệm có kiểm soát `ngram_range=(1,3)`, `min_df`, `max_df`, `strip_accents=None`, và text input kết hợp `trieu_chung + chan_doan_du_kien` nếu không leak nhãn nhóm trực tiếp.
- [ ] Không dùng `ten_thuoc` làm feature train chính cho prediction từ triệu chứng; field này chỉ dùng curate output.
- [ ] Giữ các rule mơ hồ trong `backend/app.py:2052-2064` (`dermatology_rule_drug_group`) và `backend/app.py:2340+` (`should_force_more_info`) làm lớp ưu tiên khi triệu chứng không đủ phân biệt.
- [ ] Thêm logic top-gap cho model path tại `backend/app.py:2766-2784`: nếu `confidence` đủ cao nhưng `top1 - top2` thấp ở cụm chồng lấn, trả `needs_more_input` hoặc hiển thị top-1 với lý do "độ tin cậy vừa phải" tùy risk. Rule path vẫn không ép top-gap.

### Task A5: Calibration và top_predictions nhất quán

- [ ] Trong `scripts/train_model.py:129-145`, giữ calibration nhưng đo chất lượng xác suất bằng Brier/ECE hoặc calibration bins; không chỉ nhìn accuracy.
- [ ] Lưu thêm metadata: `calibration_method`, `top_gap_thresholds`, `per_class_f1`, `rare_class_strategy`, `data_source_hash` trong `models/metadata.json`.
- [ ] Trong `/api/predict`, giữ `top_predictions` cho model path như hiện tại nhưng cân nhắc khi `score_type="rule"`:
  - Option an toàn: `top_predictions=[]`, thêm `score_type="rule"` và `confidence=null` như hiện tại.
  - Option nhất quán hơn: trả một item `{disease: rule_group, probability: null, source: "rule"}`. Nếu chọn option này, update eval/stress/UI parser để không hiểu nhầm là xác suất.
- [ ] Plan khuyến nghị: giữ `top_predictions=[]` cho rule để tránh giả xác suất; thêm `prediction_source`/`score_type` rõ trong response.

### Task A6: Train reproducible

- [ ] Lệnh train đề xuất sau khi chốt data:

```powershell
python scripts/train_model.py --data data/train_ready_mapped_drug_groups.csv --out models --text-column trieu_chung --target-column nhom_thuoc --test-size 0.2 --random-state 42 --features-data data/train_ready_mapped_drug_groups.csv
```

- [ ] Nếu cần thử nghiệm nhiều cấu hình, lưu ra thư mục tạm như `models/experiments/<date>-<strategy>` trước; chỉ copy vào `models/` khi VN eval/stress đạt tiêu chí.
- [ ] Giữ tương thích `feature_lookup`: metadata vẫn phải có `features` atomic từ `trieu_chung`, không bị phình bởi mô tả tự nhiên.
- [ ] Sau train, kiểm tra `models/disease_model.joblib`, `models/metadata.json`, `models/classification_report.json`, `models/mapped_drug_group_reference.json` được cập nhật đồng bộ.

### Task A7: Đánh giá thật bắt buộc

- [ ] Bổ sung hoặc ghi script phụ để tính per-class precision/recall/f1 trên:

```powershell
python scripts/eval_vietnamese.py
python scripts/eval_vietnamese.py --cases data/test_vi_cases_v3.csv
```

- [ ] Với `also_ok`, report 2 lớp số liệu: strict expected-only và accepted expected+also_ok. Per-class f1 nên dùng accepted label nhưng vẫn log strict confusion để thấy nhóm bị lẫn.
- [ ] Chạy stress:

```powershell
python scripts/stress_test_user_cases.py
```

- [ ] Tiêu chí đạt tối thiểu:
  - Accuracy VN không giảm so baseline trên cả `data/test_vi_cases.csv` và `data/test_vi_cases_v3.csv`.
  - Macro-F1 VN tăng hoặc không giảm; per-class f1 của `thuốc chống nôn` và cụm da liễu không giảm.
  - Không tăng số fail trong `stress_test_500_summary.json`.
  - Không có emergency/needs_more_input regression: ca cấp cứu vẫn `422`, `top_predictions=[]`, không thuốc.
  - Nhóm hiếm rủi ro cao không được tăng false positive; nếu không đủ dữ liệu thì ưu tiên hỏi thêm.

---

## PHẦN B - Curate output 1 nhóm + 2-3 hoạt chất sạch

### Task B1: Thiết kế contract output mới

- [ ] Response thành công `LABEL_TYPE=="drug_group"` tại `backend/app.py:2962-2998` cần có các field rõ:
  - `disease`/`disease_vi`: top-1 nhóm thuốc.
  - `display_title`: `Nhóm thuốc gợi ý: <nhóm>`.
  - `confidence`: xác suất model nếu model path, `null` nếu rule.
  - `score_type`: `probability`, `rule`, hoặc `emergency`.
  - `representative_active_ingredients`: list 2-3 item tiếng Việt đã làm sạch.
  - `reason`: câu ngắn dạng `Triệu chứng đã nhận diện (<a>, <b>) phù hợp nhất với nhóm <nhóm>.`
  - `warning`: giữ cảnh báo an toàn hiện tại.
- [ ] `medications` chỉ nên chứa 2-3 hoạt chất minh họa hoặc guidance ngắn; không còn dump 8-10 dòng raw.
- [ ] `dataset_treatment` raw tại `backend/app.py:2987` phải ẩn khỏi UI chính hoặc đổi thành debug/internal. Nếu vẫn giữ trong API vì tương thích, cap nhỏ và đặt tên rõ `raw_dataset_treatment_debug`, không render mặc định.
- [ ] Với `needs_more_input`/emergency tại `backend/app.py:2691-2702`, `2742-2753`, `2895-2920`: tuyệt đối không trả `representative_active_ingredients` và không gợi ý thuốc.

### Task B2: Sinh draft mapping nhóm -> hoạt chất từ `ten_thuoc`

- [ ] Create `scripts/build_drug_group_representatives.py` đọc `data/train_ready_mapped_drug_groups.csv`, chỉ dùng cột `ten_thuoc`, `nhom_thuoc`, `trieu_chung`, `source`.
- [ ] Thuật toán draft:
  - Normalize Unicode, trim, collapse spaces, lowercase key để dedupe nhưng giữ display chuẩn.
  - Bỏ prefix/suffix mô tả nguồn như `Thuốc trong dữ liệu:`, `Nhóm thuốc dự đoán:`.
  - Tách ví dụ trong ngoặc: `Antihistamines (e.g., Loratadine)` ưu tiên lấy `Loratadine`; nếu chỉ là class không hoạt chất thì đưa vào bucket reject.
  - Chuẩn hóa biến thể class/generic: `Antihistamines`, `Oral antihistamines`, `Antihistamine eye drops` không được coi là hoạt chất.
  - Lọc đường dùng/dạng bào chế không phù hợp khi không có hoạt chất: `eye drops`, `oral`, `topical`, `cream`, `ointment`, `tablet`, `injection`, `drops`, `syrup`, `spray`.
  - Nếu item có hoạt chất + dạng bào chế, giữ hoạt chất: `Clotrimazole cream` -> `clotrimazole`; `Hydrocortisone cream` -> `hydrocortisone`.
  - Dedupe theo canonical key không dấu/lowercase và map display tiếng Việt: `paracetamol` -> `paracetamol`, `acetaminophen` -> `paracetamol (acetaminophen)` nếu cần.
  - Rank theo frequency trong group, ưu tiên `source` sạch nếu có, loại item quá dài/generic.
  - Cap draft top 5 để reviewer chọn 2-3 cuối.
- [ ] Output draft `data/drug_group_representatives.draft.json` hoặc report markdown tạm, nhưng artifact runtime cuối cùng là `data/drug_group_representatives.json`.

### Task B3: Manual review/allowlist để đảm bảo y tế an toàn

- [ ] Tạo `data/drug_group_representatives.json` dạng:

```json
{
  "thuốc kháng histamin": {
    "active_ingredients": ["cetirizin", "loratadin", "fexofenadin"],
    "source": "ten_thuoc_frequency_plus_manual_review",
    "manual_reviewed": true
  }
}
```

- [ ] Mỗi nhóm tối đa 3 hoạt chất, tối thiểu 0 nếu không đủ an toàn. Không bịa hoạt chất cho nhóm hiếm/rủi ro cao nếu `ten_thuoc` không sạch.
- [ ] Với nhóm rủi ro cao (`thuốc/điều trị ung thư`, `thuốc chống đông/kháng tiểu cầu`, `thuốc điều hòa/ức chế miễn dịch`), cân nhắc để list rỗng hoặc chỉ hiển thị "cần bác sĩ chuyên khoa xác nhận", không đưa ví dụ gây hiểu nhầm tự dùng.
- [ ] Với ca da liễu, mapping phải tránh đường dùng sai: ca ngứa da không được hiện `Antihistamine eye drops`; chỉ hiện hoạt chất phù hợp nhóm như `cetirizin/loratadin` nếu nhóm kháng histamin.
- [ ] Với nhóm chống nôn, mapping không được trộn thuốc dạ dày/bù dịch; nếu output nhóm chống nôn thì hoạt chất minh họa chỉ từ group đó.

### Task B4: Load curated mapping trong backend

- [ ] Thêm constant path gần `DATA_SOURCE` trong `backend/app.py`: `DRUG_REPRESENTATIVES_PATH = PROJECT_ROOT / "data" / "drug_group_representatives.json"`.
- [ ] Thêm helper đề xuất quanh `backend/app.py:1204`:
  - `load_drug_representatives() -> dict[str, list[str]]`
  - `representative_active_ingredients_for_group(group: str | None, active_symptoms: set[str] | None = None, limit: int = 3) -> list[str]`
  - `safe_active_ingredient_display(name: str) -> str`
- [ ] `load_reference_data()` vẫn có thể build `references["medications"]` để tương thích, nhưng output chính không phụ thuộc raw list nữa.
- [ ] `medication_reference_items_for_group()` tại `backend/app.py:1611-1633` nên trả curated items trước; fallback raw chỉ dùng debug hoặc khi mapping thiếu và nhóm không high-risk, cap 2.
- [ ] `drug_group_guidance()` tại `backend/app.py:1636-1666` append câu dạng `Hoạt chất minh họa trong nhóm: <a>, <b>, <c>.` thay vì nhiều dòng `Thuốc trong dữ liệu: ...`.

### Task B5: Lý do triệu chứng -> nhóm

- [ ] Thêm helper quanh `case_summary()` hoặc trước `/api/predict`:
  - `prediction_reason(prediction, matched_symptom_labels, confidence, score_type) -> str`
  - Nội dung ngắn, không chẩn đoán quá mức, không nói "nên dùng".
- [ ] Với model path: `Triệu chứng đã nhận diện: <2-4 triệu chứng>. Model xếp nhóm <nhóm> cao nhất trong các nhóm thuốc đã huấn luyện.`
- [ ] Với rule path: `Triệu chứng/ngữ cảnh đặc hiệu kích hoạt rule an toàn cho nhóm <nhóm>.`
- [ ] Với top-gap thấp hoặc high-risk: không trả thuốc; đưa vào `quality_reasons`/`needs_more_input`.

### Task B6: Không phá case_summary và output cũ

- [ ] `case_summary()` tại `backend/app.py:2511-2527` giữ các field cũ nhưng `medication_name` dùng curated 2-3 hoạt chất.
- [ ] Nếu frontend đang đọc `case_summary.medication_name`, format chỉ nên là `a; b; c`, không kèm raw English route.
- [ ] `medications_en` tại `backend/app.py:2986` không nên copy raw tiếng Anh nếu output chính đã là tiếng Việt; nếu giữ vì tương thích, giá trị phải đồng bộ với curated list hoặc bỏ khỏi UI.
- [ ] Không đổi behavior khi `LABEL_TYPE != "drug_group"` nếu repo vẫn hỗ trợ mode disease cũ.

### Task B7: Verify output mới bằng Flask client

- [ ] Tạo script test hoặc chạy inline Flask client cho các ca mẫu:

```powershell
@'
import sys, json
sys.path.insert(0, "backend")
import app as A
client = A.app.test_client()
cases = [
  "Ngứa da, nổi mề đay từng mảng, không khó thở",
  "Buồn nôn, nôn nhiều sau ăn, không đau ngực",
  "Đau bụng dưới, tiểu buốt, nước tiểu đục",
  "Đau ngực dữ dội, khó thở, vã mồ hôi",
]
for text in cases:
    r = client.post("/api/predict", json={"notes": text, "symptoms": []})
    print("\\nCASE:", text)
    print(r.status_code)
    print(json.dumps(r.get_json(), ensure_ascii=False, indent=2))
'@ | python -
```

- [ ] Expected cho ca normal: chỉ 1 nhóm chính, 2-3 hoạt chất, có `reason`, có `confidence` hoặc `score_type=rule`, không có list raw dài.
- [ ] Expected cho ca emergency/needs_more_input: status `422`, không có hoạt chất, không kê thuốc, `top_predictions=[]`.
- [ ] Kiểm tra ca ngứa da không xuất hiện đường dùng mắt như `eye drops`.

---

## Kế hoạch đánh giá trước/sau

- [ ] Baseline trước khi sửa:

```powershell
$env:LLM_CONTEXT_ENABLED="0"
python scripts/eval_vietnamese.py
python scripts/eval_vietnamese.py --cases data/test_vi_cases_v3.csv
python scripts/stress_test_user_cases.py
```

- [ ] Sau mỗi thay đổi backend output nhưng trước retrain: chạy lại 3 lệnh trên để chắc output cleanup không làm regress prediction/safety.
- [ ] Sau retrain: chạy lại 3 lệnh, so sánh với baseline và report:
  - Accuracy tổng, macro-F1, weighted-F1.
  - Per-class f1 cho 24 nhóm trên split synthetic và VN cases.
  - Confusion các cụm da liễu/chống nôn/đau-viêm-sốt.
  - Số ca `needs_more_input`, số emergency, số fail stress.
- [ ] Tiêu chí release:
  - Không giảm accuracy VN trên `data/test_vi_cases.csv` và `data/test_vi_cases_v3.csv`.
  - Macro-F1 VN không giảm; nếu rare-class recall giảm thì phải chứng minh false-positive high-risk giảm và output an toàn hơn.
  - Stress 500 không tăng fail.
  - Ít nhất 5 ca Flask client thủ công chứng minh output mới không còn raw dump và không đưa đường dùng sai.

## Rủi ro và giảm thiểu

- [ ] **Giảm recall nhóm hiếm:** Do tăng ngưỡng/top-gap hoặc tách về rule. Giảm thiểu bằng report per-class trước/sau, không dùng accuracy tổng để che lỗi, và ưu tiên `needs_more_input` cho high-risk.
- [ ] **Lệch dữ liệu train:** Metadata hiện ghi 46587 dòng nhưng file current có 89869 dòng. Giảm thiểu bằng audit nguồn, hash file, lưu source/rows trong metadata.
- [ ] **Bịa/augment sai y khoa:** Không sinh tri thức mới; chỉ tạo biến thể từ text sẵn có hoặc chọn rule/ask-more.
- [ ] **Output hoạt chất gây hiểu nhầm là đơn thuốc:** Luôn ghi "hoạt chất minh họa", không liều, không chỉ định tự dùng; warning nhắc hỏi dược sĩ/bác sĩ.
- [ ] **Raw data lẫn đường dùng/sai ngữ cảnh:** Curated mapping dùng reject bucket và manual review; fallback raw bị cap/ẩn.
- [ ] **Phá lớp LLM/rule an toàn:** Không sửa thứ tự emergency/LLM safety/rule hiện tại nếu không có test chứng minh; ca `needs_more_input` và emergency không được trả hoạt chất.
- [ ] **Frontend/API compatibility:** Nếu frontend dựa vào `medications`, giữ field nhưng đổi nội dung sang curated list ngắn; raw debug đặt field khác và không render.

## Definition of Done

- [ ] `data/drug_group_representatives.json` có mapping reviewed cho các nhóm phổ biến, mỗi nhóm tối đa 3 hoạt chất tiếng Việt/chuẩn hóa.
- [ ] `/api/predict` normal trả 1 nhóm chính + 2-3 hoạt chất + lý do + độ tin cậy/cách tính; không dump raw `raw_medication_or_treatment`.
- [ ] Emergency và `needs_more_input` không gợi ý thuốc/hoạt chất.
- [ ] Model retrain có metadata reproducible, per-class report, và tương thích `feature_lookup`.
- [ ] `python scripts/eval_vietnamese.py`, `python scripts/eval_vietnamese.py --cases data/test_vi_cases_v3.csv`, `python scripts/stress_test_user_cases.py` đạt tiêu chí không-regress.
- [ ] Flask client sample xác nhận không còn output "quá chung chung và nhiều loại thuốc cho 1 vấn đề".
