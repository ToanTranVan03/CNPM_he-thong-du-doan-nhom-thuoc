from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))
    specialty = db.Column(db.String(100))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
symptom_drug_mapping = db.Table(
    'symptom_drug_mapping',
    db.Column('symptom_id', db.Integer, db.ForeignKey('trieu_chung.id', ondelete='CASCADE'), primary_key=True),
    db.Column('drug_group_id', db.Integer, db.ForeignKey('nhom_thuoc.id', ondelete='CASCADE'), primary_key=True)
)
class NhomThuoc(db.Model):
    """Nhóm thuốc — ví dụ: Thuốc kháng sinh, Thuốc giảm đau hạ sốt..."""
    __tablename__ = 'nhom_thuoc'

    id     = db.Column(db.Integer, primary_key=True)
    ten_nhom = db.Column(db.String(255), nullable=False, unique=True)
    mo_ta  = db.Column(db.String(500))
    thuoc_list = db.relationship(
        'Thuoc',
        backref='nhom_thuoc',
        lazy=True,
        cascade='all, delete-orphan',
    )

    def to_dict(self):
        return {
            'id':       self.id,
            'ten_nhom': self.ten_nhom,
            'mo_ta':    self.mo_ta,
        }
class Thuoc(db.Model):
    """Thuốc cụ thể liên kết với một NhomThuoc qua khóa ngoại nhom_thuoc_id."""
    __tablename__ = 'thuoc'

    id              = db.Column(db.Integer, primary_key=True)
    ten_thuoc       = db.Column(db.String(255), nullable=False)
    hoat_chat       = db.Column(db.String(255))
    ham_luong       = db.Column(db.String(100))
    dang_bao_che    = db.Column(db.String(100))
    hang_san_xuat   = db.Column(db.String(255))
    nuoc_san_xuat   = db.Column(db.String(100))
    so_dang_ky      = db.Column(db.String(100))
    gia_tham_khao   = db.Column(db.Float)
    don_vi_tinh     = db.Column(db.String(50))
    mo_ta           = db.Column(db.Text)

    nhom_thuoc_id = db.Column(
        db.Integer,
        db.ForeignKey('nhom_thuoc.id', ondelete='CASCADE'),
        nullable=False,
    )

    def to_dict(self):
        return {
            'id':             self.id,
            'ten_thuoc':      self.ten_thuoc,
            'hoat_chat':      self.hoat_chat,
            'ham_luong':      self.ham_luong,
            'dang_bao_che':   self.dang_bao_che,
            'hang_san_xuat':  self.hang_san_xuat,
            'nuoc_san_xuat':  self.nuoc_san_xuat,
            'so_dang_ky':     self.so_dang_ky,
            'gia_tham_khao':  self.gia_tham_khao,
            'don_vi_tinh':    self.don_vi_tinh,
            'mo_ta':          self.mo_ta,
            'nhom_thuoc_id':  self.nhom_thuoc_id,
            'nhom_thuoc': {
                'id':       self.nhom_thuoc.id,
                'ten_nhom': self.nhom_thuoc.ten_nhom,
            } if self.nhom_thuoc else None,
        }
class TrieuChung(db.Model):
    """Bảng từ điển triệu chứng."""
    __tablename__ = 'trieu_chung'

    id = db.Column(db.Integer, primary_key=True)
    ma = db.Column(db.String(100), unique=True, nullable=True)
    ten = db.Column(db.String(255), nullable=False)
    ten_en = db.Column(db.String(255))
    synonyms = db.Column(db.Text)  # JSON array stored as text
    mo_ta = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── THIẾT LẬP MAPPING CHO TASK 19 ────────────────────────────────────────
  
    nhom_thuoc_list = db.relationship(
        'NhomThuoc', 
        secondary=symptom_drug_mapping, 
        backref=db.backref('trieu_chung_list', lazy='dynamic')
    )
    # ────────────────────────────────────────────────────────────────────────

    def to_dict(self):
        return {
            'id': self.id,
            'ma': self.ma,
            'ten': self.ten,
            'ten_en': self.ten_en,
            'synonyms': json_loads(self.synonyms) if self.synonyms else [],
            'mo_ta': self.mo_ta,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
# =========================================================
# 6. BẢNG LƯU PHẢN HỒI ĐÁNH GIÁ CỦA BÁC SĨ (TASK 45)
# =========================================================
class DanhGiaDuDoan(db.Model):
    __tablename__ = 'danh_gia_du_doan'

    id = db.Column(db.Integer, primary_key=True)
    trieu_chung_nhap = db.Column(db.String(255), nullable=False)
    trang_thai = db.Column(db.String(50), nullable=False)  # APPROVE / REJECT / REVIEWED
    ghi_chu = db.Column(db.Text, nullable=True)
    xu_ly = db.Column(db.String(20), default="CHUA_XU_LY")  # CHUA_XU_LY / DA_XU_LY
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'trieu_chung_nhap': self.trieu_chung_nhap,
            'trang_thai': self.trang_thai,
            'ghi_chu': self.ghi_chu,
            'xu_ly': self.xu_ly or "CHUA_XU_LY",
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

def json_loads(s: str):
    try:
        return __import__('json').loads(s)
    except Exception:
        return []