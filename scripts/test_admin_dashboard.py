"""US19 — Test Dashboard Admin: phân quyền + tổng hợp thống kê (chỉ đọc).

Chạy:  python scripts/test_admin_dashboard.py
Không cần server; dùng Flask test_client + fixture JSONL tạm (KHÔNG đụng data thật).
"""

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import os
os.environ["DB_DISABLED"] = "1"  # test JSON-mode (auth users.json + stats JSONL), không đụng Postgres

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402
import stats_source  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")


def write_jsonl(path: Path, rows):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")


def setup_fixtures(tmp: Path):
    # ── Lịch sử dự đoán mẫu (3 ngày, 5 ca) ──
    preds = [
        {"ts": "2026-06-18T08:00:00+00:00", "status": "suggest", "predicted_group": "thuốc kháng histamin"},
        {"ts": "2026-06-18T09:00:00+00:00", "status": "suggest", "predicted_group": "thuốc kháng histamin"},
        {"ts": "2026-06-19T10:00:00+00:00", "status": "emergency", "predicted_group": None},
        {"ts": "2026-06-19T11:00:00+00:00", "status": "safety_block", "predicted_group": "thuốc kháng sinh"},
        {"ts": "2026-06-20T07:30:00+00:00", "status": "suggest", "predicted_group": "thuốc giảm đau hạ sốt"},
        "DÒNG-HỎNG-KHÔNG-PHẢI-JSON",  # phải bị bỏ qua, không crash
    ]
    pred_path = tmp / "prediction_log.jsonl"
    pred_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) if isinstance(r, dict) else r for r in preds),
        encoding="utf-8",
    )

    # ── Feedback mẫu: 3 Đồng ý + 1 Không đồng ý => agree_rate = 75.0 ──
    fb = [
        {"ts": "2026-06-18T08:05:00+00:00", "verdict": "APPROVE"},
        {"ts": "2026-06-18T09:05:00+00:00", "verdict": "APPROVE"},
        {"ts": "2026-06-19T10:05:00+00:00", "verdict": "REJECT"},
        {"ts": "2026-06-20T07:35:00+00:00", "verdict": "approve"},  # chữ thường vẫn tính
    ]
    write_jsonl(tmp / "feedback.jsonl", fb)

    stats_source.PREDICTION_LOG_PATH = pred_path
    stats_source.FEEDBACK_LOG_PATH = tmp / "feedback.jsonl"


def setup_users(tmp: Path):
    users_path = tmp / "users.json"
    now = datetime.now(timezone.utc)
    expires = A.iso_utc(now + A.timedelta(days=1))
    store = {
        "users": [
            {"id": "a1", "name": "Quản trị", "email": "admin@pharma.vn", "password_hash": "x",
             "role": "admin", "session_token": "ADMIN_TOKEN", "session_expires_at": expires},
            {"id": "u1", "name": "Người dùng", "email": "user@pharma.vn", "password_hash": "x",
             "session_token": "USER_TOKEN", "session_expires_at": expires},
        ]
    }
    users_path.write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")
    A.USERS_PATH = users_path


def main():
    tmp = Path(tempfile.mkdtemp(prefix="us19_"))
    setup_fixtures(tmp)
    setup_users(tmp)
    client = A.app.test_client()

    def get(token=None, qs=""):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return client.get(f"/api/admin/stats{qs}", headers=headers)

    print("== PHÂN QUYỀN ==")
    check("chưa đăng nhập -> 401", get().status_code == 401)
    check("user thường -> 403", get("USER_TOKEN").status_code == 403)
    check("token sai -> 401", get("SAI").status_code == 401)
    r = get("ADMIN_TOKEN")
    check("admin -> 200", r.status_code == 200)

    print("== TỔNG HỢP THỐNG KÊ (toàn bộ) ==")
    d = r.get_json()
    check("total_predictions = 5", d["total_predictions"] == 5)
    check("by_status.suggest = 3", d["by_status"]["suggest"] == 3)
    check("by_status.emergency = 1", d["by_status"]["emergency"] == 1)
    check("by_status.safety_block = 1", d["by_status"]["safety_block"] == 1)
    check("agree_count = 3", d["agree_count"] == 3)
    check("disagree_count = 1", d["disagree_count"] == 1)
    check("feedback_total = 4", d["feedback_total"] == 4)
    check("agree_rate = 75.0", d["agree_rate"] == 75.0)
    check("over_time có 3 ngày", len(d["predictions_over_time"]) == 3)
    check("over_time sắp xếp tăng dần", [p["date"] for p in d["predictions_over_time"]] == sorted(p["date"] for p in d["predictions_over_time"]))
    top = {g["group"]: g["count"] for g in d["top_groups"]}
    check("top_groups: kháng histamin = 2", top.get("thuốc kháng histamin") == 2)
    check("top_groups không gồm None", None not in top and "" not in top)

    print("== LỌC THEO NGÀY ==")
    d2 = get("ADMIN_TOKEN", "?from=2026-06-19&to=2026-06-19").get_json()
    check("lọc 1 ngày -> 2 ca", d2["total_predictions"] == 2)
    check("lọc 1 ngày -> feedback 1", d2["feedback_total"] == 1)
    d3 = get("ADMIN_TOKEN", "?from=2026-06-20").get_json()
    check("from mở -> 1 ca", d3["total_predictions"] == 1)
    d4 = get("ADMIN_TOKEN", "?from=SAI-NGAY").get_json()
    check("from sai định dạng -> bỏ lọc (5 ca)", d4["total_predictions"] == 5)

    print("== PHÂN QUYỀN QUA ADMIN_EMAILS ==")
    saved = A.ADMIN_EMAILS
    A.ADMIN_EMAILS = frozenset({"user@pharma.vn"})
    check("user trong ADMIN_EMAILS -> 200", get("USER_TOKEN").status_code == 200)
    A.ADMIN_EMAILS = saved

    print("== STORE RỖNG (chưa có US15/US18) ==")
    stats_source.PREDICTION_LOG_PATH = tmp / "khong-ton-tai.jsonl"
    stats_source.FEEDBACK_LOG_PATH = tmp / "khong-ton-tai-2.jsonl"
    d5 = get("ADMIN_TOKEN").get_json()
    check("không file -> total 0", d5["total_predictions"] == 0)
    check("không file -> agree_rate None", d5["agree_rate"] is None)

    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
