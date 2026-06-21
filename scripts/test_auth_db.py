"""Test auth DB-backed: register/login/me/logout/forgot/reset chạy trên Postgres.

Yêu cầu DB bật. Tạo user test với email riêng rồi XÓA sau khi xong (không để rác CNPM).
Chạy:  python scripts/test_auth_db.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402

PASS = 0
FAIL = 0
EMAIL = "authtest_db@cnpm.vn"
PW = "matkhau123"


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")


def cleanup():
    with A.app.app_context():
        nd = A.db.session.query(A.db_models.NguoiDung).filter_by(email=EMAIL).first()
        if nd:
            A.db.session.delete(nd)
            A.db.session.commit()


def main():
    if not A.DB_ENABLED:
        print("DB chưa bật — bỏ qua.")
        return 1
    cleanup()
    c = A.app.test_client()

    print("== REGISTER (ghi vào Postgres) ==")
    r = c.post("/api/auth/register", json={"name": "Auth Test", "email": EMAIL, "password": PW})
    check("register -> 200/201", r.status_code in (200, 201), str(r.status_code))
    token = (r.get_json() or {}).get("token")
    check("có token", bool(token))
    with A.app.app_context():
        nd = A.db.session.query(A.db_models.NguoiDung).filter_by(email=EMAIL).first()
        check("user nằm trong bảng nguoi_dung", nd is not None)
        check("có tai_khoan + mật khẩu hash", bool(nd and nd.tai_khoan and nd.tai_khoan.mat_khau_hash))
        check("mật khẩu verify đúng", bool(nd and nd.tai_khoan.check_password(PW)))

    print("== ME / LOGIN / LOGOUT ==")
    me = c.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    check("me bằng token -> 200", me.status_code == 200)
    check("me trả đúng email", (me.get_json() or {}).get("user", {}).get("email") == EMAIL)

    bad = c.post("/api/auth/login", json={"email": EMAIL, "password": "sai"})
    check("login sai mật khẩu -> 401", bad.status_code == 401)
    ok = c.post("/api/auth/login", json={"email": EMAIL, "password": PW})
    check("login đúng -> 200 + token", ok.status_code == 200 and bool(ok.get_json().get("token")))
    token2 = ok.get_json()["token"]

    lo = c.post("/api/auth/logout", headers={"Authorization": f"Bearer {token2}"})
    check("logout -> 200", lo.status_code == 200)
    me2 = c.get("/api/auth/me", headers={"Authorization": f"Bearer {token2}"})
    check("sau logout token hết hiệu lực -> 401", me2.status_code == 401)

    print("== FORGOT / RESET ==")
    fp = c.post("/api/auth/forgot-password", json={"email": EMAIL})
    code = (fp.get_json() or {}).get("reset_code")
    check("forgot -> có reset_code (dev)", bool(code))
    rp = c.post("/api/auth/reset-password", json={"email": EMAIL, "reset_code": code, "password": "matkhaumoi9"})
    check("reset-password -> 200", rp.status_code == 200, str(rp.status_code))
    re_login = c.post("/api/auth/login", json={"email": EMAIL, "password": "matkhaumoi9"})
    check("đăng nhập bằng mật khẩu mới -> 200", re_login.status_code == 200)

    cleanup()
    with A.app.app_context():
        gone = A.db.session.query(A.db_models.NguoiDung).filter_by(email=EMAIL).first()
        check("dọn user test (cascade tai_khoan)", gone is None)

    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
