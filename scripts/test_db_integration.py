"""Test tích hợp SQLAlchemy vào Flask app: endpoint DB-backed đọc danh mục đã seed.

Yêu cầu: DB Postgres BẬT (DATABASE_URL trong .env) + đã chạy seed_db.py.
Chạy:  python scripts/test_db_integration.py
"""

import json
import sys
import tempfile
from datetime import datetime, timezone
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


def setup_admin():
    tmp = Path(tempfile.mkdtemp(prefix="dbint_"))
    expires = A.iso_utc(datetime.now(timezone.utc) + A.timedelta(days=1))
    store = {"users": [
        {"id": "a1", "name": "Admin", "email": "admin@cnpm.vn", "password_hash": "x",
         "role": "admin", "session_token": "ADMIN", "session_expires_at": expires},
        {"id": "u1", "name": "User", "email": "user@cnpm.vn", "password_hash": "x",
         "session_token": "USER", "session_expires_at": expires},
    ]}
    (tmp / "users.json").write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")
    A.USERS_PATH = tmp / "users.json"


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
    saved = A.DB_ENABLED
    A.DB_ENABLED = False
    check("DB tắt -> health 503", get("/api/admin/db/health").status_code == 503)
    A.DB_ENABLED = saved

    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
