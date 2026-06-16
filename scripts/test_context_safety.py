"""Test REGRESSION cho tầng ngữ cảnh-an toàn (backend/context_safety.py + /api/predict).

Khóa các hành vi an toàn theo NGỮ CẢNH (bệnh nền/tuổi/thai kỳ/tương tác/dị ứng/phản vệ) để
không bị regress khi sửa code sau này. Chạy: python scripts/test_context_safety.py
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import app as A  # noqa: E402

CLIENT = A.app.test_client()


def call(notes):
    r = CLIENT.post("/api/predict", json={"notes": notes, "symptoms": []})
    return r.status_code, (r.get_json() or {})


def check(name, notes, *, must_block=False, must_emergency=False, must_allergy=False,
          must_suggest=False, expect_keyword=None):
    code, j = call(notes)
    title = j.get("display_title") or ""
    err = j.get("error") or ""
    ok = True
    if must_emergency:
        ok = code == 422 and "khẩn cấp" in title.lower()
    elif must_block:
        ok = code == 422 and "cảnh báo an toàn" in title.lower()
    elif must_allergy:
        ok = code == 422 and "dị ứng thuốc" in err.lower()
    elif must_suggest:
        ok = code == 200 and "gợi ý" in title.lower()
    if expect_keyword and expect_keyword.lower() not in (title + " " + err).lower():
        ok = False
    print(f"  {'✓' if ok else '✗ FAIL'}  [{code}] {name}")
    if not ok:
        print(f"        title={title!r} err={err[:80]!r}")
    return ok


def main():
    print("=== TEST NGỮ CẢNH - AN TOÀN ===")
    results = [
        # Chống chỉ định cứng -> CHẶN
        check("NSAID × suy thận", "Ông tôi 80 tuổi, suy thận mạn, đau khớp gối nhiều", must_block=True),
        check("NSAID × loét dạ dày", "Tôi bị loét dạ dày tá tràng, đau lưng nhiều", must_block=True),
        check("NSAID × chống đông", "Tôi đang uống warfarin chống đông, giờ đau khớp gối sưng", must_block=True),
        check("Paracetamol × xơ gan", "Tôi bị xơ gan, sốt đau đầu đau người", must_block=True),
        # Cấp cứu phản vệ
        check("Phản vệ (sưng môi + khó thở)", "Ăn tôm xong sưng môi, ngứa, khó thở", must_emergency=True),
        # Dị ứng thuốc theo nhân quả
        check("Dị ứng thuốc", "Sau khi uống amoxicillin tôi nổi mề đay ngứa khắp người", must_allergy=True),
        # Thai kỳ / tuổi -> cảnh báo (422)
        check("Thai kỳ", "Tôi đang mang thai 8 tuần, sốt cao, đau nhức người", expect_keyword="mang thai"),
        check("Trẻ sơ sinh", "Con tôi 5 tháng tuổi, sốt 38.5 độ, bỏ bú", expect_keyword="nhi"),
        # KHÔNG false-positive: viêm gân (gân ≠ gan)
        check("Viêm gân (không chặn)", "Viêm gân cổ tay, đau khi cử động, sưng nhẹ", must_suggest=True),
        # Ca thường không ngữ cảnh -> vẫn gợi ý bình thường
        check("OTC thường (không context)", "Da nổi mẩn đỏ, ngứa nhiều, hắt hơi sổ mũi", must_suggest=True),
    ]
    passed = sum(results)
    print(f"\n>>> {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
