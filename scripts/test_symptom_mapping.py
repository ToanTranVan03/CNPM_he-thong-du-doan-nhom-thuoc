"""US28 (SCRUM-112): test API ánh xạ triệu chứng ↔ nhóm thuốc (theo dữ liệu train).

DB mode. Lấy 1 triệu chứng có thật ('fever'), gọi /api/admin/symptom-mapping, kiểm tra
danh sách nhóm thuốc + count + percent. Tự dọn admin test.
Chạy:  python scripts/test_symptom_mapping.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402

PASS = 0
FAIL = 0
ADMIN_EMAIL = "map_admin@cnpm.vn"


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")


def setup():
    with A.app.app_context():
        nd = A.db.session.query(A.db_models.NguoiDung).filter_by(email=ADMIN_EMAIL).first()
        if nd:
            A.db.session.delete(nd)
        admin = A.db_models.NguoiDung(ho_ten="Admin", email=ADMIN_EMAIL, vai_tro="admin")
        admin.tai_khoan = A.db_models.TaiKhoan(
            ten_dang_nhap=ADMIN_EMAIL, mat_khau_hash="x",
            session_token="ADMIN", session_expires_at=datetime.now(timezone.utc) + timedelta(days=1))
        A.db.session.add(admin)
        A.db.session.commit()
        row = A.db.session.query(A.db_models.TrieuChung).filter(
            A.db_models.TrieuChung.ten_trieu_chung.ilike("fever")).first()
        return row.ma_trieu_chung if row else None


def cleanup():
    with A.app.app_context():
        nd = A.db.session.query(A.db_models.NguoiDung).filter_by(email=ADMIN_EMAIL).first()
        if nd:
            A.db.session.delete(nd)
        A.db.session.commit()


def main():
    if not A.DB_ENABLED:
        print("DB chưa bật — bỏ qua.")
        return 1
    fever_ma = setup()
    c = A.app.test_client()

    def get(qs="", token="ADMIN"):
        h = {"Authorization": f"Bearer {token}"} if token else {}
        return c.get(f"/api/admin/symptom-mapping{qs}", headers=h)

    print("== PHÂN QUYỀN / THAM SỐ ==")
    check("chưa login -> 401", get("?ten=fever", token=None).status_code == 401)
    check("thiếu tham số -> 400", get().status_code == 400)
    check("lấy được ma của 'fever'", fever_ma is not None)

    print("== SCRUM-113/115: ánh xạ theo ?ma ==")
    d = get(f"?ma={fever_ma}").get_json()
    check("ten = fever", (d.get("ten") or "").lower() == "fever", str(d.get("ten")))
    check("total_cases > 0", d["total_cases"] > 0, str(d["total_cases"]))
    check("có >= 2 nhóm liên quan", d["distinct_groups"] >= 2, str(d["distinct_groups"]))
    groups = d["groups"]
    check("nhóm xếp giảm dần theo count", [g["count"] for g in groups] == sorted([g["count"] for g in groups], reverse=True))
    check("có 'thuốc kháng sinh'", any(g["group"] == "thuốc kháng sinh" for g in groups))
    check("percent hợp lệ (0-100, tổng ~100)", abs(sum(g["percent"] for g in groups) - 100) < 1.5, str(sum(g["percent"] for g in groups)))

    print("== Ánh xạ theo ?ten + ca lạ ==")
    d2 = get("?ten=fever").get_json()
    check("?ten=fever khớp ?ma", d2["total_cases"] == d["total_cases"])
    d3 = get("?ten=trieuchunglakhongtontai999").get_json()
    check("triệu chứng lạ -> 0 nhóm", d3["distinct_groups"] == 0 and d3["total_cases"] == 0)

    cleanup()
    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
