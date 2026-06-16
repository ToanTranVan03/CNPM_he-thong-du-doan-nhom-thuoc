"""Chấm điểm chất lượng THẬT bằng tiếng Việt qua đúng pipeline backend (/api/predict).

Đọc data/test_vi_cases.csv (mô tả VN + nhãn nhóm thuốc đúng), gọi backend như người
dùng thật, so kết quả. Đây là phép đo đầu tiên trên đúng ngôn ngữ hệ thống phải phục vụ.

Quy ước:
- loai=safety/vague: ĐÚNG nếu hệ thống trả "cần thêm thông tin" (HTTP 422 / needs_more_input).
- loai=normal/hard: ĐÚNG nếu nhóm dự đoán nằm trong {expected} ∪ also_ok.

Chạy: python scripts/eval_vietnamese.py
"""
import argparse, csv, sys, warnings, collections
from pathlib import Path

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import app as A  # noqa: E402

_ap = argparse.ArgumentParser()
_ap.add_argument("--cases", default=str(ROOT / "data" / "test_vi_cases.csv"))
CASES = Path(_ap.parse_args().cases)


def predict(client, text):
    """Trả (pred, suggested_group). suggested_group = nhóm hệ nhận diện khi NÉ thuốc kê đơn
    (đã gồm rule + tầng #1), None nếu không có."""
    r = client.post("/api/predict", json={"notes": text, "symptoms": []})
    j = r.get_json() or {}
    if r.status_code == 422:
        return "NEEDS_MORE_INFO", j.get("suggested_group")
    if r.status_code != 200:
        pred = "NEEDS_MORE_INFO" if "không nhận diện" in (j.get("error", "")) else f"ERR_{r.status_code}"
        return pred, None
    return (j.get("disease_vi") or "NONE"), None


def model_top1_group(text: str) -> str | None:
    """Fallback: nhóm top-1 model thô (chỉ dùng khi hệ KHÔNG nêu suggested_group)."""
    order = A.ordered_symptoms_from_text(text)
    if not order:
        return None
    inputs = A.model_input_candidates(order)
    if hasattr(A.model, "predict_proba"):
        return A.ranked_proba(inputs)[0][0]
    return A.model.predict([inputs[0]])[0]


def main():
    client = A.app.test_client()
    rows = list(csv.DictReader(open(CASES, encoding="utf-8-sig")))

    by_loai = collections.defaultdict(lambda: [0, 0])
    recommend_ok = identify_ok = total = 0
    safe_defers = []   # né nhóm kê đơn nhưng model NHẬN ĐÚNG nhóm -> hành vi an toàn ĐÚNG
    genuine_miss = []  # sai thật (gợi ý sai nhóm, hoặc né mà model cũng nhận sai)
    for row in rows:
        text = row["mo_ta"]
        expected = row["expected"].strip()
        also_ok = [x.strip() for x in row.get("also_ok", "").split("|") if x.strip()]
        loai = row.get("loai", "normal").strip()
        accept = {expected, *also_ok}

        pred, suggested = predict(client, text)
        rec_ok = pred in accept
        total += 1
        by_loai[loai][1] += 1
        if rec_ok:
            recommend_ok += 1
            identify_ok += 1
            by_loai[loai][0] += 1
            continue

        # Né (NEEDS_MORE): hệ có nhận ĐÚNG nhóm không? Ưu tiên suggested_group (gồm rule + #1),
        # fallback model thô khi hệ không nêu nhóm (vd nhóm "không bao giờ gợi ý").
        sys_id = suggested if suggested else (model_top1_group(text) if pred == "NEEDS_MORE_INFO" else None)
        identified = sys_id in accept
        if identified:
            identify_ok += 1
            if A.is_high_risk_group(expected):
                safe_defers.append((row["id"], loai, text, expected, sys_id))
            else:
                genuine_miss.append((row["id"], loai, text, expected, f"NÉ (hệ nghĩ {sys_id}, lẽ ra gợi ý)"))
        else:
            genuine_miss.append((row["id"], loai, text, expected, pred if pred != "NEEDS_MORE_INFO" else f"NÉ (hệ nghĩ {sys_id})"))

    print("=" * 74)
    print(f"BỘ TEST TIẾNG VIỆT: {total} ca")
    print(f">>> ĐỘ CHÍNH XÁC GỢI Ý (recommend): {recommend_ok/total:.1%}  ({recommend_ok}/{total})")
    print(f"    (= hệ trực tiếp gợi ý đúng nhóm; NÉ nhóm kê đơn bị tính là chưa gợi ý)")
    print(f">>> ĐỘ CHÍNH XÁC NHẬN DIỆN (identification): {identify_ok/total:.1%}  ({identify_ok}/{total})")
    print(f"    (= recommend đúng + né-an-toàn-ĐÚNG-nhóm; gồm rule + tầng #1, phản ánh năng lực hệ thật)")
    print(f">>> NÉ AN TOÀN đúng nhóm (thuốc kê đơn): {len(safe_defers)} ca — hành vi ĐÚNG, không phải lỗi")
    print("=" * 74)
    print("\nTheo loại ca (recommend):")
    for lo, (c, t) in sorted(by_loai.items()):
        print(f"  {lo:8} {c}/{t}  ({c/t:.0%})")

    if safe_defers:
        print(f"\nNÉ AN TOÀN — model nhận ĐÚNG nhóm kê đơn rồi chuyển khám ({len(safe_defers)}):")
        for cid, lo, text, exp, top1 in safe_defers:
            print(f"  #{cid:>2} [{lo}] {text[:44]:46} → {exp}")

    print(f"\nSAI THẬT cần xem ({len(genuine_miss)}):")
    for cid, lo, text, exp, pred in genuine_miss:
        print(f"  #{cid:>2} [{lo}] {text[:44]:46}")
        print(f"       kỳ vọng={exp} | {pred}")


if __name__ == "__main__":
    main()
