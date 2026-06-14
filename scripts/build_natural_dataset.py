"""Chuyển dataset MÔ TẢ TỰ NHIÊN (gretel train) thành dòng train cho model nhóm thuốc.

- Chỉ dùng gretel_symptom_to_diagnosis_TRAIN.jsonl (giữ TEST làm tập đánh giá thật).
- Map disease -> nhom_thuoc bằng: bảng đa số từ data đã làm sạch + mapping_overrides.csv.
- celikmus bị loại: nhãn là triệu chứng thô (cough, joint pain, feeling cold...), không map
  sạch sang nhóm thuốc -> gây nhiễu.

Xuất data/natural_train.csv đúng schema của train CSV gốc.
"""
import csv, json, collections, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "train_clean.csv"
OVERRIDES = ROOT / "data" / "mapping_overrides.csv"
GRETEL_TRAIN = ROOT / "data" / "raw" / "gretel_symptom_to_diagnosis_train.jsonl"
OUT = ROOT / "data" / "natural_train.csv"

FIELDS = ["mo_ta_benh_an", "trieu_chung", "chan_doan_du_kien", "ten_thuoc",
          "nhom_thuoc", "source", "raw_medication_or_treatment"]


def build_dx_to_group():
    m = collections.defaultdict(collections.Counter)
    with open(CLEAN, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            m[row["chan_doan_du_kien"].strip().lower()][row["nhom_thuoc"]] += 1
    grp = {dx: c.most_common(1)[0][0] for dx, c in m.items()}
    # thêm override (kể cả chẩn đoán không có sẵn trong data: arthritis, GERD, peptic ulcer)
    with open(OVERRIDES, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            grp[row["chan_doan_du_kien"].strip().lower()] = row["nhom_thuoc_dung"].strip()
    return grp


def main():
    grp = build_dx_to_group()
    rows, skipped = [], collections.Counter()
    with open(GRETEL_TRAIN, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            text = d["input_text"].strip()
            disease = d["output_text"].strip().lower()
            group = grp.get(disease)
            if not group or group == "EXCLUDE":
                skipped[disease] += 1
                continue
            rows.append({
                "mo_ta_benh_an": text,
                "trieu_chung": text,            # model train trên cột trieu_chung
                "chan_doan_du_kien": disease,
                "ten_thuoc": "",
                "nhom_thuoc": group,
                "source": "natural:gretel_train",
                "raw_medication_or_treatment": "",
            })

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f"Dòng tự nhiên tạo được: {len(rows)} -> {OUT}")
    print("Phân bố nhóm thuốc:")
    for g, n in collections.Counter(r["nhom_thuoc"] for r in rows).most_common():
        print(f"  {n:4d}  {g}")
    if skipped:
        print("\nBỏ qua (disease không map được):")
        for dx, n in skipped.items():
            print(f"  {dx}: {n}")


if __name__ == "__main__":
    main()
