"""Test tích hợp SQLAlchemy vào Flask app: endpoint DB-backed đọc danh mục đã seed.

Yêu cầu: DB Postgres BẬT (DATABASE_URL trong .env) + đã chạy seed_db.py.
Chạy:  python scripts/test_db_integration.py
"""

import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")


ADMIN_EMAIL = "dbint_admin@cnpm.vn"
USER_EMAIL = "dbint_user@cnpm.vn"


def _del(email):
    nd = A.db.session.query(A.db_models.NguoiDung).filter_by(email=email).first()
    if nd:
        A.db.session.delete(nd)
        A.db.session.commit()


def setup_admin():
    """Auth giờ DB-backed -> tạo admin + user trong Postgres với session_token cố định."""
    expires = datetime.now(timezone.utc) + timedelta(days=1)
    with A.app.app_context():
        _del(ADMIN_EMAIL)
        _del(USER_EMAIL)
        for email, role, token in [(ADMIN_EMAIL, "admin", "ADMIN"), (USER_EMAIL, "user", "USER")]:
            nd = A.db_models.NguoiDung(ho_ten=role, email=email, vai_tro=role)
            nd.tai_khoan = A.db_models.TaiKhoan(
                ten_dang_nhap=email, mat_khau_hash="x",
                session_token=token, session_expires_at=expires,
            )
            A.db.session.add(nd)
        A.db.session.commit()


def teardown_admin():
    with A.app.app_context():
        _del(ADMIN_EMAIL)
        _del(USER_EMAIL)


def main():
    if not A.DB_ENABLED:
        print("  [!] DB chưa bật (DATABASE_URL?) — không chạy được test tích hợp DB.")
        return 1
    setup_admin()
    c = A.app.test_client()

    def get(path, token="ADMIN"):
        h = {"Authorization": f"Bearer {token}"} if token else {}
        return c.get(path, headers=h)

    print("== PHÂN QUYỀN ==")
    check("health: chưa login -> 401", get("/api/admin/db/health", token=None).status_code == 401)
    check("health: user thường -> 403", get("/api/admin/db/health", token="USER").status_code == 403)

    print("== HEALTH (đếm danh mục) ==")
    h = get("/api/admin/db/health")
    check("health -> 200", h.status_code == 200)
    counts = h.get_json().get("counts", {})
    check("nhom_thuoc = 24", counts.get("nhom_thuoc") == 24, str(counts.get("nhom_thuoc")))
    check("trieu_chung = 582", counts.get("trieu_chung") == 582, str(counts.get("trieu_chung")))
    check("chan_doan_du_kien = 369", counts.get("chan_doan_du_kien") == 369, str(counts.get("chan_doan_du_kien")))
    check("mo_hinh_du_doan >= 1", counts.get("mo_hinh_du_doan", 0) >= 1)

    print("== NHÓM THUỐC (đọc từ Postgres + join N-N) ==")
    r = get("/api/admin/db/nhom-thuoc")
    data = r.get_json().get("nhom_thuoc", [])
    check("trả 24 nhóm", len(data) == 24, str(len(data)))
    khs = next((n for n in data if n["ten"] == "thuốc kháng histamin"), None)
    check("có nhóm 'thuốc kháng histamin'", khs is not None)
    check("nhóm có thuốc liên kết (so_thuoc>0)", bool(khs and khs["so_thuoc"] > 0), str(khs and khs["so_thuoc"]))

    print("== TRIỆU CHỨNG (tìm kiếm) ==")
    r2 = get("/api/admin/db/trieu-chung?q=fever")
    js = r2.get_json()
    check("tìm 'fever' -> có kết quả", js.get("total", 0) >= 1, str(js.get("total")))
    check("mỗi item có ma+ten", all("ma" in t and "ten" in t for t in js.get("trieu_chung", [])))

    print("== GRACEFUL (DB tắt -> 503) ==")
    # Khi DB tắt, auth cũng về JSON -> cấp admin qua users.json tạm để kiểm đúng nhánh 503.
    saved_db, saved_path = A.DB_ENABLED, A.USERS_PATH
    tmp = Path(tempfile.mkdtemp(prefix="dbint_off_"))
    expires = A.iso_utc(datetime.now(timezone.utc) + timedelta(days=1))
    (tmp / "users.json").write_text(json.dumps({"users": [
        {"id": "a", "name": "A", "email": ADMIN_EMAIL, "password_hash": "x",
         "role": "admin", "session_token": "ADMIN", "session_expires_at": expires}]},
        ensure_ascii=False), encoding="utf-8")
    A.USERS_PATH = tmp / "users.json"
    A.DB_ENABLED = False
    check("DB tắt (auth JSON) -> health 503", get("/api/admin/db/health").status_code == 503)
    A.DB_ENABLED, A.USERS_PATH = saved_db, saved_path

    teardown_admin()
    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
