"""US19 — Lớp ĐỌC dữ liệu cho Dashboard thống kê (CHỈ ĐỌC, không ghi).

Đây là điểm tách (adapter) DUY NHẤT giữa Dashboard và nơi lưu dữ liệu. US19 không tự
sinh dữ liệu lịch sử/feedback — việc đó thuộc US15 (lưu lịch sử dự đoán) và US18 (thu
phản hồi Đồng ý/Không đồng ý). Khi hai story đó được gộp vào nhánh này, CHỈ cần sửa
2 hàm `read_predictions` / `read_feedback` ở đây để trỏ sang nguồn thật (DB hay file
khác); toàn bộ endpoint thống kê và UI Dashboard không phải đổi.

Mặc định đọc từ JSONL theo phong cách file-based của nhánh (giống learned_context.jsonl):

  data/prediction_log.jsonl   mỗi dòng 1 ca dự đoán
      {"ts": "2026-06-20T08:00:00+00:00", "status": "suggest|emergency|safety_block",
       "predicted_group": "thuốc kháng histamin", "user_email": "..."}

  data/feedback.jsonl         mỗi dòng 1 phản hồi của người dùng
      {"ts": "2026-06-20T08:05:00+00:00", "verdict": "APPROVE|REJECT",
       "predicted_group": "...", "user_email": "..."}

Thiếu file -> trả [] (Dashboard hiển thị 0), không lỗi.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent

PREDICTION_LOG_PATH = Path(
    os.environ.get("PREDICTION_LOG_PATH", _PROJECT_ROOT / "data" / "prediction_log.jsonl")
)
FEEDBACK_LOG_PATH = Path(
    os.environ.get("FEEDBACK_LOG_PATH", _PROJECT_ROOT / "data" / "feedback.jsonl")
)

# Trạng thái ca dự đoán hợp lệ (khớp các nhánh kết thúc của /api/predict).
PREDICTION_STATUSES = ("suggest", "emergency", "safety_block")
# Phản hồi: APPROVE = "Đồng ý", REJECT = "Không đồng ý" (khớp DanhGiaDuDoan.trang_thai của US18).
FEEDBACK_VERDICTS = ("APPROVE", "REJECT")


def _read_jsonl(path: Path) -> list[dict]:
    """Đọc file JSONL, bỏ qua dòng hỏng. Thiếu file -> []."""
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    except OSError:
        return []
    return rows


def _record_date(record: dict) -> str | None:
    """Lấy phần ngày 'YYYY-MM-DD' từ trường ts (ISO 8601). Lỗi -> None."""
    ts = record.get("ts")
    if not isinstance(ts, str) or not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        # Cho phép ts đã là 'YYYY-MM-DD' sẵn.
        return ts[:10] if len(ts) >= 10 else None


def _within_range(record: dict, date_from: str | None, date_to: str | None) -> bool:
    if not date_from and not date_to:
        return True
    day = _record_date(record)
    if day is None:
        return False
    if date_from and day < date_from:
        return False
    if date_to and day > date_to:
        return False
    return True


def read_predictions(date_from: str | None = None, date_to: str | None = None) -> list[dict]:
    """Danh sách ca dự đoán đã lưu, lọc theo khoảng ngày (YYYY-MM-DD) nếu có."""
    return [r for r in _read_jsonl(PREDICTION_LOG_PATH) if _within_range(r, date_from, date_to)]


def read_feedback(date_from: str | None = None, date_to: str | None = None) -> list[dict]:
    """Danh sách phản hồi Đồng ý/Không đồng ý, lọc theo khoảng ngày nếu có."""
    return [r for r in _read_jsonl(FEEDBACK_LOG_PATH) if _within_range(r, date_from, date_to)]


def record_day(record: dict) -> str | None:
    """Tiện ích public để endpoint gộp theo ngày (tái dùng cùng logic parse ts)."""
    return _record_date(record)
