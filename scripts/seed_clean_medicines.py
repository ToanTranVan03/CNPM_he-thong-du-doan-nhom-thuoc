"""Dọn thuốc trùng tên và bổ sung danh mục thuốc mẫu đa dạng.
Chạy tại thư mục gốc project: py scripts/seed_clean_medicines.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app import app, db  # noqa: E402
from models import NhomThuoc, Thuoc  # noqa: E402

SAMPLE_GROUPS = [
    "Thuốc giảm đau hạ sốt", "Thuốc kháng viêm không steroid", "Thuốc kháng sinh",
    "Thuốc kháng nấm/ký sinh trùng ngoài da", "Thuốc long đờm / giảm ho",
    "Thuốc giãn phế quản", "Thuốc kháng histamin", "Thuốc tiêu hóa",
    "Thuốc tim mạch", "Thuốc thần kinh", "Thuốc nội tiết", "Vitamin và khoáng chất"
]

SAMPLE_MEDICINES = [
    ("Paracetamol", "Paracetamol", "500mg", "Viên nén", "Thuốc giảm đau hạ sốt"),
    ("Ibuprofen", "Ibuprofen", "200mg", "Viên nén", "Thuốc kháng viêm không steroid"),
    ("Naproxen", "Naproxen", "250mg", "Viên nén", "Thuốc kháng viêm không steroid"),
    ("Diclofenac", "Diclofenac sodium", "50mg", "Viên nén", "Thuốc kháng viêm không steroid"),
    ("Amoxicillin", "Amoxicillin", "500mg", "Viên nang", "Thuốc kháng sinh"),
    ("Azithromycin", "Azithromycin", "500mg", "Viên nén", "Thuốc kháng sinh"),
    ("Cefixime", "Cefixime", "200mg", "Viên nang", "Thuốc kháng sinh"),
    ("Clotrimazole", "Clotrimazole", "1%", "Kem bôi", "Thuốc kháng nấm/ký sinh trùng ngoài da"),
    ("Terbinafine", "Terbinafine", "1%", "Kem bôi", "Thuốc kháng nấm/ký sinh trùng ngoài da"),
    ("Cetirizine", "Cetirizine", "10mg", "Viên nén", "Thuốc kháng histamin"),
    ("Loratadine", "Loratadine", "10mg", "Viên nén", "Thuốc kháng histamin"),
    ("Salbutamol", "Salbutamol", "100mcg/liều", "Khí dung", "Thuốc giãn phế quản"),
    ("Bromhexine", "Bromhexine", "8mg", "Viên nén", "Thuốc long đờm / giảm ho"),
    ("Ambroxol", "Ambroxol", "30mg", "Viên nén", "Thuốc long đờm / giảm ho"),
    ("Omeprazole", "Omeprazole", "20mg", "Viên nang", "Thuốc tiêu hóa"),
    ("Domperidone", "Domperidone", "10mg", "Viên nén", "Thuốc tiêu hóa"),
    ("Amlodipine", "Amlodipine", "5mg", "Viên nén", "Thuốc tim mạch"),
    ("Metformin", "Metformin", "500mg", "Viên nén", "Thuốc nội tiết"),
    ("Vitamin C", "Ascorbic acid", "500mg", "Viên nén", "Vitamin và khoáng chất"),
    ("Magnesium B6", "Magnesium lactate + Vitamin B6", "—", "Viên nén", "Vitamin và khoáng chất"),
]


def get_or_create_group(name):
    group = NhomThuoc.query.filter(db.func.lower(NhomThuoc.ten_nhom) == name.lower()).first()
    if not group:
        group = NhomThuoc(ten_nhom=name, mo_ta=f"Nhóm {name.lower()}.")
        db.session.add(group)
        db.session.flush()
    return group


def dedupe_by_name():
    items = Thuoc.query.order_by(Thuoc.ten_thuoc.asc(), Thuoc.id.asc()).all()
    seen = set()
    removed = 0
    for item in items:
        key = (item.ten_thuoc or "").strip().lower()
        if not key:
            continue
        if key in seen:
            db.session.delete(item)
            removed += 1
        else:
            seen.add(key)
    return removed


with app.app_context():
    for name in SAMPLE_GROUPS:
        get_or_create_group(name)
    db.session.commit()

    removed = dedupe_by_name()
    added = 0
    for ten, hoat_chat, ham_luong, dang, group_name in SAMPLE_MEDICINES:
        exists = Thuoc.query.filter(db.func.lower(Thuoc.ten_thuoc) == ten.lower()).first()
        if exists:
            continue
        group = get_or_create_group(group_name)
        db.session.add(Thuoc(
            ten_thuoc=ten,
            hoat_chat=hoat_chat,
            ham_luong=ham_luong,
            dang_bao_che=dang,
            nhom_thuoc_id=group.id,
            don_vi_tinh="Hộp",
            mo_ta=f"Thuốc tham khảo thuộc {group_name.lower()}."
        ))
        added += 1
    db.session.commit()
    print(f"Đã xóa {removed} thuốc trùng tên, bổ sung {added} thuốc mẫu đa dạng.")
