"""Sửa mapping chẩn đoán -> nhóm thuốc bị sai trong data gốc.

Đọc data/train_ready_mapped_drug_groups.csv, áp dụng data/mapping_overrides.csv
(khớp theo chan_doan_du_kien, không phân biệt hoa thường) để ghi đè cột nhom_thuoc,
rồi xuất data/train_clean.csv.
"""
import argparse, csv, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]


def load_overrides(path: Path) -> dict[str, str]:
    ov = {}
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            ov[row["chan_doan_du_kien"].strip().lower()] = row["nhom_thuoc_dung"].strip()
    return ov


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(ROOT / "data" / "train_ready_mapped_drug_groups.csv"))
    ap.add_argument("--overrides", default=str(ROOT / "data" / "mapping_overrides.csv"))
    ap.add_argument("--out", default=str(ROOT / "data" / "train_clean.csv"))
    args = ap.parse_args()

    ov = load_overrides(Path(args.overrides))
    changed = {}
    excluded = {}
    rows = []
    with open(args.inp, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        for row in reader:
            dx = row["chan_doan_du_kien"].strip().lower()
            if ov.get(dx) == "EXCLUDE":
                excluded[dx] = excluded.get(dx, 0) + 1
                continue
            if dx in ov and row["nhom_thuoc"] != ov[dx]:
                row["nhom_thuoc"] = ov[dx]
                changed[dx] = changed.get(dx, 0) + 1
            rows.append(row)

    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"Tổng dòng: {len(rows)} -> {args.out}")
    print(f"Override khả dụng: {len(ov)}")
    if changed:
        print("Đã sửa nhãn cho các chẩn đoán:")
        for dx, n in sorted(changed.items()):
            print(f"  {dx}: {n} dòng -> {ov[dx]}")
    else:
        print("Không có dòng nào bị đổi (các override có thể không xuất hiện trong data).")
    if excluded:
        print("Đã loại (EXCLUDE):")
        for dx, n in sorted(excluded.items()):
            print(f"  {dx}: {n} dòng")


if __name__ == "__main__":
    main()
