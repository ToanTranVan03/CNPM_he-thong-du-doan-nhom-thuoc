"""Di trú user từ data/users.json sang Postgres (nguoi_dung + tai_khoan).

Chạy 1 lần khi bật DB. Idempotent: user đã có (theo email) sẽ được cập nhật, không nhân đôi.
Chạy:  python scripts/migrate_users.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402


def main():
    if not A.DB_ENABLED:
        print("DB chưa bật (DATABASE_URL?) — không migrate được.")
        return 1
    users_path = A.USERS_PATH
    if not users_path.exists():
        print(f"Không thấy {users_path}")
        return 1
    data = json.loads(users_path.read_text(encoding="utf-8"))
    users = data.get("users", []) if isinstance(data, dict) else []
    print(f"Đọc {len(users)} user từ {users_path.name}")

    with A.app.app_context():
        for u in users:
            A._upsert_user_db(u)
        A.db.session.commit()
        total = A.db.session.query(A.db_models.NguoiDung).count()
        with_admin = A.db.session.query(A.db_models.NguoiDung).filter_by(vai_tro="admin").count()
    print(f"Đã migrate. Tổng nguoi_dung trong DB: {total} (admin: {with_admin})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
