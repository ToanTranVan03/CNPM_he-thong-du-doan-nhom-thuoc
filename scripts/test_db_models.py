"""Test schema DB dựng từ class diagram (backend/models.py).

- Thử DATABASE_URL trong .env (Postgres). Nếu kết nối lỗi -> fallback SQLite in-memory
  để vẫn kiểm chứng schema CHUẨN (tạo đủ bảng + quan hệ chạy được).
- Kiểm tra: tạo đủ bảng kỳ vọng + insert xuyên suốt các quan hệ 1-1, 1-N, N-N, cascade.

Chạy:  python scripts/test_db_models.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from flask import Flask  # noqa: E402
import sqlalchemy as sa  # noqa: E402

from models import (  # noqa: E402
    db, EXPECTED_TABLES,
    NguoiDung, TaiKhoan, QuanTriVien, BacSiDuocSi, MoTaBenhAn, TrieuChung,
    ChanDoanDuKien, NhomThuoc, ThuocThamKhao, LuuYAnToan, KetQuaDuDoan,
    LichSuDuDoan, PhanHoi, ThongKeBaoCao, DuLieuHuanLuyen, MoHinhDuDoan,
)

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


def load_env_url():
    p = ROOT / ".env"
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL") and "=" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def pick_database():
    """Mặc định SQLite in-memory (AN TOÀN — test có drop_all, KHÔNG đụng DB thật).

    Chỉ test trên Postgres .env khi đặt env TEST_ON_POSTGRES=1 (sẽ XÓA SẠCH dữ liệu DB đó!).
    """
    if os.environ.get("TEST_ON_POSTGRES") == "1":
        url = load_env_url()
        if url:
            try:
                eng = sa.create_engine(url)
                with eng.connect() as c:
                    c.execute(sa.text("select 1"))
                print("  [!] TEST_ON_POSTGRES=1 -> chạy trên Postgres thật (sẽ drop/tạo lại bảng!)")
                return url, "PostgreSQL (.env)"
            except Exception as e:
                print(f"  [!] Không kết nối được Postgres ({type(e).__name__}); dùng SQLite.")
    return "sqlite://", "SQLite in-memory"


def main():
    uri, label = pick_database()
    print(f"== DB kiểm thử: {label} ==")

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.drop_all()
        db.create_all()

        # 1) Đủ bảng?
        tables = set(sa.inspect(db.engine).get_table_names())
        missing = EXPECTED_TABLES - tables
        check(f"tạo đủ {len(EXPECTED_TABLES)} bảng kỳ vọng", not missing, f"thiếu: {missing}")
        check("không tạo lại bảng benh_an_mau", "benh_an_mau" not in tables)

        # 2) Người dùng + tài khoản (1-1) + admin (kế thừa 1-1)
        admin_u = NguoiDung(ho_ten="Quản Trị", email="admin@cnpm.vn", vai_tro="admin")
        admin_u.tai_khoan = TaiKhoan(ten_dang_nhap="admin")
        admin_u.tai_khoan.set_password("matkhau123")
        admin_u.quan_tri_vien = QuanTriVien(cap_quyen="full")
        db.session.add(admin_u)

        bs_u = NguoiDung(ho_ten="BS. An", email="an@cnpm.vn", vai_tro="bac_si")
        bs_u.bac_si = BacSiDuocSi(chuyen_mon="Nội khoa", so_chung_chi="CC-001")
        db.session.add(bs_u)
        db.session.commit()

        # 3) Danh mục: triệu chứng, chẩn đoán, nhóm thuốc + thuốc (N-N), lưu ý, mô hình
        tc1 = TrieuChung(ten_trieu_chung="sốt", tu_khoa="sot,fever")
        tc2 = TrieuChung(ten_trieu_chung="ho", tu_khoa="ho,cough")
        cd = ChanDoanDuKien(ten_chan_doan="Viêm họng cấp", mo_ta="...")
        thuoc1 = ThuocThamKhao(ten_thuoc="Paracetamol", hoat_chat="paracetamol")
        nhom = NhomThuoc(ten_nhom_thuoc="thuốc giảm đau hạ sốt", quan_tri_vien=admin_u.quan_tri_vien)
        nhom.thuoc_list.append(thuoc1)  # N-N nhóm-thuốc
        luuy = LuuYAnToan(noi_dung="Không tự dùng nếu suy gan", muc_do_canh_bao="cao")
        mohinh = MoHinhDuDoan(thuat_toan="TF-IDF + LinearSVM", do_chinh_xac=0.94)
        db.session.add_all([tc1, tc2, cd, nhom, luuy, mohinh])
        db.session.commit()

        # 4) Bệnh án (N-N triệu chứng) -> Kết quả (gom mọi quan hệ) -> lịch sử + phản hồi
        ba = MoTaBenhAn(noi_dung="sốt cao, ho nhiều", nguoi_dung=bs_u)
        ba.trieu_chung_list.extend([tc1, tc2])
        kq = KetQuaDuDoan(
            chan_doan_du_kien="Viêm họng cấp", nhom_thuoc_du_doan="thuốc giảm đau hạ sốt",
            do_tin_cay=0.94, mo_ta_benh_an=ba, chan_doan=cd, bac_si=bs_u.bac_si, mo_hinh=mohinh,
        )
        kq.trieu_chung_list.extend([tc1, tc2])
        kq.nhom_thuoc_list.append(nhom)
        kq.thuoc_list.append(thuoc1)
        kq.luu_y_list.append(luuy)
        kq.lich_su = LichSuDuDoan(ket_qua_tom_tat="Gợi ý: thuốc giảm đau hạ sốt (94%)")
        kq.phan_hoi_list.append(PhanHoi(noi_dung="Hợp lý", muc_do_hai_long=5, nguoi_dung=bs_u))
        db.session.add_all([ba, kq])
        # thống kê + dữ liệu huấn luyện gắn admin
        db.session.add(ThongKeBaoCao(loai_bao_cao="luot_du_doan", quan_tri_vien=admin_u.quan_tri_vien))
        db.session.add(DuLieuHuanLuyen(mo_ta_benh_an="sốt ho", trieu_chung="sốt;ho",
                                       nhom_thuoc="thuốc giảm đau hạ sốt", quan_tri_vien=admin_u.quan_tri_vien))
        db.session.commit()

        # 5) Truy vấn lại + kiểm tra quan hệ
        kq2 = db.session.get(KetQuaDuDoan, kq.ma_ket_qua)
        check("KetQua -> ChanDoan (N-1)", kq2.chan_doan.ten_chan_doan == "Viêm họng cấp")
        check("KetQua -> BacSi (N-1)", kq2.bac_si.chuyen_mon == "Nội khoa")
        check("KetQua -> MoHinh (N-1)", round(kq2.mo_hinh.do_chinh_xac, 2) == 0.94)
        check("KetQua -> TrieuChung (N-N) = 2", len(kq2.trieu_chung_list) == 2)
        check("KetQua -> NhomThuoc (N-N) = 1", len(kq2.nhom_thuoc_list) == 1)
        check("KetQua -> Thuoc (N-N) = 1", len(kq2.thuoc_list) == 1)
        check("KetQua -> LuuY (N-N) = 1", len(kq2.luu_y_list) == 1)
        check("KetQua -> LichSu (1-0..1)", kq2.lich_su is not None)
        check("KetQua -> PhanHoi (1-N) = 1", len(kq2.phan_hoi_list) == 1)
        check("Nhom -> Thuoc (N-N) = 1", len(db.session.get(NhomThuoc, nhom.ma_nhom_thuoc).thuoc_list) == 1)
        check("BenhAn -> TrieuChung (N-N) = 2", len(db.session.get(MoTaBenhAn, ba.ma_mo_ta).trieu_chung_list) == 2)
        check("NguoiDung -> TaiKhoan (1-1) + mật khẩu", admin_u.tai_khoan.check_password("matkhau123"))
        check("Admin (kế thừa) -> NhomThuoc quản lý = 1", len(admin_u.quan_tri_vien.nhom_thuoc_list) == 1)
        check("Email UNIQUE có hiệu lực", _violates_unique(db))

        # 6) Cascade: xóa KetQua -> xóa LichSu + PhanHoi kèm theo
        db.session.delete(kq2)
        db.session.commit()
        check("Cascade xóa KetQua -> LichSu rỗng", db.session.query(LichSuDuDoan).count() == 0)
        check("Cascade xóa KetQua -> PhanHoi rỗng", db.session.query(PhanHoi).count() == 0)

        db.drop_all()

    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL  [{label}]")
    return 0 if FAIL == 0 else 1


def _violates_unique(db) -> bool:
    """Thêm email trùng -> phải lỗi IntegrityError (ràng buộc UNIQUE hoạt động)."""
    try:
        db.session.add(NguoiDung(ho_ten="Trùng", email="admin@cnpm.vn", vai_tro="user"))
        db.session.commit()
        db.session.rollback()
        return False
    except Exception:
        db.session.rollback()
        return True


if __name__ == "__main__":
    sys.exit(main())
