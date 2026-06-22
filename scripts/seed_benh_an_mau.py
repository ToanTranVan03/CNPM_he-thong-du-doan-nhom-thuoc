"""US29 (SCRUM-116): seed vài BỆNH ÁN MẪU mặc định (nếu bảng đang rỗng).

Idempotent: chỉ thêm khi chưa có. Chạy:  python scripts/seed_benh_an_mau.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402

SAMPLES = [
    ("Cảm cúm thông thường",
     "Bệnh nhân sốt nhẹ, đau đầu, sổ mũi, hắt hơi, đau họng nhẹ 2 ngày nay, không khó thở.",
     "Triệu chứng hô hấp trên nhẹ"),
    ("Viêm họng cấp",
     "Đau họng dữ dội, nuốt đau, sốt 38.5 độ, amidan sưng đỏ có mủ trắng, nổi hạch góc hàm.",
     "Nghi viêm họng do vi khuẩn"),
    ("Tiêu chảy cấp",
     "Đi ngoài phân lỏng nhiều lần trong ngày, đau quặn bụng từng cơn, buồn nôn, mệt, có dấu mất nước.",
     "Rối loạn tiêu hóa cấp"),
    ("Dị ứng nổi mề đay",
     "Nổi mẩn đỏ, ngứa nhiều toàn thân, nổi mảng sẩn phù sau khi ăn hải sản, không khó thở.",
     "Phản ứng dị ứng da"),
    ("Đau khớp gối",
     "Đau và sưng khớp gối hai bên, cứng khớp buổi sáng khoảng 30 phút, đi lại khó khăn, không sốt.",
     "Bệnh lý cơ-xương-khớp"),
]


def main():
    if not A.DB_ENABLED:
        print("DB chưa bật — bỏ qua.")
        return 1
    with A.app.app_context():
        existing = A.db.session.query(A.db_models.BenhAnMau).count()
        if existing:
            print(f"Đã có {existing} bệnh án mẫu — không seed lại.")
            return 0
        for tieu_de, noi_dung, mo_ta in SAMPLES:
            A.db.session.add(A.db_models.BenhAnMau(tieu_de=tieu_de, noi_dung=noi_dung, mo_ta=mo_ta))
        A.db.session.commit()
        total = A.db.session.query(A.db_models.BenhAnMau).count()
    print(f"Đã seed {total} bệnh án mẫu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
