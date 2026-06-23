"""Drop the obsolete benh_an_mau table from DATABASE_URL.

Safe to run repeatedly. This migration intentionally deletes the five seed rows
because the product feature has been removed.
"""

import sys
from pathlib import Path

import sqlalchemy as sa

ROOT = Path(__file__).resolve().parent.parent


def load_env_url():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL") and "=" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def drop_benh_an_mau(engine):
    with engine.begin() as connection:
        if not sa.inspect(connection).has_table("benh_an_mau"):
            return False, 0
        removed_rows = connection.execute(
            sa.text("SELECT count(*) FROM benh_an_mau")
        ).scalar_one()
        connection.execute(sa.text("DROP TABLE IF EXISTS benh_an_mau"))
    return True, removed_rows


def main():
    url = load_env_url()
    if not url:
        print("Không tìm thấy DATABASE_URL trong .env")
        return 1
    try:
        engine = sa.create_engine(url)
        existed, removed_rows = drop_benh_an_mau(engine)
    except Exception as exc:
        print(f"Không thể xóa bảng benh_an_mau: {type(exc).__name__}")
        return 1
    if existed:
        print(f"Đã xóa bảng benh_an_mau ({removed_rows} dòng).")
    else:
        print("Bảng benh_an_mau không tồn tại; không cần thay đổi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
