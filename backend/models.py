from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

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


class NhomThuoc(db.Model):
    """Nhóm thuốc — ví dụ: Thuốc kháng sinh, Thuốc giảm đau hạ sốt..."""
    __tablename__ = 'nhom_thuoc'

    id     = db.Column(db.Integer, primary_key=True)
    ten_nhom = db.Column(db.String(255), nullable=False, unique=True)
    mo_ta  = db.Column(db.String(500))

    # Một nhóm thuốc có nhiều thuốc (one-to-many).
    # cascade='all, delete-orphan': xóa nhóm → xóa tất cả thuốc trong nhóm.
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
    hoat_chat       = db.Column(db.String(255))          # hoạt chất chính
    ham_luong       = db.Column(db.String(100))          # 500mg, 250mg/5ml…
    dang_bao_che    = db.Column(db.String(100))          # viên nén, siro, thuốc bôi…
    hang_san_xuat   = db.Column(db.String(255))
    nuoc_san_xuat   = db.Column(db.String(100))
    so_dang_ky      = db.Column(db.String(100))          # số đăng ký lưu hành
    gia_tham_khao   = db.Column(db.Float)                # VNĐ
    don_vi_tinh     = db.Column(db.String(50))           # hộp, lọ, tuýp…
    mo_ta           = db.Column(db.Text)

    # ── KHÓA NGOẠI ──────────────────────────────────────────────────────────
    # nhom_thuoc_id tham chiếu tới nhom_thuoc.id
    # ondelete='CASCADE': nếu xóa nhóm ở tầng DB thì thuốc cũng bị xóa
    nhom_thuoc_id = db.Column(
        db.Integer,
        db.ForeignKey('nhom_thuoc.id', ondelete='CASCADE'),
        nullable=False,
    )
    # ────────────────────────────────────────────────────────────────────────

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
            # embed thông tin nhóm để frontend không cần gọi thêm
            'nhom_thuoc': {
                'id':       self.nhom_thuoc.id,
                'ten_nhom': self.nhom_thuoc.ten_nhom,
            } if self.nhom_thuoc else None,
        }
