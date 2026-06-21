"""Tạo (create_all) toàn bộ bảng theo backend/models.py vào database trỏ bởi DATABASE_URL.

KHÔNG xóa dữ liệu cũ (create_all chỉ tạo bảng còn THIẾU). Dùng để khởi tạo schema thật
trên Postgres CNPM. Chạy:  python scripts/init_db.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from flask import Flask  # noqa: E402
import sqlalchemy as sa  # noqa: E402
from models import db, EXPECTED_TABLES  # noqa: E402


def load_env_url():
    p = ROOT / ".env"
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL") and "=" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def main():
    url = load_env_url()
    if not url:
        print("Không tìm thấy DATABASE_URL trong .env")
        return 1
    try:
        eng = sa.create_engine(url)
        with eng.connect() as c:
            ver = c.execute(sa.text("show server_version")).scalar()
            dbname = c.execute(sa.text("select current_database()")).scalar()
        print(f"[OK] Kết nối: {dbname} (PostgreSQL {ver})")
    except Exception as e:
        print("[FAIL] Không kết nối được:", str(e).splitlines()[0][:160])
        return 1

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        # Đảm bảo cột HẠ TẦNG cho auth (nếu DB đã tạo từ trước, create_all không tự thêm cột).
        for stmt in (
            "ALTER TABLE nguoi_dung ADD COLUMN IF NOT EXISTS created_at TIMESTAMP",
            "ALTER TABLE tai_khoan ADD COLUMN IF NOT EXISTS session_token VARCHAR(255)",
            "ALTER TABLE tai_khoan ADD COLUMN IF NOT EXISTS session_expires_at TIMESTAMP",
            "ALTER TABLE tai_khoan ADD COLUMN IF NOT EXISTS reset_code_hash VARCHAR(255)",
            "ALTER TABLE tai_khoan ADD COLUMN IF NOT EXISTS reset_code_expires_at TIMESTAMP",
            "CREATE INDEX IF NOT EXISTS ix_tai_khoan_session_token ON tai_khoan(session_token)",
        ):
            db.session.execute(sa.text(stmt))
        db.session.commit()
        tables = set(sa.inspect(db.engine).get_table_names())

    created = sorted(EXPECTED_TABLES & tables)
    missing = EXPECTED_TABLES - tables
    print(f"[OK] Có {len(created)}/{len(EXPECTED_TABLES)} bảng trong DB:")
    for t in created:
        print("   -", t)
    if missing:
        print("[FAIL] Thiếu bảng:", missing)
        return 1
    print("=> Đã tạo đủ schema trên Postgres.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
