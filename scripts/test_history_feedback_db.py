"""US15/18/19 trên Postgres: predict -> ghi ket_qua_du_doan/lich_su, feedback -> phan_hoi,
dashboard /api/admin/stats đọc DB.

Yêu cầu DB bật. Dọn sạch bảng giao dịch trước (để số liệu xác định) + dọn admin test sau.
Chạy:  python scripts/test_history_feedback_db.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402

PASS = 0
FAIL = 0
ADMIN_EMAIL = "histdb_admin@cnpm.vn"


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")


def reset_tx_tables():
    with A.app.app_context():
        A.db.session.query(A.db_models.PhanHoi).delete()
        A.db.session.query(A.db_models.LichSuDuDoan).delete()
        A.db.session.query(A.db_models.KetQuaDuDoan).delete()
        nd = A.db.session.query(A.db_models.NguoiDung).filter_by(email=ADMIN_EMAIL).first()
        if nd:
            A.db.session.delete(nd)
        A.db.session.commit()


def setup_admin():
    with A.app.app_context():
        nd = A.db_models.NguoiDung(ho_ten="Admin", email=ADMIN_EMAIL, vai_tro="admin")
        nd.tai_khoan = A.db_models.TaiKhoan(
            ten_dang_nhap=ADMIN_EMAIL, mat_khau_hash="x",
            session_token="ADMIN", session_expires_at=datetime.now(timezone.utc) + timedelta(days=1))
        A.db.session.add(nd)
        A.db.session.commit()


def main():
    if not A.DB_ENABLED:
        print("DB chưa bật — bỏ qua.")
        return 1
    reset_tx_tables()
    setup_admin()
    c = A.app.test_client()

    print("== US15: predict ghi vào ket_qua_du_doan/lich_su ==")
    r1 = c.post("/api/predict", json={"notes": "tôi bị đau đầu, sổ mũi, hắt hơi mấy hôm nay", "symptoms": []})
    r2 = c.post("/api/predict", json={"notes": "đột nhiên đau thắt ngực dữ dội, khó thở, vã mồ hôi", "symptoms": []})
    check("predict OTC -> 200", r1.status_code == 200)
    check("predict cấp cứu -> 422", r2.status_code == 422)
    with A.app.app_context():
        kq = A.db.session.query(A.db_models.KetQuaDuDoan).count()
        ls = A.db.session.query(A.db_models.LichSuDuDoan).count()
        statuses = sorted(s for (s,) in A.db.session.query(A.db_models.KetQuaDuDoan.trang_thai))
        check("ket_qua_du_doan có 2 dòng", kq == 2, str(kq))
        check("lich_su_du_doan có 2 dòng (1-1)", ls == 2, str(ls))
        check("trạng thái gồm suggest + emergency", statuses == ["emergency", "suggest"], str(statuses))

    print("== US18: feedback ghi vào phan_hoi ==")
    c.post("/api/feedback", json={"verdict": "APPROVE", "predicted_group": "thuốc kháng histamin"})
    c.post("/api/feedback", json={"verdict": "REJECT", "predicted_group": "thuốc kháng histamin"})
    with A.app.app_context():
        ph = A.db.session.query(A.db_models.PhanHoi).count()
        approve = A.db.session.query(A.db_models.PhanHoi).filter_by(trang_thai="APPROVE").count()
        check("phan_hoi có 2 dòng", ph == 2, str(ph))
        check("1 APPROVE", approve == 1)

    print("== US19: /api/admin/stats đọc từ Postgres ==")
    s = c.get("/api/admin/stats", headers={"Authorization": "Bearer ADMIN"}).get_json()
    check("source = postgres", s.get("source") == "postgres", str(s.get("source")))
    check("total_predictions = 2", s["total_predictions"] == 2, str(s["total_predictions"]))
    check("by_status suggest=1, emergency=1", s["by_status"]["suggest"] == 1 and s["by_status"]["emergency"] == 1, str(s["by_status"]))
    check("agree=1, disagree=1, rate=50.0", s["agree_count"] == 1 and s["disagree_count"] == 1 and s["agree_rate"] == 50.0, str((s["agree_count"], s["disagree_count"], s["agree_rate"])))
    check("over_time có dữ liệu", len(s["predictions_over_time"]) >= 1)
    check("top_groups có kháng histamin", any(g["group"] == "thuốc kháng histamin" for g in s["top_groups"]))

    reset_tx_tables()
    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
