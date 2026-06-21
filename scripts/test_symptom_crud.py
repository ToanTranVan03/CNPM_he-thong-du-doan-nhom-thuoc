"""PORT toan/main: test CRUD từ điển triệu chứng (thêm/sửa/xóa).

DB mode. Tạo triệu chứng test, kiểm tra CRUD + guard, dọn (giữ nguyên 582 seed).
Chạy:  python scripts/test_symptom_crud.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402

PASS = 0
FAIL = 0
ADMIN_EMAIL = "tc_admin@cnpm.vn"
USER_EMAIL = "tc_user@cnpm.vn"
TEN = "zz trieu chung test"
TEN2 = "zz trieu chung test sua"


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS  {name}")
    else:
        FAIL += 1; print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")


def purge():
    with A.app.app_context():
        for email in (ADMIN_EMAIL, USER_EMAIL):
            nd = A.db.session.query(A.db_models.NguoiDung).filter_by(email=email).first()
            if nd:
                A.db.session.delete(nd)
        for nm in (TEN, TEN2):
            for t in A.db.session.query(A.db_models.TrieuChung).filter_by(ten_trieu_chung=nm).all():
                A.db.session.delete(t)
        A.db.session.commit()


def setup():
    purge()
    with A.app.app_context():
        exp = datetime.now(timezone.utc) + timedelta(days=1)
        for email, role, tok in [(ADMIN_EMAIL, "admin", "ADMIN"), (USER_EMAIL, "user", "USER")]:
            nd = A.db_models.NguoiDung(ho_ten=role, email=email, vai_tro=role)
            nd.tai_khoan = A.db_models.TaiKhoan(ten_dang_nhap=email, mat_khau_hash="x",
                                                session_token=tok, session_expires_at=exp)
            A.db.session.add(nd)
        A.db.session.commit()


def main():
    if not A.DB_ENABLED:
        print("DB chưa bật — bỏ qua.")
        return 1
    setup()
    c = A.app.test_client()
    HA = {"Authorization": "Bearer ADMIN"}
    HU = {"Authorization": "Bearer USER"}

    print("== CRUD triệu chứng ==")
    check("user thường tạo -> 403", c.post("/api/admin/db/trieu-chung", json={"ten": TEN}, headers=HU).status_code == 403)
    check("thiếu tên -> 400", c.post("/api/admin/db/trieu-chung", json={}, headers=HA).status_code == 400)
    cr = c.post("/api/admin/db/trieu-chung", json={"ten": TEN, "tu_khoa": "kw-test"}, headers=HA)
    check("admin tạo -> 201", cr.status_code == 201)
    ma = cr.get_json()["ma"]
    check("tạo trùng -> 409", c.post("/api/admin/db/trieu-chung", json={"ten": TEN}, headers=HA).status_code == 409)
    found = c.get(f"/api/admin/db/trieu-chung?q={TEN}", headers=HA).get_json()
    check("tìm thấy triệu chứng vừa tạo", any(t["ma"] == ma for t in found["trieu_chung"]))
    check("sửa -> 200", c.put(f"/api/admin/db/trieu-chung/{ma}", json={"ten": TEN2}, headers=HA).status_code == 200)
    after = c.get(f"/api/admin/db/trieu-chung?q={TEN2}", headers=HA).get_json()
    check("tên đã đổi", any(t["ma"] == ma and t["ten"] == TEN2 for t in after["trieu_chung"]))
    check("xóa -> 200", c.delete(f"/api/admin/db/trieu-chung/{ma}", headers=HA).status_code == 200)
    check("xóa lại -> 404", c.delete(f"/api/admin/db/trieu-chung/{ma}", headers=HA).status_code == 404)
    check("user thường xóa -> 403", c.delete("/api/admin/db/trieu-chung/1", headers=HU).status_code == 403)

    purge()
    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
