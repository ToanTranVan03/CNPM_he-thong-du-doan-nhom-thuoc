"""PORT toan/main: test bulk import CSV (nhóm thuốc / thuốc).

DB mode. Upload CSV qua test_client (multipart), kiểm tra inserted/skipped + template.
Dọn item test sau. Chạy:  python scripts/test_bulk_import.py
"""

import io
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402

PASS = 0
FAIL = 0
ADMIN_EMAIL = "imp_admin@cnpm.vn"
USER_EMAIL = "imp_user@cnpm.vn"
GA, GB = "ZZ Import Nhóm A", "ZZ Import Nhóm B"
TX, TY = "ZZ Import Thuốc X", "ZZ Import Thuốc Y"


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
        for nm in (GA, GB):
            for g in A.db.session.query(A.db_models.NhomThuoc).filter_by(ten_nhom_thuoc=nm).all():
                A.db.session.delete(g)
        for nm in (TX, TY):
            for t in A.db.session.query(A.db_models.ThuocThamKhao).filter_by(ten_thuoc=nm).all():
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
        # GA tồn tại sẵn -> import sẽ skip
        A.db.session.add(A.db_models.NhomThuoc(ten_nhom_thuoc=GA))
        A.db.session.commit()


def upload(c, url, csv_text, token="ADMIN"):
    return c.post(url, data={"file": (io.BytesIO(csv_text.encode("utf-8")), "x.csv")},
                  content_type="multipart/form-data",
                  headers={"Authorization": f"Bearer {token}"})


def main():
    if not A.DB_ENABLED:
        print("DB chưa bật — bỏ qua.")
        return 1
    setup()
    c = A.app.test_client()

    print("== GUARD ==")
    check("user thường import -> 403", upload(c, "/api/admin/bulk-import/nhom-thuoc", "ten_nhom\nx\n", "USER").status_code == 403)
    check("không file -> 400", c.post("/api/admin/bulk-import/nhom-thuoc", headers={"Authorization": "Bearer ADMIN"}).status_code == 400)

    print("== IMPORT NHÓM THUỐC (GA trùng, GB mới) ==")
    r = upload(c, "/api/admin/bulk-import/nhom-thuoc", f"ten_nhom,mo_ta\n{GA},x\n{GB},mô tả B\n")
    d = r.get_json()
    check("status 200", r.status_code == 200)
    check("inserted = 1 (GB)", d["inserted"] == 1, str(d["inserted"]))
    check("skipped = 1 (GA trùng)", d["skipped"] == 1, str(d["skipped"]))
    with A.app.app_context():
        check("GB đã có trong DB", A.db.session.query(A.db_models.NhomThuoc).filter_by(ten_nhom_thuoc=GB).first() is not None)

    print("== IMPORT THUỐC (TX gắn GB, TY không nhóm) ==")
    r2 = upload(c, "/api/admin/bulk-import/thuoc", f"ten_thuoc,hoat_chat,nhom_thuoc\n{TX},hc-x,{GB}\n{TY},hc-y,\n")
    d2 = r2.get_json()
    check("inserted = 2", d2["inserted"] == 2, str(d2["inserted"]))
    with A.app.app_context():
        tx = A.db.session.query(A.db_models.ThuocThamKhao).filter_by(ten_thuoc=TX).first()
        check("TX gắn đúng nhóm GB", tx is not None and any(n.ten_nhom_thuoc == GB for n in tx.nhom_thuoc_list))

    print("== IMPORT THUỐC nhóm không tồn tại -> cảnh báo ==")
    r3 = upload(c, "/api/admin/bulk-import/thuoc", "ten_thuoc,nhom_thuoc\nZZ Import Thuốc X,Nhóm Không Tồn Tại 999\n")
    check("vẫn thêm + có cảnh báo", r3.get_json()["inserted"] == 1 and len(r3.get_json()["errors"]) >= 1)

    print("== TEMPLATE ==")
    t1 = c.get("/api/admin/bulk-import/template/nhom-thuoc", headers={"Authorization": "Bearer ADMIN"})
    check("template nhóm -> 200 + CSV", t1.status_code == 200 and b"ten_nhom" in t1.data)
    t2 = c.get("/api/admin/bulk-import/template/thuoc", headers={"Authorization": "Bearer ADMIN"})
    check("template thuốc -> 200 + CSV", t2.status_code == 200 and b"ten_thuoc" in t2.data)

    purge()
    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
