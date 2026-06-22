"""US29 (SCRUM-116): test API bệnh án mẫu — list (user) + create/delete (admin).

DB mode. Tạo admin + user test, thử CRUD, dọn sạch (giữ nguyên 5 mẫu seed).
Chạy:  python scripts/test_benh_an_mau.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402

PASS = 0
FAIL = 0
ADMIN_EMAIL = "bam_admin@cnpm.vn"
USER_EMAIL = "bam_user@cnpm.vn"
TEST_TITLE = "ZZ Test Mẫu xóa được"


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
        for email in (ADMIN_EMAIL, USER_EMAIL):
            nd = A.db.session.query(A.db_models.NguoiDung).filter_by(email=email).first()
            if nd:
                A.db.session.delete(nd)
        A.db.session.query(A.db_models.BenhAnMau).filter_by(tieu_de=TEST_TITLE).delete()
        exp = datetime.now(timezone.utc) + timedelta(days=1)
        for email, role, tok in [(ADMIN_EMAIL, "admin", "ADMIN"), (USER_EMAIL, "user", "USER")]:
            nd = A.db_models.NguoiDung(ho_ten=role, email=email, vai_tro=role)
            nd.tai_khoan = A.db_models.TaiKhoan(ten_dang_nhap=email, mat_khau_hash="x",
                                                session_token=tok, session_expires_at=exp)
            A.db.session.add(nd)
        A.db.session.commit()


def cleanup():
    with A.app.app_context():
        for email in (ADMIN_EMAIL, USER_EMAIL):
            nd = A.db.session.query(A.db_models.NguoiDung).filter_by(email=email).first()
            if nd:
                A.db.session.delete(nd)
        A.db.session.query(A.db_models.BenhAnMau).filter_by(tieu_de=TEST_TITLE).delete()
        A.db.session.commit()


def main():
    if not A.DB_ENABLED:
        print("DB chưa bật — bỏ qua.")
        return 1
    setup()
    c = A.app.test_client()
    H_ADMIN = {"Authorization": "Bearer ADMIN"}
    H_USER = {"Authorization": "Bearer USER"}

    print("== SCRUM-118: danh sách (cần đăng nhập) ==")
    check("chưa login -> 401", c.get("/api/benh-an-mau").status_code == 401)
    r = c.get("/api/benh-an-mau", headers=H_USER)
    check("user thường xem được list -> 200", r.status_code == 200)
    base_n = len(r.get_json()["benh_an_mau"])
    check("có >= 5 mẫu (đã seed)", base_n >= 5, str(base_n))
    check("mỗi mẫu có tieu_de + noi_dung", all("tieu_de" in s and "noi_dung" in s for s in r.get_json()["benh_an_mau"]))

    print("== SCRUM-116: thêm (admin) ==")
    check("user thường POST -> 403", c.post("/api/admin/benh-an-mau", json={"tieu_de": "x", "noi_dung": "y"}, headers=H_USER).status_code == 403)
    check("thiếu nội dung -> 400", c.post("/api/admin/benh-an-mau", json={"tieu_de": "x"}, headers=H_ADMIN).status_code == 400)
    cr = c.post("/api/admin/benh-an-mau", json={"tieu_de": TEST_TITLE, "noi_dung": "sốt ho test", "mo_ta": "test"}, headers=H_ADMIN)
    check("admin thêm -> 201", cr.status_code == 201, str(cr.status_code))
    new_ma = cr.get_json()["benh_an_mau"]["ma"]
    after = c.get("/api/benh-an-mau", headers=H_USER).get_json()["benh_an_mau"]
    check("list tăng 1", len(after) == base_n + 1)
    check("mẫu mới có trong list", any(s["ma"] == new_ma for s in after))

    print("== SCRUM-116: xóa (admin) ==")
    check("user thường DELETE -> 403", c.delete(f"/api/admin/benh-an-mau/{new_ma}", headers=H_USER).status_code == 403)
    check("admin xóa -> 200", c.delete(f"/api/admin/benh-an-mau/{new_ma}", headers=H_ADMIN).status_code == 200)
    check("xóa rồi -> 404", c.delete(f"/api/admin/benh-an-mau/{new_ma}", headers=H_ADMIN).status_code == 404)
    final = c.get("/api/benh-an-mau", headers=H_USER).get_json()["benh_an_mau"]
    check("list trở về số ban đầu", len(final) == base_n)

    cleanup()
    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
