"""US23 (SCRUM-92): test API Top nhóm thuốc được dự đoán nhiều nhất.

DB mode: chèn ket_qua_du_doan với các nhóm khác nhau, gọi /api/admin/group-stats,
kiểm tra thứ hạng + count + percent + limit + lọc ngày. Tự dọn.
Chạy:  python scripts/test_group_stats.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402

PASS = 0
FAIL = 0
ADMIN_EMAIL = "grpstats_admin@cnpm.vn"


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
        A.db.session.query(A.db_models.LichSuDuDoan).delete()
        A.db.session.query(A.db_models.KetQuaDuDoan).delete()
        nd = A.db.session.query(A.db_models.NguoiDung).filter_by(email=ADMIN_EMAIL).first()
        if nd:
            A.db.session.delete(nd)
        A.db.session.commit()
        admin = A.db_models.NguoiDung(ho_ten="Admin", email=ADMIN_EMAIL, vai_tro="admin")
        admin.tai_khoan = A.db_models.TaiKhoan(
            ten_dang_nhap=ADMIN_EMAIL, mat_khau_hash="x",
            session_token="ADMIN", session_expires_at=datetime.now(timezone.utc) + timedelta(days=1))
        A.db.session.add(admin)
        d0 = datetime.now(timezone.utc)
        d1 = d0 - timedelta(days=1)
        # 3 kháng histamin, 2 kháng sinh, 1 giảm đau (hôm nay) ; + 1 emergency (group None -> bỏ)
        rows = [
            ("thuốc kháng histamin", d1), ("thuốc kháng histamin", d1), ("thuốc kháng histamin", d0),
            ("thuốc kháng sinh", d1), ("thuốc kháng sinh", d0),
            ("thuốc giảm đau hạ sốt", d0),
            (None, d0),
        ]
        for grp, ts in rows:
            A.db.session.add(A.db_models.KetQuaDuDoan(
                trang_thai="suggest" if grp else "emergency", nhom_thuoc_du_doan=grp, created_at=ts))
        A.db.session.commit()


def cleanup():
    with A.app.app_context():
        A.db.session.query(A.db_models.KetQuaDuDoan).delete()
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
        return c.get(f"/api/admin/group-stats{qs}", headers=h)

    print("== PHÂN QUYỀN ==")
    check("chưa login -> 401", get(token=None).status_code == 401)
    r = get()
    check("admin -> 200", r.status_code == 200)

    d = r.get_json()
    print("== SCRUM-93: đếm + xếp hạng nhóm ==")
    check("total_with_group = 6 (bỏ None)", d["total_with_group"] == 6, str(d["total_with_group"]))
    check("distinct_groups = 3", d["distinct_groups"] == 3, str(d["distinct_groups"]))
    groups = d["groups"]
    check("hạng 1 = kháng histamin (3)", groups[0]["group"] == "thuốc kháng histamin" and groups[0]["count"] == 3, str(groups[0]))
    check("percent hạng 1 = 50.0", groups[0]["percent"] == 50.0, str(groups[0]["percent"]))
    check("hạng 2 = kháng sinh (2)", groups[1]["group"] == "thuốc kháng sinh" and groups[1]["count"] == 2)
    check("xếp giảm dần theo count", [g["count"] for g in groups] == sorted([g["count"] for g in groups], reverse=True))

    print("== limit + lọc ngày ==")
    d2 = get(qs="?limit=2").get_json()
    check("limit=2 -> trả 2 nhóm", len(d2["groups"]) == 2, str(len(d2["groups"])))
    today = datetime.now(timezone.utc).date().isoformat()
    d3 = get(qs=f"?from={today}&to={today}").get_json()
    check("lọc hôm nay -> total_with_group = 3", d3["total_with_group"] == 3, str(d3["total_with_group"]))

    cleanup()
    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
