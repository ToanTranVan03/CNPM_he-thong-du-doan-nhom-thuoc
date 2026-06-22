"""Seed dữ liệu DANH MỤC vào Postgres CNPM từ dữ liệu sẵn có của dự án.

Đổ các bảng master (không phải dữ liệu giao dịch runtime):
  - nhom_thuoc        <- distinct nhom_thuoc (CSV), mô tả từ drug_group_representatives.json
  - thuoc_tham_khao   <- distinct ten_thuoc (CSV)
  - nhom_thuoc_thuoc  <- liên kết N-N (ten_thuoc <-> nhom_thuoc) từ CSV
  - trieu_chung       <- distinct triệu chứng (cột trieu_chung, tách bằng ';')
  - chan_doan_du_kien <- distinct chan_doan_du_kien (CSV)
  - mo_hinh_du_doan   <- metadata model hiện tại (models/metadata.json)

Idempotent: xóa sạch các bảng danh mục trên rồi nạp lại. KHÔNG đụng bảng giao dịch
(nguoi_dung, ket_qua_du_doan, lich_su_du_doan, phan_hoi...).

Chạy:  python scripts/seed_db.py
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from flask import Flask  # noqa: E402
from models import (  # noqa: E402
    db, NhomThuoc, ThuocThamKhao, TrieuChung, ChanDoanDuKien, MoHinhDuDoan,
    nhom_thuoc_thuoc,
)

CSV_PATH = ROOT / "data" / "train_ready_mapped_drug_groups.csv"
REPS_PATH = ROOT / "data" / "drug_group_representatives.json"
META_PATH = ROOT / "models" / "metadata.json"


def load_env_url():
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL") and "=" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def collect():
    groups, drugs, syms, diags = set(), set(), set(), set()
    pairs = set()  # (ten_thuoc, nhom_thuoc)
    with CSV_PATH.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            g = (r.get("nhom_thuoc") or "").strip()
            d = (r.get("ten_thuoc") or "").strip()
            cd = (r.get("chan_doan_du_kien") or "").strip()
            if g:
                groups.add(g)
            if d:
                drugs.add(d)
            if cd:
                diags.add(cd)
            if g and d:
                pairs.add((d, g))
            for s in (r.get("trieu_chung") or "").split(";"):
                s = s.strip()
                if s:
                    syms.add(s)
    return groups, drugs, pairs, syms, diags


def group_descriptions():
    try:
        reps = json.loads(REPS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for k, v in reps.items():
        if k.startswith("_") or not isinstance(v, dict):
            continue
        ai = v.get("active_ingredients") or []
        note = v.get("note") or ""
        mo_ta = ("Hoạt chất minh hoạ: " + ", ".join(ai)) if ai else ""
        if note:
            mo_ta = (mo_ta + " — " + note) if mo_ta else note
        out[k] = mo_ta[:480]
    return out


def model_meta():
    try:
        m = json.loads(META_PATH.read_text(encoding="utf-8"))
        return m.get("model_type", "tfidf_linear_svm"), float(m.get("accuracy") or 0.0)
    except Exception:
        return "tfidf_linear_svm", 0.0


def main():
    url = load_env_url()
    if not url:
        print("Không có DATABASE_URL trong .env")
        return 1

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    print("Đọc CSV...")
    groups, drugs, pairs, syms, diags = collect()
    descs = group_descriptions()
    algo, acc = model_meta()
    print(f"  nhóm={len(groups)} thuốc={len(drugs)} cặp(nhóm-thuốc)={len(pairs)} "
          f"triệu_chứng={len(syms)} chẩn_đoán={len(diags)}")

    with app.app_context():
        # Xóa danh mục cũ (FK-safe: bảng nối trước).
        db.session.execute(nhom_thuoc_thuoc.delete())
        for model in (ThuocThamKhao, NhomThuoc, TrieuChung, ChanDoanDuKien, MoHinhDuDoan):
            db.session.query(model).delete()
        db.session.commit()

        # Vài giá trị trong CSV vượt 255 ký tự (câu mô tả điều trị, không phải tên thuốc/triệu
        # chứng thật) -> cắt cho khớp cột String(255). Key dict GIỮ chuỗi gốc để liên kết N-N đúng.
        cap = lambda s, n=255: s if s is None or len(s) <= n else s[: n - 1] + "…"
        nhom_objs = {g: NhomThuoc(ten_nhom_thuoc=cap(g), mo_ta=descs.get(g)) for g in sorted(groups)}
        thuoc_objs = {d: ThuocThamKhao(ten_thuoc=cap(d)) for d in sorted(drugs)}
        db.session.add_all(nhom_objs.values())
        db.session.add_all(thuoc_objs.values())
        db.session.flush()  # gán id

        for d, g in pairs:  # liên kết N-N nhóm <-> thuốc
            nhom_objs[g].thuoc_list.append(thuoc_objs[d])

        db.session.add_all([TrieuChung(ten_trieu_chung=cap(s), tu_khoa=s) for s in sorted(syms)])
        db.session.add_all([ChanDoanDuKien(ten_chan_doan=cap(c)) for c in sorted(diags)])
        db.session.add(MoHinhDuDoan(thuat_toan=algo, do_chinh_xac=acc))
        db.session.commit()

        # Báo cáo
        print("Đã seed:")
        print("  nhom_thuoc        =", db.session.query(NhomThuoc).count())
        print("  thuoc_tham_khao   =", db.session.query(ThuocThamKhao).count())
        print("  nhom_thuoc_thuoc  =", db.session.execute(db.select(db.func.count()).select_from(nhom_thuoc_thuoc)).scalar())
        print("  trieu_chung       =", db.session.query(TrieuChung).count())
        print("  chan_doan_du_kien =", db.session.query(ChanDoanDuKien).count())
        print("  mo_hinh_du_doan   =", db.session.query(MoHinhDuDoan).count())
        # kiểm tra liên kết mẫu
        sample = db.session.query(NhomThuoc).filter_by(ten_nhom_thuoc="thuốc giảm đau hạ sốt").first()
        if sample:
            print(f"  [check] '{sample.ten_nhom_thuoc}' có {len(sample.thuoc_list)} thuốc liên kết")
    print("=> Seed danh mục xong.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
