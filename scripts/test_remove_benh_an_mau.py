"""Regression test for the idempotent benh_an_mau removal migration."""

import sys
from pathlib import Path

import sqlalchemy as sa

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from remove_benh_an_mau import drop_benh_an_mau  # noqa: E402


def main():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(sa.text(
            "CREATE TABLE benh_an_mau (ma_benh_an_mau INTEGER PRIMARY KEY, tieu_de VARCHAR(255))"
        ))
        connection.execute(sa.text(
            "INSERT INTO benh_an_mau (ma_benh_an_mau, tieu_de) VALUES (1, 'seed')"
        ))

    existed, removed_rows = drop_benh_an_mau(engine)
    assert existed is True
    assert removed_rows == 1
    assert not sa.inspect(engine).has_table("benh_an_mau")

    existed_again, removed_rows_again = drop_benh_an_mau(engine)
    assert existed_again is False
    assert removed_rows_again == 0
    print("PASS: migration xóa bảng và chạy lặp lại an toàn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
