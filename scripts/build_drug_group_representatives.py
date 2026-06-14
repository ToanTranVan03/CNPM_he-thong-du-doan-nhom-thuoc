"""B2 (vòng 6): Sinh DRAFT mapping nhóm thuốc -> hoạt chất tiêu biểu, từ cột ten_thuoc.

Mục đích: gom/làm sạch ứng viên hoạt chất theo từng nhóm để CON NGƯỜI review chọn 2-3 cái
cuối (ghi vào data/drug_group_representatives.json). KHÔNG dùng trực tiếp output script này làm
runtime — vì xếp hạng thuần tần suất dễ sai (vd "eye drops" đứng đầu nhóm kháng histamin).

Chạy: python scripts/build_drug_group_representatives.py
Xuất:  data/drug_group_representatives.draft.json
"""
import csv
import json
import re
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "train_combined.csv"   # nguồn chuẩn (đã chốt sau audit)
OUT = ROOT / "data" / "drug_group_representatives.draft.json"

_PAREN = re.compile(r"\(([^)]*)\)")
_EG = re.compile(r"e\.?\s*g\.?\.?,?\s*", re.IGNORECASE)
_SPLIT = re.compile(r"\s*(?:,|/| or | and )\s*", re.IGNORECASE)

# Từ chỉ ĐƯỜNG DÙNG / dạng bào chế -> đánh dấu, KHÔNG phải hoạt chất.
ROUTE_WORDS = {
    "oral", "iv", "intravenous", "topical", "eye", "drops", "eye drops", "cream", "creams",
    "ointment", "ointments", "tablet", "tablets", "injection", "syrup", "spray", "nasal",
    "inhaled", "suppository", "suppositories", "patch", "gel", "lotion", "solution",
}
# Từ chỉ LỚP/NHÓM (không phải hoạt chất cụ thể).
CLASS_WORDS = {
    "antihistamine", "antihistamines", "pain", "relievers", "reliever", "analgesics", "analgesic",
    "antipyretics", "antipyretic", "antacids", "antacid", "proton", "pump", "inhibitors", "ppis", "ppi",
    "nsaids", "nsaid", "antifungal", "antifungals", "antibiotic", "antibiotics", "corticosteroid",
    "corticosteroids", "steroids", "medication", "medications", "drug", "drugs", "treatment", "agents",
    "prescription", "otc", "supplements", "vaccine", "vaccines",
}


def extract_candidates(ten_thuoc: str) -> list[tuple[str, bool]]:
    """Trả list (candidate, has_route) từ một chuỗi ten_thuoc."""
    text = ten_thuoc.strip()
    low = text.lower()
    has_route = any(w in low for w in ("eye drop", "oral", " iv", "topical", "intravenous", "nasal", "inhaled", "suppositor"))
    cands: list[str] = []

    inside = _PAREN.findall(text)
    if inside:
        for chunk in inside:
            chunk = _EG.sub("", chunk).strip()
            for part in _SPLIT.split(chunk):
                part = part.strip(" .")
                if part:
                    cands.append(part)
    else:
        base = _PAREN.sub("", text).strip(" .")
        if base:
            cands.append(base)

    out = []
    for c in cands:
        tokens = [t for t in re.split(r"\s+", c) if t]
        # bỏ token route/class ở rìa để lấy phần lõi hoạt chất
        core = [t for t in tokens if t.lower().strip(".,") not in ROUTE_WORDS]
        core_str = " ".join(core).strip()
        if not core_str:
            continue
        # nếu toàn bộ là từ lớp/nhóm -> đánh dấu là class (không phải hoạt chất)
        is_class = all(t.lower().strip(".,") in CLASS_WORDS for t in core)
        out.append((core_str, has_route, is_class))
    return [(c, r) for (c, r, is_cls) in out if not is_cls] or [(c, r) for (c, r, is_cls) in out]


def main():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    by_group: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    route_flag: dict[str, set] = collections.defaultdict(set)

    for r in rows:
        g = (r.get("nhom_thuoc") or "").strip()
        t = (r.get("ten_thuoc") or "").strip()
        if not g or not t:
            continue
        for cand, has_route in extract_candidates(t):
            key = cand.lower()
            by_group[g][cand] += 1
            if has_route:
                route_flag[g].add(key)

    draft = {}
    for g in sorted(by_group):
        items = []
        for cand, freq in by_group[g].most_common(12):
            items.append({
                "candidate": cand,
                "freq": freq,
                "has_route_form": cand.lower() in route_flag[g],
            })
        draft[g] = {"candidates": items, "chosen_vi": [], "manual_reviewed": False}

    OUT.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã ghi draft: {OUT}  ({len(draft)} nhóm)")


if __name__ == "__main__":
    main()
