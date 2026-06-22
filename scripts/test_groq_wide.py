"""BẢNG TEST RỘNG — Groq LLM hiểu câu hỏi + hệ thống trả kết quả gì, đối chiếu THỰC TẾ.

Bật Groq (LLM_CONTEXT_ENABLED=1, đọc LLM_* từ .env). Mỗi ca: chạy /api/predict (LLM hỗ trợ
hiểu ngữ cảnh), bắt ĐÚNG ngữ cảnh Groq trả, phân loại HƯỚNG hệ thống, so HƯỚNG ĐÚNG -> ĐÚNG/SAI.
KHÔNG dùng %/độ tin cậy để chấm — chỉ xét bản chất hướng xử trí.

Xuất: docs/groq_wide_results.csv + .md + .html. Chạy:  python scripts/test_groq_wide.py
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# nạp LLM_* từ .env + bật LLM context TRƯỚC khi import app
for _l in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    _l = _l.strip()
    if _l and not _l.startswith("#") and "=" in _l:
        _k, _v = _l.split("=", 1)
        if _k.strip().startswith("LLM_"):
            os.environ[_k.strip()] = _v.strip().strip('"').strip("'")
os.environ["LLM_CONTEXT_ENABLED"] = "1"
os.environ["DB_DISABLED"] = "1"  # test logic, không ghi lịch sử DB

sys.path.insert(0, str(ROOT / "backend"))
import app as A          # noqa: E402
import llm_context as LC  # noqa: E402

# Patch để BẮT đúng ngữ cảnh mà predict dùng (1 call Groq/ca).
_captured = {}
_orig = LC.extract_context
def _wrap(notes):
    r = _orig(notes)
    _captured["last"] = r
    return r
LC.extract_context = _wrap

# ── HƯỚNG (category) ─────────────────────────────────────────────────────────
EMERGENCY = "CẤP CỨU"
SAFETY = "NÉ AN TOÀN (cần bác sĩ)"
OTC = "GỢI Ý OTC"
INSUFFICIENT = "CHƯA ĐỦ DỮ LIỆU"

# Mỗi ca: (mô tả nhập, HƯỚNG ĐÚNG kỳ vọng, ghi chú lâm sàng)
CASES = [
    ("Bệnh nhân vừa va đập đầu vào tường, giờ nhức đầu dữ dội và nôn, không sốt", EMERGENCY, "Chấn thương đầu"),
    ("Đột nhiên đau thắt ngực lan ra tay trái, vã mồ hôi, khó thở", EMERGENCY, "Nghi nhồi máu cơ tim"),
    ("Ăn tôm xong sưng môi, nổi mề đay và bắt đầu khó thở", EMERGENCY, "Phản vệ"),
    ("Dạo này chán sống, mệt mỏi, có ý nghĩ muốn tự tử", EMERGENCY, "Khủng hoảng/tự hại"),
    ("Tự nhiên méo miệng, yếu nửa người bên phải, nói đớ", EMERGENCY, "Nghi đột quỵ"),
    ("Đi ngoài phân đen như bã cà phê, nôn ra ít máu, chóng mặt", EMERGENCY, "Xuất huyết tiêu hóa"),
    ("Lên cơn co giật toàn thân, sùi bọt mép, lơ mơ sau cơn", EMERGENCY, "Co giật"),
    ("Tôi bị đau đầu, sổ mũi, hắt hơi mấy hôm nay", OTC, "Cảm thường - OTC"),
    ("Nổi mề đay ngứa khắp người sau khi ăn hải sản, không khó thở", OTC, "Dị ứng nhẹ - kháng histamin"),
    ("Hơi rát họng với sổ mũi nhẹ tí thôi, người vẫn khỏe", OTC, "Khẩu ngữ - OTC nhẹ"),
    ("Sốt cao 39 độ, ho khạc đờm vàng đặc, đau tức ngực khi ho", SAFETY, "Nghi nhiễm khuẩn - kháng sinh kê đơn"),
    ("Tiểu buốt, tiểu rắt, nước tiểu đục, đau bụng dưới", SAFETY, "Nhiễm khuẩn tiết niệu - kê đơn"),
    ("Em bị sốt nhẹ, đang có bé trong bụng 3 tháng", SAFETY, "Thai kỳ - thận trọng thuốc"),
    ("Đau nhức khớp gối nhiều, mà tôi đang bị suy thận", SAFETY, "NSAID chống chỉ định suy thận"),
    ("Đang uống thuốc chống đông máu, giờ đau đầu muốn uống giảm đau", SAFETY, "Tương tác - tránh NSAID"),
    ("Đau đầu, buồn nôn sau khi nhậu say tối qua", SAFETY, "Ngữ cảnh rượu - thận trọng paracetamol"),
    ("Chạy bộ ngoài nắng về thấy chóng mặt, mệt lả, khát nước", OTC, "Say nắng nhẹ - bù nước ORS (OTC hợp lệ)"),
    ("Tiêu chảy nhiều lần, khát nhiều, tiểu ít, người lừ đừ", EMERGENCY, "Mất nước nặng"),
    ("Sốt nhẹ thôi, không ho, không khó thở, không đau họng", OTC, "Phủ định nhiều - sốt đơn thuần OTC"),
    ("Người mệt mệt khó tả, không rõ triệu chứng gì", (SAFETY, INSUFFICIENT), "Mơ hồ - cần hỏi thêm/đi khám"),
    # ── Mở rộng: ca KHÓ (khẩu ngữ/viết tắt, phủ định bẫy, ngữ cảnh, nhi/lão, từ dọa) ──
    ("Bị sốt với đau mỏi ng, hắt xì liên tục, chảy nc mũi 2 hôm nay", OTC, "Khẩu ngữ/viết tắt - cảm OTC"),
    ("Không phải đau ngực đâu, chỉ hơi tức nhẹ lúc hít sâu thôi", (OTC, SAFETY, INSUFFICIENT), "Phủ định đau ngực - KHÔNG được báo cấp cứu giả"),
    ("Sau khi uống thuốc kháng sinh xong nổi mẩn ngứa khắp người, không khó thở", (OTC, SAFETY), "Dị ứng thuốc nhẹ"),
    ("Bé 8 tháng tuổi sốt cao 39 độ, lên cơn co giật", EMERGENCY, "Sốt cao co giật trẻ nhỏ"),
    ("Ông tôi tự nhiên khó thở dữ dội, tím môi tím tái", EMERGENCY, "Suy hô hấp/tím tái"),
    ("Đầu đau như búa bổ, đột ngột, nặng nhất từ trước tới nay", EMERGENCY, "Đau đầu sét đánh"),
    ("Tiêu chảy 2 hôm nhưng vẫn ăn uống bình thường, người không mệt", OTC, "Tiêu chảy nhẹ - ORS OTC"),
    ("Đau lưng âm ỉ mấy hôm, mà em đang mang thai 5 tháng", SAFETY, "Thai kỳ - thận trọng thuốc"),
    ("Bị bỏng nước sôi ở cẳng tay, phồng rộp lên", (EMERGENCY, SAFETY), "Bỏng - cần xử trí y tế"),
    ("Tôi thấy hơi mệt với chán ăn, chắc bị ung thư rồi", (INSUFFICIENT, SAFETY), "Lo âu/mơ hồ - cần hỏi thêm"),
    # ── Mở rộng đợt 2: ca biên/đối kháng (sản khoa, quá liều, lão, nhi, bệnh nền, khẩu ngữ vùng) ──
    ("Có thai 7 tháng, đau đầu dữ dội, nhìn mờ, phù hai chân", EMERGENCY, "Tiền sản giật"),
    ("Lỡ uống cả vỉ paracetamol một lúc cho nhanh khỏi", EMERGENCY, "Quá liều paracetamol"),
    ("Tiêm vaccine xong choáng váng, nổi mẩn đỏ và khó thở", EMERGENCY, "Phản vệ sau tiêm"),
    ("Không thiết sống nữa, thấy mọi thứ vô nghĩa", EMERGENCY, "Ý định tự hại"),
    ("Cụ bà 80 tuổi tự nhiên lú lẫn, nói nhảm, sốt nhẹ", (EMERGENCY, SAFETY), "Lão - lú lẫn cấp nghi nhiễm khuẩn"),
    ("Trẻ 2 tuổi tiêu chảy, mắt trũng, khóc không có nước mắt, li bì", EMERGENCY, "Mất nước nặng trẻ nhỏ"),
    ("Khát nước liên tục, tiểu nhiều, sụt cân nhanh mấy tuần", SAFETY, "Nghi đái tháo đường - kê đơn"),
    ("Mất ngủ kéo dài nhiều tuần, lo âu, hồi hộp, bồn chồn", SAFETY, "Tâm thần kinh - kê đơn"),
    ("Đang uống thuốc huyết áp, dạo này ho khan nhiều", (SAFETY, OTC), "Tác dụng phụ ACE - hỏi bác sĩ"),
    ("Đau bụng dữ dội vùng thượng vị, nôn, lan ra sau lưng", (EMERGENCY, SAFETY), "Nghi viêm tụy - khám gấp"),
    ("Nuốt nghẹn tăng dần, sụt cân, hay nôn ói", SAFETY, "Cờ đỏ tiêu hóa - đi khám tầm soát (KHÔNG phải cấp cứu)"),
    ("Tau bị đau bụng quằn quại với đi cầu lỏng cả ngày", (OTC, SAFETY), "Khẩu ngữ vùng - tiêu hóa"),
    ("Muỗi đốt sưng đỏ ngứa một nốt ở tay", OTC, "Côn trùng đốt nhẹ - OTC"),
    ("Ngã xe trẹo cổ chân, sưng đau, đi lại được", (OTC, SAFETY), "Chấn thương chi nhẹ"),
    ("Ho đờm xanh, sốt rét run từng cơn 3 ngày nay", SAFETY, "Nhiễm khuẩn - kháng sinh kê đơn"),
    ("Đau nửa đầu kèm sợ ánh sáng, buồn nôn, từng bị nhiều lần", (OTC, SAFETY), "Migraine tái diễn"),
    ("Đau mắt đỏ, cộm, ghèn nhiều một bên", (OTC, SAFETY), "Viêm kết mạc"),
    ("Sốt cao liên tục 4 ngày, đau hốc mắt, phát ban, chảy máu chân răng", (EMERGENCY, SAFETY), "Nghi sốt xuất huyết nặng"),
    ("Tê bì hai bàn chân kéo dài, châm chích, có tiểu đường", SAFETY, "Đau thần kinh ngoại biên ĐTĐ"),
    ("Bình thường thôi, chỉ hỏi cho biết vậy", INSUFFICIENT, "Không có triệu chứng"),
]


def classify(status, body):
    if status == 422 and body.get("score_type") == "emergency":
        return EMERGENCY
    if status == 422:
        return SAFETY
    if status == 200:
        return OTC
    return INSUFFICIENT


def short_group(body):
    cs = (body.get("case_summary") or {}).get("drug_group") or ""
    return cs if cs and not cs.startswith("Chưa") else ""


def main():
    client = A.app.test_client()
    rows = []
    n_dung = 0
    print(f"Chạy {len(CASES)} ca với Groq ({os.environ.get('LLM_MODEL')})...\n")
    for i, (notes, expected, ghi_chu) in enumerate(CASES, 1):
        _captured.clear()
        r = client.post("/api/predict", json={"notes": notes, "symptoms": []})
        body = r.get_json() or {}
        llm = _captured.get("last")
        direction = classify(r.status_code, body)
        title = body.get("display_title") or body.get("error") or ""
        group = short_group(body)
        accept = expected if isinstance(expected, tuple) else (expected,)
        verdict = "ĐÚNG" if direction in accept else "SAI"
        if verdict == "ĐÚNG":
            n_dung += 1
        llm_txt = "LLM None"
        if llm:
            parts = []
            if llm.get("symptoms_vi"): parts.append("TC: " + ", ".join(llm["symptoms_vi"]))
            if llm.get("negated_vi"): parts.append("Phủ định: " + ", ".join(llm["negated_vi"]))
            if llm.get("contexts"): parts.append("Ngữ cảnh: " + ", ".join(c["type"] for c in llm["contexts"]))
            if llm.get("red_flags"): parts.append("Cờ đỏ: " + ", ".join(llm["red_flags"]))
            llm_txt = " | ".join(parts) if parts else "(rỗng)"
        rows.append({
            "stt": i, "nhap": notes, "llm": llm_txt,
            "huong_he_thong": direction + (f" — {group}" if group else ""),
            "tieu_de": title[:90],
            "huong_dung": f"{' / '.join(accept)} ({ghi_chu})",
            "verdict": verdict,
        })
        print(f"  [{verdict}] #{i} {direction:30s} | {notes[:42]}")

    # CSV
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    import csv as _csv
    with (docs / "groq_wide_results.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=["stt", "nhap", "llm", "huong_he_thong", "tieu_de", "huong_dung", "verdict"])
        w.writeheader(); w.writerows(rows)

    # HTML (để chụp)
    th = "".join(f"<th>{h}</th>" for h in ["#", "Câu nhập", "Groq hiểu", "Hệ thống trả (hướng)", "Tiêu đề hệ thống", "Hướng ĐÚNG (thực tế)", ""])
    trs = ""
    for r in rows:
        color = "#1b8a5a" if r["verdict"] == "ĐÚNG" else "#c0392b"
        trs += (f"<tr><td>{r['stt']}</td><td>{r['nhap']}</td><td class='llm'>{r['llm']}</td>"
                f"<td>{r['huong_he_thong']}</td><td class='small'>{r['tieu_de']}</td>"
                f"<td>{r['huong_dung']}</td><td style='color:{color};font-weight:700'>{r['verdict']}</td></tr>")
    html = f"""<!doctype html><html><head><meta charset='utf-8'><style>
    body{{font-family:Inter,Arial,sans-serif;background:#0c1420;color:#e6edf5;padding:24px}}
    h1{{margin:0 0 4px}} .sub{{color:#9daaba;margin:0 0 16px}}
    table{{border-collapse:collapse;width:100%;font-size:13px}}
    th,td{{border:1px solid #243349;padding:8px 10px;text-align:left;vertical-align:top}}
    th{{background:#16304d}} td.llm{{color:#8fd6ff;max-width:280px}} td.small{{color:#9daaba;font-size:11px}}
    tr:nth-child(even){{background:#101b2b}}
    </style></head><body>
    <h1>Bảng test rộng — Groq LLM hiểu câu & hệ thống trả kết quả (đối chiếu thực tế)</h1>
    <p class='sub'>Model: {os.environ.get('LLM_MODEL')} · {len(CASES)} ca · ĐÚNG {n_dung}/{len(CASES)} · chấm theo BẢN CHẤT hướng xử trí (không dùng %).</p>
    <table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></body></html>"""
    (docs / "groq_wide_results.html").write_text(html, encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"ĐÚNG {n_dung}/{len(CASES)} ca theo hướng xử trí thực tế")
    print(f"Xuất: docs/groq_wide_results.csv / .html")
    # liệt kê ca SAI
    sai = [r for r in rows if r["verdict"] == "SAI"]
    if sai:
        print(f"\nCA LỆCH HƯỚNG ({len(sai)}):")
        for r in sai:
            print(f"  #{r['stt']} nhập: {r['nhap'][:50]}")
            print(f"      hệ thống: {r['huong_he_thong']}  |  đúng: {r['huong_dung']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
