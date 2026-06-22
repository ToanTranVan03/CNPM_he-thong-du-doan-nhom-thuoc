"""US15 + US18 (port) — test ghi lịch sử dự đoán & feedback, và tích hợp với Dashboard US19.

Chạy:  python scripts/test_history_feedback.py
Dùng test_client + file JSONL tạm (KHÔNG đụng data thật).
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


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")


def read_lines(path: Path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    tmp = Path(tempfile.mkdtemp(prefix="us15_18_"))
    stats_source.PREDICTION_LOG_PATH = tmp / "prediction_log.jsonl"
    stats_source.FEEDBACK_LOG_PATH = tmp / "feedback.jsonl"

    # User admin để gọi /api/admin/stats cuối bài.
    expires = A.iso_utc(datetime.now(timezone.utc) + A.timedelta(days=1))
    users = {"users": [{"id": "a1", "name": "Admin", "email": "admin@pharma.vn",
                        "password_hash": "x", "role": "admin",
                        "session_token": "ADMIN", "session_expires_at": expires}]}
    upath = tmp / "users.json"
    upath.write_text(json.dumps(users, ensure_ascii=False), encoding="utf-8")
    A.USERS_PATH = upath

    client = A.app.test_client()

    print("== US15: tự lưu lịch sử khi /api/predict ==")
    r1 = client.post("/api/predict", json={"notes": "tôi bị đau đầu, sổ mũi, hắt hơi mấy hôm nay", "symptoms": []})
    r2 = client.post("/api/predict", json={"notes": "đột nhiên đau thắt ngực dữ dội, khó thở, vã mồ hôi", "symptoms": []})
    r3 = client.post("/api/predict", json={"notes": "xyz", "symptoms": []})  # 400 -> KHÔNG log
    logs = read_lines(stats_source.PREDICTION_LOG_PATH)
    check("predict OTC -> 200", r1.status_code == 200, str(r1.status_code))
    check("predict cấp cứu -> 422", r2.status_code == 422, str(r2.status_code))
    check("ghi đúng 2 dòng (400 không log)", len(logs) == 2, f"{len(logs)} dòng")
    statuses = [x.get("status") for x in logs]
    check("có status 'suggest'", "suggest" in statuses, str(statuses))
    check("có status 'emergency'", "emergency" in statuses, str(statuses))
    suggest_row = next((x for x in logs if x["status"] == "suggest"), {})
    check("suggest có predicted_group", bool(suggest_row.get("predicted_group")), str(suggest_row.get("predicted_group")))
    check("mỗi dòng có ts", all(x.get("ts") for x in logs))

    print("== US18: endpoint feedback ==")
    f_bad = client.post("/api/feedback", json={"verdict": "MAYBE"})
    check("verdict sai -> 400", f_bad.status_code == 400)
    f1 = client.post("/api/feedback", json={"verdict": "APPROVE", "predicted_group": "thuốc kháng histamin"})
    f2 = client.post("/api/feedback", json={"verdict": "reject", "predicted_group": "thuốc kháng histamin"})
    f3 = client.post("/api/feedback", json={"trang_thai": "APPROVE"})  # alias contract toan/main
    check("APPROVE -> 201", f1.status_code == 201, str(f1.status_code))
    check("reject (thường) -> 201", f2.status_code == 201)
    check("alias trang_thai -> 201", f3.status_code == 201)
    fb = read_lines(stats_source.FEEDBACK_LOG_PATH)
    check("ghi 3 dòng feedback", len(fb) == 3, f"{len(fb)} dòng")
    check("verdict được chuẩn hoá HOA", sorted(x["verdict"] for x in fb) == ["APPROVE", "APPROVE", "REJECT"], str([x["verdict"] for x in fb]))

    print("== TÍCH HỢP US19: Dashboard sáng số thật ==")
    s = client.get("/api/admin/stats", headers={"Authorization": "Bearer ADMIN"}).get_json()
    check("total_predictions = 2", s["total_predictions"] == 2, str(s["total_predictions"]))
    check("agree_count = 2", s["agree_count"] == 2, str(s["agree_count"]))
    check("disagree_count = 1", s["disagree_count"] == 1, str(s["disagree_count"]))
    check("agree_rate = 66.7", s["agree_rate"] == 66.7, str(s["agree_rate"]))
    check("top_groups có kháng histamin", any(g["group"] == "thuốc kháng histamin" for g in s["top_groups"]))

    print("=" * 50)
    print(f"TỔNG: {PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
