"""Xuất CHI TIẾT ĐẦY ĐỦ output hệ thống cho TẤT CẢ ca trong bộ test rộng (không chỉ ca sai).

Dùng lại CASES + cấu hình Groq từ test_groq_wide. Chạy:  python scripts/groq_wide_detail.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import test_groq_wide as W  # noqa: E402  (chạy setup env Groq + import app + patch)

A = W.A


def main():
    client = A.app.test_client()
    out = []
    for i, (notes, expected, ghi) in enumerate(W.CASES, 1):
        W._captured.clear()
        r = client.post("/api/predict", json={"notes": notes, "symptoms": []})
        body = r.get_json() or {}
        llm = W._captured.get("last")
        dirn = W.classify(r.status_code, body)
        accept = expected if isinstance(expected, tuple) else (expected,)
        verdict = "ĐÚNG" if dirn in accept else "SAI"

        groq = "None"
        if llm:
            groq = (f"TC={llm.get('symptoms_vi')} | phủ định={llm.get('negated_vi')} | "
                    f"ngữ cảnh={[c['type'] for c in llm.get('contexts', [])]} | cờ đỏ={llm.get('red_flags')}")
        title = body.get("display_title") or ""
        group = (body.get("case_summary") or {}).get("drug_group") or "—"
        meds = body.get("medications") or []
        msg = body.get("error") or body.get("reason") or body.get("quality_message") or ""

        block = [
            f"#{i:<2} [{verdict}]  hướng hệ thống = {dirn}",
            f"   Nhập      : {notes}",
            f"   Groq hiểu : {groq}",
            f"   HTTP {r.status_code} · score_type={body.get('score_type')}",
            f"   Tiêu đề   : {title}",
            f"   Nhóm thuốc: {group}",
        ]
        if r.status_code == 200 and meds:
            block.append(f"   Thuốc gợi ý: {', '.join(str(m) for m in meds[:3])}")
        if msg:
            block.append(f"   Thông điệp: {msg[:240]}")
        block.append(f"   >> Hướng đúng (thực tế): {' / '.join(accept)} ({ghi})")
        out.append("\n".join(block))

    text = "\n\n".join(out)
    (ROOT / "docs" / "groq_wide_detail.txt").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
