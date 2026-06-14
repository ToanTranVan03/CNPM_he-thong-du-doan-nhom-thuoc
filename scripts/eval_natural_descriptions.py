"""Đánh giá model nhóm thuốc trên MÔ TẢ BỆNH ÁN TỰ NHIÊN (held-out).

Mặc định chỉ đánh giá trên gretel TEST (212 câu, chưa từng đưa vào train) để công bằng
khi so model cũ (models/) với model mới (models_v2/).

Cách map nhãn: dataset cho nhãn BỆNH. Ta suy ra nhóm thuốc kỳ vọng bằng bảng chẩn đoán
-> nhóm thuốc (theo đa số, từ data đã làm sạch) + mapping_overrides.csv. Bệnh đánh dấu
EXCLUDE sẽ bị bỏ khỏi đánh giá.

Ví dụ:
    python scripts/eval_natural_descriptions.py --model models
    python scripts/eval_natural_descriptions.py --model models_v2
    python scripts/eval_natural_descriptions.py --model models_v2 --split all
"""
import argparse, csv, json, collections, warnings, sys
from pathlib import Path
import joblib

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "train_clean.csv"
OVERRIDES = ROOT / "data" / "mapping_overrides.csv"
TEST = ROOT / "data" / "raw" / "gretel_symptom_to_diagnosis_test.jsonl"
TRAIN = ROOT / "data" / "raw" / "gretel_symptom_to_diagnosis_train.jsonl"


def build_dx_to_group():
    m = collections.defaultdict(collections.Counter)
    with open(CLEAN, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            m[row["chan_doan_du_kien"].strip().lower()][row["nhom_thuoc"]] += 1
    grp = {dx: c.most_common(1)[0][0] for dx, c in m.items()}
    with open(OVERRIDES, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            grp[row["chan_doan_du_kien"].strip().lower()] = row["nhom_thuoc_dung"].strip()
    return grp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="models", help="Thư mục chứa disease_model.joblib")
    ap.add_argument("--split", choices=["test", "all"], default="test",
                    help="test = chỉ gretel test (held-out, mặc định); all = train+test")
    args = ap.parse_args()

    grp = build_dx_to_group()
    model = joblib.load(Path(args.model) / "disease_model.joblib")

    files = [TEST] if args.split == "test" else [TRAIN, TEST]
    data = []
    for p in files:
        with open(p, encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                data.append((d["input_text"], d["output_text"].strip().lower()))

    total = correct = skipped = 0
    per_disease = collections.defaultdict(lambda: [0, 0])
    confusion = collections.Counter()
    for text, disease in data:
        expected = grp.get(disease)
        if not expected or expected == "EXCLUDE":
            skipped += 1
            continue
        pred = model.predict([text])[0]
        total += 1
        per_disease[disease][1] += 1
        if pred == expected:
            correct += 1
            per_disease[disease][0] += 1
        else:
            confusion[(disease, expected, pred)] += 1

    print("=" * 72)
    print(f"MODEL: {args.model} | SPLIT: {args.split} ({'held-out' if args.split=='test' else 'train+test'})")
    print(f"Câu: {len(data)} | đánh giá: {total} | bỏ qua (EXCLUDE/không map): {skipped}")
    print(f">>> ACCURACY THẬT trên mô tả tự nhiên: {correct/total:.3f}  ({correct}/{total})")
    print("=" * 72)
    print("\nĐộ chính xác theo bệnh (tăng dần):")
    for dis, (c, t) in sorted(per_disease.items(), key=lambda x: x[1][0] / x[1][1]):
        print(f"  {c/t:5.2f}  {c:3d}/{t:<3d}  {dis}")
    print("\nTop 10 nhầm lẫn (bệnh: kỳ vọng -> dự đoán):")
    for (dis, exp, pred), n in confusion.most_common(10):
        print(f"  x{n:<3d} {dis}: [{exp}] -> [{pred}]")


if __name__ == "__main__":
    main()
