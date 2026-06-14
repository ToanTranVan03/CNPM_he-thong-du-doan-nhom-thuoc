"""Gộp data templated (đã làm sạch) + data mô tả tự nhiên thành tập train cuối.

Bước:
  1. Đọc data/train_clean.csv, khử trùng (trieu_chung, nhom_thuoc) trùng nhau (bỏ hoán vị lặp).
  2. Giới hạn số dòng mỗi nhóm thuốc (--cap) để bớt áp đảo của lớp lớn; giữ trọn lớp nhỏ.
  3. Nhân bản data tự nhiên (--natural-repeat) để tăng trọng số tín hiệu ngôn ngữ tự nhiên.
  4. Nối lại, xáo trộn, xuất data/train_combined.csv.
"""
import argparse, csv, collections, random, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["mo_ta_benh_an", "trieu_chung", "chan_doan_du_kien", "ten_thuoc",
          "nhom_thuoc", "source", "raw_medication_or_treatment"]


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", default=str(ROOT / "data" / "train_clean.csv"))
    ap.add_argument("--natural", default=str(ROOT / "data" / "natural_train.csv"))
    ap.add_argument("--out", default=str(ROOT / "data" / "train_combined.csv"))
    ap.add_argument("--cap", type=int, default=3000, help="Số dòng tối đa mỗi nhóm thuốc (data templated)")
    ap.add_argument("--natural-repeat", type=int, default=3, help="Số lần nhân bản data tự nhiên")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    random.seed(args.seed)

    clean = read_csv(args.clean)
    natural = read_csv(args.natural)

    # 1. khử trùng templated theo (trieu_chung, nhom_thuoc)
    seen = set()
    dedup = []
    for r in clean:
        key = (r["trieu_chung"].strip().lower(), r["nhom_thuoc"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)

    # 2. cap mỗi lớp
    by_class = collections.defaultdict(list)
    for r in dedup:
        by_class[r["nhom_thuoc"]].append(r)
    capped = []
    for g, rows in by_class.items():
        if len(rows) > args.cap:
            rows = random.sample(rows, args.cap)
        capped.extend(rows)

    # 3. nhân bản natural
    natural_x = natural * args.natural_repeat

    combined = capped + natural_x
    random.shuffle(combined)

    # chuẩn hoá cột (một số dòng templated có thể thiếu cột mới)
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in combined:
            w.writerow({k: r.get(k, "") for k in FIELDS})

    print(f"Templated: {len(clean)} -> khử trùng {len(dedup)} -> cap/{args.cap} còn {len(capped)}")
    print(f"Natural: {len(natural)} x{args.natural_repeat} = {len(natural_x)}")
    print(f"TỔNG train_combined: {len(combined)} -> {args.out}\n")
    print("Phân bố nhóm thuốc cuối:")
    for g, n in collections.Counter(r["nhom_thuoc"] for r in combined).most_common():
        print(f"  {n:5d}  {g}")


if __name__ == "__main__":
    main()
