"""PORT toan/main: test CRUD Quản lý thuốc (nhóm thuốc + thuốc) trên schema huy.

DB mode. Tạo item test với tên riêng, kiểm tra CRUD + guard, rồi dọn (giữ nguyên seed).
Chạy:  python scripts/test_drug_crud.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402

PASS = 0
FAIL = 0
ADMIN_EMAIL = "drug_admin@cnpm.vn"
USER_EMAIL = "drug_user@cnpm.vn"
G_NAME = "ZZ Nhóm Test CRUD"
G_NAME2 = "ZZ Nhóm Test CRUD (đã sửa)"
D_NAME = "ZZ Thuốc Test CRUD"


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")


def purge():
    with A.app.app_context():
        for email in (ADMIN_EMAIL, USER_EMAIL):
            nd = A.db.session.query(A.db_models.NguoiDung).filter_by(email=email).first()
            if nd:
                A.db.session.delete(nd)
        for nm in (G_NAME, G_NAME2):
            for g in A.db.session.query(A.db_models.NhomThuoc).filter_by(ten_nhom_thuoc=nm).all():
                A.db.session.delete(g)
        for t in A.db.session.query(A.db_models.ThuocThamKhao).filter_by(ten_thuoc=D_NAME).all():
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

    print("== NHÓM THUỐC: tạo/sửa/xóa ==")
    check("user thường tạo -> 403", c.post("/api/admin/db/nhom-thuoc", json={"ten": G_NAME}, headers=HU).status_code == 403)
    check("thiếu tên -> 400", c.post("/api/admin/db/nhom-thuoc", json={}, headers=HA).status_code == 400)
    cr = c.post("/api/admin/db/nhom-thuoc", json={"ten": G_NAME, "mo_ta": "test"}, headers=HA)
    check("admin tạo nhóm -> 201", cr.status_code == 201)
    g_ma = cr.get_json()["ma"]
    check("tạo trùng -> 409", c.post("/api/admin/db/nhom-thuoc", json={"ten": G_NAME}, headers=HA).status_code == 409)
    up = c.put(f"/api/admin/db/nhom-thuoc/{g_ma}", json={"ten": G_NAME2}, headers=HA)
    check("sửa nhóm -> 200", up.status_code == 200)
    listed = c.get("/api/admin/db/nhom-thuoc", headers=HA).get_json()["nhom_thuoc"]
    check("nhóm đã đổi tên trong list", any(x["ma"] == g_ma and x["ten"] == G_NAME2 for x in listed))

    print("== THUỐC: tạo/sửa/xóa + tìm ==")
    check("user thường tạo thuốc -> 403", c.post("/api/admin/db/thuoc", json={"ten": D_NAME}, headers=HU).status_code == 403)
    cr2 = c.post("/api/admin/db/thuoc", json={"ten": D_NAME, "hoat_chat": "test-hc", "ma_nhom_thuoc": g_ma}, headers=HA)
    check("admin tạo thuốc (gắn nhóm) -> 201", cr2.status_code == 201)
    d_ma = cr2.get_json()["ma"]
    found = c.get("/api/admin/db/thuoc?q=ZZ Thuốc Test", headers=HA).get_json()
    check("tìm thấy thuốc test", any(t["ma"] == d_ma for t in found["thuoc"]), str(found["total"]))
    check("thuốc có gắn nhóm", any(t["ma"] == d_ma and G_NAME2 in (t.get("nhom") or []) for t in found["thuoc"]))
    # nhóm tăng so_thuoc
    g_now = next(x for x in c.get("/api/admin/db/nhom-thuoc", headers=HA).get_json()["nhom_thuoc"] if x["ma"] == g_ma)
    check("so_thuoc của nhóm = 1", g_now["so_thuoc"] == 1, str(g_now["so_thuoc"]))
    up2 = c.put(f"/api/admin/db/thuoc/{d_ma}", json={"hoat_chat": "hc-moi"}, headers=HA)
    check("sửa thuốc -> 200", up2.status_code == 200)

    print("== PHÂN TRANG thuốc ==")
    p1 = c.get("/api/admin/db/thuoc?per_page=5&page=1", headers=HA).get_json()
    check("per_page=5 -> 5 thuốc", len(p1["thuoc"]) == 5, str(len(p1["thuoc"])))
    check("total_pages hợp lệ", p1["total_pages"] == (p1["total"] + 4) // 5)

    print("== XÓA ==")
    check("xóa thuốc -> 200", c.delete(f"/api/admin/db/thuoc/{d_ma}", headers=HA).status_code == 200)
    check("xóa thuốc lại -> 404", c.delete(f"/api/admin/db/thuoc/{d_ma}", headers=HA).status_code == 404)
    check("xóa nhóm -> 200", c.delete(f"/api/admin/db/nhom-thuoc/{g_ma}", headers=HA).status_code == 200)
    check("xóa nhóm lại -> 404", c.delete(f"/api/admin/db/nhom-thuoc/{g_ma}", headers=HA).status_code == 404)

    purge()
    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
