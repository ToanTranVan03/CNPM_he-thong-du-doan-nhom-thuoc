import ast
import csv
import io
import json
import os
import re
import secrets
import unicodedata
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from itertools import permutations
from pathlib import Path

import joblib
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from translations import (
    disease_description_vi,
    disease_name_vi,
    translate_items,
)
import stats_source  # US19: lớp ĐỌC dữ liệu cho Dashboard thống kê (adapter, chỉ đọc)
import models as db_models  # Tích hợp SQLAlchemy: models domain (Postgres)
from sqlalchemy import text as _sql_text
from lexicon import (
    AUTO_BODY_PARTS,
    AUTO_EXACT_SYMPTOM_KEYWORDS,
    DIAGNOSIS_VI,
    DRUG_GROUP_GUIDANCE,
    RULE_MEDICATION_NAMES,
    UNSUPPORTED_SYMPTOM_KEYWORDS,
    VI_SYMPTOM_KEYWORDS,
)


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def _load_dotenv(path: Path) -> None:
    """Nạp KEY=VALUE từ .env vào os.environ (KHÔNG ghi đè biến môi trường sẵn có).

    Cho phép cấu hình cố định qua .env (vd ADMIN_EMAILS) mà không cần đặt env thủ công.
    """
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = val.strip().strip('"').strip("'")
    except OSError:
        pass


_load_dotenv(PROJECT_ROOT / ".env")

MODEL_DIR = Path(os.environ.get("MODEL_DIR", PROJECT_ROOT / "models"))
MODEL_PATH = MODEL_DIR / "disease_model.joblib"
METADATA_PATH = MODEL_DIR / "metadata.json"
DATA_SOURCE = Path(os.environ.get("DATA_SOURCE", PROJECT_ROOT / "data" / "train_ready_mapped_drug_groups.csv"))
DATA_ARCHIVE = Path(os.environ.get("DATA_ARCHIVE", DATA_SOURCE))
GUIDANCE_PATH = Path(os.environ.get("GUIDANCE_PATH", PROJECT_ROOT / "data" / "disease_guidance.json"))
USERS_PATH = Path(os.environ.get("USERS_PATH", PROJECT_ROOT / "data" / "users.json"))
# US19: danh sách email được cấp quyền Admin (phân tách bằng dấu phẩy). Một user là admin nếu
# email nằm trong danh sách này HOẶC bản ghi user có "role": "admin".
ADMIN_EMAILS = frozenset(
    re.sub(r"\s+", "", e).lower()
    for e in os.environ.get("ADMIN_EMAILS", "").split(",")
    if e.strip()
)
# Vòng 6: mapping nhóm -> 2-3 hoạt chất tiêu biểu (đã curate, làm sạch) cho output trọng tâm.
DRUG_REPRESENTATIVES_PATH = Path(
    os.environ.get("DRUG_REPRESENTATIVES_PATH", PROJECT_ROOT / "data" / "drug_group_representatives.json")
)

app = Flask(__name__, static_folder=None)
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://127.0.0.1:5000",
                "http://127.0.0.1:5001",
                "http://localhost:5000",
                "http://localhost:5001",
            ]
        }
    },
)


# ── TÍCH HỢP SQLAlchemy (Postgres) — GRACEFUL ────────────────────────────────
# Bật DB khi có DATABASE_URL (env hoặc .env) và kết nối được. Thiếu/hỏng -> app vẫn
# chạy chế độ JSON như cũ (DB_ENABLED=False). Tắt cưỡng bức bằng env DB_DISABLED=1.
db = db_models.db


def _resolve_database_url() -> str | None:
    if os.environ.get("DB_DISABLED"):
        return None
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL") and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


DB_ENABLED = False
_database_url = _resolve_database_url()
if _database_url:
    try:
        app.config["SQLALCHEMY_DATABASE_URI"] = _database_url
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        db.init_app(app)
        with app.app_context():
            db.session.execute(_sql_text("SELECT 1"))
        DB_ENABLED = True
        app.logger.info("SQLAlchemy: DB Postgres ĐÃ BẬT")
    except Exception:
        DB_ENABLED = False
        app.logger.warning("SQLAlchemy: không kết nối được DB -> chạy chế độ JSON")


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

model = joblib.load(MODEL_PATH)
metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
features = metadata["features"]
feature_lookup = {feature.lower(): feature for feature in features}
LABEL_TYPE = metadata.get("label_type", "disease")
MIN_RELIABLE_CONFIDENCE = 0.5
# Ngưỡng scoped (vòng 3): nhóm thuốc "rủi ro cao" (sai gây hại) cần độ tin cậy cao hơn
# khi do MODEL đoán (score_type != "rule"). Lớp phòng thủ phụ ngoài các rule đặc hiệu.
MIN_HIGH_RISK_MODEL_CONFIDENCE = 0.85
HIGH_RISK_DRUG_GROUPS = {
    "thuốc kháng sinh",
    "thuốc tim mạch/huyết áp",
    "thuốc thần kinh/tâm thần",
    "thuốc kháng virus",
    "thuốc/điều trị ung thư",
}
# P2.3: bắt thêm nhóm rủi ro cao theo TỪ KHÓA (kể cả khi tên nhóm khác chính tả/biến thể).
# Các nhóm này cần kê đơn/bác sĩ -> không auto-suggest tự tin dù do rule hay model.
HIGH_RISK_GROUP_KEYWORDS = (
    "kháng sinh", "tim mạch", "huyết áp", "tâm thần", "thần kinh", "kháng virus",
    "ung thư", "chống đông", "kháng tiểu cầu", "nội tiết", "miễn dịch", "opioid",
    "đái tháo đường", "tiểu đường", "insulin",  # nhóm ĐTĐ là thuốc KÊ ĐƠN -> né an toàn
)


def is_high_risk_group(group) -> bool:
    if not group:
        return False
    g = str(group).lower()
    return group in HIGH_RISK_DRUG_GROUPS or any(k in g for k in HIGH_RISK_GROUP_KEYWORDS)


# P4: nhóm KHÔNG BAO GIỜ tự gợi ý qua công cụ OTC (điều trị chuyên sâu) -> luôn chuyển khám.
NEVER_SUGGEST_KEYWORDS = ("ung thư", "ung bướu", "hóa trị", "miễn dịch")


def is_never_suggest_group(group) -> bool:
    if not group:
        return False
    g = str(group).lower()
    return any(k in g for k in NEVER_SUGGEST_KEYWORDS)
# Ngưỡng top-gap (vòng 6 Phần A): khi top-1 và top-2 của model SÁT nhau -> model phân vân
# giữa các nhóm chồng lấn. Phán đoán "trọng" hơn: hạ tin cậy/xin thêm thông tin thay vì đoán
# bừa. Đặt 0 để TẮT. Đọc env để dễ chỉnh/đo.
MIN_TOPGAP = float(os.environ.get("MIN_TOPGAP", "0.12"))
MIN_RELIABLE_SYMPTOMS = 2
MAX_NOTES_LENGTH = 2000
MIN_PASSWORD_LENGTH = 6
ALLOWED_STATIC_FILES = {"index.html", "styles.css", "script.js", "vendor/chart.umd.min.js"}
SCORE_LABEL = "Độ tương đồng" if metadata.get("model_type") == "json_symptom_search" else "Độ tin cậy"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _iso_dt(dt) -> str | None:
    """datetime (DB, naive=UTC) -> chuỗi ISO tz-aware để khớp luồng dùng iso_utc/parse_iso_datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _user_dict_from_db(nd) -> dict:
    """Map bản ghi NguoiDung(+TaiKhoan) -> dict ĐÚNG shape mà các route auth đang dùng."""
    tk = nd.tai_khoan
    return {
        "id": nd.ma_nguoi_dung,
        "name": nd.ho_ten or "",
        "email": nd.email or "",
        "password_hash": (tk.mat_khau_hash if tk else "") or "",
        "created_at": _iso_dt(nd.created_at),
        "role": nd.vai_tro or "user",
        "session_token": tk.session_token if tk else None,
        "session_expires_at": _iso_dt(tk.session_expires_at) if tk else None,
        "reset_code_hash": tk.reset_code_hash if tk else None,
        "reset_code_expires_at": _iso_dt(tk.reset_code_expires_at) if tk else None,
        "_ma_nguoi_dung": nd.ma_nguoi_dung,
    }


def _upsert_user_db(u: dict) -> None:
    """Ghi 1 user dict trở lại DB (tạo mới nếu chưa có; cập nhật field hay đổi)."""
    email = normalize_email(u.get("email", ""))
    nd = None
    if u.get("_ma_nguoi_dung"):
        nd = db.session.get(db_models.NguoiDung, u["_ma_nguoi_dung"])
    if nd is None:
        nd = db.session.query(db_models.NguoiDung).filter_by(email=email).first()
    if nd is None:
        nd = db_models.NguoiDung(email=email)
        nd.tai_khoan = db_models.TaiKhoan(ten_dang_nhap=email, mat_khau_hash="")
        db.session.add(nd)
    nd.ho_ten = u.get("name", "")
    nd.email = email
    nd.vai_tro = u.get("role") or "user"
    if u.get("created_at"):
        nd.created_at = parse_iso_datetime(u["created_at"]) or nd.created_at
    tk = nd.tai_khoan
    if tk is None:
        tk = db_models.TaiKhoan(ten_dang_nhap=email, mat_khau_hash="")
        nd.tai_khoan = tk
    tk.ten_dang_nhap = email
    if u.get("password_hash"):
        tk.mat_khau_hash = u["password_hash"]
    tk.session_token = u.get("session_token")
    tk.session_expires_at = parse_iso_datetime(u.get("session_expires_at"))
    tk.reset_code_hash = u.get("reset_code_hash")
    tk.reset_code_expires_at = parse_iso_datetime(u.get("reset_code_expires_at"))


def load_user_store() -> dict:
    # DB-backed khi bật; ngược lại đọc users.json (graceful fallback).
    if DB_ENABLED:
        try:
            rows = db.session.query(db_models.NguoiDung).order_by(db_models.NguoiDung.ma_nguoi_dung).all()
            return {"users": [_user_dict_from_db(nd) for nd in rows]}
        except Exception:
            app.logger.exception("load_user_store: lỗi DB -> fallback JSON")
    if not USERS_PATH.exists():
        return {"users": []}
    try:
        data = json.loads(USERS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"users": []}
    if not isinstance(data, dict) or not isinstance(data.get("users"), list):
        return {"users": []}
    return data


def save_user_store(store: dict) -> None:
    if DB_ENABLED:
        try:
            for u in store.get("users", []):
                _upsert_user_db(u)
            db.session.commit()
            return
        except Exception:
            db.session.rollback()
            app.logger.exception("save_user_store: lỗi DB")
            return
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = USERS_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(USERS_PATH)


def _append_jsonl(path: Path, record: dict) -> None:
    """Ghi nối 1 bản ghi JSON xuống file JSONL (US15/US18). Lỗi I/O không làm hỏng request."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        app.logger.exception("Không ghi được %s", path)


def normalize_email(email: str) -> str:
    return re.sub(r"\s+", "", email or "").lower()


def find_user_by_email(store: dict, email: str) -> dict | None:
    normalized = normalize_email(email)
    for user in store["users"]:
        if user.get("email") == normalized:
            return user
    return None


def user_public_view(user: dict) -> dict:
    return {
        "id": user.get("id"),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "created_at": user.get("created_at"),
        "role": user_role(user),
    }


def validate_auth_payload(name: str | None, email: str, password: str) -> str | None:
    if name is not None and not name.strip():
        return "Vui lòng nhập họ tên."
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalize_email(email)):
        return "Email không hợp lệ."
    if len(password or "") < MIN_PASSWORD_LENGTH:
        return f"Mật khẩu phải có ít nhất {MIN_PASSWORD_LENGTH} ký tự."
    return None


def issue_session(user: dict) -> str:
    token = secrets.token_urlsafe(32)
    user["session_token"] = token
    user["session_expires_at"] = iso_utc(now_utc() + timedelta(days=7))
    return token


def current_user_from_request(store: dict) -> dict | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        return None

    for user in store["users"]:
        if user.get("session_token") != token:
            continue
        expires_at = parse_iso_datetime(user.get("session_expires_at"))
        if not expires_at or expires_at <= now_utc():
            return None
        return user
    return None


# ── US19: PHÂN QUYỀN ADMIN ────────────────────────────────────────────────────
def user_role(user: dict | None) -> str:
    """Vai trò của user: 'admin' nếu role lưu trong store là admin, hoặc email thuộc ADMIN_EMAILS."""
    if not user:
        return "user"
    if str(user.get("role", "")).lower() == "admin":
        return "admin"
    if normalize_email(user.get("email", "")) in ADMIN_EMAILS:
        return "admin"
    return "user"


def is_admin(user: dict | None) -> bool:
    return user_role(user) == "admin"


def current_admin_from_request(store: dict) -> tuple[dict | None, tuple | None]:
    """Trả (user, None) nếu là admin hợp lệ; ngược lại (None, (json, status)) để route trả thẳng.

    - Chưa đăng nhập / token sai/hết hạn -> 401.
    - Đã đăng nhập nhưng không phải admin -> 403.
    """
    user = current_user_from_request(store)
    if not user:
        return None, (jsonify({"error": "Phiên đăng nhập không hợp lệ hoặc đã hết hạn."}), 401)
    if not is_admin(user):
        return None, (jsonify({"error": "Bạn không có quyền truy cập trang quản trị."}), 403)
    return user, None

def normalize(value: str) -> str:
    text = value.replace("_", " ").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s().]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_exact(value: str) -> str:
    text = value.replace("_", " ").lower()
    text = re.sub(r"[^\w\s().]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def symptom_lookup_key(symptom: str) -> str:
    return normalize(symptom).replace(" ", "_")


def unique_list(values: list[str]) -> list[str]:
    result = []
    for value in values:
        clean = re.sub(r"\s+", " ", str(value).strip())
        if clean and clean not in result:
            result.append(clean)
    return result


def auto_symptom_keywords(symptom: str) -> list[str]:
    text = symptom.replace("_", " ").lower().strip()
    text = re.sub(r"\s+", " ", text)
    keywords = []

    if text in AUTO_EXACT_SYMPTOM_KEYWORDS:
        keywords.extend(AUTO_EXACT_SYMPTOM_KEYWORDS[text])

    # Composite features in the dataset often contain whole clinical descriptions.
    # Mapping their fragments causes one Vietnamese phrase to activate many unrelated features.
    if "," in text or "(" in text or ")" in text or len(text) > 70:
        return unique_list([keyword for keyword in keywords if len(keyword) >= 3])

    parts = [
        part.strip(" .:-")
        for part in re.split(r",|;|\band\b|\bor\b|/", text)
        if part.strip(" .:-")
    ]
    candidates = unique_list(parts if len(parts) > 1 else [text])

    for candidate in candidates:
        if candidate in AUTO_EXACT_SYMPTOM_KEYWORDS:
            keywords.extend(AUTO_EXACT_SYMPTOM_KEYWORDS[candidate])

        for english_part, vi_parts in AUTO_BODY_PARTS.items():
            if not re.search(rf"(?<!\w){re.escape(english_part)}(?!\w)", candidate):
                continue
            for vi_part in vi_parts:
                if "pain" in candidate or "ache" in candidate or "painful" in candidate:
                    keywords.append(f"đau {vi_part}")
                    keywords.append(f"nhức {vi_part}")
                if "swelling" in candidate or "swollen" in candidate or "edema" in candidate:
                    keywords.append(f"sưng {vi_part}")
                    keywords.append(f"phù {vi_part}")
                if "weakness" in candidate or "weak" in candidate:
                    keywords.append(f"yếu {vi_part}")
                if "stiffness" in candidate or "stiff" in candidate or "tightness" in candidate:
                    keywords.append(f"cứng {vi_part}")
                    keywords.append(f"căng {vi_part}")
                if "lump" in candidate or "mass" in candidate:
                    keywords.append(f"khối ở {vi_part}")
                    keywords.append(f"u cục ở {vi_part}")
                if "bleeding" in candidate or "blood" in candidate:
                    keywords.append(f"chảy máu {vi_part}")
                if "redness" in candidate or "red" in candidate:
                    keywords.append(f"đỏ {vi_part}")
                if "burning" in candidate or "burns" in candidate:
                    keywords.append(f"nóng rát {vi_part}")
                    keywords.append(f"bỏng rát {vi_part}")

    return unique_list([keyword for keyword in keywords if len(keyword) >= 3])


def symptom_keywords(symptom: str) -> list[str]:
    manual = VI_SYMPTOM_KEYWORDS.get(symptom, VI_SYMPTOM_KEYWORDS.get(symptom_lookup_key(symptom), []))
    return unique_list([*manual, *auto_symptom_keywords(symptom)])


def symptom_label_vi(symptom: str) -> str:
    keywords = symptom_keywords(symptom)
    return (keywords[0] if keywords else symptom.replace("_", " ").replace("  ", " ")).capitalize()


def is_composite_feature(feature: str) -> bool:
    text = str(feature)
    return "," in text or "(" in text or ")" in text or len(text) > 70


def has_safe_vi_label(feature: str) -> bool:
    label = symptom_label_vi(feature)
    return bool(symptom_keywords(feature)) and label != feature.replace("_", " ").replace("  ", " ").capitalize()


def build_readable_symptoms() -> list[dict[str, str]]:
    rows = []
    seen_labels = set()
    for feature in features:
        if is_composite_feature(feature) or not has_safe_vi_label(feature):
            continue
        label = symptom_label_vi(feature)
        key = normalize(label)
        if key in seen_labels:
            continue
        seen_labels.add(key)
        rows.append(
            {
                "id": feature,
                "label": label,
                "label_vi": label,
                "label_en": feature.replace("_", " ").replace("  ", " ").title(),
            }
        )
    return sorted(rows, key=lambda item: normalize(item["label_vi"]))


readable_symptoms = build_readable_symptoms()

NORMALIZED_FEATURES = [
    (feature, normalized)
    for feature in features
    for normalized in [normalize(feature)]
    if normalized
]
NORMALIZED_KEYWORDS = [
    (feature, normalized)
    for feature in features
    for keyword in symptom_keywords(feature)
    for normalized in [normalize(keyword)]
    if normalized
]
SUPPORTED_KEYWORD_NORMALS = {normalized for _, normalized in NORMALIZED_KEYWORDS}
EXACT_KEYWORDS = [
    (feature, exact)
    for feature in features
    for keyword in symptom_keywords(feature)
    for exact in [normalize_exact(keyword)]
    if exact
]
KEYWORD_VARIANTS_BY_NORMAL = {}
for _, exact_keyword in EXACT_KEYWORDS:
    KEYWORD_VARIANTS_BY_NORMAL.setdefault(normalize(exact_keyword), set()).add(exact_keyword)
AMBIGUOUS_NORMALIZED_KEYWORDS = {
    normalized
    for normalized, variants in KEYWORD_VARIANTS_BY_NORMAL.items()
    if len(variants) > 1
}

# ── Lớp khớp NGỮ NGHĨA tiếng Việt (SBERT) — bổ sung cho khớp từ khóa cứng ──────
# Bật/tắt qua env. Graceful: thiếu thư viện/model -> tự dùng exact-match như cũ.
SEMANTIC_ENABLED = os.environ.get("SEMANTIC_MATCH", "1") != "0"
SEMANTIC_THRESHOLD = float(os.environ.get("SEMANTIC_THRESHOLD", "0.62"))
# Lớp ngữ nghĩa chỉ chạy khi exact-match thu được < ngưỡng này (fallback).
SEMANTIC_FALLBACK_MAX = int(os.environ.get("SEMANTIC_FALLBACK_MAX", "2"))
# P4.4: feature thần kinh "nguy hiểm" KHÔNG được nhận từ semantic match mờ (dễ false-positive,
# vd "bê vật nặng" -> "weakness of one body side"). Chỉ nhận qua khớp từ khóa chính xác; ca thật
# vẫn được cổng cờ đỏ raw-text (đột quỵ/co giật...) bắt độc lập với feature extraction.
SEMANTIC_BLOCKLIST = {
    "weakness of one body side", "altered sensorium", "coma", "slurred speech", "seizures",
    "loss of balance", "unsteadiness", "lack of concentration",
}
SEMANTIC_READY = False
if SEMANTIC_ENABLED:
    try:
        import semantic_matcher
        _semantic_pairs = [
            (kw, feature)
            for feature in features
            for kw in symptom_keywords(feature)
            if len(kw) >= 3
        ]
        SEMANTIC_READY = semantic_matcher.build_index(_semantic_pairs)
    except Exception:
        SEMANTIC_READY = False


# ── Lớp LLM trích xuất NGỮ CẢNH (vòng 5) — BỔ SUNG, mặc định TẮT ──────────────
# Đọc env theo RUNTIME (mỗi request) để bật/tắt linh hoạt và dễ test/stub. LLM chỉ làm
# giàu đầu vào; KHÔNG bao giờ là nguồn quyết định nhóm thuốc (xem /api/predict).
try:
    import llm_context
except Exception:
    llm_context = None

# Lớp DỰ PHÒNG LLM (phân loại nhóm khi pipeline không trích được triệu chứng). Mặc định TẮT.
try:
    import llm_classify
except Exception:
    llm_classify = None

# Tầng NGỮ CẢNH - AN TOÀN (bệnh nền/tuổi/thai kỳ/tương tác/dị ứng/phản vệ). LUÔN bật.
try:
    import context_safety
except Exception:
    context_safety = None

# Trích ngữ cảnh bằng LLM (semantic, bắt cách nói mới) + vòng học. Mặc định TẮT (LLM_CONTEXT_ENABLED).
try:
    import llm_context_extract
except Exception:
    llm_context_extract = None


def llm_context_enabled() -> bool:
    if llm_context is None:
        return False
    return os.environ.get("LLM_CONTEXT_ENABLED", "0").strip().lower() in {"1", "true", "yes"}


def has_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


def parse_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except (ValueError, SyntaxError):
        pass
    return [text]


def compact_reference_item(value: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value).strip())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def read_csv_source(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def read_csv_from_archive(name: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(DATA_ARCHIVE) as archive:
        with archive.open(name) as csv_file:
            text_file = io.TextIOWrapper(csv_file, encoding="utf-8-sig", newline="")
            return list(csv.DictReader(text_file))


def archive_names() -> set[str]:
    if not DATA_ARCHIVE.exists():
        return set()
    with zipfile.ZipFile(DATA_ARCHIVE) as archive:
        return set(archive.namelist())


def read_json_from_archive(name: str):
    with zipfile.ZipFile(DATA_ARCHIVE) as archive:
        with archive.open(name) as json_file:
            return json.load(json_file)


def treatment_items(text: str) -> list[str]:
    hidden_message = "Dataset có đề cập thuốc/liệu pháp cụ thể, nhưng hệ thống đã ẩn liều dùng. Cần bác sĩ hoặc dược sĩ đánh giá trước khi sử dụng."
    lines = [
        re.sub(r"\s+", " ", line.strip(" -\t"))
        for line in str(text).splitlines()
        if line.strip()
    ]
    if not lines and text:
        lines = [re.sub(r"\s+", " ", str(text).strip())]

    safe_lines = []
    dosage_pattern = re.compile(
        r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml|l/min|iu|u/ml|units?|tablets?|capsules?|times\s+a\s+day|twice\s+a\s+day|three\s+times)\b",
        re.IGNORECASE,
    )
    medication_pattern = re.compile(
        r"\b(drug|drugs|medication|medications|antibiotic|antibiotics|sedative|sedatives|analgesic|analgesics|diuretic|diuretics|aspirin|diazepam|acetazolamide|furosemide|spironolactone|metoclopramide|promethazine|chlorpromazine|prochlorperazine)\b",
        re.IGNORECASE,
    )
    for line in lines:
        if dosage_pattern.search(line) or medication_pattern.search(line):
            if hidden_message not in safe_lines:
                safe_lines.append(hidden_message)
            continue
        if len(line) > 420:
            line = line[:417].rstrip() + "..."
        safe_lines.append(line)
        if len(safe_lines) >= 6:
            break

    return safe_lines[:6]


def guidance_key(value: str) -> str:
    return normalize(value).strip()


def load_guidance_data() -> dict:
    if not GUIDANCE_PATH.exists():
        return {}
    data = json.loads(GUIDANCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("disease_guidance.json must contain an object keyed by disease name.")
    return data


guidance_data = load_guidance_data()
guidance_lookup = {guidance_key(name): name for name in guidance_data.keys()}


def resolve_guidance_entry(disease: str) -> tuple[dict, str]:
    name = guidance_lookup.get(guidance_key(disease))
    if not name:
        return guidance_data.get("default", {}), "default"

    entry = guidance_data.get(name, {})
    visited = set()
    while isinstance(entry, dict) and entry.get("alias_of"):
        visited.add(name)
        alias_name = guidance_lookup.get(guidance_key(entry["alias_of"]))
        if not alias_name or alias_name in visited:
            break
        name = alias_name
        entry = guidance_data.get(name, {})
    return entry if isinstance(entry, dict) else {}, name


def symptom_text(active_symptoms: set[str]) -> str:
    return " ".join(normalize(symptom) for symptom in active_symptoms)


def has_any_symptom(active_symptoms: set[str], keywords: list[str]) -> bool:
    haystack = symptom_text(active_symptoms)
    return any(normalize(keyword) in haystack for keyword in keywords)


def extend_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        if value and value not in target:
            target.append(value)


def symptom_based_guidance(active_symptoms: set[str], disease: str) -> dict[str, list[str] | str]:
    entry, guidance_source = resolve_guidance_entry(disease)
    if entry and guidance_source != "default":
        warning_signs = entry.get("warning_signs") or []
        warning = " ".join(warning_signs) if warning_signs else (
            "Không thay thế chẩn đoán của bác sĩ. Nếu triệu chứng nặng, kéo dài hoặc bất thường, hãy đi khám."
        )
        return {
            "treatment": list(entry.get("treatment_groups") or []),
            "precautions": list(entry.get("precautions") or []),
            "care": list(entry.get("care") or []),
            "warning": warning,
            "guidance_source": guidance_source,
        }

    treatment = []
    precautions = []
    care = []
    warnings = []

    if has_any_symptom(active_symptoms, ["sore throat", "throat pain", "pain in the throat", "cough", "fever"]):
        extend_unique(
            treatment,
            [
                "Nhóm giảm đau - hạ sốt không kê đơn có thể được cân nhắc khi đau họng/sốt; hỏi dược sĩ nếu có bệnh nền, đang mang thai, bệnh gan/thận hoặc đang dùng thuốc khác.",
                "Nhóm thuốc/viên ngậm làm dịu họng hoặc xịt họng có thể hỗ trợ giảm rát họng tạm thời.",
                "Nếu ho, chọn nhóm thuốc ho phù hợp loại ho khan hoặc ho có đờm; không tự phối nhiều thuốc ho/cảm cùng lúc.",
                "Kháng sinh chỉ phù hợp khi bác sĩ xác định hoặc nghi ngờ nhiễm khuẩn; không tự dùng kháng sinh cho cảm lạnh/viêm họng nghi do virus.",
            ],
        )
        extend_unique(
            precautions,
            [
                "Rửa tay thường xuyên, che miệng khi ho hoặc hắt hơi.",
                "Đeo khẩu trang khi có triệu chứng hô hấp và hạn chế tiếp xúc gần với người khác.",
                "Tránh khói thuốc, bụi, rượu bia và thức uống quá lạnh nếu làm họng kích ứng hơn.",
            ],
        )
        extend_unique(
            care,
            [
                "Uống đủ nước, nghỉ ngơi và giữ ấm vùng cổ.",
                "Có thể súc miệng bằng nước muối ấm nếu không có chống chỉ định.",
                "Theo dõi nhiệt độ, mức độ ho, đau họng và khả năng ăn uống trong 24-48 giờ.",
            ],
        )
        warnings.append(
            "Đi khám sớm nếu khó thở, nuốt nghẹn/không uống được, sốt cao kéo dài, đau họng nặng một bên, nổi hạch lớn, phát ban, ho ra máu hoặc triệu chứng nặng lên."
        )

    if has_any_symptom(active_symptoms, ["headache", "visual disturbances", "nausea", "vomiting", "dizziness"]):
        extend_unique(
            treatment,
            [
                "Nhóm giảm đau thông thường có thể được cân nhắc cho đau đầu nhẹ; tránh tự dùng nếu đau đầu bất thường, có bệnh nền hoặc đang dùng thuốc chống đông.",
                "Nếu đau đầu kèm buồn nôn, nhìn mờ, chóng mặt hoặc mất ngủ kéo dài, nên được nhân viên y tế đánh giá thay vì chỉ tự điều trị triệu chứng.",
            ],
        )
        extend_unique(
            care,
            [
                "Nghỉ ở nơi yên tĩnh, uống đủ nước và ghi lại thời điểm khởi phát, mức độ đau, yếu tố làm nặng/giảm.",
            ],
        )
        warnings.append(
            "Cần cấp cứu nếu đau đầu dữ dội đột ngột, yếu/liệt một bên, nói khó, co giật, lú lẫn, ngất, sốt cao kèm cứng cổ hoặc nhìn mờ đột ngột."
        )

    if has_any_symptom(active_symptoms, ["diarrhoea", "vomiting", "dehydration", "abdominal pain"]):
        extend_unique(
            treatment,
            [
                "Ưu tiên bù nước và điện giải; nhóm men vi sinh hoặc thuốc hỗ trợ tiêu hóa chỉ nên dùng theo tư vấn phù hợp.",
                "Không tự dùng thuốc cầm tiêu chảy nếu sốt cao, phân máu hoặc nghi ngộ độc/nhiễm khuẩn nặng.",
            ],
        )
        extend_unique(
            care,
            [
                "Ăn nhẹ, chia nhỏ bữa, tránh rượu bia và thức ăn nhiều dầu mỡ trong giai đoạn triệu chứng còn nặng.",
            ],
        )
        warnings.append("Đi khám sớm nếu mất nước, nôn không kiểm soát, đau bụng dữ dội, sốt cao hoặc đi ngoài ra máu.")

    if has_any_symptom(active_symptoms, ["burning micturition", "bladder discomfort", "continuous feel of urine", "foul smell of urine"]):
        extend_unique(
            treatment,
            [
                "Nghi nhiễm trùng tiết niệu cần xét nghiệm và bác sĩ đánh giá; không tự dùng kháng sinh.",
            ],
        )
        extend_unique(precautions, ["Uống đủ nước và không nhịn tiểu kéo dài."])
        warnings.append("Đi khám nếu tiểu buốt kèm sốt, đau hông lưng, buồn nôn hoặc đang mang thai.")

    if has_any_symptom(active_symptoms, ["chest pain", "breathlessness", "weakness of one body side", "slurred speech", "coma"]):
        warnings.append("Có dấu hiệu nguy hiểm như đau ngực, khó thở, yếu/liệt hoặc nói khó: cần đi cấp cứu ngay.")

    if not treatment:
        treatment.append(
            "Hệ thống chưa có rule nhóm thuốc riêng cho cụm triệu chứng này. Có thể xem phần điều trị tham khảo từ dataset và nên hỏi bác sĩ/dược sĩ trước khi dùng thuốc."
        )
    if not precautions:
        precautions.append("Theo dõi triệu chứng, tránh tự dùng thuốc không rõ chỉ định và đi khám nếu tình trạng kéo dài hoặc nặng lên.")
    if not care:
        care.append("Nghỉ ngơi, uống đủ nước và bổ sung thông tin như thời gian khởi phát, mức độ nặng, sốt, bệnh nền, thuốc đang dùng.")

    warning = " ".join(unique_values(warnings)) if warnings else (
        "Không thay thế chẩn đoán của bác sĩ. Nếu triệu chứng nặng, kéo dài, hoặc xuất hiện dấu hiệu bất thường, hãy đi khám."
    )

    return {
        "treatment": treatment,
        "precautions": precautions,
        "care": care,
        "warning": warning,
        "guidance_source": "symptom_fallback",
    }


def symptom_triage_guidance(active_symptoms: set[str]) -> dict[str, list[str] | str]:
    treatment = []
    precautions = []
    care = []
    warnings = []

    if has_any_symptom(active_symptoms, ["headache", "dizziness", "insomnia"]):
        extend_unique(
            treatment,
            [
                "Chưa đủ dữ liệu để gợi ý thuốc. Với đau đầu/chóng mặt/mất ngủ, trước hết nên nghỉ ở nơi yên tĩnh, uống đủ nước và tránh lái xe hoặc vận hành máy nếu còn chóng mặt.",
                "Theo dõi huyết áp, nhiệt độ, thời điểm khởi phát, mức độ đau đầu và yếu tố làm nặng/giảm; bổ sung các thông tin này để hệ thống đánh giá tốt hơn.",
            ],
        )
        extend_unique(
            care,
            [
                "Giảm ánh sáng/màn hình, ngủ đúng giờ, tránh caffeine/rượu vào chiều tối và không tự dùng thuốc an thần hoặc thuốc ngủ.",
                "Nếu có dùng thuốc giảm đau không kê đơn, cần kiểm tra chống chỉ định, bệnh gan/thận/dạ dày, thai kỳ, dị ứng và thuốc đang dùng; hỏi dược sĩ/bác sĩ khi không chắc.",
            ],
        )
        warnings.append(
            "Cần đi khám/cấp cứu nếu đau đầu dữ dội đột ngột, yếu/liệt, nói khó, nhìn mờ, ngất, co giật, sốt cao/cứng cổ, nôn nhiều, đau đầu sau chấn thương hoặc chóng mặt không đứng vững."
        )

    if has_any_symptom(active_symptoms, ["fever", "high fever", "mild fever", "cough", "sore throat", "throat pain"]):
        extend_unique(
            treatment,
            [
                "Có triệu chứng hô hấp/sốt: ưu tiên nghỉ ngơi, uống đủ nước, theo dõi nhiệt độ và tránh tự dùng kháng sinh khi chưa được bác sĩ chỉ định.",
            ],
        )
        extend_unique(care, ["Đeo khẩu trang, rửa tay, tránh tiếp xúc gần khi đang ho/sốt."])
        warnings.append("Đi khám nếu khó thở, đau ngực, sốt cao kéo dài, lơ mơ, tím môi hoặc triệu chứng nặng lên nhanh.")

    if has_any_symptom(active_symptoms, ["diarrhoea", "vomiting", "dehydration", "abdominal pain", "nausea"]):
        extend_unique(
            treatment,
            [
                "Có triệu chứng tiêu hóa: ưu tiên bù nước/điện giải từng ngụm nhỏ, ăn nhẹ và tránh tự dùng thuốc cầm tiêu chảy khi có sốt cao hoặc phân máu.",
            ],
        )
        extend_unique(care, ["Theo dõi số lần nôn/tiêu chảy, lượng nước tiểu và dấu hiệu mất nước."])
        warnings.append("Đi khám nếu nôn liên tục, đau bụng dữ dội, mất nước, sốt cao, phân máu hoặc người bệnh là trẻ nhỏ/người già.")

    if has_unclear_limb_stiffness(active_symptoms):
        extend_unique(
            treatment,
            [
                "Cứng/co rút tay đơn độc chưa đủ để gợi ý thuốc. Trước mắt nên nghỉ tay, tránh vận động lặp lại, xoa giãn nhẹ nếu không đau/sưng và bổ sung thêm triệu chứng đi kèm.",
                "Không tự dùng thuốc kháng viêm chỉ vì cứng tay nếu chưa rõ có đau, viêm, chấn thương hay bệnh khớp.",
            ],
        )
        extend_unique(
            care,
            [
                "Theo dõi thời điểm xuất hiện, thời gian cứng buổi sáng, mức độ ảnh hưởng vận động, tê/yếu tay, đau/sưng/nóng đỏ khớp và yếu tố nghề nghiệp.",
            ],
        )
        warnings.append(
            "Đi khám sớm nếu cứng tay kèm yếu/tê lan rộng, sưng nóng đỏ khớp, đau nhiều, biến dạng khớp, sốt, sau chấn thương hoặc kéo dài/tái diễn."
        )

    if not treatment:
        treatment.append(
            "Chưa đủ dữ liệu để gợi ý thuốc. Hãy bổ sung triệu chứng chính, thời gian khởi phát, mức độ nặng, bệnh nền, dị ứng và thuốc đang dùng."
        )
    if not precautions:
        precautions.append("Không tự dùng thuốc kê đơn hoặc phối nhiều thuốc khi chưa rõ nguyên nhân triệu chứng.")
    if not care:
        care.append("Nghỉ ngơi, uống đủ nước và theo dõi diễn tiến trong 24-48 giờ nếu triệu chứng nhẹ.")

    warning = " ".join(unique_values(warnings)) if warnings else (
        "Nếu triệu chứng nặng, kéo dài, xuất hiện bất thường hoặc bạn có bệnh nền quan trọng, hãy đi khám."
    )

    return {
        "treatment": treatment,
        "precautions": precautions,
        "care": care,
        "warning": warning,
        "guidance_source": "symptom_triage",
    }


def load_reference_data():
    references = {
        "description": {},
        "medications": {},
        "diets": {},
        "precautions": {},
        "workouts": {},
        "case_index": [],
    }

    if DATA_SOURCE.exists() and DATA_SOURCE.suffix.lower() == ".csv":
        rows = read_csv_source(DATA_SOURCE)
        symptoms_by_group = {}
        meds_by_group = {}
        groups_by_disease = {}
        symptoms_by_disease = {}

        for row in rows:
            disease = str(row.get("chan_doan_du_kien", "")).strip()
            group = str(row.get("nhom_thuoc", "")).strip()
            medication = str(row.get("ten_thuoc", "")).strip()
            symptoms = [
                " ".join(part.strip().split())
                for part in str(row.get("trieu_chung", "")).split(";")
                if part.strip()
            ]

            if group:
                symptoms_by_group.setdefault(group, [])
                extend_unique(symptoms_by_group[group], symptoms)
                meds_by_group.setdefault(group, [])
                if medication:
                    extend_unique(meds_by_group[group], [compact_reference_item(medication)])

            if disease:
                symptoms_by_disease.setdefault(disease, [])
                extend_unique(symptoms_by_disease[disease], symptoms)
                groups_by_disease.setdefault(disease, [])
                if group:
                    extend_unique(groups_by_disease[disease], [group])

            if disease and group and symptoms:
                references["case_index"].append(
                    {
                        "symptoms": {symptom.lower() for symptom in symptoms},
                        "disease": disease,
                        "group": group,
                    }
                )

        for group, symptoms in symptoms_by_group.items():
            references["description"][group] = "Triệu chứng thường gặp trong dữ liệu: " + ", ".join(symptoms[:12])
            references["medications"][group] = [
                f"Nhóm thuốc dự đoán: {group}",
                *[f"Thuốc trong dữ liệu: {medication}" for medication in meds_by_group.get(group, [])[:8]],
            ]

        for disease, groups in groups_by_disease.items():
            if symptoms_by_disease.get(disease):
                references["description"][disease] = "Triệu chứng thường gặp trong dữ liệu: " + ", ".join(
                    symptoms_by_disease[disease][:12]
                )
            references["medications"][disease] = [f"Nhóm thuốc trong dữ liệu: {group}" for group in groups[:8]]

        return references

    if not DATA_ARCHIVE.exists():
        return references

    names = archive_names()
    if "disease_database_en.json" in names:
        for row in read_json_from_archive("disease_database_en.json"):
            disease = str(row.get("disease", "")).strip()
            common_symptom = str(row.get("common_symptom", "")).strip()
            treatment = str(row.get("treatment", "")).strip()
            if not disease:
                continue
            if common_symptom:
                references["description"][disease] = f"Common symptoms: {common_symptom}"
            if treatment:
                references["medications"][disease] = treatment_items(treatment)
        return references

    descriptions = read_csv_from_archive("description.csv")
    for row in descriptions:
        references["description"][row["Disease"]] = row["Description"]

    medications = read_csv_from_archive("medications.csv")
    for row in medications:
        references["medications"][row["Disease"]] = parse_list(row["Medication"])

    diets = read_csv_from_archive("diets.csv")
    for row in diets:
        references["diets"][row["Disease"]] = parse_list(row["Diet"])

    precautions = read_csv_from_archive("precautions_df.csv")
    for row in precautions:
        items = [
            row.get("Precaution_1"),
            row.get("Precaution_2"),
            row.get("Precaution_3"),
            row.get("Precaution_4"),
        ]
        references["precautions"][row["Disease"]] = [
            str(item) for item in items if item is not None and str(item).strip()
        ]

    workouts = read_csv_from_archive("workout_df.csv")
    for row in workouts:
        disease = row.get("disease")
        workout = row.get("workout")
        if disease and workout:
            references["workouts"].setdefault(disease, [])
            if len(references["workouts"][disease]) < 5:
                references["workouts"][disease].append(str(workout))

    return references


references = load_reference_data()


def load_drug_representatives() -> dict[str, dict]:
    """Nạp mapping nhóm -> hoạt chất tiêu biểu đã curate. Bỏ qua key bắt đầu bằng '_' (metadata).
    Lỗi/thiếu file -> dict rỗng (output tự lùi về cách cũ, không crash)."""
    try:
        raw = json.loads(DRUG_REPRESENTATIVES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for group, entry in raw.items():
        if group.startswith("_") or not isinstance(entry, dict):
            continue
        ingredients = [str(x).strip() for x in entry.get("active_ingredients", []) if str(x).strip()]
        out[group] = {"active_ingredients": ingredients, "note": str(entry.get("note", "")).strip()}
    return out


DRUG_REPRESENTATIVES = load_drug_representatives()


def representative_active_ingredients_for_group(group: str | None, limit: int = 3) -> list[str]:
    """2-3 hoạt chất minh hoạ đã làm sạch cho nhóm; [] nếu nhóm rủi ro/chuyên khoa hoặc chưa map."""
    if not group:
        return []
    entry = DRUG_REPRESENTATIVES.get(group)
    if not entry:
        return []
    return entry["active_ingredients"][:limit]


def representative_note_for_group(group: str | None) -> str:
    if not group:
        return ""
    entry = DRUG_REPRESENTATIVES.get(group)
    return entry["note"] if entry else ""


def symptoms_from_text(text: str) -> set[str]:
    normalized_text = normalize(text)
    exact_text = normalize_exact(text)
    matches = set()
    for symptom, normalized_symptom in NORMALIZED_FEATURES:
        if normalized_symptom in normalized_text and has_phrase(normalized_text, normalized_symptom):
            matches.add(symptom)
    for symptom, exact_keyword in EXACT_KEYWORDS:
        if exact_keyword in exact_text and has_phrase(exact_text, exact_keyword):
            matches.add(symptom)

    if has_phrase(normalized_text, "dau hong") and any(
        has_phrase(normalized_text, context) for context in ["ho", "sot", "rat hong", "nghet mui", "so mui"]
    ):
        for throat_symptom in ["sore throat", "throat pain", "pain in the throat"]:
            if throat_symptom in feature_lookup:
                matches.add(feature_lookup[throat_symptom])

    for symptom, normalized_keyword in NORMALIZED_KEYWORDS:
        if normalized_keyword in AMBIGUOUS_NORMALIZED_KEYWORDS:
            continue
        if normalized_keyword in normalized_text and has_phrase(normalized_text, normalized_keyword):
            matches.add(symptom)

    if any(has_phrase(normalized_text, phrase) for phrase in ["sung nuou", "sung loi", "nuou sung", "loi sung"]):
        if "gum pain" in feature_lookup:
            matches.add(feature_lookup["gum pain"])
        if "pain in gums" in feature_lookup:
            matches.add(feature_lookup["pain in gums"])
    if any(has_phrase(normalized_text, phrase) for phrase in ["kho nhai", "nhai dau", "dau khi nhai"]):
        if "toothache" in feature_lookup:
            matches.add(feature_lookup["toothache"])
    if any(has_phrase(normalized_text, phrase) for phrase in ["mat ca chan dau", "co chan dau", "dau sau khi teo", "dau sau khi te"]):
        if "ankle pain" in feature_lookup:
            matches.add(feature_lookup["ankle pain"])
    if any(has_phrase(normalized_text, phrase) for phrase in ["mat ca chan sung", "co chan sung"]):
        if "ankle swelling" in feature_lookup:
            matches.add(feature_lookup["ankle swelling"])
    # P4.4: "mỏi/đau vai gáy" -> neck pain (cơ-xương), tránh trả rỗng -> 400.
    if any(has_phrase(normalized_text, phrase) for phrase in ["vai gay", "moi vai", "dau vai gay", "moi vai gay", "dau vai"]):
        if "neck pain" in feature_lookup:
            matches.add(feature_lookup["neck pain"])

    # Lớp ngữ nghĩa (fallback): chỉ kích hoạt khi khớp từ khóa thu được ÍT triệu chứng,
    # để giữ độ chính xác cho ca rõ ràng (exact đủ) và cứu ca lạ (exact bỏ sót).
    if SEMANTIC_READY and len(matches) < SEMANTIC_FALLBACK_MAX:
        try:
            sem = semantic_matcher.match(text, threshold=SEMANTIC_THRESHOLD)
            matches.update(s for s in sem if s not in SEMANTIC_BLOCKLIST)
        except Exception:
            pass
    return matches


def ordered_symptoms_from_text(text: str) -> list[str]:
    matched = symptoms_from_text(text)
    if not matched:
        return []

    normalized_text = normalize(text)
    exact_text = normalize_exact(text)
    ordered = []
    for symptom in matched:
        positions = []
        normalized_symptom = normalize(symptom)
        if normalized_symptom:
            index = normalized_text.find(normalized_symptom)
            if index >= 0:
                positions.append(index)
        for keyword in symptom_keywords(symptom):
            normalized_keyword = normalize(keyword)
            if normalized_keyword:
                index = normalized_text.find(normalized_keyword)
                if index >= 0:
                    positions.append(index)
            exact_keyword = normalize_exact(keyword)
            if exact_keyword:
                index = exact_text.find(exact_keyword)
                if index >= 0:
                    positions.append(index)
        ordered.append((min(positions) if positions else len(normalized_text) + len(ordered), symptom))

    return refine_symptom_order(
        [symptom for _, symptom in sorted(ordered, key=lambda item: (item[0], symptom_complexity(item[1]), item[1]))],
        text,
    )


def features_from_llm_symptoms(symptoms_vi) -> list[str]:
    """Map triệu chứng (tiếng Việt) do LLM trích -> feature thật của model, TÁI DÙNG matcher
    sẵn có (exact/keyword/semantic). Không viết matcher mới. Trả list feature, giữ thứ tự, khử trùng.
    """
    out: list[str] = []
    if not isinstance(symptoms_vi, list):
        return out
    for item in symptoms_vi:
        if not isinstance(item, str) or not item.strip():
            continue
        mapped = ordered_symptoms_from_text(item)
        if not mapped:
            feature = feature_lookup.get(item.strip().lower())
            mapped = [feature] if feature else []
        for feature in mapped:
            if feature not in out:
                out.append(feature)
    return out


def apply_llm_negations(symptoms_order: list[str], negated_vi) -> list[str]:
    """Loại feature mà LLM đánh dấu phủ định (map negated_vi -> feature rồi trừ khỏi danh sách)."""
    negated_features = set(features_from_llm_symptoms(negated_vi))
    if not negated_features:
        return symptoms_order
    return [symptom for symptom in symptoms_order if symptom not in negated_features]


def symptom_complexity(symptom: str) -> tuple[int, int]:
    text = str(symptom)
    composite = int("," in text or "(" in text or ")" in text or len(text) > 70)
    return composite, len(text)


FEVER_FEATURE_NORMALS = {normalize(feature) for feature in ["fever", "mild fever", "high fever", "mild_fever", "high_fever"]}


def negated_feature_normals(source_text: str) -> set[str]:
    normalized_source = normalize(source_text)
    negated = set()
    no_fever_phrases = [
        "khong sot",
        "khong bi sot",
        "khong co sot",
        "khong thay sot",
        "chua sot",
    ]
    if any(has_phrase(normalized_source, phrase) for phrase in no_fever_phrases):
        negated.update(FEVER_FEATURE_NORMALS)
    # Phủ định tổng quát: "không <triệu chứng>" -> loại feature tương ứng.
    NEG_MAP = {
        ("khong tieu chay", "khong di ngoai", "khong di long"): ["diarrhoea", "diarrhea"],
        ("khong dau dau", "khong nhuc dau"): ["headache", "frontal headache"],
        ("khong buon non", "khong non"): ["nausea", "vomiting"],
        ("khong ho",): ["cough"],
        ("khong kho tho",): ["breathlessness", "shortness of breath", "difficulty breathing"],
        ("khong dau bung", "khong dau da day", "khong dau thuong vi"): [
            "abdominal pain", "belly pain", "stomach pain", "acidity", "heartburn", "indigestion",
            "lower abdominal pain", "upper abdominal pain", "sharp abdominal pain", "burning abdominal pain",
        ],
        ("khong chong mat",): ["dizziness"],
        ("khong ngua",): ["itching", "itching of skin"],
    }
    for phrases, feats in NEG_MAP.items():
        if any(has_phrase(normalized_source, p) for p in phrases):
            negated.update(normalize(f) for f in feats)
    return negated


def filter_negated_symptoms(symptoms: list[str], source_text: str) -> list[str]:
    negated = negated_feature_normals(source_text)
    if not negated:
        return symptoms
    return [symptom for symptom in symptoms if normalize(symptom) not in negated]


def refine_symptom_order(symptoms: list[str], source_text: str = "") -> list[str]:
    normalized_source = normalize(source_text)
    symptoms = filter_negated_symptoms(symptoms, source_text)
    if "mat ca chan" in normalized_source:
        symptoms = [
            symptom
            for symptom in symptoms
            if "eye" not in symptom.lower() and "vision" not in symptom.lower()
        ]
    if "co chan" in normalized_source:
        symptoms = [
            symptom
            for symptom in symptoms
            if not ("neck" in symptom.lower() and "ankle" not in symptom.lower())
        ]
    if "dau bung duoi" not in normalized_source:
        symptoms = [symptom for symptom in symptoms if symptom != "belly pain"]
    if "buon non" in normalized_source and not any(
        phrase in normalized_source
        for phrase in ["non nhieu", "non oi", "non lien tuc", "bi non", "va non", "non sau"]
    ):
        symptoms = [symptom for symptom in symptoms if symptom != "vomiting"]

    symptom_set = set(symptoms)
    best_by_label = {}
    for symptom in symptoms:
        if symptom == "fever" and ({"mild_fever", "high_fever", "mild fever", "high fever"} & symptom_set):
            continue
        label = symptom_label_vi(symptom).lower()
        current = best_by_label.get(label)
        if current is None or symptom_complexity(symptom) < symptom_complexity(current):
            best_by_label[label] = symptom

    refined = []
    for symptom in symptoms:
        label = symptom_label_vi(symptom).lower()
        if best_by_label.get(label) == symptom and symptom not in refined:
            refined.append(symptom)
    return refined


def unsupported_symptoms_from_text(text: str) -> list[dict[str, str]]:
    normalized_text = normalize(text)
    matches = []
    for symptom_id, symptom in UNSUPPORTED_SYMPTOM_KEYWORDS.items():
        for phrase in symptom["phrases"]:
            normalized_phrase = normalize(phrase)
            if normalized_phrase and has_phrase(normalized_text, normalized_phrase):
                if normalized_phrase in SUPPORTED_KEYWORD_NORMALS:
                    break
                matches.append({"id": symptom_id, "label_vi": symptom["label_vi"]})
                break
    return matches


def unique_values(values):
    seen = set()
    unique = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def symptoms_to_model_text(symptoms) -> str:
    return " ".join(symptoms)


def model_input_candidates(symptoms: list[str]) -> list[str]:
    base = [symptom for symptom in symptoms if symptom]
    candidates = []
    for ordered in (base, sorted(base), list(reversed(base))):
        text = symptoms_to_model_text(ordered)
        if text and text not in candidates:
            candidates.append(text)

    if 2 <= len(base) <= 4:
        for ordered in permutations(base):
            text = symptoms_to_model_text(ordered)
            if text not in candidates:
                candidates.append(text)

    return candidates or [symptoms_to_model_text(base)]


def build_model_input(active_symptoms: set[str]):
    if metadata.get("model_type") in {"tfidf_linear_svm", "json_symptom_search"}:
        return [symptoms_to_model_text(active_symptoms)]

    raise ValueError("Unsupported model type. Retrain with TF-IDF + Linear SVM.")


def model_accepts_raw_text() -> bool:
    """True nếu model đã train trên câu mô tả THÔ (vd tiếng Việt tự nhiên).

    Khi True, backend được phép feed raw notes thẳng vào model (luồng hybrid),
    tận dụng năng lực hiểu câu VN của model thay vì chỉ cụm triệu chứng đã trích.
    """
    return bool(metadata.get("trained_on_raw_text"))


def ranked_proba(inputs: list[str]):
    """predict_proba trung bình trên các ứng viên input -> list (label, prob) giảm dần."""
    proba_rows = model.predict_proba(inputs)
    class_names = model.classes_
    proba = [
        sum(float(row[index]) for row in proba_rows) / len(proba_rows)
        for index in range(len(class_names))
    ]
    return sorted(zip(class_names, proba), key=lambda item: item[1], reverse=True)


def predicted_label_vi(value: str) -> str:
    if LABEL_TYPE == "drug_group":
        return value
    return disease_name_vi(value)


def display_title_for_prediction(value: str, needs_more_input: bool) -> str:
    if LABEL_TYPE == "drug_group":
        prefix = "Gợi ý tham khảo: " if needs_more_input else "Nhóm thuốc gợi ý: "
        return f"{prefix}{value}"
    return f"Gợi ý tham khảo: {disease_name_vi(value)}" if needs_more_input else disease_name_vi(value)


def has_eye_allergy_symptom(active_symptoms: set[str] | None) -> bool:
    return bool(
        active_symptoms
        and has_any_symptom(
            active_symptoms,
            ["watering from eyes", "lacrimation", "itchiness of eye", "redness of eyes", "eye redness"],
        )
    )


def has_nasal_allergy_symptom(active_symptoms: set[str] | None) -> bool:
    return bool(
        active_symptoms
        and has_any_symptom(
            active_symptoms,
            ["continuous sneezing", "coryza", "runny nose", "congestion", "itching", "itching of skin"],
        )
    )


def medication_reference_items_for_group(group: str | None, active_symptoms: set[str] | None = None) -> list[str]:
    if not group:
        return []

    # Vòng 6: ưu tiên 2-3 hoạt chất ĐÃ CURATE (sạch, tiếng Việt) thay cho dump dữ liệu thô.
    reps = representative_active_ingredients_for_group(group)
    if reps:
        return [f"Hoạt chất minh hoạ trong nhóm: {', '.join(reps)}"]
    note = representative_note_for_group(group)
    if note:
        return [note]

    # Fallback (chỉ khi nhóm chưa được curate): danh sách thô, cap nhỏ để tránh dài dòng.
    items = list(references["medications"].get(group, [f"Nhóm thuốc dự đoán: {group}"]))
    return items[:3]


def drug_group_guidance(group: str, active_symptoms: set[str] | None = None) -> dict[str, list[str] | str]:
    base = DRUG_GROUP_GUIDANCE.get(group.lower(), {})
    treatment = list(base.get("treatment", []))
    precautions = list(base.get("precautions", []))
    care = list(base.get("care", []))

    if not treatment:
        treatment = [
            f"Hướng xử trí tham khảo: model gợi ý nhóm '{group}' từ các triệu chứng đã nhận diện; cần bác sĩ/dược sĩ xác nhận trước khi dùng thuốc.",
        ]
    treatment.extend(medication_reference_items_for_group(group, active_symptoms))

    if not precautions:
        precautions = [
            "Không tự dùng thuốc chỉ dựa trên kết quả mô hình; cần đánh giá bệnh nền, tuổi, thai kỳ, dị ứng và thuốc đang dùng.",
            "Không tự phối nhiều thuốc cùng nhóm hoặc nhiều thuốc cảm/giảm đau nếu chưa kiểm tra hoạt chất trùng lặp.",
        ]
    if not care:
        care = [
            "Theo dõi diễn tiến triệu chứng, thời điểm khởi phát, mức độ sốt/đau/khó thở và các dấu hiệu bất thường để cung cấp khi đi khám.",
        ]

    return {
        "treatment": treatment,
        "precautions": precautions,
        "care": care,
        "warning": base.get(
            "warning",
            "Kết quả chỉ là gợi ý nhóm thuốc từ dữ liệu huấn luyện, không phải đơn thuốc. Không có liều dùng trong hệ thống này. Đi khám ngay nếu triệu chứng nặng, kéo dài, khó thở, đau ngực, lơ mơ, mất nước, sốt cao hoặc có dấu hiệu nguy hiểm.",
        ),
        "guidance_source": "mapped_drug_group_csv",
    }


def respiratory_rule_drug_group(active_symptoms: set[str]) -> str | None:
    has_respiratory = has_any_symptom(active_symptoms, ["cough", "sore throat", "throat irritation", "runny nose", "coryza", "congestion", "continuous sneezing"])
    if not has_respiratory:
        return None

    has_fever = has_any_symptom(active_symptoms, ["fever", "mild fever", "high fever"])
    has_lower_airway_warning = has_any_symptom(active_symptoms, ["breathlessness", "chest pain", "blood in sputum"])
    has_phlegm = has_any_symptom(active_symptoms, ["phlegm", "mucoid sputum", "rusty sputum"])
    # Dấu hiệu DỊ ỨNG thật (hắt hơi/chảy nước mắt/ngứa) -> kháng histamin mới hợp lý.
    has_allergic_pattern = has_any_symptom(active_symptoms, ["continuous sneezing", "watering from eyes", "itching"])
    has_rhinitis_pattern = has_any_symptom(active_symptoms, ["coryza", "runny nose", "congestion"])
    has_sore_throat = has_any_symptom(active_symptoms, ["sore throat", "throat irritation", "throat pain", "pain in the throat"])

    if has_lower_airway_warning:
        return None
    if has_phlegm:
        return "thuốc long đờm / giảm ho"
    if has_allergic_pattern and not has_fever:
        return "thuốc kháng histamin"
    # Đau/rát họng (không sốt, không kèm dị ứng rõ) -> giảm đau hạ sốt OTC, KHÔNG ép kháng histamin.
    if has_sore_throat and not has_fever:
        return "thuốc giảm đau hạ sốt"
    if has_rhinitis_pattern and not has_fever:
        return "thuốc kháng histamin"
    if has_fever:
        return "thuốc giảm đau hạ sốt"
    return None


def bacterial_respiratory_rule_drug_group(notes: str, active_symptoms: set[str]) -> str | None:
    """Nghi NHIỄM KHUẨN hô hấp: sốt cao KÈM đờm mủ (vàng/xanh/đặc) -> nhóm kháng sinh (kê đơn,
    sẽ bị né an toàn). Bắt MÀU đờm từ notes vì feature 'phlegm' không phân biệt màu/độ đặc."""
    t = normalize(notes or "")
    def has(*ps): return any(p in t for p in ps)
    high_fever = has_any_symptom(active_symptoms, ["high fever"]) or \
        affirmative_mention(t, ("sot cao", "sot 38", "sot 39", "sot 40", "sot tren 38", "sot tren 39", "sot gan 40",
                                "sot ret run", "ret run", "run lanh", "lanh run", "soc lanh", "sot lanh run"))
    purulent_sputum = has("dom vang", "dam vang", "dom xanh", "dam xanh", "dom mu", "dam mu",
                          "dom dac", "dam dac", "khac dom vang", "khac dom xanh", "ho dom vang", "ho dom xanh")
    if high_fever and purulent_sputum:
        return "thuốc kháng sinh"
    return None


def general_fever_pain_rule_drug_group(active_symptoms: set[str]) -> str | None:
    # Sốt kèm đau mỏi người, đau đầu hoặc đau khớp nhưng không có yếu tố dịch tễ vùng sốt rét
    has_fever = has_any_symptom(active_symptoms, ["fever", "mild fever", "high fever"])
    has_pain = has_any_symptom(active_symptoms, ["muscle_pain", "headache", "joint_pain", "back_pain"])
    if has_fever and has_pain:
        return "thuốc giảm đau hạ sốt"
    return None


_FEVER_FEATURES = {"fever", "mild fever", "high fever"}


def isolated_fever_rule_drug_group(active_symptoms: set[str]) -> str | None:
    """Sốt NHẸ ĐƠN THUẦN (là triệu chứng duy nhất còn lại, KHÔNG phải sốt cao) -> hạ sốt OTC.
    Vá over-triage: trước đây ca 'sốt nhẹ, không ho/khó thở/đau họng' bị chặn 'cần bác sĩ'."""
    has_fever = has_any_symptom(active_symptoms, list(_FEVER_FEATURES))
    has_high = has_any_symptom(active_symptoms, ["high fever"])
    non_fever = {s for s in active_symptoms if normalize(s) not in {normalize(x) for x in _FEVER_FEATURES}}
    if has_fever and not has_high and not non_fever:
        return "thuốc giảm đau hạ sốt"
    return None


def insect_bite_rule_drug_group(notes: str) -> str | None:
    """Côn trùng (muỗi/kiến) đốt khu trú: sưng/ngứa 1 vùng, KHÔNG dấu hiệu toàn thân nặng
    -> kháng histamin OTC (vá over-triage 'né an toàn' cho 1 nốt muỗi đốt)."""
    t = normalize(notes or "")
    def has(*ps): return any(p in t for p in ps)
    bite = has("muoi dot", "muoi can", "con trung dot", "con trung can", "kien dot", "kien can",
               "bo chet dot", "ve dot")
    if not bite:
        return None
    # Có dấu hiệu phản vệ/toàn thân -> KHÔNG hạ OTC (để cổng cấp cứu/né lo).
    if has("kho tho", "sung moi", "sung luoi", "sung hong", "choang", "ngat", "tut huyet ap",
           "lan khap nguoi", "noi khap nguoi", "sot cao"):
        return None
    return "thuốc kháng histamin"


def heat_exhaustion_rule_drug_group(notes: str) -> str | None:
    """Gắng sức/nắng nóng (chạy bộ/ngoài nắng) + chóng mặt/mệt lả/khát, KHÔNG rối loạn tri giác
    -> bù dịch & điện giải (ORS) OTC. Pin kết quả ổn định cho ca say nắng nhẹ."""
    t = normalize(notes or "")
    def has(*ps): return any(p in t for p in ps)
    heat_ctx = has("ngoai nang", "duoi nang", "troi nang", "chay bo", "gang suc", "tap the thao",
                   "lao dong nang", "di nang ve", "phoi nang", "nang nong")
    sx = has("chong mat", "met la", "met lu", "khat nuoc", "hoa mat", "met lai", "uon oai", "met moi")
    severe = has("lu du", "li bi", "lo mo", "ngat", "xiu", "co giat", "kho tho", "dau nguc")
    if heat_ctx and sx and not severe:
        return "bù dịch và điện giải"
    return None


def dental_rule_drug_group(active_symptoms: set[str]) -> str | None:
    if not has_any_symptom(active_symptoms, ["toothache", "gum pain", "pain in gums", "jaw swelling", "bleeding gums", "mouth pain"]):
        return None
    return "thuốc giảm đau nha khoa"


def gastrointestinal_rule_drug_group(active_symptoms: set[str]) -> str | None:
    if has_any_symptom(active_symptoms, ["diarrhea", "diarrhoea", "dehydration"]):
        return "bù dịch và điện giải"
    if has_any_symptom(active_symptoms, ["vomiting", "nausea"]):
        return "thuốc chống nôn"
    if has_any_symptom(active_symptoms, ["stomach pain", "abdominal pain", "belly pain", "heartburn", "acidity", "indigestion"]):
        return "thuốc điều trị dạ dày"
    return None


def urinary_rule_drug_group(active_symptoms: set[str]) -> str | None:
    # Cụm nhiễm khuẩn tiết niệu: tiểu buốt/tiểu rắt... -> gợi ý nhóm kháng sinh tham khảo.
    # Đặt TRƯỚC gastrointestinal_rule để "đau bụng dưới" không kéo về "thuốc điều trị dạ dày".
    has_urinary = has_any_symptom(
        active_symptoms,
        [
            "burning micturition",
            "painful urination",
            "bladder discomfort",
            "foul smell of urine",
            "continuous feel of urine",
            "spotting urination",
        ],
    )
    if not has_urinary:
        return None
    return "thuốc kháng sinh"


def migraine_rule_drug_group(active_symptoms: set[str]) -> str | None:
    # Đau đầu kiểu migraine (kèm buồn nôn/nôn/sợ ánh sáng/chóng mặt) -> nhóm giảm đau hạ sốt.
    # Đặt TRƯỚC gastrointestinal_rule để "buồn nôn" không kéo về "thuốc chống nôn".
    if not has_any_symptom(active_symptoms, ["headache", "frontal headache"]):
        return None
    # Loại trừ dấu hiệu đỏ thần kinh: không tự gợi ý giảm đau, để luồng cần-thêm-thông-tin/cảnh báo xử lý.
    red_flags = has_any_symptom(
        active_symptoms,
        [
            "weakness of one body side",
            "altered sensorium",
            "coma",
            "slurred speech",
            "stiff neck",
            "loss of balance",
            "seizures",
        ],
    )
    if red_flags:
        return None
    companion = has_any_symptom(
        active_symptoms,
        ["visual disturbances", "nausea", "vomiting", "dizziness"],
    )
    if not companion:
        return None
    return "thuốc giảm đau hạ sốt"


def has_neuro_danger_signs(active_symptoms: set[str]) -> bool:
    # Dấu hiệu đỏ thần kinh: cần đi khám cấp, không nên dựa vào gợi ý thuốc tham khảo.
    hard_flags = has_any_symptom(
        active_symptoms,
        [
            "weakness of one body side",
            "altered sensorium",
            "coma",
            "slurred speech",
            "seizures",
        ],
    )
    if hard_flags:
        return True
    # "Cứng cổ" CHỈ là dấu hiệu đỏ (nghi viêm màng não) khi kèm sốt hoặc đau đầu;
    # cứng cổ cơ học đơn thuần (đau vai gáy) là lành tính, không báo động.
    has_stiff_neck = has_any_symptom(active_symptoms, ["stiff neck"])
    has_meningism_context = has_any_symptom(
        active_symptoms, ["fever", "high fever", "mild fever", "headache"]
    )
    return has_stiff_neck and has_meningism_context


_NEGATORS = ("khong", "chua", "chang", "khong he", "deu khong", "lam gi co")


def affirmative_mention(text: str, patterns, window: int = 16) -> bool:
    """True nếu có ÍT NHẤT một lần xuất hiện của pattern mà KHÔNG bị phủ định ngay trước đó
    (trong cửa sổ `window` ký tự). Dùng cho ngữ cảnh nhạy như chấn thương đầu, rượu — để câu
    'không va đập vào đầu' KHÔNG bị hiểu là có chấn thương. `text` phải đã qua normalize().
    """
    for pattern in patterns:
        start = 0
        while True:
            i = text.find(pattern, start)
            if i < 0:
                break
            prefix = text[max(0, i - window):i]
            if not any(neg in prefix for neg in _NEGATORS):
                return True
            start = i + len(pattern)
    return False


# Hậu tố thông điệp cờ đỏ — DÙNG ĐỂ PHÂN LOẠI MỨC ĐỘ ở caller:
#   GO  = CẤP CỨU thật (gọi 115/đến viện ngay) -> score_type "emergency".
#   SEE = cần đi khám sớm để tầm soát, KHÔNG phải cấp cứu -> score_type "referral".
# Caller (/api/predict) phân biệt 2 mức này bằng cách so hậu tố message.
EMERGENCY_GO_SUFFIX = " Đây có thể là CẤP CỨU; gọi 115 hoặc đến cơ sở y tế ngay, KHÔNG tự dùng thuốc theo gợi ý."
REFERRAL_SEE_SUFFIX = " Hãy đi khám bác sĩ sớm để được đánh giá, KHÔNG tự dùng thuốc theo gợi ý."


def emergency_red_flag_from_notes(notes: str) -> str | None:
    """Dấu hiệu CẤP CỨU/khủng hoảng nhận từ mô tả thô (không phụ thuộc feature trích được).
    Trả về thông điệp cảnh báo nếu phát hiện; None nếu không. Ưu tiên AN TOÀN: thà cảnh báo thừa.

    Message kết thúc bằng GO (cấp cứu) hoặc SEE (đi khám sớm) để caller phân loại mức độ.
    """
    t = normalize(notes or "")
    def has(*ps): return any(p in t for p in ps)

    GO = EMERGENCY_GO_SUFFIX

    # 1) Ý định tự tử / tự hại -> thông điệp hỗ trợ khủng hoảng (ưu tiên cao nhất)
    if has("tu tu", "tu sat", "muon chet", "ket thuc cuoc doi", "tu hai", "hai ban than",
           "cat tay cho", "khong muon song", "khong thiet song", "khong con thiet song",
           "chan song", "buong xuoi cuoc song", "song khong con y nghia", "chet cho xong"):
        return ("Bạn đang mô tả ý định tự tử/tự hại. Bạn không đơn độc — hãy liên hệ NGAY người thân "
                "tin cậy hoặc đường dây hỗ trợ tâm lý (vd Ngày Mai 096 306 1414) hoặc gọi cấp cứu 115. "
                "Hệ thống này KHÔNG thay thế hỗ trợ y tế/khủng hoảng.")

    # 2) Ngộ độc / quá liều
    if has("ngo doc", "qua lieu", "uong nham", "thuoc tru sau", "uong thuoc sau", "uong nhieu thuoc",
           "uong hoa chat", "uong nham thuoc", "uong ca vi", "uong nguyen vi", "uong het vi",
           "uong ca lo thuoc", "uong nhieu vien", "uong vai vi", "uong ca hop thuoc", "uong qua nhieu thuoc"):
        return "Nghi ngộ độc/quá liều." + GO

    # 3) Phản vệ / phù mạch (dị ứng nặng)
    angioedema = has("sung moi", "sung luoi", "phu moi", "phu luoi", "phu mat", "sung mat",
                     "hong nghen", "co hong nghen", "phu mach", "sung hong")
    allergic_trigger = has("an tom", "an hai san", "ong dot", "ong chich", "uong thuoc la", "sau khi tiem",
                           "tiem vaccine", "tiem phong", "chich ngua", "tiem thuoc", "sau tiem", "tiem xong",
                           "noi me day", "man khap nguoi", "noi man khap", "noi man do", "noi man")
    # Dùng affirmative_mention để câu "KHÔNG khó thở" KHÔNG kích hoạt (has() khớp nhầm chuỗi con).
    # Nhánh phù mạch (sưng môi/lưỡi rất đặc hiệu): chấp nhận cả "choáng". Nhánh tác nhân dị ứng
    # (đồ ăn/tiêm) chỉ nhận khó thở/thở rít/tụt HA/ngất (sốc thật) để tránh báo giả.
    severe_resp_or_shock = affirmative_mention(t, ("kho tho", "tho rit", "tut huyet ap", "choang", "ngat"))
    severe_resp_or_real_shock = affirmative_mention(
        t, ("kho tho", "tho rit", "khong tho duoc", "tut huyet ap", "ngat", "soc phan ve"))
    if (angioedema and severe_resp_or_shock) or (allergic_trigger and severe_resp_or_real_shock) \
       or (allergic_trigger and affirmative_mention(t, ("tut huyet ap", "ngat", "soc"))):
        return "Nghi PHẢN VỆ (dị ứng nặng: sưng môi/lưỡi/họng, khó thở, tụt huyết áp)." + GO

    # 4) Xuất huyết nặng: nôn ra máu / phân đen (melena)
    if has("non ra mau", "oi ra mau", "non mau", "phan den", "di ngoai phan den", "phan hac in"):
        return "Nghi xuất huyết tiêu hóa nặng (nôn ra máu/phân đen)." + GO
    if has("di ngoai ra mau", "chay mau nhieu", "mau chay nhieu") and has("choang", "hoa mat", "nguoi lanh", "tut huyet ap", "tim dap nhanh"):
        return "Nghi mất máu cấp/sốc." + GO

    # 5) Suy hô hấp cấp / tím tái
    cyanosis = has("tim tai", "moi tim", "tim moi", "da tim", "tim nguoi")
    severe_dyspnea = has("kho tho du doi", "kho tho nang", "tho gap", "ngat tho", "khong tho duoc")
    if cyanosis or severe_dyspnea:
        return "Dấu hiệu suy hô hấp cấp (tím tái/khó thở dữ dội)." + GO

    # 6) Nhồi máu cơ tim: đau ngực + (lan tay/hàm | vã mồ hôi | bóp nghẹt)
    chest = has("dau nguc", "dau that nguc", "tuc nguc du doi", "nguc bi bop")
    mi_feat = has("lan tay trai", "lan canh tay", "lan ham", "lan vai", "lan ra tay", "va mo hoi", "bop nghet", "bop chat")
    if chest and mi_feat:
        return "Đau ngực nghi nhồi máu cơ tim (lan tay/hàm, vã mồ hôi, bóp nghẹt)." + GO

    # 7) Chấn thương đầu nặng
    #   (a) Cơ chế chấn thương cũ + dấu hiệu nặng (giữ nguyên để không regress).
    if has("nga cao", "tai nan", "chan thuong dau", "chan thuong so nao", "nga dap dau", "ta nga") and \
       has("chay mau tai", "noi lan", "lan lon", "lo mo", "bat tinh", "dau dau du doi", "non oi"):
        return "Nghi chấn thương đầu nặng." + GO
    #   (b) Vòng 4: bắt thêm cách diễn đạt "va đập/đập/đánh vào đầu" KÈM dấu hiệu thần kinh/nôn.
    #   - Dùng affirmative_mention để câu phủ định "không va đập vào đầu" KHÔNG kích hoạt.
    #   - Thay "dau goi" (đầu gối) bằng "goi" trước khi dò, để "đầu" chắc chắn là cái đầu
    #     (tránh bẫy "đập vào đầu gối"/"đau đầu gối").
    t_head = t.replace("dau goi", " goi ")
    head_impact = affirmative_mention(t_head, (
        "va dap vao dau", "dap vao dau", "dap dau", "nga dap dau", "te dap dau",
        "danh vao dau", "va vao dau", "dung vao dau", "dung dau", "chan thuong dau",
        "chan thuong so nao",
    ))
    post_injury_sign = any(p in t_head for p in (
        "dau dau", "nhuc dau", "buon non", "non", "oi", "chong mat", "choang",
        "lo mo", "bat tinh", "ngat", "lan lon", "noi kho", "yeu liet", "co giat",
        "mat thang bang", "di khong vung", "hoa mat",
    ))
    if head_impact and post_injury_sign:
        return ("Nghi chấn thương đầu/sọ não sau va đập, kèm đau đầu, buồn nôn/nôn hoặc dấu hiệu "
                "thần kinh.") + GO

    # 8) Bụng ngoại khoa (viêm phúc mạc): bụng cứng
    if has("bung cung", "cung nhu go", "bung cung nhu go", "do cung bung", "phan ung thanh bung"):
        return "Nghi bụng ngoại khoa cấp (bụng cứng, đau dữ dội)." + GO

    # 9) Cấp cứu sản khoa: thai + chảy máu/đau bụng HOẶC dấu tiền sản giật
    if has("mang thai", "co thai", "dang bau", "co bau", "thai ", "thai nhi", "bau ", "co bau", "bau bi"):
        if has("chay mau", "ra mau", "ra dich nau", "dau bung", "dau quan", "dau lung du doi"):
            return "Có thai kèm chảy máu/đau bụng — nguy cơ cấp cứu sản khoa (sảy thai/thai ngoài tử cung)." + GO
        # Tiền sản giật/sản giật: đau đầu dữ dội / rối loạn thị giác / phù nhiều / co giật.
        preeclampsia_sign = (
            (has("dau dau") and has("du doi", "nhieu", "nang", "nhu bua bo", "khong giam"))
            or has("nhin mo", "mo mat", "mat mo", "hoa mat", "nhin khong ro", "loa mat")
            or has("phu mat", "phu chan", "phu hai chan", "phu toan than", "phu nhieu", "phu tay chan", "phu nang")
        )
        if preeclampsia_sign:
            return ("Có thai kèm đau đầu dữ dội / nhìn mờ / phù — nghi TIỀN SẢN GIẬT, cần cấp cứu "
                    "sản khoa ngay.") + GO

    # ── P0 (2026-06-15): bổ sung cờ đỏ còn lọt, đo bằng scripts/independent_probe.py.
    # Dùng affirmative_mention (aff) để phủ định "không sụt cân"/"không co giật"/"không tê"
    # KHÔNG kích hoạt cờ đỏ sai (P0.6 near-miss).
    SEE = REFERRAL_SEE_SUFFIX
    def aff(*ps): return affirmative_mention(t, ps)

    # 10) Đột quỵ (FAST): méo miệng / yếu-liệt nửa người / nói khó khởi phát đột ngột
    if aff("meo mieng", "lech mat", "lech mieng", "mieng meo",
           "yeu nua nguoi", "liet nua nguoi", "te nua nguoi", "yeu mot ben nguoi", "liet mot ben nguoi") \
       or (aff("noi kho", "noi ngong", "kho noi", "noi dap") and has("dot ngot")):
        return "Dấu hiệu nghi ĐỘT QUỴ (méo miệng, yếu/liệt nửa người, nói khó)." + GO

    # 10b) Co giật ĐANG/VỪA lên cơn (kể cả sốt cao co giật ở trẻ -> vẫn CẤP CỨU, ưu tiên trước
    #      mọi luật né an toàn theo bệnh nền/lứa tuổi). CHỈ bắt cơn cấp, KHÔNG bắt tiền sử
    #      "từng co giật"/"không co giật" (giữ aff cho phủ định + chọn cụm cấp tính).
    if aff("len con co giat", "len con giat", "vua co giat", "vua len con giat", "dang co giat",
           "co giat toan than", "giat toan than", "sui bot mep", "co giat lien tuc", "co giat ca nguoi"):
        return "Nghi CO GIẬT/động kinh đang lên cơn." + GO

    # 11) Chèn ép tủy/đuôi ngựa: yếu liệt 2 chân + bí tiểu / tê vùng yên ngựa
    saddle = aff("te yen ngua", "te vung yen ngua", "te bo phan sinh duc", "mat cam giac yen ngua", "te hau mon")
    leg_weak = aff("yeu hai chan", "liet hai chan", "yeu hai chi duoi", "liet hai chi duoi", "yeu chan dot ngot", "liet chan dot ngot")
    bladder = aff("bi tieu", "tieu khong tu chu", "dai khong tu chu", "mat tu chu tieu", "khong di tieu duoc")
    if saddle or (leg_weak and bladder):
        return "Yếu/liệt hai chân kèm bí tiểu hoặc tê vùng yên ngựa — nghi chèn ép tủy/đuôi ngựa." + GO

    # 12) Đau đầu sét đánh: khởi phát đột ngột + dữ dội (nghi xuất huyết dưới nhện)
    if aff("dau dau", "nhuc dau", "dau nua dau") and aff("dot ngot", "bat ngo", "set danh", "ngay lap tuc") \
       and aff("du doi", "du doi nhat", "nhat tu truoc toi nay", "te nhat", "khung khiep", "nang chua tung"):
        return "Đau đầu dữ dội khởi phát đột ngột (đau đầu sét đánh) — nghi xuất huyết não/dưới nhện." + GO

    # 13) Đau hố chậu phải khu trú — nghi viêm ruột thừa
    if aff("ho chau phai", "hcp", "bung duoi ben phai", "bung duoi phai", "1/4 duoi phai", "vung chau phai") \
       and aff("dau"):
        return "Đau khu trú hố chậu phải — nghi viêm ruột thừa, cần khám ngoại khoa ngay." + GO

    # 14) Ho kéo dài + sụt cân / mồ hôi đêm / ho ra máu — tầm soát lao/bệnh phổi/ung thư
    chronic_cough = aff("ho keo dai", "ho dai dang", "ho man", "ho lau ngay", "ho nhieu tuan", "ho may tuan",
                        "ho 2 tuan", "ho 3 tuan", "ho ba tuan", "ho hai tuan", "ho khan keo dai", "ho may thang")
    systemic = aff("sut can", "giam can", "gay sut", "mo hoi dem", "do mo hoi dem", "ra mo hoi dem", "ho ra mau", "khac ra mau")
    if chronic_cough and systemic:
        return "Ho kéo dài kèm sụt cân/đổ mồ hôi đêm/ho ra máu — cần khám tầm soát (lao, bệnh phổi, ung thư)." + SEE

    # 15) Bỏng (nước sôi/lửa/điện/hóa chất) hoặc bỏng diện rộng/sâu -> xử trí y tế.
    if aff("bong nuoc soi", "bong lua", "bong dien", "bong hoa chat", "bong axit", "bong po xe", "bong xang") \
       or (aff("bi bong") and aff("dien rong", "ca mang", "nhieu vung", "phong rop", "lan rong", "nang", "sau")):
        return "Bỏng (đặc biệt diện rộng/sâu hoặc ở mặt/tay/bộ phận sinh dục) cần được xử trí y tế." + SEE

    # 15b) Đau thượng vị/bụng trên DỮ DỘI lan ra sau lưng -> nghi viêm tụy cấp / bụng ngoại khoa.
    if (has("dau bung tren", "dau thuong vi", "dau vung tren ron", "dau bung vung tren", "dau ham vi")
        or (has("dau bung") and has("tren ron", "thuong vi"))) \
       and has("du doi", "quan tham", "dau nhieu", "dau quan") \
       and has("lan ra sau lung", "lan sau lung", "xuyen ra sau lung", "ra sau lung", "lan ra lung"):
        return "Đau thượng vị dữ dội lan ra sau lưng — nghi viêm tụy cấp, cần đi khám/cấp cứu ngay." + GO

    # 15c) Cờ đỏ NUỐT: nuốt nghẹn/khó nuốt tăng dần kèm sụt cân -> tầm soát thực quản/dạ dày.
    if aff("nuot nghen", "kho nuot", "nuot vuong", "nghen khi nuot", "nuot kho", "nuot dau tang dan") \
       and aff("sut can", "giam can", "gay sut", "sut ki"):
        return ("Nuốt nghẹn/khó nuốt kèm sụt cân — dấu hiệu CẢNH BÁO, cần đi khám tầm soát "
                "(thực quản/dạ dày) sớm.") + SEE

    # 16) Mất nước NẶNG: tiêu chảy/nôn nhiều KÈM dấu hiệu NẶNG THẬT (rối loạn tri giác / không
    #     uống được). CHỈ "tiểu ít/môi khô" là mất nước VỪA -> để ORS (OTC) xử lý, không chặn.
    gi_fluid_loss = aff("tieu chay", "di ngoai nhieu lan", "di ngoai phan long", "di ngoai lien tuc",
                        "non nhieu", "non lien tuc", "oi nhieu", "non oi nhieu")
    severe_dehydr_sign = aff("lu du", "li bi", "lo mo", "kiet suc", "khong uong duoc nuoc",
                             "uong vao non het", "mat nuoc nang", "kho danh thuc", "ngu li bi", "met la di")
    if gi_fluid_loss and severe_dehydr_sign:
        return ("Nghi MẤT NƯỚC NẶNG (tiêu chảy/nôn kèm tiểu ít hoặc lừ đừ/li bì). Cần bù dịch và "
                "ĐI KHÁM NGAY, KHÔNG tự dùng thuốc theo gợi ý.") + ""

    return None


# ── Rule notes-aware (2026-06-09 vòng 3): 2 nhóm bệnh NGOÀI tập train mà model hay
# "đoán sai tự tin". Nhận diện từ mô tả thô vì dấu đặc hiệu (dịch tễ vùng rừng núi,
# da/niêm nhợt) KHÔNG có feature tương ứng trong model. Mỗi rule rất đặc hiệu để tránh
# dương tính giả, và trả ĐÚNG nhóm thuốc thay vì để model trả kháng sinh/tim mạch.

def malaria_rule_drug_group(notes: str, active_symptoms: set[str]) -> str | None:
    """Nghi sốt rét: sốt thành cơn/rét run + KÈM yếu tố dịch tễ (vùng rừng núi/sốt rét).
    Yếu tố dịch tễ là BẮT BUỘC để không nhầm với sốt virus/cúm thông thường. Trả nhóm
    'thuốc điều trị sốt rét' (kèm cảnh báo xét nghiệm) thay vì để model trả 'thuốc kháng sinh'.
    """
    t = normalize(notes or "")
    def has(*ps): return any(p in t for p in ps)

    # Yếu tố dịch tễ vùng lưu hành sốt rét — điều kiện BẮT BUỘC.
    epidemiology = has(
        "rung nui", "vung rung", "di rung", "vao rung", "o rung",
        "vung sot ret", "mien nui", "vung nui", "vung cao", "tay nguyen", "vung dich te",
    )
    if not epidemiology:
        return None

    periodic_fever = has("sot thanh con", "sot tung con", "sot con", "sot ret", "sot chu ky", "sot cach nhat")
    chills = has("ret run", "lanh run", "run lap cap") or has_any_symptom(active_symptoms, ["chills", "shivering"])
    fever_signal = has("sot") or has_any_symptom(active_symptoms, ["fever", "high fever", "mild fever"])

    if periodic_fever or (fever_signal and chills):
        return "thuốc điều trị sốt rét"
    return None


def anemia_rule_drug_group(notes: str, active_symptoms: set[str]) -> str | None:
    """Nghi thiếu máu/thiếu vi chất: da/niêm NHỢT (dấu đặc hiệu) kèm mệt mỏi/chóng mặt/
    móng giòn. Neo vào dấu xanh xao/niêm nhợt vì ca tim mạch thật KHÔNG mô tả triệu chứng
    này -> tránh chặn nhầm. Trả 'vitamin và khoáng chất' thay vì để model trả 'thuốc tim mạch/huyết áp'.
    """
    t = normalize(notes or "")
    def has(*ps): return any(p in t for p in ps)

    # Da/niêm nhợt là dấu neo BẮT BUỘC.
    pallor = has(
        "da xanh", "xanh xao", "niem nhot", "niem mac nhot", "nhot nhat",
        "moi nhot", "da nhot", "long ban tay nhot", "sac mat nhot",
    )
    if not pallor:
        return None

    systemic = (
        has_any_symptom(active_symptoms, ["fatigue", "dizziness", "brittle nails"])
        or has("met moi", "met", "choang", "hoa mat", "chong mat", "mong tay gion", "mong gion")
    )
    if systemic:
        return "vitamin và khoáng chất"
    return None


# ── Ngữ cảnh notes-aware (2026-06-09 vòng 4): nhân–quả/hoàn cảnh "sau khi X" mà hệ "túi
# triệu chứng" bỏ qua. KHÔNG phải nhóm thuốc nên không vào rule_group; dùng để chặn/cảnh báo.

def has_strong_alcohol_context(notes: str) -> bool:
    """Ngữ cảnh rượu RÕ/NHIỀU -> chống chỉ định paracetamol (độc gan). Có guard phủ định."""
    t = normalize(notes or "")
    return affirmative_mention(t, (
        "uong ruou nhieu", "uong nhieu ruou", "sau khi uong ruou", "vua uong ruou",
        "vua nhau", "sau khi nhau", "nhau nhieu", "nhau xin", "say ruou", "say xin",
        "qua chen", "lam dung ruou", "nghien ruou", "ruou bia nhieu", "uong bia ruou nhieu",
    ))


def has_weak_alcohol_context(notes: str) -> bool:
    """Ngữ cảnh rượu NHẸ/không rõ mức độ -> vẫn gợi ý nhưng thêm cảnh báo động."""
    t = normalize(notes or "")
    return affirmative_mention(t, (
        "co uong ruou", "uong ruou", "uong bia", "ruou bia", "moi uong bia", "moi uong ruou",
        "nhau",
    ))


def has_exertion_heat_context(notes: str) -> bool:
    """Ngữ cảnh gắng sức/nắng nóng -> gợi ý bù nước/nghỉ (không cấp cứu mặc định)."""
    t = normalize(notes or "")
    return affirmative_mention(t, (
        "sau khi chay bo", "chay bo xong", "sau khi tap nang", "tap nang xong",
        "sau khi gang suc", "gang suc qua", "van dong manh", "sau khi van dong",
        "ra nang", "phoi nang", "duoi nang", "troi nang", "nang nong", "lam viec ngoai troi",
    ))


def has_headache_nausea_or_dizzy(active_symptoms: set[str], notes: str) -> bool:
    if has_any_symptom(active_symptoms, ["headache", "frontal headache", "nausea", "vomiting", "dizziness"]):
        return True
    t = normalize(notes or "")
    return any(p in t for p in ("dau dau", "nhuc dau", "buon non", "non", "chong mat", "choang", "hoa mat"))


# ── Helper LLM (vòng 5): đọc output đã-validate của tầng LLM để CỦNG CỐ lưới an toàn.
# Không có hàm nào ở đây chọn nhóm thuốc; chỉ trả tín hiệu cảnh báo/ngữ cảnh.

def llm_context_has(context: dict | None, type_name: str) -> bool:
    if not isinstance(context, dict):
        return False
    return any(
        isinstance(item, dict) and item.get("type") == type_name
        for item in context.get("contexts", [])
    )


def llm_red_flag_has(context: dict | None, flag: str) -> bool:
    if not isinstance(context, dict):
        return False
    return flag in (context.get("red_flags") or [])


def llm_context_text(context: dict | None, type_name: str) -> str:
    """Trả phần text của context type đầu tiên khớp (để đưa qua helper ngữ cảnh sẵn có)."""
    if not isinstance(context, dict):
        return ""
    for item in context.get("contexts", []):
        if isinstance(item, dict) and item.get("type") == type_name:
            return str(item.get("text", ""))
    return ""


def llm_safety_red_flag_message(context: dict | None, notes: str, active_symptoms: set[str]) -> str | None:
    """Cổng an toàn THỨ HAI dựa trên LLM (chạy SAU cổng cấp cứu lexicon). Chỉ kích hoạt khi cờ đỏ
    của LLM được CHỨNG THỰC bằng triệu chứng/notes -> tránh báo động giả. Trả message hoặc None.
    Lưu ý: cổng cấp cứu lexicon đã chạy trước; tới đây nghĩa là lexicon bỏ sót cách diễn đạt, nên
    LLM bù vào phần đó.
    """
    if not isinstance(context, dict):
        return None
    flags = set(context.get("red_flags") or [])
    if not flags:
        return None
    t = normalize(notes or "")
    GO = EMERGENCY_GO_SUFFIX

    # Nhóm ý định/ngộ độc/phản vệ: ưu tiên an toàn (lexicon đã bỏ sót mới tới đây).
    if "suicide_self_harm" in flags:
        return ("Bạn đang mô tả ý định tự tử/tự hại. Bạn không đơn độc — hãy liên hệ NGAY người thân "
                "tin cậy hoặc đường dây hỗ trợ tâm lý (vd Ngày Mai 096 306 1414) hoặc gọi cấp cứu 115. "
                "Hệ thống này KHÔNG thay thế hỗ trợ y tế/khủng hoảng.")
    if "poisoning_overdose" in flags:
        return "Nghi ngộ độc/quá liều." + GO
    if "anaphylaxis" in flags:
        return "Nghi phản vệ (dị ứng nặng)." + GO

    # Nhóm theo triệu chứng: BẮT BUỘC có bằng chứng chứng thực trong notes/triệu chứng.
    if "head_trauma" in flags and has_headache_nausea_or_dizzy(active_symptoms, notes):
        return "Nghi chấn thương đầu/sọ não kèm dấu hiệu thần kinh." + GO
    if "stroke_neuro" in flags and has_neuro_danger_signs(active_symptoms):
        return "Nghi đột quỵ/tổn thương thần kinh cấp." + GO
    if "chest_pain_mi" in flags and any(p in t for p in ("dau nguc", "tuc nguc", "that nguc")):
        return "Nghi hội chứng vành cấp (đau ngực)." + GO
    if "severe_dyspnea" in flags and any(p in t for p in ("kho tho", "tho gap", "hut hoi", "ngat tho")):
        return "Nghi suy hô hấp cấp (khó thở nặng)." + GO
    if "seizure" in flags and any(p in t for p in ("co giat", "len con giat", "sui bot mep")):
        return "Nghi co giật." + GO
    if "altered_consciousness" in flags and any(p in t for p in ("lo mo", "lu lan", "bat tinh", "hon me", "li bi")):
        return "Nghi rối loạn ý thức." + GO
    if "gi_bleeding" in flags and any(p in t for p in ("non ra mau", "oi ra mau", "phan den", "di ngoai ra mau", "phan hac in")):
        return "Nghi xuất huyết tiêu hóa." + GO
    if "pregnancy_bleeding" in flags and any(p in t for p in ("mang thai", "co thai", "co bau", "thai")) and any(p in t for p in ("chay mau", "ra mau", "dau bung")):
        return "Nghi cấp cứu sản khoa (có thai kèm chảy máu/đau bụng)." + GO
    if "severe_dehydration" in flags and any(p in t for p in ("tieu it", "khong tieu", "mat nuoc", "li bi")):
        return "Nghi mất nước nặng." + GO
    return None


def dermatology_rule_drug_group(active_symptoms: set[str]) -> str | None:
    has_itch_or_rash = has_any_symptom(active_symptoms, ["itching", "itching of skin", "skin rash"])
    has_fungal_pattern = has_any_symptom(
        active_symptoms,
        ["dischromic patches", "skin peeling", "nodal skin eruptions", "abnormal appearing skin"],
    )
    if has_itch_or_rash and has_fungal_pattern:
        return "thuốc kháng nấm/ký sinh trùng ngoài da"
    return None


def fungal_notes_rule_drug_group(notes: str) -> str | None:
    # Nhiễm nấm da/móng/kẽ chân hoặc nấm sinh dục (khí hư bã đậu) -> kháng nấm.
    # Dùng token ĐẶC HIỆU đa ký tự, tránh "nấm"->"nam" trùng "nằm/năm/nam giới".
    t = normalize(notes or "")
    if any(k in t for k in (
        "nam ke chan", "nam da", "nam mong", "nam ban chan", "nam chan", "hac lao",
        "lang ben", "nhiem nam", "viem nam", "nam mieng", "nam am dao", "nam vung kin",
        "ba dau", "khi hu trang duc nhu ba dau",
    )):
        return "thuốc kháng nấm/ký sinh trùng ngoài da"
    return None


# ── Rule cluster theo logic y khoa chuẩn (2026-06-09, robust hoá) ─────────────
# Mỗi rule yêu cầu tổ hợp triệu chứng đặc hiệu để hạn chế dương tính giả.

def diabetes_rule_drug_group(active_symptoms: set[str]) -> str | None:
    polyuria = has_any_symptom(active_symptoms, ["polyuria", "frequent urination", "excessive urination at night"])
    metabolic = has_any_symptom(active_symptoms, ["weight loss", "excessive hunger", "increased appetite"])
    if polyuria and metabolic:
        return "thuốc điều trị đái tháo đường"
    return None


def thyroid_rule_drug_group(notes: str, active_symptoms: set[str]) -> str | None:
    # Bướu cổ là dấu hiệu rất đặc hiệu cho bệnh tuyến giáp.
    if has_any_symptom(active_symptoms, ["enlarged thyroid"]):
        return "thuốc nội tiết tuyến giáp"
    # Cường giáp KHÔNG kèm bướu cổ: hồi hộp + sụt cân + vã mồ hôi.
    if (
        has_any_symptom(active_symptoms, ["palpitations"])
        and has_any_symptom(active_symptoms, ["weight loss"])
        and has_any_symptom(active_symptoms, ["sweating", "excessive sweating"])
    ):
        return "thuốc nội tiết tuyến giáp"
    # Suy giáp KHÔNG kèm bướu cổ: tăng cân + sợ lạnh + (da khô / rụng tóc). 3 điều kiện -> đặc hiệu.
    t = normalize(notes or "")
    if has_any_symptom(active_symptoms, ["weight gain"]) and "so lanh" in t and any(k in t for k in ("da kho", "rung toc")):
        return "thuốc nội tiết tuyến giáp"
    return None


def bronchodilator_rule_drug_group(active_symptoms: set[str]) -> str | None:
    has_wheeze = has_any_symptom(active_symptoms, ["wheezing"])
    has_dyspnea = has_any_symptom(active_symptoms, ["breathlessness", "shortness of breath", "difficulty breathing", "chest tightness"])
    if has_wheeze and has_dyspnea:
        return "thuốc giãn phế quản"
    return None


def wound_infection_rule_drug_group(active_symptoms: set[str]) -> str | None:
    has_wound = has_any_symptom(active_symptoms, ["Redness, swelling, discharge from the wound", "pus filled pimples"])
    if has_wound and has_any_symptom(active_symptoms, ["fever", "high fever", "mild fever", "muscle pain", "swelling"]):
        return "thuốc kháng sinh"
    if has_wound:
        return "thuốc kháng sinh"
    return None


def infectious_bloody_diarrhea_rule_drug_group(active_symptoms: set[str]) -> str | None:
    has_blood = has_any_symptom(active_symptoms, ["bloody stool", "blood in stool", "melena"])
    has_gi = has_any_symptom(active_symptoms, ["abdominal pain", "belly pain", "stomach pain", "diarrhea", "diarrhoea"])
    has_fever = has_any_symptom(active_symptoms, ["fever", "high fever", "mild fever"])
    if has_blood and has_gi and has_fever:
        return "thuốc kháng sinh"
    return None


def neuropathic_pain_rule_drug_group(notes: str, active_symptoms: set[str]) -> str | None:
    nerve_pain = has_any_symptom(active_symptoms, ["Shooting or burning pain, tingling or numbness"])
    paresthesia = has_any_symptom(active_symptoms, ["paresthesia", "loss of sensation"])
    if nerve_pain:
        return "thuốc chống co giật/đau thần kinh"
    # Tê bì/dị cảm ở người ĐÁI THÁO ĐƯỜNG = bệnh thần kinh đái tháo đường.
    t = normalize(notes or "")
    if paresthesia and any(k in t for k in ("tieu duong", "dai thao duong")):
        return "thuốc chống co giật/đau thần kinh"
    return None


def musculoskeletal_nsaid_rule_drug_group(active_symptoms: set[str]) -> str | None:
    # Đau cơ-xương-khớp hoặc thống kinh, KHÔNG kèm sốt (loại nhiễm trùng) -> NSAID.
    if has_any_symptom(active_symptoms, ["fever", "high fever", "mild fever"]):
        return None
    musculo = has_any_symptom(
        active_symptoms,
        ["neck pain", "back pain", "low back pain", "joint pain", "knee pain", "painful menstruation"],
    )
    if musculo:
        return "thuốc kháng viêm không steroid"
    return None


def constipation_rule_drug_group(active_symptoms: set[str]) -> str | None:
    if has_any_symptom(active_symptoms, ["constipation"]) and not has_any_symptom(active_symptoms, ["diarrhea", "diarrhoea"]):
        return "thuốc nhuận tràng"
    return None


def antiviral_skin_rule_drug_group(notes: str, active_symptoms: set[str]) -> str | None:
    # Mụn nước/bóng nước kèm sốt hoặc phát ban (thuỷ đậu/zona) -> kháng virus.
    has_vesicle = has_any_symptom(active_symptoms, ["blister"])
    if has_vesicle and has_any_symptom(active_symptoms, ["fever", "high fever", "mild fever", "skin rash"]):
        return "thuốc kháng virus"
    # Herpes môi/miệng: mụn nước THÀNH CHÙM ở môi/quanh miệng, thường KHÔNG sốt.
    # Token đặc hiệu (đã bỏ dấu) + đã có bóng nước -> rất khó dương tính giả.
    t = normalize(notes or "")
    if has_vesicle and any(k in t for k in ("thanh chum", "quanh mieng", "quanh moi", "tren moi", "o moi", "o mep", "vung mieng")):
        return "thuốc kháng virus"
    return None


def psych_rule_drug_group(active_symptoms: set[str]) -> str | None:
    # Lo âu / trầm cảm / hoảng sợ -> nhóm thần kinh-tâm thần. Đặt TRƯỚC tim mạch để
    # hồi hộp do lo âu không bị kéo về tim mạch.
    if has_any_symptom(
        active_symptoms,
        [
            "anxiety", "anxiety and nervousness", "fears and phobias", "depression",
            "Persistent depressive symptoms (low mood, lack of interest, changes in sleep and appetite), lasting for at least two years",
        ],
    ):
        return "thuốc thần kinh/tâm thần"
    return None


def cardiac_rule_drug_group(active_symptoms: set[str]) -> str | None:
    # Tăng huyết áp / đau thắt ngực gắng sức / loạn nhịp kèm khó thở -> tim mạch-huyết áp.
    if has_any_symptom(active_symptoms, ["High blood pressure, chest pain or discomfort, shortness of breath, fatigue"]):
        return "thuốc tim mạch/huyết áp"
    # Đau thắt ngực KHÔNG kèm sốt/ho (loại viêm phổi, viêm sụn sườn).
    angina = has_any_symptom(active_symptoms, ["chest pain"]) and not has_any_symptom(
        active_symptoms, ["fever", "high fever", "mild fever", "cough", "phlegm"]
    )
    palp = has_any_symptom(
        active_symptoms,
        ["palpitations", "fast heart rate", "increased heart rate",
         "Irregular or rapid heartbeat, palpitations, shortness of breath, chest pain or discomfort, dizziness or lightheadedness, fatigue"],
    )
    dyspnea = has_any_symptom(active_symptoms, ["breathlessness", "shortness of breath", "difficulty breathing"])
    if angina or (palp and dyspnea):
        return "thuốc tim mạch/huyết áp"
    return None


def has_unclear_limb_stiffness(active_symptoms: set[str]) -> bool:
    has_stiffness = has_any_symptom(
        active_symptoms,
        [
            "arm stiffness or tightness",
            "hand or finger stiffness or tightness",
            "movement stiffness",
            "cramps",
        ],
    )
    if not has_stiffness:
        return False

    has_deciding_context = has_any_symptom(
        active_symptoms,
        [
            "arm pain",
            "hand or finger pain",
            "joint pain",
            "swelling joints",
            "arm swelling",
            "hand or finger swelling",
            "muscle weakness",
            "weakness in limbs",
            "arm weakness",
            "hand or finger weakness",
            "loss of sensation",
            "paresthesia",
            "fever",
            "high fever",
            "mild fever",
            "skin rash",
        ],
    )
    return not has_deciding_context


def has_unclear_cough_itch(active_symptoms: set[str]) -> bool:
    if not (has_any_symptom(active_symptoms, ["cough"]) and has_any_symptom(active_symptoms, ["itching", "itching of skin"])):
        return False

    has_deciding_context = has_any_symptom(
        active_symptoms,
        [
            "skin rash",
            "nodal skin eruptions",
            "dischromic patches",
            "skin peeling",
            "continuous sneezing",
            "watering from eyes",
            "runny nose",
            "congestion",
            "sore throat",
            "throat irritation",
            "phlegm",
            "coughing up sputum",
            "fever",
            "mild fever",
            "high fever",
            "breathlessness",
            "chest pain",
        ],
    )
    return not has_deciding_context


def resolve_feature_id(feature_id: str) -> str | None:
    keys = unique_list(
        [
            feature_id,
            feature_id.replace("_", " "),
            feature_id.replace(" ", "_"),
        ]
    )
    for key in keys:
        feature = feature_lookup.get(key.lower())
        if feature:
            return feature
    normalized_target = normalize(feature_id)
    for feature in features:
        if normalize(feature) == normalized_target:
            return feature
    return None


def suggestion_item(feature_id: str, hint: str = "") -> dict[str, str] | None:
    feature = resolve_feature_id(feature_id)
    if not feature:
        return None
    return {
        "id": feature,
        "label": symptom_label_vi(feature),
        "label_vi": symptom_label_vi(feature),
        "hint": hint,
    }


def suggested_symptoms_for_more_info(active_symptoms: set[str]) -> list[dict[str, str]]:
    suggestions = []

    def add(feature_id: str, hint: str = "") -> None:
        item = suggestion_item(feature_id, hint)
        if not item or item["id"] in active_symptoms:
            return
        if item["id"] not in {suggestion["id"] for suggestion in suggestions}:
            suggestions.append(item)

    if has_unclear_cough_itch(active_symptoms):
        add("skin rash", "Nếu có nổi ban/mẩn đỏ")
        add("continuous sneezing", "Nếu nghi dị ứng")
        add("watering from eyes", "Nếu chảy nước mắt/ngứa mắt")
        add("runny nose", "Nếu chảy nước mũi")
        add("sore throat", "Nếu đau/rát họng")
        add("phlegm", "Nếu ho có đờm")
        add("mild fever", "Nếu có sốt nhẹ")
        add("breathlessness", "Nếu khó thở")
        return suggestions[:8]

    if has_unclear_limb_stiffness(active_symptoms):
        add("arm pain", "Nếu tay đau")
        add("hand or finger pain", "Nếu đau ngón/bàn tay")
        add("arm swelling", "Nếu tay sưng")
        add("hand or finger swelling", "Nếu ngón/bàn tay sưng")
        add("loss of sensation", "Nếu tê/mất cảm giác")
        add("arm weakness", "Nếu yếu tay")
        add("fever", "Nếu có sốt")
        return suggestions[:8]

    if has_any_symptom(active_symptoms, ["cough", "sore throat", "throat irritation"]):
        add("fever", "Có sốt không")
        add("phlegm", "Ho khan hay ho có đờm")
        add("runny nose", "Có sổ mũi không")
        add("congestion", "Có nghẹt mũi không")
        add("breathlessness", "Có khó thở không")
        add("chest pain", "Có đau/tức ngực không")
        add("sore throat", "Có đau/rát họng không")
        return suggestions[:8]

    if has_any_symptom(active_symptoms, ["headache", "dizziness", "insomnia"]):
        add("fever", "Có sốt không")
        add("nausea", "Có buồn nôn không")
        add("vomiting", "Có nôn không")
        add("visual disturbances", "Có nhìn mờ/rối loạn thị giác không")
        add("stiff neck", "Có cứng cổ/gáy không")
        return suggestions[:8]

    if has_any_symptom(active_symptoms, ["diarrhoea", "vomiting", "dehydration", "abdominal pain", "nausea"]):
        add("fever", "Có sốt không")
        add("diarrhoea", "Có tiêu chảy không")
        add("vomiting", "Có nôn không")
        add("dehydration", "Có dấu hiệu mất nước không")
        add("abdominal pain", "Có đau bụng không")
        return suggestions[:8]

    if has_any_symptom(active_symptoms, ["toothache", "gum pain", "pain in gums", "jaw swelling", "bleeding gums", "mouth pain"]):
        add("jaw swelling", "Có sưng mặt/hàm không")
        add("bleeding gums", "Có chảy máu nướu không")
        add("fever", "Có sốt không")
        return suggestions[:8]

    return suggestions[:8]


def should_force_more_info(active_symptoms: set[str]) -> bool:
    headache_cluster = has_any_symptom(active_symptoms, ["headache", "frontal headache"]) and has_any_symptom(
        active_symptoms,
        ["dizziness", "insomnia", "difficulty falling asleep or staying asleep", "fatigue"],
    )
    if headache_cluster:
        return True
    mild_respiratory = has_any_symptom(active_symptoms, ["cough"]) and has_any_symptom(
        active_symptoms,
        ["sore throat", "throat irritation"],
    )
    has_respiratory_decider = has_any_symptom(
        active_symptoms,
        ["fever", "mild fever", "high fever", "phlegm", "coughing up sputum", "breathlessness", "chest pain"],
    )
    if mild_respiratory and not has_respiratory_decider:
        return True
    if has_unclear_limb_stiffness(active_symptoms):
        return True
    if has_unclear_cough_itch(active_symptoms):
        return True
    return False


def more_info_prompt(active_symptoms: set[str]) -> str:
    if has_unclear_cough_itch(active_symptoms):
        return (
            "Hãy bổ sung: ngứa ở da hay ngứa họng, có phát ban/nổi mẩn không, có hắt hơi/sổ mũi/chảy nước mắt không, "
            "ho khan hay ho có đờm, có sốt/khó thở/tức ngực không và triệu chứng kéo dài mấy ngày."
        )
    if has_unclear_limb_stiffness(active_symptoms):
        return (
            "Hãy bổ sung: cứng tay xuất hiện khi nào, có đau/sưng/nóng đỏ khớp không, có tê/yếu tay không, "
            "có chấn thương hoặc làm việc lặp lại nhiều không, cứng buổi sáng kéo dài bao lâu và có bệnh nền/thuốc đang dùng không."
        )
    if has_any_symptom(active_symptoms, ["toothache", "gum pain", "pain in gums", "jaw swelling", "bleeding gums", "mouth pain"]):
        return (
            "Hãy bổ sung: đau răng kéo dài bao lâu, có sâu răng/lỗ răng không, có sốt không, sưng mặt hay chảy mủ không, "
            "đau tăng khi nhai/nóng/lạnh không, có chảy máu nướu hoặc hôi miệng không."
        )
    if has_any_symptom(active_symptoms, ["cough", "sore throat", "throat pain", "throat irritation", "fever"]):
        return (
            "Hãy bổ sung: có sốt không, ho khan hay ho có đờm, màu đờm, nghẹt/sổ mũi, khó thở, đau ngực, "
            "nuốt đau nhiều không, triệu chứng kéo dài mấy ngày, có test COVID/cúm chưa, bệnh nền hoặc thuốc đang dùng."
        )
    if has_any_symptom(active_symptoms, ["headache", "dizziness", "insomnia"]):
        return (
            "Hãy bổ sung: thời gian khởi phát, mức độ đau, đau một bên hay toàn đầu, có sốt/nôn/nhìn mờ/đau cổ gáy không, "
            "huyết áp, tiền sử migraine, bệnh nền hoặc thuốc đang dùng."
        )
    if has_any_symptom(active_symptoms, ["diarrhoea", "vomiting", "dehydration", "abdominal pain", "nausea"]):
        return (
            "Hãy bổ sung: số lần nôn/tiêu chảy, có sốt hoặc phân máu không, đau bụng vị trí nào, uống được nước không, "
            "lượng nước tiểu, thức ăn nghi ngờ và bệnh nền."
        )
    return "Hãy mô tả thêm triệu chứng đi kèm, thời gian khởi phát, mức độ nặng, bệnh nền, dị ứng hoặc thuốc đang dùng."


def short_case_description(notes: str, matched_labels: list[str]) -> str:
    text = re.sub(r"\s+", " ", notes.strip())
    if not text:
        text = "Bệnh nhân có triệu chứng: " + "; ".join(label.lower() for label in matched_labels)
    if len(text) > 160:
        text = text[:157].rstrip() + "..."
    return text


def heuristic_diagnosis(active_symptoms: set[str]) -> str | None:
    if has_unclear_limb_stiffness(active_symptoms):
        return "Cứng/co rút tay chưa rõ nguyên nhân (cần bổ sung thông tin)"

    if has_any_symptom(active_symptoms, ["itching", "itching of skin"]) and has_any_symptom(
        active_symptoms,
        ["skin rash", "continuous sneezing", "watering from eyes", "runny nose", "congestion"],
    ):
        return "Dị ứng / phát ban hoặc viêm da (tham khảo)"

    if has_any_symptom(active_symptoms, ["continuous sneezing", "coryza", "runny nose", "congestion", "watering from eyes"]) and not has_any_symptom(
        active_symptoms,
        ["fever", "mild fever", "high fever"],
    ):
        return "Viêm mũi dị ứng / cảm lạnh không sốt (tham khảo)"

    if has_any_symptom(active_symptoms, ["chest pain", "breathlessness", "difficulty breathing", "shortness of breath"]) and has_any_symptom(active_symptoms, ["cough", "phlegm", "coughing up sputum"]):
        return "Triệu chứng hô hấp dưới / cần khám sớm (tham khảo)"

    if has_any_symptom(active_symptoms, ["cough", "sore throat", "throat irritation", "runny nose", "congestion"]):
        if has_any_symptom(active_symptoms, ["high fever", "fever", "mild fever", "muscle pain", "fatigue"]):
            return "Viêm hô hấp trên / cảm cúm (tham khảo)"
        if has_any_symptom(active_symptoms, ["sore throat", "throat irritation"]) and has_any_symptom(active_symptoms, ["cough"]):
            return "Viêm họng / viêm hô hấp trên (tham khảo)"
        return "Triệu chứng hô hấp trên (cần bổ sung thông tin)"

    if has_any_symptom(active_symptoms, ["headache", "dizziness", "insomnia"]):
        return "Đau đầu/chóng mặt chưa rõ nguyên nhân (cần bổ sung thông tin)"

    if has_any_symptom(active_symptoms, ["diarrhoea", "vomiting", "nausea", "abdominal pain", "stomach pain"]):
        if has_any_symptom(active_symptoms, ["diarrhoea", "vomiting", "nausea"]):
            return "Rối loạn tiêu hóa / viêm dạ dày ruột nhẹ (tham khảo)"
        return "Đau bụng/khó chịu tiêu hóa (cần bổ sung thông tin)"

    if has_any_symptom(active_symptoms, ["toothache", "gum pain", "pain in gums", "jaw swelling", "bleeding gums", "mouth pain"]):
        if has_any_symptom(active_symptoms, ["gum pain", "pain in gums", "jaw swelling", "bleeding gums"]):
            return "Viêm nướu / bệnh răng miệng (tham khảo)"
        return "Đau răng / sâu răng (tham khảo)"

    if has_any_symptom(active_symptoms, ["ear pain", "diminished hearing", "fluid in ear"]):
        return "Viêm tai giữa / bệnh lý tai (tham khảo)"

    if has_any_symptom(active_symptoms, ["ankle pain", "ankle swelling", "foot or toe pain", "foot or toe swelling"]):
        return "Chấn thương/viêm vùng cổ chân hoặc bàn chân (tham khảo)"

    if has_any_symptom(active_symptoms, ["itching", "skin rash", "nodal skin eruptions", "dischromic patches"]):
        return "Nấm da / viêm da (tham khảo)"

    # P2 (2026-06-15): nhãn hội chứng cho các khoảng trống thường gặp, tránh rơi xuống
    # dataset_diagnosis trả nhãn thô vô nghĩa (spinal stenosis, hemorrhoids, gout...).
    if has_any_symptom(active_symptoms, ["muscle pain", "joint pain", "knee pain", "hip joint pain", "neck pain", "back pain", "cramps", "painful walking", "swelling joints", "movement stiffness", "muscle weakness"]):
        return "Đau cơ-xương-khớp (tham khảo)"

    if has_any_symptom(active_symptoms, ["constipation"]):
        return "Táo bón (tham khảo)"

    if has_any_symptom(active_symptoms, ["acidity", "indigestion", "passage of gases"]):
        return "Khó tiêu / trào ngược dạ dày (tham khảo)"

    if has_any_symptom(active_symptoms, ["burning micturition", "bladder discomfort", "spotting urination", "foul smell of urine", "continuous feel of urine"]):
        return "Triệu chứng tiết niệu (tham khảo)"

    return None


def dataset_diagnosis(active_symptoms: set[str]) -> str | None:
    if not active_symptoms:
        return None

    symptom_set = {symptom.lower() for symptom in active_symptoms}
    scored = []
    for row in references.get("case_index", []):
        row_symptoms = row["symptoms"]
        overlap = len(symptom_set & row_symptoms)
        if overlap == 0:
            continue
        precision = overlap / len(symptom_set)
        coverage = overlap / max(len(row_symptoms), 1)
        score = precision * 0.7 + coverage * 0.3
        if precision >= 0.5:
            scored.append((score, row["disease"]))

    if not scored:
        return None

    best_score = max(score for score, _ in scored)
    if best_score < 0.35:
        return None
    candidates = [disease for score, disease in scored if score >= best_score - 0.05]
    return Counter(candidates).most_common(1)[0][0]


def medication_names_for_group(
    group: str | None,
    can_suggest_drug: bool,
    active_symptoms: set[str] | None = None,
) -> str:
    if not can_suggest_drug or not group:
        return "Chưa đủ dữ liệu để gợi ý thuốc"

    # Vòng 6: ưu tiên 2-3 hoạt chất ĐÃ CURATE (sạch, tiếng Việt) cho output trọng tâm.
    reps = representative_active_ingredients_for_group(group)
    if reps:
        return "; ".join(reps)
    note = representative_note_for_group(group)
    if note:
        return note  # nhóm rủi ro/chuyên khoa: hiện ghi chú thay vì tên thuốc cụ thể

    if group in RULE_MEDICATION_NAMES:
        return RULE_MEDICATION_NAMES[group]

    names = []
    for item in medication_reference_items_for_group(group, active_symptoms):
        text = str(item).strip()
        if text.lower().startswith("thuốc trong dữ liệu:"):
            text = text.split(":", 1)[1].strip()
        elif text.lower().startswith("nhóm thuốc dự đoán:"):
            continue
        if text and text not in names:
            names.append(text)

    if names:
        return "; ".join(names[:3])
    return "Chưa có tên thuốc cụ thể trong dữ liệu"


def case_summary(
    notes: str,
    active_symptoms: set[str],
    matched_labels: list[str],
    predicted_group: str | None,
    can_suggest_drug: bool,
) -> dict[str, str]:
    # P2: ưu tiên nhãn hội chứng đã curate (tiếng Việt). Chỉ dùng nhãn dataset nếu nó đã
    # được CURATE sang tiếng Việt (DIAGNOSIS_VI); nhãn thô tiếng Anh (spinal stenosis, gout,
    # hemorrhoids, Drug Reaction...) KHÔNG hiển thị như chẩn đoán chắc chắn.
    diagnosis = heuristic_diagnosis(active_symptoms)
    if not diagnosis:
        raw = dataset_diagnosis(active_symptoms)
        diagnosis = DIAGNOSIS_VI.get(raw) if raw else None
    if not diagnosis:
        diagnosis = "Chưa đủ cơ sở cho chẩn đoán cụ thể (tham khảo theo triệu chứng)"
    diagnosis = DIAGNOSIS_VI.get(diagnosis, diagnosis)
    drug_group = predicted_group if can_suggest_drug and predicted_group else "Chưa đủ dữ liệu để gợi ý thuốc"
    return {
        "description": short_case_description(notes, matched_labels),
        "symptoms": "; ".join(label.lower() for label in matched_labels) if matched_labels else "Chưa nhận diện được",
        "diagnosis": diagnosis,
        "medication_name": medication_names_for_group(predicted_group, can_suggest_drug, active_symptoms),
        "drug_group": drug_group,
    }


def prediction_reason(matched_labels: list[str], confidence, score_type: str, group: str | None) -> str:
    """Câu LÝ DO ngắn (triệu chứng -> nhóm) cho output. Không chẩn đoán quá mức, không nói 'nên dùng'."""
    if not group:
        return ""
    syms = ", ".join(matched_labels[:4]) if matched_labels else "các dấu hiệu đã mô tả"
    if score_type == "rule":
        return f"Triệu chứng/ngữ cảnh đặc hiệu ({syms}) khớp quy tắc lâm sàng cho nhóm {group}."
    if confidence is not None:
        return (
            f"Triệu chứng đã nhận diện ({syms}) phù hợp nhất với nhóm {group} "
            f"trong các nhóm đã huấn luyện (độ tin cậy {confidence * 100:.0f}%)."
        )
    return f"Triệu chứng đã nhận diện ({syms}) phù hợp nhất với nhóm {group}."


@app.get("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:path>")
def static_files(path):
    if path not in ALLOWED_STATIC_FILES:
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(FRONTEND_DIR, path)


@app.get("/api/health")
def health():
    return jsonify(
        {
            "ok": True,
            "model": str(MODEL_PATH),
            "data_source": str(DATA_SOURCE),
            "data_source_exists": DATA_SOURCE.exists(),
            "features": len(features),
            "classes": len(metadata["classes"]),
            "accuracy": metadata.get("accuracy"),
            "model_type": metadata.get("model_type", "tabular"),
            "label_type": LABEL_TYPE,
            "guidance_entries": len(guidance_data),
        }
    )


@app.post("/api/auth/register")
def register():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or "").strip()
    email = normalize_email(str(payload.get("email") or ""))
    password = str(payload.get("password") or "")

    validation_error = validate_auth_payload(name, email, password)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    store = load_user_store()
    if find_user_by_email(store, email):
        return jsonify({"error": "Email này đã được đăng ký."}), 409

    user = {
        "id": secrets.token_hex(8),
        "name": name,
        "email": email,
        "password_hash": generate_password_hash(password),
        "created_at": iso_utc(now_utc()),
    }
    token = issue_session(user)
    store["users"].append(user)
    save_user_store(store)
    return jsonify({"user": user_public_view(user), "token": token}), 201


@app.post("/api/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = normalize_email(str(payload.get("email") or ""))
    password = str(payload.get("password") or "")

    store = load_user_store()
    user = find_user_by_email(store, email)
    if not user or not check_password_hash(user.get("password_hash", ""), password):
        return jsonify({"error": "Email hoặc mật khẩu không đúng."}), 401

    token = issue_session(user)
    save_user_store(store)
    return jsonify({"user": user_public_view(user), "token": token})


@app.get("/api/auth/me")
def auth_me():
    store = load_user_store()
    user = current_user_from_request(store)
    if not user:
        return jsonify({"error": "Phiên đăng nhập không hợp lệ hoặc đã hết hạn."}), 401
    return jsonify({"user": user_public_view(user)})


@app.post("/api/auth/logout")
def logout():
    store = load_user_store()
    user = current_user_from_request(store)
    if user:
        user.pop("session_token", None)
        user.pop("session_expires_at", None)
        save_user_store(store)
    return jsonify({"ok": True})


@app.post("/api/auth/forgot-password")
def forgot_password():
    payload = request.get_json(silent=True) or {}
    email = normalize_email(str(payload.get("email") or ""))
    store = load_user_store()
    user = find_user_by_email(store, email)
    response = {
        "message": "Nếu email tồn tại, hệ thống đã tạo mã đặt lại mật khẩu.",
    }

    if user:
        reset_code = f"{secrets.randbelow(1000000):06d}"
        user["reset_code_hash"] = generate_password_hash(reset_code)
        user["reset_code_expires_at"] = iso_utc(now_utc() + timedelta(minutes=15))
        save_user_store(store)
        response["reset_code"] = reset_code
        response["message"] = "Mã đặt lại mật khẩu có hiệu lực trong 15 phút."

    return jsonify(response)


@app.post("/api/auth/reset-password")
def reset_password():
    payload = request.get_json(silent=True) or {}
    email = normalize_email(str(payload.get("email") or ""))
    reset_code = str(payload.get("reset_code") or "").strip()
    password = str(payload.get("password") or "")

    validation_error = validate_auth_payload(None, email, password)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    store = load_user_store()
    user = find_user_by_email(store, email)
    expires_at = parse_iso_datetime(user.get("reset_code_expires_at") if user else None)
    code_hash = user.get("reset_code_hash", "") if user else ""
    if not user or not expires_at or expires_at <= now_utc() or not check_password_hash(code_hash, reset_code):
        return jsonify({"error": "Mã đặt lại mật khẩu không đúng hoặc đã hết hạn."}), 400

    user["password_hash"] = generate_password_hash(password)
    user.pop("reset_code_hash", None)
    user.pop("reset_code_expires_at", None)
    token = issue_session(user)
    save_user_store(store)
    return jsonify({"user": user_public_view(user), "token": token})


@app.post("/api/auth/profile")
def update_profile():
    """Cập nhật họ tên người dùng đang đăng nhập."""
    store = load_user_store()
    user = current_user_from_request(store)
    if not user:
        return jsonify({"error": "Phiên đăng nhập không hợp lệ hoặc đã hết hạn."}), 401
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Vui lòng nhập họ tên."}), 400
    user["name"] = name[:150]
    save_user_store(store)
    return jsonify({"user": user_public_view(user)})


@app.post("/api/auth/change-password")
def change_password():
    """Đổi mật khẩu khi đã đăng nhập (xác thực mật khẩu hiện tại)."""
    store = load_user_store()
    user = current_user_from_request(store)
    if not user:
        return jsonify({"error": "Phiên đăng nhập không hợp lệ hoặc đã hết hạn."}), 401
    payload = request.get_json(silent=True) or {}
    current = str(payload.get("current_password") or "")
    new_password = str(payload.get("new_password") or "")
    if not check_password_hash(user.get("password_hash", ""), current):
        return jsonify({"error": "Mật khẩu hiện tại không đúng."}), 400
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return jsonify({"error": f"Mật khẩu mới phải có ít nhất {MIN_PASSWORD_LENGTH} ký tự."}), 400
    user["password_hash"] = generate_password_hash(new_password)
    token = issue_session(user)
    save_user_store(store)
    return jsonify({"user": user_public_view(user), "token": token})


@app.get("/api/symptoms")
def symptoms():
    return jsonify({"symptoms": readable_symptoms})


def _valid_date_param(value: str | None) -> str | None:
    """Chấp nhận 'YYYY-MM-DD'; sai định dạng -> None (bỏ lọc thay vì báo lỗi)."""
    if not value:
        return None
    value = value.strip()
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return value


def _admin_stats_from_db(date_from, date_to):
    """US19 (DB): gộp số liệu Dashboard từ Postgres — cùng shape JSON với bản JSONL."""
    from sqlalchemy import Date, cast, func

    KQ = db_models.KetQuaDuDoan
    PH = db_models.PhanHoi

    def drange(col):
        conds = []
        if date_from:
            conds.append(cast(col, Date) >= date_from)
        if date_to:
            conds.append(cast(col, Date) <= date_to)
        return conds

    total = db.session.query(func.count(KQ.ma_ket_qua)).filter(*drange(KQ.created_at)).scalar() or 0

    by_status = {s: 0 for s in stats_source.PREDICTION_STATUSES}
    for st, cnt in (db.session.query(KQ.trang_thai, func.count()).filter(*drange(KQ.created_at)).group_by(KQ.trang_thai)):
        if st in by_status:
            by_status[st] = cnt

    over_time = [
        {"date": d.isoformat(), "count": cnt}
        for d, cnt in (
            db.session.query(cast(KQ.created_at, Date).label("d"), func.count())
            .filter(*drange(KQ.created_at)).group_by("d").order_by("d")
        )
    ]

    top_groups = [
        {"group": g, "count": cnt}
        for g, cnt in (
            db.session.query(KQ.nhom_thuoc_du_doan, func.count())
            .filter(KQ.nhom_thuoc_du_doan.isnot(None), *drange(KQ.created_at))
            .group_by(KQ.nhom_thuoc_du_doan).order_by(func.count().desc()).limit(5)
        )
    ]

    agree = db.session.query(func.count()).filter(PH.trang_thai == "APPROVE", *drange(PH.thoi_gian_gui)).scalar() or 0
    disagree = db.session.query(func.count()).filter(PH.trang_thai == "REJECT", *drange(PH.thoi_gian_gui)).scalar() or 0
    feedback_total = agree + disagree
    agree_rate = round(agree / feedback_total * 100, 1) if feedback_total else None

    return jsonify({
        "range": {"from": date_from, "to": date_to},
        "total_predictions": total,
        "by_status": by_status,
        "predictions_over_time": over_time,
        "top_groups": top_groups,
        "feedback_total": feedback_total,
        "agree_count": agree,
        "disagree_count": disagree,
        "agree_rate": agree_rate,
        "source": "postgres",
    })


@app.get("/api/admin/stats")
def admin_stats():
    """US19: Dashboard tổng quan cho Admin — số ca dự đoán + tỷ lệ 'Đồng ý'.

    CHỈ ĐỌC qua stats_source (adapter). Hỗ trợ lọc ?from=YYYY-MM-DD&to=YYYY-MM-DD.
    """
    store = load_user_store()
    _admin, error = current_admin_from_request(store)
    if error:
        return error

    date_from = _valid_date_param(request.args.get("from"))
    date_to = _valid_date_param(request.args.get("to"))

    if DB_ENABLED:
        return _admin_stats_from_db(date_from, date_to)

    predictions = stats_source.read_predictions(date_from, date_to)
    feedback = stats_source.read_feedback(date_from, date_to)

    # ── Số ca dự đoán + phân loại theo trạng thái ──
    by_status = {status: 0 for status in stats_source.PREDICTION_STATUSES}
    over_time: dict[str, int] = {}
    group_counter: Counter = Counter()
    for record in predictions:
        status = record.get("status")
        if status in by_status:
            by_status[status] += 1
        day = stats_source.record_day(record)
        if day:
            over_time[day] = over_time.get(day, 0) + 1
        group = record.get("predicted_group")
        if isinstance(group, str) and group.strip():
            group_counter[group.strip()] += 1

    predictions_over_time = [
        {"date": day, "count": over_time[day]} for day in sorted(over_time)
    ]
    top_groups = [
        {"group": group, "count": count} for group, count in group_counter.most_common(5)
    ]

    # ── Tỷ lệ đánh giá 'Đồng ý' ──
    agree_count = sum(1 for r in feedback if str(r.get("verdict", "")).upper() == "APPROVE")
    disagree_count = sum(1 for r in feedback if str(r.get("verdict", "")).upper() == "REJECT")
    feedback_total = agree_count + disagree_count
    agree_rate = round(agree_count / feedback_total * 100, 1) if feedback_total else None

    return jsonify(
        {
            "range": {"from": date_from, "to": date_to},
            "total_predictions": len(predictions),
            "by_status": by_status,
            "predictions_over_time": predictions_over_time,
            "top_groups": top_groups,
            "feedback_total": feedback_total,
            "agree_count": agree_count,
            "disagree_count": disagree_count,
            "agree_rate": agree_rate,
        }
    )


# ── US22 (SCRUM-88): thống kê lý do KHÔNG ĐỒNG Ý phổ biến ─────────────────────
# Stopword tiếng Việt (từ ngữ pháp) — bỏ khi đếm từ khóa lý do để giữ từ có nghĩa.
_VI_STOPWORDS = frozenset(
    "và là của cho các có được khi này đó một những để ở ra vào thì mà với đã sẽ bị nên "
    "cũng rất quá lại còn do vì nếu hơn như trong trên dưới theo tôi bạn mình nó họ ông bà "
    "anh chị em không bệnh nhân thuốc bị thấy nhưng hay rồi đang tại bởi the a an is are of to "
    "này nọ kia ấy đây đấy nhiều ít hoặc tuy dù mỗi vẫn chỉ".split()
)


def _top_keywords(notes, top=12):
    """SCRUM-90: đếm từ khóa phổ biến trong ghi chú phản hồi.

    Đếm cả từ đơn lẫn cụm 2 âm tiết (bigram) vì tiếng Việt nghĩa thường theo cụm
    ('chẩn đoán', 'sai nhóm'). Bỏ stopword/số/từ ngắn.
    """
    counter: Counter = Counter()
    for note in notes:
        if not note:
            continue
        text = re.sub(r"[^\w\s]", " ", str(note).lower(), flags=re.UNICODE)
        toks = [t for t in text.split() if len(t) >= 2 and not t.isdigit() and t not in _VI_STOPWORDS]
        counter.update(toks)
        for a, b in zip(toks, toks[1:]):
            counter[f"{a} {b}"] += 1
    return [{"keyword": k, "count": c} for k, c in counter.most_common(top)]


@app.get("/api/admin/feedback-stats")
def admin_feedback_stats():
    """US22: thống kê phản hồi 'Không đồng ý' — số lượng theo ngày + từ khóa lý do phổ biến.

    Admin-only. Lọc ?from=YYYY-MM-DD&to=YYYY-MM-DD. Chạy DB hoặc JSONL (graceful).
    """
    store = load_user_store()
    _admin, error = current_admin_from_request(store)
    if error:
        return error
    date_from = _valid_date_param(request.args.get("from"))
    date_to = _valid_date_param(request.args.get("to"))

    if DB_ENABLED:
        from sqlalchemy import Date, cast, func
        PH = db_models.PhanHoi

        def drange(col):
            conds = [PH.trang_thai == "REJECT"]
            if date_from:
                conds.append(cast(col, Date) >= date_from)
            if date_to:
                conds.append(cast(col, Date) <= date_to)
            return conds

        reject_total = db.session.query(func.count()).filter(*drange(PH.thoi_gian_gui)).scalar() or 0
        approve_total = db.session.query(func.count()).filter(
            PH.trang_thai == "APPROVE",
            *([cast(PH.thoi_gian_gui, Date) >= date_from] if date_from else []),
            *([cast(PH.thoi_gian_gui, Date) <= date_to] if date_to else []),
        ).scalar() or 0
        over_time = [
            {"date": d.isoformat(), "count": cnt}
            for d, cnt in (
                db.session.query(cast(PH.thoi_gian_gui, Date).label("d"), func.count())
                .filter(*drange(PH.thoi_gian_gui)).group_by("d").order_by("d")
            )
        ]
        by_group = [
            {"group": g, "count": cnt}
            for g, cnt in (
                db.session.query(PH.nhom_thuoc_du_doan, func.count())
                .filter(PH.nhom_thuoc_du_doan.isnot(None), *drange(PH.thoi_gian_gui))
                .group_by(PH.nhom_thuoc_du_doan).order_by(func.count().desc()).limit(5)
            )
        ]
        notes = [n for (n,) in db.session.query(PH.noi_dung).filter(*drange(PH.thoi_gian_gui)) if n]
        source = "postgres"
    else:
        rows = [r for r in stats_source.read_feedback(date_from, date_to)
                if str(r.get("verdict", "")).upper() == "REJECT"]
        approves = [r for r in stats_source.read_feedback(date_from, date_to)
                    if str(r.get("verdict", "")).upper() == "APPROVE"]
        reject_total = len(rows)
        approve_total = len(approves)
        ot: dict[str, int] = {}
        grp: Counter = Counter()
        notes = []
        for r in rows:
            day = stats_source.record_day(r)
            if day:
                ot[day] = ot.get(day, 0) + 1
            g = r.get("predicted_group")
            if isinstance(g, str) and g.strip():
                grp[g.strip()] += 1
            if r.get("note"):
                notes.append(r["note"])
        over_time = [{"date": d, "count": ot[d]} for d in sorted(ot)]
        by_group = [{"group": g, "count": c} for g, c in grp.most_common(5)]
        source = "jsonl"

    total_fb = reject_total + approve_total
    return jsonify({
        "range": {"from": date_from, "to": date_to},
        "reject_total": reject_total,
        "approve_total": approve_total,
        "reject_rate": round(reject_total / total_fb * 100, 1) if total_fb else None,
        "reject_over_time": over_time,        # SCRUM-89
        "top_keywords": _top_keywords(notes),  # SCRUM-90
        "reject_by_group": by_group,
        "source": source,
    })


# ── US23 (SCRUM-92): Top nhóm thuốc được dự đoán nhiều nhất ───────────────────
@app.get("/api/admin/group-stats")
def admin_group_stats():
    """US23 (SCRUM-93): đếm số lần mỗi nhóm thuốc xuất hiện trong lịch sử dự đoán.

    Admin-only. ?limit=N (mặc định 10), lọc ?from=&to=. Mỗi nhóm kèm count + percent.
    Chạy DB (ket_qua_du_doan) hoặc JSONL (graceful).
    """
    store = load_user_store()
    _admin, error = current_admin_from_request(store)
    if error:
        return error
    date_from = _valid_date_param(request.args.get("from"))
    date_to = _valid_date_param(request.args.get("to"))
    try:
        limit = max(1, min(50, int(request.args.get("limit", 10))))
    except (TypeError, ValueError):
        limit = 10

    if DB_ENABLED:
        from sqlalchemy import Date, cast, func
        KQ = db_models.KetQuaDuDoan

        def drange():
            conds = [KQ.nhom_thuoc_du_doan.isnot(None)]
            if date_from:
                conds.append(cast(KQ.created_at, Date) >= date_from)
            if date_to:
                conds.append(cast(KQ.created_at, Date) <= date_to)
            return conds

        pairs = (
            db.session.query(KQ.nhom_thuoc_du_doan, func.count())
            .filter(*drange()).group_by(KQ.nhom_thuoc_du_doan).order_by(func.count().desc())
        ).all()
        source = "postgres"
    else:
        counter: Counter = Counter()
        for r in stats_source.read_predictions(date_from, date_to):
            g = r.get("predicted_group")
            if isinstance(g, str) and g.strip():
                counter[g.strip()] += 1
        pairs = counter.most_common()
        source = "jsonl"

    total = sum(c for _, c in pairs)
    groups = [
        {"group": g, "count": c, "percent": round(c / total * 100, 1) if total else 0.0}
        for g, c in pairs[:limit]
    ]
    return jsonify({
        "range": {"from": date_from, "to": date_to},
        "total_with_group": total,
        "distinct_groups": len(pairs),
        "groups": groups,
        "source": source,
    })


@app.get("/api/admin/history")
def admin_history():
    """Admin xem TOÀN BỘ lịch sử dự đoán của mọi người dùng (đọc ket_qua_du_doan).

    Admin-only, DB-only (lịch sử đầy đủ chỉ có trong Postgres). Lọc ?email=&status=&from=&to=,
    phân trang ?page=&page_size=. Trả từng ca kèm email người dùng, trạng thái, nhóm thuốc, thời gian.
    """
    _admin, error = _require_admin_db()
    if error:
        return error
    from sqlalchemy import Date, cast
    KQ = db_models.KetQuaDuDoan

    q = db.session.query(KQ)
    email = (request.args.get("email") or "").strip().lower()
    status = (request.args.get("status") or "").strip()
    date_from = _valid_date_param(request.args.get("from"))
    date_to = _valid_date_param(request.args.get("to"))
    if email:
        q = q.filter(KQ.user_email.ilike(f"%{email}%"))
    if status in ("suggest", "emergency", "safety_block"):
        q = q.filter(KQ.trang_thai == status)
    if date_from:
        q = q.filter(cast(KQ.created_at, Date) >= date_from)
    if date_to:
        q = q.filter(cast(KQ.created_at, Date) <= date_to)

    total = q.count()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = max(1, min(100, int(request.args.get("page_size", 20))))
    except (TypeError, ValueError):
        page_size = 20

    rows = (
        q.order_by(KQ.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    items = [{
        "id": r.ma_ket_qua,
        "time": iso_utc(r.created_at) if r.created_at else None,
        "email": r.user_email or "guest",
        "status": r.trang_thai,
        "group": r.nhom_thuoc_du_doan,
        "confidence": r.do_tin_cay,
        "notes": r.mo_ta_benh_an.noi_dung if r.mo_ta_benh_an else None,
    } for r in rows]
    return jsonify({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 1,
        "source": "postgres",
    })


@app.get("/api/admin/history.csv")
def admin_history_csv():
    """Xuất lịch sử dự đoán toàn hệ thống ra CSV (theo bộ lọc hiện tại). Admin-only, DB-only."""
    _admin, error = _require_admin_db()
    if error:
        return error
    from sqlalchemy import Date, cast
    KQ = db_models.KetQuaDuDoan

    q = db.session.query(KQ)
    email = (request.args.get("email") or "").strip().lower()
    status = (request.args.get("status") or "").strip()
    date_from = _valid_date_param(request.args.get("from"))
    date_to = _valid_date_param(request.args.get("to"))
    if email:
        q = q.filter(KQ.user_email.ilike(f"%{email}%"))
    if status in ("suggest", "emergency", "safety_block"):
        q = q.filter(KQ.trang_thai == status)
    if date_from:
        q = q.filter(cast(KQ.created_at, Date) >= date_from)
    if date_to:
        q = q.filter(cast(KQ.created_at, Date) <= date_to)

    rows = q.order_by(KQ.created_at.desc()).limit(5000).all()
    buffer = io.StringIO()
    buffer.write("﻿")  # BOM để Excel đọc đúng UTF-8
    writer = csv.writer(buffer)
    writer.writerow(["thoi_gian", "email", "huong_xu_tri", "nhom_thuoc", "do_tin_cay", "cau_nhap"])
    labels = {"suggest": "Gợi ý OTC", "safety_block": "Né an toàn", "emergency": "Cấp cứu"}
    for r in rows:
        writer.writerow([
            iso_utc(r.created_at) if r.created_at else "",
            r.user_email or "guest",
            labels.get(r.trang_thai, r.trang_thai or ""),
            r.nhom_thuoc_du_doan or "",
            f"{round(r.do_tin_cay * 100)}%" if isinstance(r.do_tin_cay, (int, float)) else "",
            (r.mo_ta_benh_an.noi_dung if r.mo_ta_benh_an else "") or "",
        ])
    from flask import Response
    return Response(
        buffer.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=lich_su_he_thong.csv"},
    )


# ── DB-BACKED: đọc danh mục đã seed từ Postgres (admin) ───────────────────────
# Tích hợp SQLAlchemy vào Flask app: các endpoint sau ĐỌC trực tiếp từ Postgres
# (nhom_thuoc/thuoc_tham_khao/trieu_chung) — phục vụ QuanLyNhomThuoc() của Admin.
def _require_admin_db():
    """Guard admin + DB bật. Trả (None, response) nếu chặn; ngược lại (admin, None)."""
    store = load_user_store()
    admin, error = current_admin_from_request(store)
    if error:
        return None, error
    if not DB_ENABLED:
        return None, (jsonify({"error": "Cơ sở dữ liệu chưa được bật (đang chạy chế độ JSON)."}), 503)
    return admin, None


@app.get("/api/admin/db/health")
def admin_db_health():
    _admin, error = _require_admin_db()
    if error:
        return error
    counts = {
        "nhom_thuoc": db.session.query(db_models.NhomThuoc).count(),
        "thuoc_tham_khao": db.session.query(db_models.ThuocThamKhao).count(),
        "trieu_chung": db.session.query(db_models.TrieuChung).count(),
        "chan_doan_du_kien": db.session.query(db_models.ChanDoanDuKien).count(),
        "mo_hinh_du_doan": db.session.query(db_models.MoHinhDuDoan).count(),
    }
    return jsonify({"db_enabled": True, "counts": counts})


@app.get("/api/admin/db/nhom-thuoc")
def admin_db_nhom_thuoc():
    _admin, error = _require_admin_db()
    if error:
        return error
    rows = (
        db.session.query(db_models.NhomThuoc)
        .order_by(db_models.NhomThuoc.ten_nhom_thuoc)
        .all()
    )
    return jsonify({
        "nhom_thuoc": [
            {
                "ma": n.ma_nhom_thuoc,
                "ten": n.ten_nhom_thuoc,
                "mo_ta": n.mo_ta,
                "so_thuoc": len(n.thuoc_list),
                "thuoc": [{"ma": t.ma_thuoc, "ten": t.ten_thuoc, "hoat_chat": t.hoat_chat} for t in n.thuoc_list[:50]],
            }
            for n in rows
        ]
    })


# ── PORT toan/main: CRUD QUẢN LÝ THUỐC (nhóm thuốc + thuốc) — adapt schema huy ──
@app.post("/api/admin/db/nhom-thuoc")
def create_nhom_thuoc():
    _admin, error = _require_admin_db()
    if error:
        return error
    p = request.get_json(silent=True) or {}
    ten = str(p.get("ten") or p.get("ten_nhom") or "").strip()
    if not ten:
        return jsonify({"error": "Cần tên nhóm thuốc."}), 400
    if db.session.query(db_models.NhomThuoc).filter_by(ten_nhom_thuoc=ten).first():
        return jsonify({"error": "Nhóm thuốc đã tồn tại."}), 409
    n = db_models.NhomThuoc(ten_nhom_thuoc=ten[:255], mo_ta=(str(p.get("mo_ta") or "").strip() or None))
    db.session.add(n)
    db.session.commit()
    return jsonify({"ok": True, "ma": n.ma_nhom_thuoc}), 201


@app.put("/api/admin/db/nhom-thuoc/<int:ma>")
def update_nhom_thuoc(ma):
    _admin, error = _require_admin_db()
    if error:
        return error
    n = db.session.get(db_models.NhomThuoc, ma)
    if not n:
        return jsonify({"error": "Không tìm thấy nhóm thuốc."}), 404
    p = request.get_json(silent=True) or {}
    ten = str(p.get("ten") or "").strip()
    if ten:
        dup = db.session.query(db_models.NhomThuoc).filter_by(ten_nhom_thuoc=ten).first()
        if dup and dup.ma_nhom_thuoc != ma:
            return jsonify({"error": "Tên nhóm thuốc đã tồn tại."}), 409
        n.ten_nhom_thuoc = ten[:255]
    if "mo_ta" in p:
        n.mo_ta = (str(p.get("mo_ta") or "").strip() or None)
    db.session.commit()
    return jsonify({"ok": True}), 200


@app.delete("/api/admin/db/nhom-thuoc/<int:ma>")
def delete_nhom_thuoc(ma):
    _admin, error = _require_admin_db()
    if error:
        return error
    n = db.session.get(db_models.NhomThuoc, ma)
    if not n:
        return jsonify({"error": "Không tìm thấy nhóm thuốc."}), 404
    db.session.delete(n)
    db.session.commit()
    return jsonify({"ok": True}), 200


@app.get("/api/admin/db/thuoc")
def admin_db_thuoc():
    _admin, error = _require_admin_db()
    if error:
        return error
    q = (request.args.get("q") or "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = max(1, min(100, int(request.args.get("per_page", 10))))
    except (TypeError, ValueError):
        page, per_page = 1, 10
    TH = db_models.ThuocThamKhao
    query = db.session.query(TH)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(TH.ten_thuoc.ilike(like), TH.hoat_chat.ilike(like)))
    total = query.count()
    rows = query.order_by(TH.ten_thuoc).offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total else 0,
        "thuoc": [
            {"ma": t.ma_thuoc, "ten": t.ten_thuoc, "hoat_chat": t.hoat_chat, "cong_dung": t.cong_dung,
             "nhom": [n.ten_nhom_thuoc for n in t.nhom_thuoc_list]}
            for t in rows
        ],
    })


@app.post("/api/admin/db/thuoc")
def create_thuoc():
    _admin, error = _require_admin_db()
    if error:
        return error
    p = request.get_json(silent=True) or {}
    ten = str(p.get("ten") or "").strip()
    if not ten:
        return jsonify({"error": "Cần tên thuốc."}), 400
    t = db_models.ThuocThamKhao(
        ten_thuoc=ten[:255],
        hoat_chat=(str(p.get("hoat_chat") or "").strip() or None),
        cong_dung=(str(p.get("cong_dung") or "").strip() or None),
    )
    ma_nhom = p.get("ma_nhom_thuoc")
    if ma_nhom:
        n = db.session.get(db_models.NhomThuoc, int(ma_nhom))
        if n:
            t.nhom_thuoc_list.append(n)
    db.session.add(t)
    db.session.commit()
    return jsonify({"ok": True, "ma": t.ma_thuoc}), 201


@app.put("/api/admin/db/thuoc/<int:ma>")
def update_thuoc(ma):
    _admin, error = _require_admin_db()
    if error:
        return error
    t = db.session.get(db_models.ThuocThamKhao, ma)
    if not t:
        return jsonify({"error": "Không tìm thấy thuốc."}), 404
    p = request.get_json(silent=True) or {}
    if str(p.get("ten") or "").strip():
        t.ten_thuoc = str(p["ten"]).strip()[:255]
    if "hoat_chat" in p:
        t.hoat_chat = (str(p.get("hoat_chat") or "").strip() or None)
    if "cong_dung" in p:
        t.cong_dung = (str(p.get("cong_dung") or "").strip() or None)
    db.session.commit()
    return jsonify({"ok": True}), 200


@app.delete("/api/admin/db/thuoc/<int:ma>")
def delete_thuoc(ma):
    _admin, error = _require_admin_db()
    if error:
        return error
    t = db.session.get(db_models.ThuocThamKhao, ma)
    if not t:
        return jsonify({"error": "Không tìm thấy thuốc."}), 404
    db.session.delete(t)
    db.session.commit()
    return jsonify({"ok": True}), 200


# ── PORT toan/main: BULK IMPORT CSV (nhóm thuốc / thuốc) ──────────────────────
def _read_csv_upload():
    """Đọc file CSV upload (field 'file') -> list[dict]. Lỗi -> (None, message)."""
    f = request.files.get("file")
    if not f or not f.filename:
        return None, "Chưa chọn file CSV."
    if not f.filename.lower().endswith(".csv"):
        return None, "Chỉ chấp nhận file .csv."
    try:
        text = f.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, "File phải mã hóa UTF-8."
    return list(csv.DictReader(io.StringIO(text))), None


@app.post("/api/admin/bulk-import/nhom-thuoc")
def bulk_import_nhom_thuoc():
    _admin, error = _require_admin_db()
    if error:
        return error
    rows, msg = _read_csv_upload()
    if rows is None:
        return jsonify({"error": msg}), 400
    inserted, skipped, errors = 0, 0, []
    for i, row in enumerate(rows, start=2):
        ten = str(row.get("ten_nhom") or row.get("ten_nhom_thuoc") or row.get("tên_nhóm") or "").strip()
        if not ten:
            errors.append(f"Dòng {i}: thiếu tên nhóm")
            continue
        if db.session.query(db_models.NhomThuoc).filter_by(ten_nhom_thuoc=ten).first():
            skipped += 1
            continue
        db.session.add(db_models.NhomThuoc(ten_nhom_thuoc=ten[:255], mo_ta=(str(row.get("mo_ta") or "").strip() or None)))
        inserted += 1
    db.session.commit()
    return jsonify({"ok": True, "inserted": inserted, "skipped": skipped, "errors": errors[:20]})


@app.post("/api/admin/bulk-import/thuoc")
def bulk_import_thuoc():
    _admin, error = _require_admin_db()
    if error:
        return error
    rows, msg = _read_csv_upload()
    if rows is None:
        return jsonify({"error": msg}), 400
    inserted, errors = 0, []
    for i, row in enumerate(rows, start=2):
        ten = str(row.get("ten_thuoc") or row.get("tên_thuốc") or "").strip()
        if not ten:
            errors.append(f"Dòng {i}: thiếu tên thuốc")
            continue
        t = db_models.ThuocThamKhao(
            ten_thuoc=ten[:255],
            hoat_chat=(str(row.get("hoat_chat") or "").strip() or None),
            cong_dung=(str(row.get("cong_dung") or row.get("mo_ta") or "").strip() or None),
        )
        nhom_name = str(row.get("nhom_thuoc") or row.get("nhom_thuoc_id") or row.get("nhóm_thuốc") or "").strip()
        if nhom_name:
            n = db.session.query(db_models.NhomThuoc).filter_by(ten_nhom_thuoc=nhom_name).first()
            if n:
                t.nhom_thuoc_list.append(n)
            else:
                errors.append(f"Dòng {i}: nhóm '{nhom_name}' không tồn tại (thuốc vẫn được thêm)")
        db.session.add(t)
        inserted += 1
    db.session.commit()
    return jsonify({"ok": True, "inserted": inserted, "errors": errors[:20]})


@app.get("/api/admin/bulk-import/template/nhom-thuoc")
def template_nhom_thuoc():
    _admin, error = _require_admin_db()
    if error:
        return error
    csv_data = "ten_nhom,mo_ta\nthuốc giảm đau hạ sốt,Hạ sốt giảm đau thông thường\n"
    return app.response_class(csv_data, mimetype="text/csv",
                              headers={"Content-Disposition": "attachment; filename=nhom_thuoc_template.csv"})


@app.get("/api/admin/bulk-import/template/thuoc")
def template_thuoc():
    _admin, error = _require_admin_db()
    if error:
        return error
    csv_data = "ten_thuoc,hoat_chat,cong_dung,nhom_thuoc\nParacetamol,paracetamol,Hạ sốt giảm đau,thuốc giảm đau hạ sốt\n"
    return app.response_class(csv_data, mimetype="text/csv",
                              headers={"Content-Disposition": "attachment; filename=thuoc_template.csv"})


# ── PORT toan/main: DUYỆT PHẢN HỒI KHÔNG ĐỒNG Ý (review workflow) ─────────────
@app.get("/api/admin/rejected-feedbacks")
def list_rejected_feedbacks():
    """Danh sách phản hồi 'Không đồng ý' để admin duyệt. ?reviewed=0|1 lọc theo trạng thái
    duyệt; ?page=&per_page= phân trang. Admin-only, DB."""
    _admin, error = _require_admin_db()
    if error:
        return error
    PH = db_models.PhanHoi
    query = db.session.query(PH).filter(PH.trang_thai == "REJECT")
    reviewed = request.args.get("reviewed")
    if reviewed in ("0", "1"):
        query = query.filter(PH.da_xu_ly.is_(reviewed == "1"))
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = max(1, min(100, int(request.args.get("per_page", 10))))
    except (TypeError, ValueError):
        page, per_page = 1, 10
    total = query.count()
    chua_xu_ly = db.session.query(PH).filter(PH.trang_thai == "REJECT", PH.da_xu_ly.isnot(True)).count()
    rows = query.order_by(PH.thoi_gian_gui.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({
        "total": total,
        "chua_xu_ly": chua_xu_ly,
        "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total else 0,
        "feedbacks": [
            {
                "ma": r.ma_phan_hoi,
                "noi_dung": r.noi_dung,
                "nhom_thuoc": r.nhom_thuoc_du_doan,
                "thoi_gian": _iso_dt(r.thoi_gian_gui),
                "da_xu_ly": bool(r.da_xu_ly),
            }
            for r in rows
        ],
    })


@app.post("/api/admin/rejected-feedbacks/<int:ma>/reviewed")
def mark_feedback_reviewed(ma):
    """Đánh dấu phản hồi đã/chưa duyệt. Body {da_xu_ly: true|false} (mặc định true)."""
    _admin, error = _require_admin_db()
    if error:
        return error
    r = db.session.get(db_models.PhanHoi, ma)
    if not r:
        return jsonify({"error": "Không tìm thấy phản hồi."}), 404
    p = request.get_json(silent=True) or {}
    r.da_xu_ly = bool(p.get("da_xu_ly", True))
    db.session.commit()
    return jsonify({"ok": True, "da_xu_ly": r.da_xu_ly}), 200


@app.get("/api/admin/db/trieu-chung")
def admin_db_trieu_chung():
    """US27 (SCRUM-109/111): tìm kiếm triệu chứng trong từ điển theo TÊN hoặc TỪ KHÓA,
    có phân trang. ?q=&page=1&per_page=10. Admin-only, đọc Postgres.
    """
    _admin, error = _require_admin_db()
    if error:
        return error
    q = (request.args.get("q") or "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = max(1, min(100, int(request.args.get("per_page", 10))))
    except (TypeError, ValueError):
        per_page = 10

    TC = db_models.TrieuChung
    query = db.session.query(TC)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(TC.ten_trieu_chung.ilike(like), TC.tu_khoa.ilike(like)))
    total = query.count()
    total_pages = (total + per_page - 1) // per_page if total else 0
    rows = (
        query.order_by(TC.ten_trieu_chung)
        .offset((page - 1) * per_page).limit(per_page).all()
    )
    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "query": q,
        "trieu_chung": [
            {"ma": t.ma_trieu_chung, "ten": t.ten_trieu_chung, "tu_khoa": t.tu_khoa}
            for t in rows
        ],
    })


# ── PORT toan/main: CRUD từ điển TRIỆU CHỨNG (thêm/sửa/xóa) ───────────────────
@app.post("/api/admin/db/trieu-chung")
def create_trieu_chung():
    _admin, error = _require_admin_db()
    if error:
        return error
    p = request.get_json(silent=True) or {}
    ten = str(p.get("ten") or "").strip()
    if not ten:
        return jsonify({"error": "Cần tên triệu chứng."}), 400
    if db.session.query(db_models.TrieuChung).filter_by(ten_trieu_chung=ten).first():
        return jsonify({"error": "Triệu chứng đã tồn tại."}), 409
    t = db_models.TrieuChung(ten_trieu_chung=ten[:255], tu_khoa=(str(p.get("tu_khoa") or "").strip() or None))
    db.session.add(t)
    db.session.commit()
    return jsonify({"ok": True, "ma": t.ma_trieu_chung}), 201


@app.put("/api/admin/db/trieu-chung/<int:ma>")
def update_trieu_chung(ma):
    _admin, error = _require_admin_db()
    if error:
        return error
    t = db.session.get(db_models.TrieuChung, ma)
    if not t:
        return jsonify({"error": "Không tìm thấy triệu chứng."}), 404
    p = request.get_json(silent=True) or {}
    ten = str(p.get("ten") or "").strip()
    if ten:
        dup = db.session.query(db_models.TrieuChung).filter_by(ten_trieu_chung=ten).first()
        if dup and dup.ma_trieu_chung != ma:
            return jsonify({"error": "Tên triệu chứng đã tồn tại."}), 409
        t.ten_trieu_chung = ten[:255]
    if "tu_khoa" in p:
        t.tu_khoa = (str(p.get("tu_khoa") or "").strip() or None)
    db.session.commit()
    return jsonify({"ok": True}), 200


@app.delete("/api/admin/db/trieu-chung/<int:ma>")
def delete_trieu_chung(ma):
    _admin, error = _require_admin_db()
    if error:
        return error
    t = db.session.get(db_models.TrieuChung, ma)
    if not t:
        return jsonify({"error": "Không tìm thấy triệu chứng."}), 404
    db.session.delete(t)
    db.session.commit()
    return jsonify({"ok": True}), 200


# ── US28 (SCRUM-112): ánh xạ chi tiết TRIỆU CHỨNG ↔ NHÓM THUỐC ────────────────
# Nguồn ánh xạ = dữ liệu TRAIN (kiểm tra dữ liệu): đếm đồng xuất hiện symptom↔nhom_thuoc
# trong train_ready_mapped_drug_groups.csv. Lazy-cache trong biến module.
_SYMPTOM_GROUP_INDEX = None


def _symptom_group_index() -> dict:
    """{symptom_lower: {nhom_thuoc: số_ca_đồng_xuất_hiện}} — dựng 1 lần từ CSV train."""
    global _SYMPTOM_GROUP_INDEX
    if _SYMPTOM_GROUP_INDEX is not None:
        return _SYMPTOM_GROUP_INDEX
    index: dict[str, Counter] = {}
    try:
        with DATA_SOURCE.open("r", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                group = (row.get("nhom_thuoc") or "").strip()
                if not group:
                    continue
                for sym in (row.get("trieu_chung") or "").split(";"):
                    sym = sym.strip().lower()
                    if sym:
                        index.setdefault(sym, Counter())[group] += 1
    except OSError:
        app.logger.exception("US28: không đọc được CSV train cho ánh xạ")
    _SYMPTOM_GROUP_INDEX = index
    return index


@app.get("/api/admin/symptom-mapping")
def admin_symptom_mapping():
    """US28 (SCRUM-113/115): trả các NHÓM THUỐC liên quan tới một triệu chứng (theo dữ
    liệu train), kèm số ca đồng xuất hiện + %. Admin-only. ?ma=<id> hoặc ?ten=<tên>.
    """
    _admin, error = _require_admin_db()
    if error:
        return error

    ten = (request.args.get("ten") or "").strip()
    ma = request.args.get("ma")
    if not ten and ma:
        try:
            row = db.session.get(db_models.TrieuChung, int(ma))
            ten = row.ten_trieu_chung if row else ""
        except (TypeError, ValueError):
            ten = ""
    if not ten:
        return jsonify({"error": "Thiếu tham số ?ma hoặc ?ten."}), 400

    counts = _symptom_group_index().get(ten.lower(), Counter())
    total = sum(counts.values())
    groups = [
        {"group": g, "count": c, "percent": round(c / total * 100, 1) if total else 0.0}
        for g, c in counts.most_common()
    ]
    return jsonify({
        "ten": ten,
        "total_cases": total,
        "distinct_groups": len(groups),
        "groups": groups,
    })


# ── US15 (port): tự động lưu lịch sử mỗi lần dự đoán ──────────────────────────
# Ghi vào prediction_log.jsonl — đúng nguồn mà US19 (stats_source) đọc. Port theo hook
# @app.after_request của nhánh toan/tu, nhưng dùng kiến trúc file-JSON + Bearer của nhánh này.
def _prediction_status_from(response, body: dict) -> str:
    if response.status_code == 200:
        return "suggest"
    if body.get("score_type") == "emergency":
        return "emergency"
    return "safety_block"  # các 422 còn lại: né an toàn / chưa đủ dữ liệu


def _group_from_body(body: dict) -> str | None:
    group = (body.get("case_summary") or {}).get("drug_group")
    if not isinstance(group, str) or not group.strip() or group.startswith("Chưa"):
        return None
    return group.strip()


def _db_log_prediction(status: str, group: str | None, email: str, confidence,
                       notes: str | None = None) -> None:
    """US15 DB: tạo KetQuaDuDoan (+LichSuDuDoan) cho mỗi lần dự đoán.

    Nếu có câu người dùng nhập (notes) -> lưu kèm MoTaBenhAn để admin xem chi tiết về sau.
    """
    kq = db_models.KetQuaDuDoan(
        trang_thai=status,
        nhom_thuoc_du_doan=group,
        user_email=email,
        do_tin_cay=confidence,
    )
    if isinstance(notes, str) and notes.strip():
        kq.mo_ta_benh_an = db_models.MoTaBenhAn(noi_dung=notes.strip()[:2000], ngon_ngu="vi")
    kq.lich_su = db_models.LichSuDuDoan(ket_qua_tom_tat=f"{status}: {group or '—'}")
    db.session.add(kq)
    db.session.commit()


@app.after_request
def log_prediction_after_request(response):
    try:
        if request.endpoint != "predict" or request.method != "POST" or not response.is_json:
            return response
        if response.status_code not in (200, 422):
            return response
        body = response.get_json(silent=True) or {}
        user = current_user_from_request(load_user_store())
        status = _prediction_status_from(response, body)
        group = _group_from_body(body)
        email = (user or {}).get("email") or "guest"
        conf = body.get("confidence")
        conf = float(conf) if isinstance(conf, (int, float)) else None
        notes = (request.get_json(silent=True) or {}).get("notes")
        if DB_ENABLED:
            try:
                _db_log_prediction(status, group, email, conf, notes)
                return response
            except Exception:
                db.session.rollback()
                app.logger.exception("US15: lỗi ghi DB -> fallback JSONL")
        _append_jsonl(
            stats_source.PREDICTION_LOG_PATH,
            {"ts": iso_utc(now_utc()), "status": status, "predicted_group": group, "user_email": email},
        )
    except Exception:
        app.logger.exception("US15: không ghi được lịch sử dự đoán")
    return response


# ── US18 (port): thu phản hồi Đồng ý / Không đồng ý ───────────────────────────
@app.post("/api/feedback")
def submit_feedback():
    """Lưu đánh giá của người dùng về kết quả dự đoán. verdict: APPROVE | REJECT.

    Tương thích contract của nhánh toan/main: chấp nhận cả 'trang_thai' (alias verdict)
    và 'ghi_chu' (alias note). Ghi vào feedback.jsonl — nguồn US19 đọc tính tỷ lệ 'Đồng ý'.
    """
    payload = request.get_json(silent=True) or {}
    verdict = str(payload.get("verdict") or payload.get("trang_thai") or "").upper()
    if verdict not in stats_source.FEEDBACK_VERDICTS:
        return jsonify({"error": "verdict phải là APPROVE (Đồng ý) hoặc REJECT (Không đồng ý)."}), 400

    group = payload.get("predicted_group")
    group = group.strip() if isinstance(group, str) and group.strip() else None
    note = str(payload.get("note") or payload.get("ghi_chu") or "")[:1000]
    user = current_user_from_request(load_user_store())

    if DB_ENABLED:
        try:
            db.session.add(db_models.PhanHoi(
                trang_thai=verdict,
                muc_do_hai_long=1 if verdict == "APPROVE" else 0,
                nhom_thuoc_du_doan=group,
                noi_dung=note or None,
                ma_nguoi_dung=(user or {}).get("_ma_nguoi_dung"),
            ))
            db.session.commit()
            return jsonify({"ok": True, "message": "Đã ghi nhận phản hồi. Cảm ơn bạn!"}), 201
        except Exception:
            db.session.rollback()
            app.logger.exception("US18: lỗi ghi DB -> fallback JSONL")

    _append_jsonl(
        stats_source.FEEDBACK_LOG_PATH,
        {
            "ts": iso_utc(now_utc()),
            "verdict": verdict,
            "predicted_group": group,
            "user_email": (user or {}).get("email") or "guest",
            "note": note,
        },
    )
    return jsonify({"ok": True, "message": "Đã ghi nhận phản hồi. Cảm ơn bạn!"}), 201


@app.post("/api/predict")
def predict():
    payload = request.get_json(silent=True) or {}
    selected = payload.get("symptoms") or []
    notes = payload.get("notes") or ""

    if not isinstance(notes, str):
        return jsonify({"error": "Mô tả triệu chứng không hợp lệ."}), 400
    if len(notes) > MAX_NOTES_LENGTH:
        return jsonify({"error": f"Mô tả triệu chứng không được vượt quá {MAX_NOTES_LENGTH} ký tự."}), 400
    if not isinstance(selected, list):
        return jsonify({"error": "Danh sách triệu chứng không hợp lệ."}), 400

    # ── CỔNG CẤP CỨU (ưu tiên cao nhất): bắt dấu hiệu nguy hiểm/khủng hoảng từ mô tả thô,
    # trước cả bước trích triệu chứng, để KHÔNG bao giờ gợi thuốc cho ca cấp cứu.
    _emergency = emergency_red_flag_from_notes(notes)
    if not _emergency and context_safety is not None:
        _emergency = context_safety.emergency_message(notes)  # phản vệ: sưng môi/lưỡi/họng + khó thở
    if _emergency:
        # Cờ đỏ dạng "đi khám sớm" (SEE) KHÔNG phải cấp cứu -> nhãn nhẹ hơn, vẫn chặn kê thuốc (422).
        is_referral = _emergency.endswith(REFERRAL_SEE_SUFFIX)
        return jsonify({
            "error": _emergency,
            "display_title": "⚠️ Cần đi khám bác sĩ sớm" if is_referral else "⚠️ Cần hỗ trợ y tế khẩn cấp",
            "needs_more_input": True,
            "confidence": None,
            "label_type": LABEL_TYPE,
            "score_type": "referral" if is_referral else "emergency",
            "matched_symptoms": [],
            "top_predictions": [],
        }), 422

    # ── Tầng LLM trích xuất NGỮ CẢNH (vòng 5, BỔ SUNG, mặc định TẮT). Chạy SAU cổng cấp cứu
    # lexicon, chỉ làm giàu đầu vào. Mọi lỗi -> _llm_context=None (fallback im lặng, không crash).
    _llm_context = None
    if llm_context_enabled():
        try:
            _llm_context = llm_context.extract_context(notes)
        except Exception:
            _llm_context = None

    active_symptoms = set()
    active_symptoms_order = []
    for symptom in selected:
        key = str(symptom).lower()
        if key in feature_lookup:
            feature = feature_lookup[key]
            if feature not in active_symptoms:
                active_symptoms.add(feature)
                active_symptoms_order.append(feature)

    for symptom in ordered_symptoms_from_text(notes):
        if symptom not in active_symptoms:
            active_symptoms.add(symptom)
            active_symptoms_order.append(symptom)
    # Hợp nhất triệu chứng LLM trích được (đã map về feature space).
    if _llm_context is not None:
        for symptom in features_from_llm_symptoms(_llm_context.get("symptoms_vi", [])):
            if symptom not in active_symptoms:
                active_symptoms.add(symptom)
                active_symptoms_order.append(symptom)
    unsupported_symptoms = unsupported_symptoms_from_text(notes)
    # Phủ định: trừ feature LLM đánh dấu phủ định, rồi vẫn chạy lọc phủ định theo notes như cũ.
    if _llm_context is not None:
        active_symptoms_order = apply_llm_negations(active_symptoms_order, _llm_context.get("negated_vi", []))
    active_symptoms_order = filter_negated_symptoms(active_symptoms_order, notes)
    active_symptoms = set(active_symptoms_order)

    # ── Cổng an toàn THỨ HAI (vòng 5): cờ đỏ LLM đã được chứng thực -> 422 cấp cứu, không kê thuốc.
    if _llm_context is not None:
        _llm_emergency = llm_safety_red_flag_message(_llm_context, notes, active_symptoms)
        if _llm_emergency:
            return jsonify({
                "error": _llm_emergency,
                "display_title": "⚠️ Cần hỗ trợ y tế khẩn cấp",
                "needs_more_input": True,
                "confidence": None,
                "label_type": LABEL_TYPE,
                "score_type": "emergency",
                "matched_symptoms": active_symptoms_order,
                "top_predictions": [],
            }), 422

    if not active_symptoms:
        # ── LỚP DỰ PHÒNG LLM (mặc định TẮT): pipeline không trích được triệu chứng -> nhờ LLM
        # đọc mô tả thô (vá "diễn đạt lạ"). Cấp cứu ĐÃ chặn ở cổng lexicon phía trên; output LLM
        # vẫn qua gating an toàn dưới đây và LUÔN là "tham khảo" (không phải gợi ý chắc chắn).
        if LABEL_TYPE == "drug_group" and llm_classify is not None:
            llm_group = llm_classify.classify_group(notes, list(model.classes_))
            if llm_group:
                if is_never_suggest_group(llm_group):
                    title = "Cần khám chuyên khoa"
                    msg = ("Theo mô tả, vấn đề có thể cần điều trị chuyên sâu (vd ung thư/miễn dịch) — "
                           "cần bác sĩ chuyên khoa đánh giá trực tiếp, công cụ không thể tự gợi ý.")
                    sg = None
                elif is_high_risk_group(llm_group):
                    title = f"Cần đi khám bác sĩ — có thể liên quan nhóm {llm_group}"
                    msg = (f"Trợ lý AI nhận định triệu chứng CÓ THỂ liên quan nhóm '{llm_group}', nhưng đây là "
                           "thuốc KÊ ĐƠN: cần bác sĩ khám và chỉ định, KHÔNG tự mua dùng.")
                    sg = llm_group
                else:
                    title = f"Gợi ý tham khảo (trợ lý AI): {llm_group}"
                    msg = (f"Chưa trích được triệu chứng chuẩn, nhưng trợ lý AI nhận định CÓ THỂ liên quan nhóm "
                           f"'{llm_group}'. Đây là gợi ý THAM KHẢO (độ tin cậy chưa định lượng) — hãy mô tả rõ "
                           "hơn triệu chứng hoặc hỏi dược sĩ/bác sĩ trước khi dùng.")
                    sg = llm_group
                return jsonify({
                    "error": msg,
                    "display_title": title,
                    "suggested_group": sg,
                    "needs_more_input": True,
                    "input_used": "llm_fallback",
                    "confidence": None,
                    "score_type": "llm_fallback",
                    "label_type": LABEL_TYPE,
                    "matched_symptoms": [],
                    "matched_symptoms_vi": [],
                    "top_predictions": [],
                }), 422

        unsupported_labels = [symptom["label_vi"] for symptom in unsupported_symptoms]
        extra = ""
        if unsupported_labels:
            extra = f" Model hiện chưa có đặc trưng cho: {', '.join(unsupported_labels)}."
        return jsonify({"error": f"Không nhận diện được triệu chứng phù hợp với tập train.{extra} Hãy viết rõ hơn hoặc chọn thêm triệu chứng trong danh sách."}), 400

    model_inputs = model_input_candidates(active_symptoms_order)
    probabilities = []
    confidence = None
    prediction = None
    top_gap = None  # khoảng cách xác suất top-1 vs top-2 (đo độ "dứt khoát" của model)
    input_used = "symptoms"  # luồng dùng để dự đoán: cụm triệu chứng đã trích hay raw notes
    if hasattr(model, "predict_proba"):
        ranked = ranked_proba(model_inputs)
        # Hybrid (raw-VI): nếu model hiểu câu thô và có mô tả VN, thử dự đoán THẲNG trên raw
        # notes; lấy ứng viên tự tin hơn. Tầng trích triệu chứng vẫn nuôi mọi cổng an toàn.
        if model_accepts_raw_text() and notes.strip():
            ranked_raw = ranked_proba([notes.strip()])
            if ranked_raw[0][1] > ranked[0][1]:
                ranked = ranked_raw
                input_used = "raw_notes"
        prediction = ranked[0][0]
        probabilities = [
            {
                "disease": disease,
                "disease_vi": predicted_label_vi(disease),
                "probability": round(float(probability), 4),
                "similarity_score": round(float(probability), 4),
            }
            for disease, probability in ranked[:5]
        ]
        confidence = round(float(ranked[0][1]), 4)
        if len(ranked) >= 2:
            top_gap = round(float(ranked[0][1] - ranked[1][1]), 4)
    else:
        prediction = model.predict([model_inputs[0]])[0]

    rule_group = (
        # Notes-aware (vòng 3): ưu tiên cao nhất vì rất đặc hiệu, chặn model đoán sai tự tin.
        malaria_rule_drug_group(notes, active_symptoms)
        or anemia_rule_drug_group(notes, active_symptoms)
        or diabetes_rule_drug_group(active_symptoms)
        or thyroid_rule_drug_group(notes, active_symptoms)
        or psych_rule_drug_group(active_symptoms)
        or cardiac_rule_drug_group(active_symptoms)
        or bacterial_respiratory_rule_drug_group(notes, active_symptoms)
        or heat_exhaustion_rule_drug_group(notes)
        or insect_bite_rule_drug_group(notes)
        or bronchodilator_rule_drug_group(active_symptoms)
        or wound_infection_rule_drug_group(active_symptoms)
        or infectious_bloody_diarrhea_rule_drug_group(active_symptoms)
        or urinary_rule_drug_group(active_symptoms)
        or neuropathic_pain_rule_drug_group(notes, active_symptoms)
        or migraine_rule_drug_group(active_symptoms)
        or antiviral_skin_rule_drug_group(notes, active_symptoms)
        or musculoskeletal_nsaid_rule_drug_group(active_symptoms)
        or constipation_rule_drug_group(active_symptoms)
        or dental_rule_drug_group(active_symptoms)
        or fungal_notes_rule_drug_group(notes)
        or gastrointestinal_rule_drug_group(active_symptoms)
        or dermatology_rule_drug_group(active_symptoms)
        or respiratory_rule_drug_group(active_symptoms)
        or general_fever_pain_rule_drug_group(active_symptoms)
        or isolated_fever_rule_drug_group(active_symptoms)
    )
    score_type = metadata.get("score_type", "probability")
    if rule_group:
        prediction = rule_group
        confidence = None
        probabilities = []
        score_type = "rule"

    description = references["description"].get(prediction, "")
    quality_reasons = []
    if has_neuro_danger_signs(active_symptoms):
        quality_reasons.append(
            "Có dấu hiệu thần kinh nguy hiểm (cứng cổ, yếu/liệt nửa người, lú lẫn, nói khó, co giật). "
            "Đây có thể là cấp cứu; cần đến cơ sở y tế ngay, KHÔNG tự dùng thuốc theo gợi ý tham khảo."
        )
    matched_symptoms = active_symptoms_order
    matched_symptom_labels = unique_values([symptom_label_vi(symptom) for symptom in matched_symptoms])
    label_kind_vi = "nhóm thuốc" if LABEL_TYPE == "drug_group" else "bệnh"

    # Khi một rule lâm sàng mạnh đã kích hoạt (score_type=="rule"), không ép "cần thêm
    # thông tin" chỉ vì ít hơn 2 triệu chứng — nhiều ca rõ ràng chỉ có 1 triệu chứng đặc
    # hiệu (táo bón, mụn nước thành chùm, mề đay...). Vẫn giữ ràng buộc cho dự đoán bằng model.
    # Hybrid raw-VI: khi dự đoán đến THẲNG từ raw notes với độ tin cậy cao và model dứt khoát
    # (top-gap đủ rộng), KHÔNG ép "cần thêm thông tin" chỉ vì trích được ít cụm triệu chứng EN
    # (mô tả VN tự nhiên thường ít khớp). Cổng cấp cứu/high-risk/never-suggest vẫn áp dụng độc lập.
    raw_confident = (
        input_used == "raw_notes"
        and confidence is not None
        and confidence >= MIN_RELIABLE_CONFIDENCE
        and (top_gap is None or top_gap >= MIN_TOPGAP)
    )
    if score_type != "rule" and not raw_confident and len(matched_symptom_labels) < MIN_RELIABLE_SYMPTOMS:
        quality_reasons.append(
            f"Chỉ nhận diện được {len(matched_symptom_labels)} triệu chứng chính trong tập train; cần thêm triệu chứng để phân biệt {label_kind_vi}."
        )
    if LABEL_TYPE == "drug_group" and score_type != "rule" and should_force_more_info(active_symptoms):
        if has_unclear_limb_stiffness(active_symptoms):
            quality_reasons.append(
                "Cứng/co rút tay đơn độc chưa đủ để xác định cần dùng thuốc kháng viêm hay nhóm thuốc khác."
            )
        elif has_unclear_cough_itch(active_symptoms):
            quality_reasons.append(
                "Ho kèm ngứa chưa đủ để phân biệt dị ứng, viêm hô hấp, kích ứng họng hoặc bệnh da; chưa nên gợi ý corticosteroid/chống viêm."
            )
        elif has_any_symptom(active_symptoms, ["headache", "dizziness", "insomnia"]):
            quality_reasons.append(
                "Cụm đau đầu/chóng mặt/mất ngủ cần thêm bối cảnh trước khi gợi ý nhóm thuốc."
            )
        else:
            quality_reasons.append(
                "Cụm triệu chứng này cần thêm bối cảnh trước khi gợi ý nhóm thuốc."
            )
    if score_type != "rule" and confidence is not None and confidence < MIN_RELIABLE_CONFIDENCE:
        quality_reasons.append(
            f"Độ tin cậy cao nhất chỉ {confidence * 100:.1f}%, thấp hơn ngưỡng {MIN_RELIABLE_CONFIDENCE * 100:.0f}%."
        )
    # Lớp phòng thủ phụ: nhóm rủi ro cao do model đoán cần ngưỡng tin cậy cao hơn.
    if (
        score_type != "rule"
        and confidence is not None
        and is_high_risk_group(prediction)
        and confidence < MIN_HIGH_RISK_MODEL_CONFIDENCE
    ):
        quality_reasons.append(
            f"Nhóm '{prediction}' là nhóm rủi ro cao, nhưng độ tin cậy chỉ {confidence * 100:.1f}% "
            f"(< {MIN_HIGH_RISK_MODEL_CONFIDENCE * 100:.0f}%); cần thêm triệu chứng để khẳng định."
        )
    # P2.3: nhóm rủi ro cao KHI DO RULE đoán cũng cần bác sĩ xác nhận (kê đơn) -> không tự dùng.
    # Rule vẫn ngăn model đoán bừa, nhưng output chuyển sang "đi khám" thay vì kê thuốc tự tin.
    if score_type == "rule" and is_high_risk_group(prediction):
        quality_reasons.append(
            f"Nhóm '{prediction}' là nhóm thuốc cần kê đơn/chỉ định của bác sĩ; không tự dùng theo "
            "gợi ý. Hãy đi khám để được đánh giá và chỉ định đúng."
        )
    # P4: nhóm KHÔNG BAO GIỜ tự gợi ý (ung thư/điều trị chuyên sâu) -> luôn chuyển khám.
    if is_never_suggest_group(prediction):
        quality_reasons.append(
            "Nhóm này thuộc điều trị chuyên sâu (vd ung thư/miễn dịch), không thể tự gợi ý qua công cụ "
            "tham khảo; cần bác sĩ chuyên khoa đánh giá trực tiếp."
        )
    # P4: triệu chứng tai -> khám tai mũi họng, chưa tự dùng thuốc.
    if LABEL_TYPE == "drug_group" and has_any_symptom(active_symptoms, ["ear pain", "fluid in ear", "diminished hearing"]):
        quality_reasons.append(
            "Triệu chứng tai (đau tai/chảy dịch/nghe kém) nên được bác sĩ tai mũi họng đánh giá; chưa nên tự dùng thuốc."
        )
    # P4: chỉ có triệu chứng KHÔNG ĐẶC HIỆU (mệt mỏi/uể oải) -> cần thêm triệu chứng cụ thể.
    if score_type != "rule" and active_symptoms and set(active_symptoms).issubset({"fatigue", "malaise", "lethargy", "feeling ill", "feeling unwell"}):
        quality_reasons.append(
            "Chỉ ghi nhận triệu chứng không đặc hiệu (mệt mỏi/uể oải); cần thêm triệu chứng cụ thể để định hướng."
        )
    # Top-gap (vòng 6): model phân vân giữa 2 nhóm sát nhau -> phán đoán "trọng" hơn bằng cách
    # xin thêm thông tin thay vì đoán bừa. Chỉ áp cho model path, khi top-1 chưa vượt trội.
    if (
        MIN_TOPGAP > 0
        and score_type != "rule"
        and top_gap is not None
        and top_gap < MIN_TOPGAP
    ):
        quality_reasons.append(
            f"Model phân vân giữa các nhóm gần nhau (chênh lệch top-1/top-2 chỉ {top_gap * 100:.1f}%); "
            "cần thêm triệu chứng để phân biệt."
        )
    # Ngữ cảnh (vòng 4): rượu RÕ/NHIỀU + nhóm giảm đau hạ sốt -> KHÔNG kê vô điều kiện vì
    # paracetamol/acetaminophen tăng nguy cơ độc gan khi có rượu. Đẩy sang "cần thêm thông tin".
    # Gộp ngữ cảnh rượu từ notes (vòng 4) + ngữ cảnh LLM (vòng 5). LLM chỉ làm giàu tín hiệu.
    _llm_alcohol_text = llm_context_text(_llm_context, "alcohol") if _llm_context is not None else ""
    strong_alcohol = has_strong_alcohol_context(notes) or has_strong_alcohol_context(_llm_alcohol_text)
    weak_alcohol = has_weak_alcohol_context(notes) or has_weak_alcohol_context(_llm_alcohol_text)
    alcohol_blocks_analgesic = (
        LABEL_TYPE == "drug_group"
        and (prediction == "thuốc giảm đau hạ sốt" or "headache" in active_symptoms or "fatigue" in active_symptoms)
        and strong_alcohol
    )
    if alcohol_blocks_analgesic:
        quality_reasons.append(
            "Mô tả có uống nhiều rượu/lạm dụng rượu kèm hướng dùng thuốc giảm đau hạ sốt: "
            "paracetamol (acetaminophen) có thể gây độc gan khi dùng cùng rượu. Cần hỏi dược sĩ/bác sĩ, "
            "không tự dùng; nêu rõ lượng rượu, bệnh gan và thuốc đang dùng."
        )
    if unsupported_symptoms:
        unsupported_labels = ", ".join(symptom["label_vi"] for symptom in unsupported_symptoms)
        quality_reasons.append(
            f"Có triệu chứng ngoài tập train nên chưa được đưa vào mô hình: {unsupported_labels}."
        )

    # ── TẦNG NGỮ CẢNH - AN TOÀN: đọc cả câu (bệnh nền/tuổi/thai kỳ/tương tác/dị ứng) và CHẶN
    # gợi ý chống chỉ định, BẤT KỂ nguồn dự đoán (model hay rule). Đây là lớp vá điểm mù ngữ cảnh.
    _contraindicated = False
    if LABEL_TYPE == "drug_group" and context_safety is not None:
        # LLM trích ngữ cảnh (semantic) để bắt cách nói MỚI lexicon sót; đồng thời HỌC lại.
        _extra = None
        if llm_context_extract is not None and llm_context_extract.enabled():
            try:
                _parsed = llm_context_extract.extract(notes)
                if _parsed:
                    context_safety.learn_from_llm(_parsed)  # lưu cụm chữ mới -> rule tự bắt lần sau
                    _extra = context_safety.flags_from_llm(_parsed)
            except Exception:
                _extra = None
        if context_safety.drug_allergy_cause(context_safety.norm(notes)) or (_extra and _extra.get("allergy")):
            quality_reasons.insert(0, context_safety.drug_allergy_message())
            _contraindicated = True
        _ctx = context_safety.safety_overrides(prediction, notes, extra=_extra)
        if _ctx["block"]:
            _contraindicated = True
            # Cảnh báo chống chỉ định phải đứng ĐẦU thông điệp.
            for r in reversed(_ctx["reasons"]):
                quality_reasons.insert(0, r)
        else:
            quality_reasons.extend(_ctx["reasons"])

    needs_more_input = bool(quality_reasons)
    quality_message = " ".join(quality_reasons)
    if needs_more_input:
        quality_message += " Chưa đủ dữ liệu để gợi ý nhóm thuốc an toàn."

    if LABEL_TYPE == "drug_group" and needs_more_input:
        triage = symptom_triage_guidance(active_symptoms)
        summary = case_summary(notes, active_symptoms, matched_symptom_labels, prediction, False)
        # Khi hệ NHẬN ĐÚNG một nhóm KÊ ĐƠN (rủi ro cao, không phải nhóm "không bao giờ gợi ý"
        # như ung thư) rồi chủ động chuyển khám: NÊU TÊN nhóm + cảnh báo kê đơn, thay vì câu
        # chung chung. Vẫn 422/needs_more, vẫn KHÔNG kê thuốc thật — chỉ minh bạch hơn về hướng.
        rx_group = (
            prediction
            if prediction and is_high_risk_group(prediction) and not is_never_suggest_group(prediction)
            else None
        )
        if _contraindicated:
            display_title = "⚠️ Cảnh báo an toàn — KHÔNG tự dùng thuốc, cần bác sĩ"
            error_message = quality_message
        elif rx_group:
            display_title = f"Cần đi khám bác sĩ — có thể liên quan nhóm {rx_group}"
            error_message = (
                f"Triệu chứng của bạn CÓ THỂ liên quan đến nhóm '{rx_group}', nhưng đây là thuốc "
                f"KÊ ĐƠN: cần bác sĩ khám và chỉ định, KHÔNG tự mua dùng. {quality_message}"
            )
        else:
            display_title = "Chưa đủ dữ liệu để gợi ý thuốc"
            error_message = f"{quality_message} {more_info_prompt(active_symptoms)}"
        return jsonify(
            {
                "error": error_message,
                "case_summary": summary,
                "display_title": display_title,
                "suggested_group": rx_group,
                "needs_more_input": True,
                "matched_symptoms": matched_symptoms,
                "matched_symptoms_vi": matched_symptom_labels,
                "confidence": None,
                "score_label": SCORE_LABEL,
                "score_type": score_type,
                "label_type": LABEL_TYPE,
                "suggested_symptoms": suggested_symptoms_for_more_info(active_symptoms),
                "medications": triage["treatment"],
                "precautions": triage["precautions"],
                "diets": triage["care"],
                "warning": triage["warning"],
                "guidance_source": triage["guidance_source"],
                "top_predictions": [],
            }
        ), 422

    if LABEL_TYPE == "drug_group":
        guidance = drug_group_guidance(prediction, active_symptoms)
        description_text = "Triệu chứng đã nhận diện từ mô tả: " + ", ".join(matched_symptom_labels) + "."
    else:
        guidance = symptom_based_guidance(active_symptoms, prediction)
        description_text = disease_description_vi(prediction, description)

    summary = case_summary(notes, active_symptoms, matched_symptom_labels, prediction, True)

    treatment_guidance = []
    extend_unique(treatment_guidance, guidance["treatment"])

    precaution_guidance = []
    extend_unique(precaution_guidance, guidance["precautions"])

    care_guidance = []
    extend_unique(care_guidance, guidance["care"])

    # Ngữ cảnh động (vòng 4): bổ sung cảnh báo/chăm sóc theo "sau khi X" cho ca VẪN gợi ý nhóm.
    warning_text = guidance["warning"]
    if LABEL_TYPE == "drug_group" and prediction == "thuốc giảm đau hạ sốt" and weak_alcohol:
        alcohol_caution = (
            "Lưu ý: không tự dùng paracetamol/acetaminophen nếu vừa uống rượu, uống rượu nhiều "
            "hoặc có bệnh gan; hỏi dược sĩ/bác sĩ và kiểm tra trùng hoạt chất."
        )
        precaution_guidance.insert(0, alcohol_caution)
        warning_text = alcohol_caution + " " + warning_text
    # Gắng sức/nắng nóng: gộp notes (vòng 4) + ngữ cảnh LLM (vòng 5).
    _llm_exertion_text = llm_context_text(_llm_context, "exertion_heat") if _llm_context is not None else ""
    exertion_heat = has_exertion_heat_context(notes) or has_exertion_heat_context(_llm_exertion_text)
    if exertion_heat and has_headache_nausea_or_dizzy(active_symptoms, notes):
        extend_unique(care_guidance, [
            "Nghỉ ở nơi mát, uống từng ngụm nước/oresol nếu ra nhiều mồ hôi; theo dõi dấu mất nước "
            "(khát nhiều, tiểu ít, chóng mặt).",
        ])
        extend_unique(precaution_guidance, [
            "Đi khám/cấp cứu nếu lơ mơ, ngất, sốt cao, co giật, nôn liên tục, đau đầu dữ dội hoặc "
            "đau ngực/khó thở.",
        ])

    # Vòng 6: output trọng tâm — 1 nhóm + 2-3 hoạt chất sạch + lý do.
    representative_ingredients = (
        representative_active_ingredients_for_group(prediction)
        if (LABEL_TYPE == "drug_group" and not needs_more_input)
        else []
    )
    reason_text = "" if needs_more_input else prediction_reason(
        matched_symptom_labels, confidence, score_type, prediction
    )

    return jsonify(
        {
            "case_summary": summary,
            "disease": prediction,
            "disease_vi": predicted_label_vi(prediction),
            "display_title": display_title_for_prediction(prediction, needs_more_input),
            "representative_active_ingredients": representative_ingredients,
            "reason": reason_text,
            "confidence": confidence,
            "top_gap": top_gap,
            "input_used": input_used,
            "score_label": SCORE_LABEL,
            "score_type": score_type,
            "label_type": LABEL_TYPE,
            "needs_more_input": needs_more_input,
            "quality_message": quality_message,
            "unsupported_symptoms": unsupported_symptoms,
            "matched_symptoms": matched_symptoms,
            "matched_symptoms_en": matched_symptoms,
            "matched_symptom_labels": matched_symptom_labels,
            "matched_symptoms_vi": matched_symptom_labels,
            "preprocessed_symptoms": [
                {"id": symptom, "label_en": symptom.replace("_", " ").replace("  ", " "), "label_vi": symptom_label_vi(symptom)}
                for symptom in sorted(active_symptoms)
            ],
            "description": description_text,
            "description_en": description,
            "medications": treatment_guidance[:6],
            "medications_en": treatment_guidance[:6],
            # Vòng 6: KHÔNG đổ dump dữ liệu thô ra output chính. Giữ field nhỏ cho debug/tương thích.
            "raw_dataset_treatment_debug": (
                translate_items(references["medications"].get(prediction, []))[:3]
                if LABEL_TYPE != "drug_group"
                else references["medications"].get(prediction, [])[:3]
            ),
            "diets": care_guidance[:10],
            "diets_en": care_guidance[:10],
            "precautions": precaution_guidance[:10],
            "precautions_en": precaution_guidance[:10],
            "workouts": [],
            "workouts_en": references["workouts"].get(prediction, []),
            "warning": warning_text,
            "guidance_source": guidance["guidance_source"],
            "suggested_symptoms": suggested_symptoms_for_more_info(active_symptoms) if needs_more_input else [],
            "top_predictions": probabilities,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    # 0.0.0.0 bat buoc tren Render/container de proxy ben ngoai truy cap duoc.
    app.run(host="0.0.0.0", port=port, debug=False)
