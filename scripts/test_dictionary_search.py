"""US27 (SCRUM-108): test API tìm kiếm triệu chứng trong từ điển + phân trang.

DB mode: dùng dữ liệu trieu_chung đã seed. Thêm 1 triệu chứng có TỪ KHÓA riêng để kiểm
tra tìm theo keyword (khác tên), rồi dọn. Chạy:  python scripts/test_dictionary_search.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402

PASS = 0
FAIL = 0
ADMIN_EMAIL = "dict_admin@cnpm.vn"
KW = "zzkeyworddacbiet"


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
        A.db.session.query(A.db_models.TrieuChung).filter(
            A.db_models.TrieuChung.tu_khoa.ilike(f"%{KW}%")).delete(synchronize_session=False)
        admin = A.db_models.NguoiDung(ho_ten="Admin", email=ADMIN_EMAIL, vai_tro="admin")
        admin.tai_khoan = A.db_models.TaiKhoan(
            ten_dang_nhap=ADMIN_EMAIL, mat_khau_hash="x",
            session_token="ADMIN", session_expires_at=datetime.now(timezone.utc) + timedelta(days=1))
        A.db.session.add(admin)
        # triệu chứng có tên KHÔNG chứa keyword, nhưng tu_khoa chứa keyword
        A.db.session.add(A.db_models.TrieuChung(ten_trieu_chung="ho khan test", tu_khoa=f"cough {KW}"))
        A.db.session.commit()


def cleanup():
    with A.app.app_context():
        A.db.session.query(A.db_models.TrieuChung).filter(
            A.db_models.TrieuChung.tu_khoa.ilike(f"%{KW}%")).delete(synchronize_session=False)
        nd = A.db.session.query(A.db_models.NguoiDung).filter_by(email=ADMIN_EMAIL).first()
        if nd:
            A.db.session.delete(nd)
        A.db.session.commit()


def main():
    if not A.DB_ENABLED:
        print("DB chưa bật — bỏ qua.")
        return 1
    setup()
    c = A.app.test_client()

    def get(qs="", token="ADMIN"):
        h = {"Authorization": f"Bearer {token}"} if token else {}
        return c.get(f"/api/admin/db/trieu-chung{qs}", headers=h)

    print("== PHÂN QUYỀN ==")
    check("chưa login -> 401", get(token=None).status_code == 401)
    check("admin -> 200", get().status_code == 200)

    print("== SCRUM-109: tìm theo tên / từ khóa ==")
    by_name = get("?q=fever").get_json()
    check("tìm 'fever' (theo tên) có kết quả", by_name["total"] >= 1, str(by_name["total"]))
    check("item có 'ten' và 'tu_khoa'", all("ten" in x and "tu_khoa" in x for x in by_name["trieu_chung"]))
    by_kw = get(f"?q={KW}").get_json()
    check("tìm theo TỪ KHÓA (tên không chứa) -> đúng 1", by_kw["total"] == 1, str(by_kw["total"]))
    check("kết quả keyword đúng triệu chứng", by_kw["trieu_chung"][0]["ten"] == "ho khan test")

    print("== SCRUM-111: phân trang ==")
    p1 = get("?per_page=5&page=1").get_json()
    p2 = get("?per_page=5&page=2").get_json()
    check("per_page=5 -> trang 1 có 5 dòng", len(p1["trieu_chung"]) == 5, str(len(p1["trieu_chung"])))
    check("total_pages = ceil(total/5)", p1["total_pages"] == (p1["total"] + 4) // 5)
    check("trang 2 khác trang 1", p1["trieu_chung"][0]["ma"] != p2["trieu_chung"][0]["ma"])
    check("page/per_page phản hồi đúng", p1["page"] == 1 and p1["per_page"] == 5)

    print("== Không khớp ==")
    none = get("?q=khongtontaitrieuchungnao999").get_json()
    check("query vô nghĩa -> total 0", none["total"] == 0, str(none["total"]))

    cleanup()
    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
