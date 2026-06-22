"""US22 (SCRUM-88): test API thống kê lý do không đồng ý.

DB mode: chèn vài phản hồi REJECT (kèm ghi chú) + APPROVE, gọi /api/admin/feedback-stats,
kiểm tra: số REJECT theo ngày (SCRUM-89), từ khóa lý do (SCRUM-90), nhóm bị phản đối.
Tự dọn dữ liệu test. Chạy:  python scripts/test_feedback_stats.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402

PASS = 0
FAIL = 0
ADMIN_EMAIL = "fbstats_admin@cnpm.vn"


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")


def reset_and_seed():
    with A.app.app_context():
        A.db.session.query(A.db_models.PhanHoi).delete()
        nd = A.db.session.query(A.db_models.NguoiDung).filter_by(email=ADMIN_EMAIL).first()
        if nd:
            A.db.session.delete(nd)
        A.db.session.commit()
        # admin
        admin = A.db_models.NguoiDung(ho_ten="Admin", email=ADMIN_EMAIL, vai_tro="admin")
        admin.tai_khoan = A.db_models.TaiKhoan(
            ten_dang_nhap=ADMIN_EMAIL, mat_khau_hash="x",
            session_token="ADMIN", session_expires_at=datetime.now(timezone.utc) + timedelta(days=1))
        A.db.session.add(admin)
        # feedback mẫu: 3 REJECT (2 ngày) + 1 APPROVE
        d0 = datetime.now(timezone.utc)
        d1 = d0 - timedelta(days=1)
        rows = [
            ("REJECT", "Chẩn đoán sai nhóm thuốc", "thuốc kháng sinh", d1),
            ("REJECT", "sai nhóm, thiếu cảnh báo tương tác", "thuốc kháng sinh", d1),
            ("REJECT", "liều chưa phù hợp với bệnh nhân", "thuốc giảm đau hạ sốt", d0),
            ("APPROVE", "", "thuốc kháng histamin", d0),
        ]
        for verdict, note, grp, ts in rows:
            A.db.session.add(A.db_models.PhanHoi(
                trang_thai=verdict, muc_do_hai_long=1 if verdict == "APPROVE" else 0,
                nhom_thuoc_du_doan=grp, noi_dung=note or None, thoi_gian_gui=ts))
        A.db.session.commit()


def cleanup():
    with A.app.app_context():
        A.db.session.query(A.db_models.PhanHoi).delete()
        nd = A.db.session.query(A.db_models.NguoiDung).filter_by(email=ADMIN_EMAIL).first()
        if nd:
            A.db.session.delete(nd)
        A.db.session.commit()


def main():
    if not A.DB_ENABLED:
        print("DB chưa bật — bỏ qua.")
        return 1
    reset_and_seed()
    c = A.app.test_client()

    def get(token="ADMIN", qs=""):
        h = {"Authorization": f"Bearer {token}"} if token else {}
        return c.get(f"/api/admin/feedback-stats{qs}", headers=h)

    print("== PHÂN QUYỀN ==")
    check("chưa login -> 401", get(token=None).status_code == 401)
    r = get()
    check("admin -> 200", r.status_code == 200)

    d = r.get_json()
    print("== SCRUM-89: số 'Không đồng ý' theo ngày ==")
    check("reject_total = 3", d["reject_total"] == 3, str(d["reject_total"]))
    check("approve_total = 1", d["approve_total"] == 1)
    check("reject_rate = 75.0", d["reject_rate"] == 75.0, str(d["reject_rate"]))
    check("reject_over_time có 2 ngày", len(d["reject_over_time"]) == 2, str(d["reject_over_time"]))

    print("== SCRUM-90: từ khóa lý do phổ biến ==")
    kws = {k["keyword"]: k["count"] for k in d["top_keywords"]}
    check("có từ khóa 'sai'", kws.get("sai", 0) >= 2, str(list(kws.items())[:6]))
    check("có cụm 'sai nhóm' (bigram)", "sai nhóm" in kws, str(list(kws.items())[:8]))
    check("không lẫn stopword 'thuốc'", "thuốc" not in kws)

    print("== Nhóm bị phản đối ==")
    grp = {g["group"]: g["count"] for g in d["reject_by_group"]}
    check("kháng sinh bị phản đối 2 lần", grp.get("thuốc kháng sinh") == 2, str(grp))

    print("== LỌC NGÀY (chỉ hôm nay) ==")
    today = datetime.now(timezone.utc).date().isoformat()
    d2 = get(qs=f"?from={today}&to={today}").get_json()
    check("lọc hôm nay -> reject_total = 1", d2["reject_total"] == 1, str(d2["reject_total"]))

    cleanup()
    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
