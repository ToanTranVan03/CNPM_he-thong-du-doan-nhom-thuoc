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
    r = client.post("/api/predict", json={"notes": text, "symptoms": []})
    if r.status_code == 422:
        return "NEEDS_MORE_INFO"
    if r.status_code != 200:
        d = r.get_json() or {}
        # 400 = không nhận diện được triệu chứng -> coi như cần thêm thông tin
        return "NEEDS_MORE_INFO" if "không nhận diện" in (d.get("error", "")) else f"ERR_{r.status_code}"
    return (r.get_json() or {}).get("disease_vi") or "NONE"


def main():
    client = A.app.test_client()
    rows = list(csv.DictReader(open(CASES, encoding="utf-8-sig")))

    by_loai = collections.defaultdict(lambda: [0, 0])
    fails = []
    correct = total = 0
    for row in rows:
        text = row["mo_ta"]
        expected = row["expected"].strip()
        also_ok = [x.strip() for x in row.get("also_ok", "").split("|") if x.strip()]
        loai = row.get("loai", "normal").strip()
        accept = {expected, *also_ok}

        pred = predict(client, text)
        ok = pred in accept
        total += 1
        by_loai[loai][1] += 1
        if ok:
            correct += 1
            by_loai[loai][0] += 1
        else:
            fails.append((row["id"], loai, text, expected, pred))

    print("=" * 74)
    print(f"BỘ TEST TIẾNG VIỆT: {total} ca")
    print(f">>> ĐỘ CHÍNH XÁC THẬT (tiếng Việt): {correct/total:.1%}  ({correct}/{total})")
    # accuracy không tính ca 'hard'
    hard = sum(1 for r in rows if r.get("loai", "").strip() == "hard")
    nonhard_ok = correct - sum(1 for _id, lo, *_ in fails if False)  # placeholder
    print("=" * 74)
    print("\nTheo loại ca:")
    for lo, (c, t) in sorted(by_loai.items()):
        print(f"  {lo:8} {c}/{t}  ({c/t:.0%})")

    print(f"\nCÁC CA SAI ({len(fails)}):")
    for cid, lo, text, exp, pred in fails:
        print(f"  #{cid:>2} [{lo}] {text[:46]:48}")
        print(f"       kỳ vọng={exp} | dự đoán={pred}")


if __name__ == "__main__":
    main()
