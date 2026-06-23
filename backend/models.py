"""SQLAlchemy models — dựng theo class diagram của hệ thống dự đoán nhóm thuốc.

Quy ước & diễn giải (để đối chiếu với class diagram):
- Mỗi LỚP THỰC THỂ (có Ma...: int) -> 1 bảng. Tên bảng/cột dùng snake_case tiếng Việt
  ánh xạ 1-1 với thuộc tính trên diagram (vd MaNguoiDung -> ma_nguoi_dung).
- Kế thừa NguoiDung <|- QuanTriVien, BacSiDuocSi: mô hình bằng bảng chi tiết 1-1
  (quan_tri_vien / bac_si_duoc_si trỏ FK duy nhất tới nguoi_dung) để GIỮ NGUYÊN khóa
  riêng MaQuanTri / MaChuyenGia như diagram.
- Các liên kết *—* (cả hai đầu nhiều) -> bảng nối N-N (vd ket_qua_trieu_chung).
- LỚP XỬ LÝ KHÔNG lưu DB (không tạo bảng): TienXuLyVanBan, BoVectorHoaTFIDF — đây là
  thành phần thuật toán (StopWords:list, Vocabulary:dict), không phải thực thể.
  MoHinhDuDoan có Ma + metadata nên GIỮ làm bảng (đăng ký mô hình).
"""

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


# ─────────────────────────────────────────────────────────────────────────────
# BẢNG NỐI N-N
# ─────────────────────────────────────────────────────────────────────────────
mo_ta_trieu_chung = db.Table(
    "mo_ta_trieu_chung",
    db.Column("ma_mo_ta", db.ForeignKey("mo_ta_benh_an.ma_mo_ta", ondelete="CASCADE"), primary_key=True),
    db.Column("ma_trieu_chung", db.ForeignKey("trieu_chung.ma_trieu_chung", ondelete="CASCADE"), primary_key=True),
)

ket_qua_trieu_chung = db.Table(
    "ket_qua_trieu_chung",
    db.Column("ma_ket_qua", db.ForeignKey("ket_qua_du_doan.ma_ket_qua", ondelete="CASCADE"), primary_key=True),
    db.Column("ma_trieu_chung", db.ForeignKey("trieu_chung.ma_trieu_chung", ondelete="CASCADE"), primary_key=True),
)

ket_qua_nhom_thuoc = db.Table(
    "ket_qua_nhom_thuoc",
    db.Column("ma_ket_qua", db.ForeignKey("ket_qua_du_doan.ma_ket_qua", ondelete="CASCADE"), primary_key=True),
    db.Column("ma_nhom_thuoc", db.ForeignKey("nhom_thuoc.ma_nhom_thuoc", ondelete="CASCADE"), primary_key=True),
)

ket_qua_thuoc = db.Table(
    "ket_qua_thuoc",
    db.Column("ma_ket_qua", db.ForeignKey("ket_qua_du_doan.ma_ket_qua", ondelete="CASCADE"), primary_key=True),
    db.Column("ma_thuoc", db.ForeignKey("thuoc_tham_khao.ma_thuoc", ondelete="CASCADE"), primary_key=True),
)

ket_qua_luu_y = db.Table(
    "ket_qua_luu_y",
    db.Column("ma_ket_qua", db.ForeignKey("ket_qua_du_doan.ma_ket_qua", ondelete="CASCADE"), primary_key=True),
    db.Column("ma_luu_y", db.ForeignKey("luu_y_an_toan.ma_luu_y", ondelete="CASCADE"), primary_key=True),
)

nhom_thuoc_thuoc = db.Table(
    "nhom_thuoc_thuoc",
    db.Column("ma_nhom_thuoc", db.ForeignKey("nhom_thuoc.ma_nhom_thuoc", ondelete="CASCADE"), primary_key=True),
    db.Column("ma_thuoc", db.ForeignKey("thuoc_tham_khao.ma_thuoc", ondelete="CASCADE"), primary_key=True),
)


# ─────────────────────────────────────────────────────────────────────────────
# NGƯỜI DÙNG & TÀI KHOẢN
# ─────────────────────────────────────────────────────────────────────────────
class NguoiDung(db.Model):
    __tablename__ = "nguoi_dung"
    ma_nguoi_dung = db.Column(db.Integer, primary_key=True)
    ho_ten = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    sdt = db.Column(db.String(20))
    vai_tro = db.Column(db.String(30), nullable=False, default="user")  # user/admin/bac_si...
    trang_thai = db.Column(db.String(30), nullable=False, default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # [hạ tầng] không có trên diagram

    tai_khoan = db.relationship("TaiKhoan", back_populates="nguoi_dung", uselist=False, cascade="all, delete-orphan")
    quan_tri_vien = db.relationship("QuanTriVien", back_populates="nguoi_dung", uselist=False, cascade="all, delete-orphan")
    bac_si = db.relationship("BacSiDuocSi", back_populates="nguoi_dung", uselist=False, cascade="all, delete-orphan")
    mo_ta_benh_an_list = db.relationship("MoTaBenhAn", back_populates="nguoi_dung")
    phan_hoi_list = db.relationship("PhanHoi", back_populates="nguoi_dung")


class TaiKhoan(db.Model):
    __tablename__ = "tai_khoan"
    ma_tai_khoan = db.Column(db.Integer, primary_key=True)
    ten_dang_nhap = db.Column(db.String(100), unique=True, nullable=False)
    mat_khau_hash = db.Column(db.String(255), nullable=False)
    ma_nguoi_dung = db.Column(db.ForeignKey("nguoi_dung.ma_nguoi_dung", ondelete="CASCADE"), unique=True, nullable=False)
    # [hạ tầng] phiên đăng nhập + mã đặt lại mật khẩu — KHÔNG có trên class diagram,
    # thêm để giữ nguyên luồng auth Bearer-session/forgot-password hiện có.
    session_token = db.Column(db.String(255), index=True)
    session_expires_at = db.Column(db.DateTime)
    reset_code_hash = db.Column(db.String(255))
    reset_code_expires_at = db.Column(db.DateTime)

    nguoi_dung = db.relationship("NguoiDung", back_populates="tai_khoan")

    def set_password(self, raw: str):
        self.mat_khau_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.mat_khau_hash, raw)


class QuanTriVien(db.Model):
    __tablename__ = "quan_tri_vien"
    ma_quan_tri = db.Column(db.Integer, primary_key=True)
    cap_quyen = db.Column(db.String(50))
    ma_nguoi_dung = db.Column(db.ForeignKey("nguoi_dung.ma_nguoi_dung", ondelete="CASCADE"), unique=True, nullable=False)

    nguoi_dung = db.relationship("NguoiDung", back_populates="quan_tri_vien")
    bao_cao_list = db.relationship("ThongKeBaoCao", back_populates="quan_tri_vien")
    du_lieu_list = db.relationship("DuLieuHuanLuyen", back_populates="quan_tri_vien")
    nhom_thuoc_list = db.relationship("NhomThuoc", back_populates="quan_tri_vien")


class BacSiDuocSi(db.Model):
    __tablename__ = "bac_si_duoc_si"
    ma_chuyen_gia = db.Column(db.Integer, primary_key=True)
    chuyen_mon = db.Column(db.String(150))
    so_chung_chi = db.Column(db.String(100))
    ma_nguoi_dung = db.Column(db.ForeignKey("nguoi_dung.ma_nguoi_dung", ondelete="CASCADE"), unique=True, nullable=False)

    nguoi_dung = db.relationship("NguoiDung", back_populates="bac_si")
    ket_qua_list = db.relationship("KetQuaDuDoan", back_populates="bac_si")


# ─────────────────────────────────────────────────────────────────────────────
# BỆNH ÁN, TRIỆU CHỨNG, CHẨN ĐOÁN
# ─────────────────────────────────────────────────────────────────────────────
class MoTaBenhAn(db.Model):
    __tablename__ = "mo_ta_benh_an"
    ma_mo_ta = db.Column(db.Integer, primary_key=True)
    noi_dung = db.Column(db.Text, nullable=False)
    thoi_gian_nhap = db.Column(db.DateTime, default=datetime.utcnow)
    ngon_ngu = db.Column(db.String(20), default="vi")
    file_kem_theo = db.Column(db.String(255))
    ma_nguoi_dung = db.Column(db.ForeignKey("nguoi_dung.ma_nguoi_dung", ondelete="SET NULL"))

    nguoi_dung = db.relationship("NguoiDung", back_populates="mo_ta_benh_an_list")
    trieu_chung_list = db.relationship("TrieuChung", secondary=mo_ta_trieu_chung, back_populates="mo_ta_list")
    ket_qua_list = db.relationship("KetQuaDuDoan", back_populates="mo_ta_benh_an")


class TrieuChung(db.Model):
    __tablename__ = "trieu_chung"
    ma_trieu_chung = db.Column(db.Integer, primary_key=True)
    ten_trieu_chung = db.Column(db.String(255), nullable=False)
    tu_khoa = db.Column(db.Text)

    mo_ta_list = db.relationship("MoTaBenhAn", secondary=mo_ta_trieu_chung, back_populates="trieu_chung_list")
    ket_qua_list = db.relationship("KetQuaDuDoan", secondary=ket_qua_trieu_chung, back_populates="trieu_chung_list")


class ChanDoanDuKien(db.Model):
    __tablename__ = "chan_doan_du_kien"
    ma_chan_doan = db.Column(db.Integer, primary_key=True)
    ten_chan_doan = db.Column(db.String(255), nullable=False)
    mo_ta = db.Column(db.Text)

    ket_qua_list = db.relationship("KetQuaDuDoan", back_populates="chan_doan")


# ─────────────────────────────────────────────────────────────────────────────
# NHÓM THUỐC, THUỐC, LƯU Ý
# ─────────────────────────────────────────────────────────────────────────────
class NhomThuoc(db.Model):
    __tablename__ = "nhom_thuoc"
    ma_nhom_thuoc = db.Column(db.Integer, primary_key=True)
    ten_nhom_thuoc = db.Column(db.String(255), unique=True, nullable=False)
    mo_ta = db.Column(db.Text)
    ma_quan_tri = db.Column(db.ForeignKey("quan_tri_vien.ma_quan_tri", ondelete="SET NULL"))

    quan_tri_vien = db.relationship("QuanTriVien", back_populates="nhom_thuoc_list")
    thuoc_list = db.relationship("ThuocThamKhao", secondary=nhom_thuoc_thuoc, back_populates="nhom_thuoc_list")
    ket_qua_list = db.relationship("KetQuaDuDoan", secondary=ket_qua_nhom_thuoc, back_populates="nhom_thuoc_list")


class ThuocThamKhao(db.Model):
    __tablename__ = "thuoc_tham_khao"
    ma_thuoc = db.Column(db.Integer, primary_key=True)
    ten_thuoc = db.Column(db.String(255), nullable=False)
    hoat_chat = db.Column(db.String(255))
    cong_dung = db.Column(db.Text)

    nhom_thuoc_list = db.relationship("NhomThuoc", secondary=nhom_thuoc_thuoc, back_populates="thuoc_list")
    ket_qua_list = db.relationship("KetQuaDuDoan", secondary=ket_qua_thuoc, back_populates="thuoc_list")


class LuuYAnToan(db.Model):
    __tablename__ = "luu_y_an_toan"
    ma_luu_y = db.Column(db.Integer, primary_key=True)
    noi_dung = db.Column(db.Text, nullable=False)
    muc_do_canh_bao = db.Column(db.String(50))

    ket_qua_list = db.relationship("KetQuaDuDoan", secondary=ket_qua_luu_y, back_populates="luu_y_list")


# ─────────────────────────────────────────────────────────────────────────────
# KẾT QUẢ DỰ ĐOÁN (trung tâm) + LỊCH SỬ + PHẢN HỒI
# ─────────────────────────────────────────────────────────────────────────────
class KetQuaDuDoan(db.Model):
    __tablename__ = "ket_qua_du_doan"
    ma_ket_qua = db.Column(db.Integer, primary_key=True)
    chan_doan_du_kien = db.Column(db.String(255))   # nhãn rút gọn (denormalized theo diagram)
    nhom_thuoc_du_doan = db.Column(db.String(255))  # nhãn rút gọn
    do_tin_cay = db.Column(db.Float)
    # [hạ tầng] phục vụ US15 (lưu lịch sử) + US19 (dashboard) — không có trên diagram
    trang_thai = db.Column(db.String(30), index=True)  # suggest | emergency | safety_block
    user_email = db.Column(db.String(150), index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    ma_mo_ta = db.Column(db.ForeignKey("mo_ta_benh_an.ma_mo_ta", ondelete="SET NULL"))
    ma_chan_doan = db.Column(db.ForeignKey("chan_doan_du_kien.ma_chan_doan", ondelete="SET NULL"))
    ma_chuyen_gia = db.Column(db.ForeignKey("bac_si_duoc_si.ma_chuyen_gia", ondelete="SET NULL"))
    ma_mo_hinh = db.Column(db.ForeignKey("mo_hinh_du_doan.ma_mo_hinh", ondelete="SET NULL"))

    mo_ta_benh_an = db.relationship("MoTaBenhAn", back_populates="ket_qua_list")
    chan_doan = db.relationship("ChanDoanDuKien", back_populates="ket_qua_list")
    bac_si = db.relationship("BacSiDuocSi", back_populates="ket_qua_list")
    mo_hinh = db.relationship("MoHinhDuDoan", back_populates="ket_qua_list")

    trieu_chung_list = db.relationship("TrieuChung", secondary=ket_qua_trieu_chung, back_populates="ket_qua_list")
    nhom_thuoc_list = db.relationship("NhomThuoc", secondary=ket_qua_nhom_thuoc, back_populates="ket_qua_list")
    thuoc_list = db.relationship("ThuocThamKhao", secondary=ket_qua_thuoc, back_populates="ket_qua_list")
    luu_y_list = db.relationship("LuuYAnToan", secondary=ket_qua_luu_y, back_populates="ket_qua_list")

    # 1 — 0..1 LichSuDuDoan (xóa kết quả -> xóa lịch sử kèm theo)
    lich_su = db.relationship("LichSuDuDoan", back_populates="ket_qua", uselist=False, cascade="all, delete-orphan")
    # PhanHoi 0..* — 1 (composition): xóa kết quả -> xóa phản hồi kèm theo
    phan_hoi_list = db.relationship("PhanHoi", back_populates="ket_qua", cascade="all, delete-orphan")


class LichSuDuDoan(db.Model):
    __tablename__ = "lich_su_du_doan"
    ma_lich_su = db.Column(db.Integer, primary_key=True)
    thoi_gian = db.Column(db.DateTime, default=datetime.utcnow)
    ket_qua_tom_tat = db.Column(db.Text)
    ma_ket_qua = db.Column(db.ForeignKey("ket_qua_du_doan.ma_ket_qua", ondelete="CASCADE"), unique=True)

    ket_qua = db.relationship("KetQuaDuDoan", back_populates="lich_su")


class PhanHoi(db.Model):
    __tablename__ = "phan_hoi"
    ma_phan_hoi = db.Column(db.Integer, primary_key=True)
    noi_dung = db.Column(db.Text)
    muc_do_hai_long = db.Column(db.Integer)  # 1 = Đồng ý (APPROVE), 0 = Không đồng ý (REJECT)
    trang_thai = db.Column(db.String(30), index=True)  # [hạ tầng US18] 'APPROVE' | 'REJECT'
    nhom_thuoc_du_doan = db.Column(db.String(255))      # [hạ tầng] nhóm thuốc được đánh giá
    da_xu_ly = db.Column(db.Boolean, default=False, index=True)  # [hạ tầng] admin đã duyệt phản hồi
    thoi_gian_gui = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    ma_nguoi_dung = db.Column(db.ForeignKey("nguoi_dung.ma_nguoi_dung", ondelete="SET NULL"))
    # [hạ tầng] nullable: feedback hiện gắn theo nhóm thuốc, không bắt buộc 1 ca cụ thể (như JSONL)
    ma_ket_qua = db.Column(db.ForeignKey("ket_qua_du_doan.ma_ket_qua", ondelete="CASCADE"), nullable=True)

    nguoi_dung = db.relationship("NguoiDung", back_populates="phan_hoi_list")
    ket_qua = db.relationship("KetQuaDuDoan", back_populates="phan_hoi_list")


# ─────────────────────────────────────────────────────────────────────────────
# THỐNG KÊ, DỮ LIỆU HUẤN LUYỆN, MÔ HÌNH
# ─────────────────────────────────────────────────────────────────────────────
class ThongKeBaoCao(db.Model):
    __tablename__ = "thong_ke_bao_cao"
    ma_bao_cao = db.Column(db.Integer, primary_key=True)
    loai_bao_cao = db.Column(db.String(100))
    thoi_gian_lap = db.Column(db.DateTime, default=datetime.utcnow)
    ma_quan_tri = db.Column(db.ForeignKey("quan_tri_vien.ma_quan_tri", ondelete="SET NULL"))

    quan_tri_vien = db.relationship("QuanTriVien", back_populates="bao_cao_list")


class DuLieuHuanLuyen(db.Model):
    __tablename__ = "du_lieu_huan_luyen"
    ma_du_lieu = db.Column(db.Integer, primary_key=True)
    mo_ta_benh_an = db.Column(db.Text)
    trieu_chung = db.Column(db.Text)
    nhom_thuoc = db.Column(db.String(255))
    ma_quan_tri = db.Column(db.ForeignKey("quan_tri_vien.ma_quan_tri", ondelete="SET NULL"))

    quan_tri_vien = db.relationship("QuanTriVien", back_populates="du_lieu_list")


class MoHinhDuDoan(db.Model):
    __tablename__ = "mo_hinh_du_doan"
    ma_mo_hinh = db.Column(db.Integer, primary_key=True)
    thuat_toan = db.Column(db.String(150))
    do_chinh_xac = db.Column(db.Float)

    ket_qua_list = db.relationship("KetQuaDuDoan", back_populates="mo_hinh")


# Danh sách bảng kỳ vọng (dùng cho test đối chiếu).
EXPECTED_TABLES = {
    "nguoi_dung", "tai_khoan", "quan_tri_vien", "bac_si_duoc_si",
    "mo_ta_benh_an", "trieu_chung", "chan_doan_du_kien",
    "nhom_thuoc", "thuoc_tham_khao", "luu_y_an_toan",
    "ket_qua_du_doan", "lich_su_du_doan", "phan_hoi",
    "thong_ke_bao_cao", "du_lieu_huan_luyen", "mo_hinh_du_doan",
    # bảng nối N-N
    "mo_ta_trieu_chung", "ket_qua_trieu_chung", "ket_qua_nhom_thuoc",
    "ket_qua_thuoc", "ket_qua_luu_y", "nhom_thuoc_thuoc",
}
