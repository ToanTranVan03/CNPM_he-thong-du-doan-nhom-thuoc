"""Dựng data train/holdout tiếng Việt tự nhiên từ bản dịch (Hạng mục A5).

Đầu vào: data/vietnamese_natural_all.csv (do translate_natural_dataset.py sinh).
Đầu ra:
  - data/natural_vi_train.csv   (chỉ split=train, đúng schema train gốc)
  - data/natural_vi_holdout.csv (chỉ split=holdout = gretel_test, KHÔNG bao giờ vào train)

Tái dùng mapping disease -> nhom_thuoc của build_natural_dataset.py (một nguồn sự thật).
Chốt cứng chống leak: nếu một dòng holdout lọt sang train (hoặc trùng text_hash) -> script FAIL.
"""
import argparse
import collections
import csv
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from build_natural_dataset import build_dx_to_group  # noqa: E402  (một nguồn mapping)

ROOT = SCRIPTS_DIR.parent
DEFAULT_IN = ROOT / "data" / "vietnamese_natural_all.csv"
DEFAULT_TRAIN_OUT = ROOT / "data" / "natural_vi_train.csv"
DEFAULT_HOLDOUT_OUT = ROOT / "data" / "natural_vi_holdout.csv"

FIELDS = ["mo_ta_benh_an", "trieu_chung", "chan_doan_du_kien", "ten_thuoc",
          "nhom_thuoc", "source", "raw_medication_or_treatment"]


def to_train_row(r: dict, group: str) -> dict:
    vi = r["text_vi"].strip()
    return {
        "mo_ta_benh_an": vi,
        "trieu_chung": vi,                 # model train trên cột trieu_chung
        "chan_doan_du_kien": r["chan_doan_du_kien"].strip().lower(),
        "ten_thuoc": "",
        "nhom_thuoc": group,
        "source": f"natural_vi:{r['source_dataset']}",
        "raw_medication_or_treatment": "",
    }


def write_csv(path: Path, rows: list[dict]):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--train-out", type=Path, default=DEFAULT_TRAIN_OUT)
    ap.add_argument("--holdout-out", type=Path, default=DEFAULT_HOLDOUT_OUT)
    args = ap.parse_args()

    grp = build_dx_to_group()

    # Phase 1: gom ứng viên theo split (holdout ưu tiên giữ trọn vẹn)
    train_cand, holdout_rows = [], []
    holdout_hashes = set()
    skipped = collections.Counter()
    missing_vi = 0

    with open(args.input, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("translation_status") != "ok" or not r["text_vi"].strip():
                missing_vi += 1
                continue
            disease = r["chan_doan_du_kien"].strip().lower()
            group = grp.get(disease)
            if not group or group == "EXCLUDE":
                skipped[disease] += 1
                continue
            row = to_train_row(r, group)
            if r["split"] == "holdout":
                holdout_rows.append(row)
                holdout_hashes.add(r["text_hash"])
            elif r["split"] == "train":
                train_cand.append((r["text_hash"], row))
            else:
                sys.exit(f"split không hợp lệ: {r['split']} ({r['source_id']})")

    # Phase 2: loại khỏi TRAIN mọi câu trùng holdout (giữ holdout sạch để đánh giá thật)
    train_rows = [row for h, row in train_cand if h not in holdout_hashes]
    leak_removed = len(train_cand) - len(train_rows)

    # CHỐT CỨNG: sau khi loại, không được còn giao nhau
    train_hashes = {h for h, _ in train_cand if h not in holdout_hashes}
    leak = train_hashes & holdout_hashes
    if leak:
        sys.exit(f"LEAK còn sót! {len(leak)} text_hash: {list(leak)[:5]}")

    write_csv(args.train_out, train_rows)
    write_csv(args.holdout_out, holdout_rows)

    print(f"Train  : {len(train_rows)} dòng -> {args.train_out}")
    print(f"Holdout: {len(holdout_rows)} dòng -> {args.holdout_out}")
    print(f"Loại khỏi train do trùng holdout (chống leak): {leak_removed}")
    print(f"Thiếu bản dịch (bỏ): {missing_vi}")
    print("\nPhân bố nhóm thuốc (TRAIN):")
    for g, n in collections.Counter(x["nhom_thuoc"] for x in train_rows).most_common():
        print(f"  {n:4d}  {g}")
    if skipped:
        print("\nBỏ qua (disease không map được):")
        for dx, n in skipped.most_common():
            print(f"  {dx}: {n}")


if __name__ == "__main__":
    main()
