"""PORT toan/main: test duyệt phản hồi không đồng ý (rejected-feedbacks + reviewed).

DB mode. Chèn vài REJECT (+APPROVE nhiễu), kiểm tra list/lọc/đánh dấu đã xử lý. Tự dọn.
Chạy:  python scripts/test_feedback_review.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402

PASS = 0
FAIL = 0
ADMIN_EMAIL = "rev_admin@cnpm.vn"
USER_EMAIL = "rev_user@cnpm.vn"
TAG = "ZZREV"


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
        A.db.session.query(A.db_models.PhanHoi).filter(A.db_models.PhanHoi.noi_dung.like(f"%{TAG}%")).delete(synchronize_session=False)
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
        # 3 REJECT (có TAG) + 1 APPROVE (nhiễu)
        for i in range(3):
            A.db.session.add(A.db_models.PhanHoi(trang_thai="REJECT", muc_do_hai_long=0,
                                                 noi_dung=f"{TAG} lý do {i}", nhom_thuoc_du_doan="thuốc kháng sinh"))
        A.db.session.add(A.db_models.PhanHoi(trang_thai="APPROVE", muc_do_hai_long=1, noi_dung=f"{TAG} ok"))
        A.db.session.commit()
        return [r.ma_phan_hoi for r in A.db.session.query(A.db_models.PhanHoi)
                .filter(A.db_models.PhanHoi.noi_dung.like(f"{TAG} lý do%")).all()]


def main():
    if not A.DB_ENABLED:
        print("DB chưa bật — bỏ qua.")
        return 1
    rej_mas = setup()
    c = A.app.test_client()
    HA = {"Authorization": "Bearer ADMIN"}
    HU = {"Authorization": "Bearer USER"}

    print("== GUARD ==")
    check("user thường -> 403", c.get("/api/admin/rejected-feedbacks", headers=HU).status_code == 403)
    check("chưa login -> 401", c.get("/api/admin/rejected-feedbacks").status_code == 401)

    print("== LIST (chỉ REJECT) ==")
    d = c.get("/api/admin/rejected-feedbacks?per_page=100", headers=HA).get_json()
    ours = [f for f in d["feedbacks"] if (f.get("noi_dung") or "").startswith(f"{TAG} lý do")]
    check("trả 3 REJECT của test", len(ours) == 3, str(len(ours)))
    check("không lẫn APPROVE", all((f.get("noi_dung") or "") != f"{TAG} ok" for f in d["feedbacks"]))
    check("mỗi item có noi_dung + da_xu_ly", all("noi_dung" in f and "da_xu_ly" in f for f in ours))
    base_pending = d["chua_xu_ly"]

    print("== ĐÁNH DẤU ĐÃ XỬ LÝ ==")
    one = rej_mas[0]
    mr = c.post(f"/api/admin/rejected-feedbacks/{one}/reviewed", json={"da_xu_ly": True}, headers=HA)
    check("mark reviewed -> 200", mr.status_code == 200 and mr.get_json()["da_xu_ly"] is True)
    d2 = c.get("/api/admin/rejected-feedbacks?per_page=100", headers=HA).get_json()
    check("chua_xu_ly giảm 1", d2["chua_xu_ly"] == base_pending - 1, f"{d2['chua_xu_ly']} vs {base_pending}")

    print("== LỌC reviewed=0 / =1 ==")
    pend = c.get("/api/admin/rejected-feedbacks?reviewed=0&per_page=100", headers=HA).get_json()
    done = c.get("/api/admin/rejected-feedbacks?reviewed=1&per_page=100", headers=HA).get_json()
    check("pending không chứa item đã xử lý", all(f["ma"] != one for f in pend["feedbacks"]))
    check("done chứa item vừa xử lý", any(f["ma"] == one for f in done["feedbacks"]))

    print("== MỞ LẠI + 404 ==")
    c.post(f"/api/admin/rejected-feedbacks/{one}/reviewed", json={"da_xu_ly": False}, headers=HA)
    d3 = c.get("/api/admin/rejected-feedbacks?per_page=100", headers=HA).get_json()
    check("mở lại -> chua_xu_ly về cũ", d3["chua_xu_ly"] == base_pending)
    check("mark id lạ -> 404", c.post("/api/admin/rejected-feedbacks/99999999/reviewed", json={}, headers=HA).status_code == 404)

    purge()
    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
