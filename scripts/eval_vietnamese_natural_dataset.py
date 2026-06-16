"""Đánh giá TRUNG THỰC trên held-out tiếng Việt tự nhiên, end-to-end qua backend (A8.1).

Đọc data/natural_vi_holdout.csv (mô tả VN đã dịch + nhãn nhom_thuoc), gọi /api/predict
như người dùng thật, đo:
  - accuracy (dự đoán đúng nhom_thuoc)
  - tỷ lệ né (NEEDS_MORE_INFO) — model thiếu tự tin
  - macro-recall theo lớp + tách riêng các lớp nguy hiểm

Đổi model bằng env MODEL_DIR (backend/app.py đọc env này lúc import):
  $env:MODEL_DIR='models_retrain_vi'; python scripts/eval_vietnamese_natural_dataset.py
"""
import argparse
import collections
import csv
import json
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import app as A  # noqa: E402

HIGH_RISK = {
    "thuốc chống đông/kháng tiểu cầu", "thuốc/điều trị ung thư",
    "thuốc nội tiết tuyến giáp", "vắc-xin", "thuốc điều hòa/ức chế miễn dịch",
}


def predict(client, text):
    r = client.post("/api/predict", json={"notes": text, "symptoms": []})
    if r.status_code == 422:
        return "NEEDS_MORE_INFO"
    if r.status_code != 200:
        return f"ERR_{r.status_code}"
    return (r.get_json() or {}).get("disease_vi") or "NONE"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=Path, default=ROOT / "data" / "natural_vi_holdout.csv")
    ap.add_argument("--text-column", default="trieu_chung")
    ap.add_argument("--label-column", default="nhom_thuoc")
    ap.add_argument("--out", type=Path, default=None, help="Ghi report JSON (tuỳ chọn).")
    args = ap.parse_args()

    client = A.app.test_client()
    rows = list(csv.DictReader(open(args.cases, encoding="utf-8-sig")))

    total = correct = abstain = 0
    per_class = collections.defaultdict(lambda: [0, 0])  # group -> [đúng, tổng]
    for r in rows:
        text = r[args.text_column].strip()
        gold = r[args.label_column].strip()
        if not text or not gold:
            continue
        pred = predict(client, text)
        total += 1
        per_class[gold][1] += 1
        if pred == "NEEDS_MORE_INFO":
            abstain += 1
        elif pred == gold:
            correct += 1
            per_class[gold][0] += 1

    acc = correct / total if total else 0.0
    recalls = [c / t for c, t in per_class.values() if t]
    macro_recall = sum(recalls) / len(recalls) if recalls else 0.0
    hr = [(g, per_class[g]) for g in per_class if g in HIGH_RISK]

    print(f"MODEL_DIR = {os.environ.get('MODEL_DIR', 'models (mặc định)')}")
    print(f"Held-out VN: {total} ca")
    print(f">>> ACCURACY (đúng nhom_thuoc): {acc:.1%} ({correct}/{total})")
    print(f">>> Tỷ lệ NÉ (NEEDS_MORE_INFO): {abstain / total:.1%} ({abstain}/{total})")
    print(f">>> MACRO-RECALL theo lớp: {macro_recall:.1%} ({len(recalls)} lớp)")
    print("\nRecall theo lớp (tăng dần):")
    for g, (c, t) in sorted(per_class.items(), key=lambda x: x[1][0] / x[1][1] if x[1][1] else 0):
        flag = "  ⚠️HIGH-RISK" if g in HIGH_RISK else ""
        print(f"  {c:3d}/{t:<3d} {c / t:5.0%}  {g}{flag}")
    if hr:
        print("\nLớp nguy hiểm (theo dõi riêng):")
        for g, (c, t) in hr:
            print(f"  {c}/{t}  {g}")

    if args.out:
        report = {
            "model_dir": os.environ.get("MODEL_DIR", "models"),
            "total": total, "correct": correct, "accuracy": round(acc, 4),
            "abstain": abstain, "abstain_rate": round(abstain / total, 4) if total else 0,
            "macro_recall": round(macro_recall, 4),
            "per_class": {g: {"correct": c, "total": t} for g, (c, t) in per_class.items()},
        }
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nReport -> {args.out}")


if __name__ == "__main__":
    main()
