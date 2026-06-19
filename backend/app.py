import ast
import csv
import io
import json
import os
import re
import secrets
import unicodedata
import zipfile
import jwt
import datetime
from collections import Counter
from datetime import datetime, timedelta, timezone
from itertools import permutations
from pathlib import Path

import joblib
from models import db, User, NhomThuoc, Thuoc
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from translations import (
    disease_description_vi,
    disease_name_vi,
    translate_items,
)
from route_bulk_import import bulk_import_bp


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
MODEL_DIR = Path(os.environ.get("MODEL_DIR", PROJECT_ROOT / "models"))
MODEL_PATH = MODEL_DIR / "disease_model.joblib"
METADATA_PATH = MODEL_DIR / "metadata.json"
DATA_SOURCE = Path(os.environ.get("DATA_SOURCE", PROJECT_ROOT / "data" / "train_ready_mapped_drug_groups.csv"))
DATA_ARCHIVE = Path(os.environ.get("DATA_ARCHIVE", DATA_SOURCE))
GUIDANCE_PATH = Path(os.environ.get("GUIDANCE_PATH", PROJECT_ROOT / "data" / "disease_guidance.json"))
USERS_PATH = Path(os.environ.get("USERS_PATH", PROJECT_ROOT / "data" / "users.json"))
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
app.config['SECRET_KEY'] = 'dev_key_bi_mat'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pharma_predict.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 3. Khởi tạo Database và tạo bảng
db.init_app(app)

with app.app_context():
    db.create_all()
    print("Database đã sẵn sàng!")

# Đăng ký blueprint cho bulk import
app.register_blueprint(bulk_import_bp)

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
ALLOWED_STATIC_FILES = {"index.html", "styles.css", "script.js"}
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


def load_user_store() -> dict:
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
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = USERS_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(USERS_PATH)


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

DRUG_GROUP_GUIDANCE = {
    "thuốc điều trị sốt rét": {
        "treatment": [
            "Hướng xử trí tham khảo: sốt thành cơn kèm rét run sau khi tới vùng lưu hành sốt rét cần được XÉT NGHIỆM (lam máu/test nhanh) để chẩn đoán; KHÔNG tự mua thuốc điều trị sốt rét.",
            "Thuốc điều trị sốt rét phải do bác sĩ chỉ định đúng loại/liều theo chủng ký sinh trùng; tự dùng có thể nguy hiểm và gây kháng thuốc.",
        ],
        "precautions": [
            "Đi khám sớm; sốt rét có thể diễn tiến nặng (sốt rét ác tính) nếu chậm điều trị. Báo bác sĩ nơi đã đi, số ngày sốt, tính chất cơn sốt.",
        ],
        "care": [
            "Bù nước, hạ sốt cơ học, theo dõi tri giác và các dấu hiệu nặng (lơ mơ, vàng da, tiểu ít, co giật) để đi cấp cứu kịp thời.",
        ],
        "warning": "Đây chỉ là gợi ý hướng bệnh, KHÔNG phải đơn thuốc. Nghi sốt rét cần đi khám và xét nghiệm máu sớm; không tự dùng thuốc điều trị sốt rét. Đến cơ sở y tế ngay nếu sốt cao liên tục, lơ mơ, vàng da, tiểu ít hoặc co giật.",
    },
    "vitamin và khoáng chất": {
        "treatment": [
            "Hướng xử trí tham khảo: mệt mỏi kèm da/niêm nhợt và móng giòn gợi ý thiếu máu/thiếu vi chất; cần XÉT NGHIỆM MÁU để xác định nguyên nhân (thiếu sắt, B12/folate, mất máu...) trước khi bổ sung.",
            "Không tự ý bổ sung sắt/vitamin liều cao kéo dài khi chưa rõ nguyên nhân; bổ sung sai loại có thể che lấp bệnh nền.",
        ],
        "precautions": [
            "Đi khám nếu mệt nhiều, khó thở, tim đập nhanh, ngất, phân đen hoặc kinh nguyệt ra nhiều — có thể là thiếu máu nặng hoặc đang mất máu cần xử trí.",
        ],
        "care": [
            "Ăn uống đủ chất (thịt đỏ, rau xanh đậm, đậu), theo dõi mức độ mệt/chóng mặt và ghi lại để cung cấp khi đi khám.",
        ],
        "warning": "Đây chỉ là gợi ý hướng bệnh, KHÔNG phải đơn thuốc. Nghi thiếu máu cần đi khám và xét nghiệm máu để tìm nguyên nhân; không tự bổ sung sắt/vitamin liều cao khi chưa rõ nguyên nhân. Đi khám ngay nếu mệt nhiều, khó thở, ngất hoặc có dấu hiệu mất máu.",
    },
    "thuốc kháng viêm không steroid": {
        "treatment": [
            "Hướng xử trí tham khảo: nhóm thuốc kháng viêm không steroid thường chỉ phù hợp khi có đau/viêm rõ và cần loại trừ nguy cơ dạ dày, thận, tim mạch hoặc thuốc chống đông.",
            "Không tự phối nhiều thuốc giảm đau/kháng viêm cùng lúc; kiểm tra hoạt chất trùng lặp trong thuốc cảm, thuốc đau đầu hoặc thuốc xương khớp.",
        ],
        "precautions": [
            "Tránh tự dùng nếu từng loét/xuất huyết dạ dày, bệnh thận, bệnh tim mạch nặng, đang dùng thuốc chống đông/kháng tiểu cầu, đang mang thai hoặc dị ứng NSAID.",
        ],
        "care": [
            "Nghỉ ngơi, uống đủ nước, theo dõi mức độ đau, yếu tố khởi phát và các dấu hiệu đi kèm như sốt, nôn, nhìn mờ, yếu liệt.",
        ],
    },
    "thuốc giảm đau hạ sốt": {
        "treatment": [
            "Hướng xử trí tham khảo: nhóm giảm đau - hạ sốt có thể được cân nhắc cho đau/sốt nhẹ, nhưng cần kiểm tra bệnh gan, uống rượu nhiều hoặc thuốc đang dùng.",
            "Không dùng nhiều sản phẩm cùng chứa hoạt chất giảm đau/hạ sốt để tránh quá liều ngoài ý muốn.",
        ],
        "precautions": [
            "Đi khám nếu sốt cao kéo dài, đau dữ dội, phát ban, cứng cổ, lơ mơ, khó thở hoặc triệu chứng nặng lên nhanh.",
        ],
        "care": [
            "Nghỉ ở nơi yên tĩnh, bù nước, theo dõi nhiệt độ và ghi lại thời điểm dùng thuốc nếu có dùng.",
        ],
    },
    "thuốc kháng histamin": {
        "treatment": [
            "Hướng xử trí tham khảo: khi hắt hơi, sổ mũi/nghẹt mũi và không sốt, hệ thống ưu tiên hướng viêm mũi dị ứng hoặc cảm lạnh không sốt thay vì thuốc hạ sốt.",
            "Nhóm kháng histamin thường phù hợp hơn với hắt hơi, sổ mũi, ngứa, nổi mề đay hoặc chảy nước mắt; nếu nghẹt mũi là triệu chứng chính, cần cân nhắc thêm chăm sóc/xịt rửa mũi hoặc nhóm thông mũi theo tư vấn dược sĩ/bác sĩ.",
        ],
        "precautions": [
            "Một số thuốc kháng histamin có thể gây buồn ngủ, chóng mặt; tránh lái xe, uống rượu hoặc phối với thuốc an thần khi chưa được tư vấn.",
            "Không tự phối nhiều thuốc cảm/dị ứng cùng lúc vì có thể trùng hoạt chất kháng histamin hoặc thông mũi.",
        ],
        "care": [
            "Tránh tác nhân nghi dị ứng, rửa mũi bằng nước muối sinh lý nếu nghẹt/sổ mũi, theo dõi phát ban hoặc khó thở.",
        ],
    },
    "thuốc thần kinh/tâm thần": {
        "treatment": [
            "Hướng xử trí tham khảo: nhóm thuốc thần kinh/tâm thần cần bác sĩ đánh giá trực tiếp, không tự dùng theo mô tả triệu chứng.",
        ],
        "precautions": [
            "Đi khám sớm nếu mất ngủ kéo dài, lo âu nặng, ý nghĩ tự hại, lú lẫn, co giật, yếu/liệt hoặc đau đầu bất thường.",
        ],
        "care": [
            "Giữ lịch ngủ đều, tránh caffeine/rượu trước khi ngủ, ghi lại thời gian mất ngủ và yếu tố kích hoạt.",
        ],
    },
    "bù dịch và điện giải": {
        "treatment": [
            "Hướng xử trí tham khảo: ưu tiên bù nước và điện giải khi có tiêu chảy, nôn, sốt hoặc dấu hiệu mất nước.",
        ],
        "precautions": [
            "Đi khám nếu nôn không kiểm soát, tiểu ít, khát nhiều, lừ đừ, phân máu, đau bụng dữ dội hoặc người bệnh là trẻ nhỏ/người già.",
        ],
        "care": [
            "Uống từng ngụm nhỏ, ăn nhẹ, tránh rượu bia và theo dõi lượng nước tiểu.",
        ],
    },
    "thuốc chống nôn": {
        "treatment": [
            "Hướng xử trí tham khảo: nếu buồn nôn/nôn, ưu tiên bù nước từng ngụm nhỏ và theo dõi dấu hiệu mất nước.",
            "Nhóm thuốc chống nôn chỉ nên dùng theo tư vấn bác sĩ/dược sĩ, đặc biệt ở trẻ em, người già, phụ nữ mang thai hoặc người có bệnh tim mạch.",
        ],
        "precautions": [
            "Đi khám nếu nôn liên tục, không uống được nước, đau bụng dữ dội, lừ đừ, sốt cao, phân máu hoặc dấu hiệu mất nước.",
        ],
        "care": [
            "Ăn nhẹ, chia nhỏ bữa, tránh rượu bia và thức ăn nhiều dầu mỡ trong giai đoạn còn nôn/buồn nôn.",
        ],
    },
    "thuốc điều trị dạ dày": {
        "treatment": [
            "Hướng xử trí tham khảo: đau thượng vị/ợ chua/nóng rát dạ dày có thể liên quan rối loạn dạ dày - trào ngược; cần đánh giá thêm bữa ăn, thuốc đang dùng và dấu hiệu cảnh báo.",
        ],
        "precautions": [
            "Đi khám nếu đau bụng dữ dội, nôn ra máu, đi ngoài phân đen, sụt cân, nuốt nghẹn hoặc đau kéo dài/tái diễn.",
        ],
        "care": [
            "Ăn nhẹ, tránh rượu bia, cà phê, đồ cay/chua nhiều và không nằm ngay sau ăn.",
        ],
    },
    "thuốc long đờm / giảm ho": {
        "treatment": [
            "Hướng xử trí tham khảo: nếu ho có đờm, ưu tiên uống đủ nước, làm ẩm không khí và chỉ cân nhắc nhóm long đờm/giảm ho theo tư vấn dược sĩ hoặc bác sĩ.",
            "Không tự phối nhiều thuốc ho/cảm cùng lúc vì dễ trùng hoạt chất hoặc làm nặng buồn ngủ, chóng mặt.",
        ],
        "precautions": [
            "Không tự dùng thuốc ức chế ho nếu ho có nhiều đờm, khó thở, đau ngực, sốt cao hoặc nghi nhiễm trùng hô hấp dưới.",
        ],
        "care": [
            "Theo dõi màu đờm, lượng đờm, sốt, khó thở và thời gian ho kéo dài.",
        ],
    },
    "thuốc giảm đau nha khoa": {
        "treatment": [
            "Hướng xử trí tham khảo: đau răng/sưng nướu thường cần khám nha khoa để tìm nguyên nhân như sâu răng, viêm nướu hoặc áp-xe răng.",
            "Có thể cân nhắc nhóm giảm đau thông thường theo tư vấn dược sĩ/bác sĩ; không tự dùng kháng sinh nếu chưa được chỉ định.",
        ],
        "precautions": [
            "Không chườm nóng vùng sưng, không tự chích/rạch nướu và không tự dùng kháng sinh còn dư.",
            "Đi khám nha khoa sớm nếu sưng nướu/mặt, đau tăng, khó há miệng, sốt, hôi miệng nặng hoặc nuốt/ thở khó.",
        ],
        "care": [
            "Súc miệng nhẹ bằng nước ấm, vệ sinh răng miệng, tránh nhai bên đau và tránh thức ăn quá nóng/lạnh/ngọt nếu làm đau tăng.",
        ],
        "warning": "Đau răng kèm sưng nướu cần khám nha khoa để xử lý nguyên nhân. Đi khám sớm nếu sưng mặt, sốt, chảy mủ, khó há miệng, nuốt khó, thở khó hoặc đau tăng nhanh.",
    },
}

RULE_MEDICATION_NAMES = {
    "thuốc giảm đau hạ sốt": "Acetaminophen/Paracetamol; Ibuprofen (tham khảo, cần kiểm tra chống chỉ định)",
    "thuốc long đờm / giảm ho": "Thuốc long đờm hoặc giảm ho phù hợp loại ho (cần dược sĩ/bác sĩ tư vấn)",
    "bù dịch và điện giải": "Dung dịch bù nước điện giải; Oral rehydration salts (ORS)",
    "thuốc chống nôn": "Thuốc chống nôn theo chỉ định/tư vấn y tế",
    "thuốc điều trị dạ dày": "Thuốc dạ dày/kháng acid theo tư vấn y tế",
    "thuốc giảm đau nha khoa": "Thuốc giảm đau thông thường theo tư vấn; cần khám nha khoa để xử lý nguyên nhân",
}

DIAGNOSIS_VI = {
    "injury to the leg": "Chấn thương/viêm vùng chân (tham khảo)",
    "otitis media": "Viêm tai giữa (tham khảo)",
    "dental caries": "Sâu răng (tham khảo)",
    "gum disease": "Bệnh nướu/viêm nướu (tham khảo)",
}

VI_SYMPTOM_KEYWORDS = {
    "itching": ["ngứa", "ngứa da"],
    "skin_rash": ["phát ban", "nổi ban", "mẩn đỏ", "nổi mẩn", "ban đỏ"],
    "nodal_skin_eruptions": ["nổi nốt trên da", "sẩn da", "nốt da"],
    "continuous_sneezing": ["hắt hơi", "hắt hơi liên tục", "nhảy mũi", "nhảy mũi liên tục"],
    "shivering": ["run rẩy", "rét run", "run lạnh"],
    "chills": ["ớn lạnh", "lạnh run", "rét"],
    "joint_pain": ["đau khớp", "nhức khớp"],
    "stomach_pain": ["đau dạ dày", "đau bao tử", "đau thượng vị"],
    "acidity": ["ợ chua", "trào ngược", "nóng rát dạ dày"],
    "ulcers_on_tongue": ["loét lưỡi", "lở lưỡi"],
    "muscle_wasting": ["teo cơ", "mất cơ"],
    "vomiting": ["nôn", "nôn ói", "buồn nôn và nôn"],
    "burning_micturition": ["tiểu buốt", "tiểu rát", "đái buốt"],
    "spotting_ urination": ["tiểu lắt nhắt", "đái rắt", "tiểu rắt", "tiểu nhắt"],
    "fatigue": ["mệt mỏi", "mệt", "đuối sức"],
    "weight_gain": ["tăng cân"],
    "anxiety": ["lo âu", "bồn chồn", "hồi hộp lo lắng"],
    "cold_hands_and_feets": ["tay chân lạnh", "bàn tay lạnh", "bàn chân lạnh"],
    "mood_swings": ["thay đổi tâm trạng", "tâm trạng thất thường"],
    "weight_loss": ["sụt cân", "giảm cân"],
    "restlessness": ["bứt rứt", "không yên"],
    "lethargy": ["lừ đừ", "uể oải", "li bì nhẹ"],
    "patches_in_throat": ["mảng trong họng", "đốm trong họng"],
    "irregular_sugar_level": ["đường huyết bất thường", "đường máu bất thường"],
    "cough": ["ho", "ho khan", "ho nhiều"],
    "high_fever": ["sốt cao", "sốt 39", "sốt 40", "sốt trên 39"],
    "mild_fever": ["sốt nhẹ", "sốt 37", "sốt 38"],
    "sunken_eyes": ["mắt trũng"],
    "breathlessness": ["khó thở", "hụt hơi", "thở gấp"],
    "sweating": ["đổ mồ hôi", "vã mồ hôi"],
    "dehydration": ["mất nước", "khô môi", "khát nước nhiều"],
    "indigestion": ["khó tiêu", "đầy bụng"],
    "headache": ["đau đầu", "nhức đầu"],
    "yellowish_skin": ["vàng da"],
    "dark_urine": ["nước tiểu sẫm", "tiểu sẫm màu", "nước tiểu đậm"],
    "nausea": ["buồn nôn", "nôn nao"],
    "loss_of_appetite": ["chán ăn", "ăn kém"],
    "pain_behind_the_eyes": ["đau sau mắt", "đau hốc mắt"],
    "back_pain": ["đau lưng"],
    "constipation": ["táo bón", "không đi cầu được", "không đi đại tiện được", "khó đi đại tiện",
                     "phân khô cứng", "phân cứng", "rặn khó", "nhiều ngày không đi ngoài", "mấy ngày không đi cầu"],
    "abdominal_pain": ["đau bụng", "bụng đau", "đau vùng bụng", "đau quặn bụng", "bụng đau quặn"],
    "diarrhoea": ["tiêu chảy", "đi ngoài phân lỏng", "đi ngoài lỏng", "đi phân lỏng"],
    "yellow_urine": ["nước tiểu vàng", "tiểu vàng"],
    "yellowing_of_eyes": ["vàng mắt", "mắt vàng"],
    "acute_liver_failure": ["suy gan cấp"],
    "fluid_overload": ["quá tải dịch", "ứ dịch"],
    "fluid_overload.1": ["quá tải dịch", "ứ dịch"],
    "swelling_of_stomach": ["bụng sưng", "bụng chướng"],
    "swelled_lymph_nodes": ["sưng hạch", "nổi hạch"],
    "malaise": ["khó chịu", "mệt lả"],
    "blurred_and_distorted_vision": ["nhìn mờ", "mờ mắt"],
    "phlegm": ["đờm", "có đờm", "ho đờm"],
    "throat_irritation": ["rát họng", "ngứa họng"],
    "sore throat": ["đau họng", "rát họng", "viêm họng"],
    "throat pain": ["đau họng"],
    "pain in the throat": ["đau họng"],
    "dry sore throat": ["khô họng", "đau họng khô"],
    "severe throat pain": ["đau họng nặng", "đau họng dữ dội"],
    "significant throat pain": ["đau họng nhiều"],
    "throat discomfort": ["khó chịu họng"],
    "irritation in the throat": ["rát họng", "ngứa họng"],
    "itching in the throat": ["ngứa họng"],
    "itchy throat": ["ngứa họng"],
    "redness_of_eyes": ["đỏ mắt", "mắt đỏ"],
    "sinus_pressure": ["đau xoang", "tức xoang"],
    "runny_nose": ["sổ mũi", "chảy nước mũi"],
    "congestion": ["nghẹt mũi", "tắc mũi"],
    "chest_pain": ["đau ngực", "tức ngực"],
    "weakness_in_limbs": ["yếu tay chân", "yếu chi"],
    "fast_heart_rate": ["tim đập nhanh", "mạch nhanh"],
    "pain_during_bowel_movements": ["đau khi đi ngoài", "đau khi đại tiện"],
    "pain_in_anal_region": ["đau hậu môn"],
    "bloody_stool": ["đi ngoài ra máu", "phân máu"],
    "irritation_in_anus": ["ngứa hậu môn", "kích ứng hậu môn"],
    "neck_pain": ["đau cổ", "đau gáy"],
    "dizziness": ["chóng mặt", "hoa mắt", "choáng", "choáng váng"],
    "cramps": ["chuột rút", "co rút cơ"],
    "bruising": ["bầm tím", "vết bầm"],
    "obesity": ["béo phì", "thừa cân"],
    "swollen_legs": ["sưng chân", "phù chân"],
    "swollen_blood_vessels": ["mạch máu sưng", "tĩnh mạch sưng"],
    "puffy_face_and_eyes": ["mặt phù", "mắt phù", "sưng mặt"],
    "enlarged_thyroid": ["bướu cổ", "tuyến giáp to"],
    "brittle_nails": ["móng giòn", "móng dễ gãy", "móng tay giòn", "móng tay dễ gãy", "móng giòn dễ gãy", "móng tay giòn dễ gãy"],
    "swollen_extremeties": ["sưng tay chân", "phù chi"],
    "excessive_hunger": ["đói nhiều", "ăn nhiều"],
    "extra_marital_contacts": ["quan hệ ngoài luồng", "quan hệ tình dục nguy cơ"],
    "drying_and_tingling_lips": ["khô môi", "tê môi"],
    "slurred_speech": ["nói khó", "nói líu", "nói đớ"],
    "knee_pain": ["đau gối", "đau khớp gối"],
    "hip_joint_pain": ["đau khớp háng", "đau hông"],
    "muscle_weakness": ["yếu cơ"],
    "stiff_neck": ["cứng cổ", "cứng gáy"],
    "swelling_joints": ["sưng khớp"],
    "movement_stiffness": ["cứng khi vận động", "cứng vận động"],
    "spinning_movements": ["chóng mặt xoay", "cảm giác quay cuồng"],
    "loss_of_balance": ["mất thăng bằng"],
    "unsteadiness": ["đi không vững", "loạng choạng"],
    "weakness_of_one_body_side": ["yếu nửa người", "liệt nửa người"],
    "loss_of_smell": ["mất khứu giác", "mất mùi"],
    "bladder_discomfort": ["khó chịu bàng quang", "đau bàng quang"],
    "foul_smell_of urine": ["nước tiểu hôi", "tiểu hôi"],
    "continuous_feel_of_urine": ["cảm giác muốn tiểu liên tục", "mắc tiểu liên tục"],
    "passage_of_gases": ["xì hơi nhiều", "đầy hơi"],
    "internal_itching": ["ngứa bên trong"],
    "toxic_look_(typhos)": ["vẻ nhiễm độc", "nhiễm độc"],
    "depression": ["trầm cảm", "buồn bã kéo dài"],
    "irritability": ["dễ cáu", "cáu gắt"],
    "muscle_pain": ["đau cơ", "nhức mỏi cơ"],
    "altered_sensorium": ["rối loạn ý thức", "lơ mơ"],
    "red_spots_over_body": ["đốm đỏ toàn thân", "chấm đỏ trên da"],
    "belly_pain": ["đau bụng dưới"],
    "abnormal_menstruation": ["kinh nguyệt bất thường", "rối loạn kinh nguyệt"],
    "dischromic _patches": ["mảng đổi màu da", "da đổi màu"],
    "dischromic patches": ["mảng đổi màu da", "da đổi màu"],
    "watering_from_eyes": ["chảy nước mắt", "mắt chảy nước"],
    "increased_appetite": ["tăng cảm giác thèm ăn", "ăn nhiều"],
    "polyuria": ["tiểu nhiều", "đái nhiều"],
    "family_history": ["tiền sử gia đình"],
    "mucoid_sputum": ["đờm nhầy", "đàm nhầy"],
    "rusty_sputum": ["đờm màu gỉ sắt", "đàm gỉ sắt"],
    "lack_of_concentration": ["kém tập trung", "giảm tập trung"],
    "visual_disturbances": ["rối loạn thị giác", "nhìn bất thường", "sợ ánh sáng", "nhạy cảm ánh sáng", "sợ tiếng ồn", "nhạy cảm tiếng ồn"],
    "receiving_blood_transfusion": ["truyền máu"],
    "receiving_unsterile_injections": ["tiêm không vô trùng", "tiêm bẩn"],
    "coma": ["hôn mê"],
    "stomach_bleeding": ["xuất huyết dạ dày", "chảy máu dạ dày"],
    "distention_of_abdomen": ["chướng bụng", "bụng căng"],
    "history_of_alcohol_consumption": ["uống rượu", "nghiện rượu", "tiền sử rượu"],
    "blood_in_sputum": ["ho ra máu", "đờm có máu"],
    "prominent_veins_on_calf": ["tĩnh mạch nổi ở bắp chân", "gân xanh bắp chân"],
    "palpitations": ["đánh trống ngực", "hồi hộp"],
    "painful_walking": ["đau khi đi bộ", "đi lại đau"],
    "pus_filled_pimples": ["mụn mủ"],
    "blackheads": ["mụn đầu đen"],
    "scurring": ["sẹo", "sẹo mụn"],
    "skin_peeling": ["bong tróc da", "da bong tróc", "tróc da", "da tróc"],
    "silver_like_dusting": ["vảy bạc", "vảy trắng bạc"],
    "small_dents_in_nails": ["lõm móng", "rỗ móng"],
    "inflammatory_nails": ["viêm móng"],
    "blister": ["mụn nước", "bọng nước"],
    "red_sore_around_nose": ["loét đỏ quanh mũi", "đỏ đau quanh mũi"],
    "yellow_crust_ooze": ["chảy dịch vàng", "đóng vảy vàng"],
    "fever": ["sốt"],
    "insomnia": ["mất ngủ", "khó ngủ", "ngủ không được", "ngủ kém", "trằn trọc", "thức giấc nhiều"],
    "toothache": ["đau răng", "nhức răng", "răng đau"],
    "gum pain": ["đau nướu", "đau lợi", "nướu đau", "lợi đau"],
    "pain in gums": ["đau nướu", "đau lợi", "nướu đau", "lợi đau"],
    "jaw swelling": ["sưng hàm", "sưng vùng hàm", "sưng mặt do răng"],
    "bleeding gums": ["chảy máu nướu", "chảy máu lợi", "nướu chảy máu", "lợi chảy máu"],
    # Bổ sung 2026-06-08: tăng độ phủ hô hấp / tiêu hóa / tiết niệu (feature có thật trong model)
    "wheezing": ["khò khè", "thở rít", "thở khò khè"],
    "chest tightness": ["tức ngực", "nặng ngực", "đè nặng ngực"],
    "heartburn": ["ợ nóng", "nóng rát thượng vị", "nóng rát sau xương ức"],
    "melena": ["phân đen", "đi ngoài phân đen", "phân hắc ín"],
    "vomiting blood": ["nôn ra máu", "ói ra máu", "nôn ra máu tươi"],
    "painful urination": ["tiểu đau", "đau khi đi tiểu", "đau khi tiểu"],
    "retention of urine": ["bí tiểu", "không tiểu được"],
    "low urine output": ["tiểu ít", "lượng nước tiểu ít"],
    "frontal headache": ["đau đầu vùng trán", "đau trán"],
}

# Bổ sung 2026-06-09 (robust hoá tiếng Việt): các cụm tiếng Việt phổ biến còn thiếu,
# map sang feature CÓ THẬT trong model. Merge để không trùng/đè key cũ.
_VI_SYMPTOM_KEYWORDS_EXTRA = {
    "headache": ["đau nửa đầu", "đau nửa đầu từng cơn", "nhức nửa đầu", "nhức một bên đầu",
                 "đau nhức nửa đầu", "nhức đầu theo nhịp mạch", "đau đầu theo nhịp mạch"],
    "stomach_pain": ["đau thượng vị lúc đói", "đau vùng thượng vị"],
    "heartburn": ["nóng rát thượng vị", "nóng rát vùng thượng vị", "ợ nóng"],
    "acidity": ["hay ợ chua", "ợ hơi"],
    "vomiting": ["nôn nhiều", "nôn nhiều lần", "nôn liên tục"],
    "diarrhoea": ["đi ngoài liên tục", "đi ngoài cả ngày", "đi ngoài nhiều lần", "đi ngoài phân lỏng nước",
                  "đi ngoài tóe nước", "tiêu chảy tóe nước", "đi ngoài nhiều nước", "đi ngoài như nước", "tiêu chảy nhiều lần"],
    "dehydration": ["khát nước nhiều", "khát nhiều"],
    "neck_pain": ["đau vai gáy", "đau cổ gáy", "nhức vai gáy"],
    "back_pain": ["đau lưng dưới", "đau thắt lưng"],
    "painful menstruation": ["đau bụng kinh", "đau bụng kinh dữ dội", "đau quặn kỳ kinh", "thống kinh"],
    "skin_rash": ["mề đay", "nổi mề đay", "mẩn ngứa"],
    "itching": ["ngứa khắp người", "ngứa nhiều"],
    "dischromic patches": ["mảng đỏ hình tròn", "mảng đỏ tròn"],
    "skin_peeling": ["bong vảy", "bong vảy dày", "bong tróc vảy"],
    "blister": ["mụn nước thành chùm", "nổi bóng nước", "bóng nước"],
    "sinus_pressure": ["đau nhức xoang", "đau xoang má", "nhức xoang"],
    "wheezing": ["khò khè khi gắng sức", "thở khò khè"],
    "breathlessness": ["lên cơn khó thở", "khó thở khi gắng sức", "khó thở khi gặp lạnh"],
    "enlarged_thyroid": ["bướu cổ to", "bướu giáp", "cổ to", "cổ phình", "cổ bạnh", "mắt lồi", "lồi mắt"],
    "excessive_urination_at_night": ["tiểu đêm", "tiểu đêm nhiều lần"],
    "excessive_hunger": ["đói nhiều"],
    "chills": ["rét run", "sốt thành cơn"],
    "sweating": ["vã mồ hôi", "ra nhiều mồ hôi", "đổ mồ hôi nhiều"],
    "bloody_stool": ["phân có máu", "đi ngoài ra máu", "đi ngoài máu nhầy", "phân máu nhầy"],
    # An toàn / thần kinh:
    "seizures": ["co giật", "co giật sùi bọt mép", "lên cơn co giật"],
    "altered_sensorium": ["mất ý thức", "lơ mơ", "rối loạn ý thức", "lú lẫn"],
    "stiff_neck": ["cổ cứng", "gáy cứng"],
    "weakness_of_one_body_side": ["méo miệng", "yếu một bên", "yếu nửa người", "liệt nửa người",
                                   "tay chân một bên yếu", "liệt một bên", "yếu hẳn một bên người", "tê yếu một bên"],
    "slurred_speech": ["nói ngọng", "nói khó", "líu lưỡi"],
    "paresthesia": ["tê bì", "châm chích", "tê rần"],
    "muscle_pain": ["đau mỏi toàn thân", "đau nhức toàn thân", "đau người", "đau mỏi người"],
    "Redness, swelling, discharge from the wound": ["chảy mủ", "vết thương chảy mủ", "vết thương sưng đỏ", "mưng mủ", "có mủ"],
    "Shooting or burning pain, tingling or numbness": ["đau rát bỏng lan dọc dây thần kinh", "đau lan dọc dây thần kinh", "đau rát bỏng lan"],
    # Batch 3: cơ-xương-khớp / lo âu / tim mạch
    "joint_pain": ["khớp sưng đau", "sưng đau khớp", "viêm khớp", "viêm gân", "đau gân", "ngón chân sưng đau", "sưng đỏ đau khớp"],
    "anxiety": ["sợ hãi vô cớ", "hoảng sợ", "lo lắng quá mức", "căng thẳng", "lo âu kéo dài"],
    "chest_pain": ["đau thắt ngực", "đau ngực khi gắng sức", "đau ngực bóp nghẹt"],
    "palpitations": ["tim đập nhanh", "tim đập mạnh", "tim đập không đều", "loạn nhịp", "trống ngực"],
    "High blood pressure, chest pain or discomfort, shortness of breath, fatigue":
        ["huyết áp cao", "cao huyết áp", "tăng huyết áp", "huyết áp 160", "huyết áp lên cao"],
}
for _k, _v in _VI_SYMPTOM_KEYWORDS_EXTRA.items():
    VI_SYMPTOM_KEYWORDS[_k] = list(dict.fromkeys(VI_SYMPTOM_KEYWORDS.get(_k, []) + _v))

UNSUPPORTED_SYMPTOM_KEYWORDS = {
    "sleep_problem": {
        "label_vi": "Mất ngủ/khó ngủ",
        "phrases": [
            "mất ngủ",
            "khó ngủ",
            "ngủ không được",
            "ngủ kém",
            "trằn trọc",
            "thức giấc nhiều",
        ],
    }
}


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


AUTO_EXACT_SYMPTOM_KEYWORDS = {
    "chest tightness": ["tức ngực", "nặng ngực", "căng tức ngực"],
    "diarrhea": ["tiêu chảy", "đi ngoài phân lỏng"],
    "difficulty breathing": ["khó thở", "thở khó", "hụt hơi"],
    "shortness of breath": ["khó thở", "hụt hơi"],
    "breathing fast": ["thở nhanh"],
    "abnormal breathing sounds": ["tiếng thở bất thường", "khò khè"],
    "wheezing": ["khò khè", "thở rít"],
    "coughing up sputum": ["ho có đờm", "khạc đờm"],
    "coryza": ["sổ mũi", "chảy nước mũi"],
    "hoarse voice": ["khàn tiếng"],
    "difficulty in swallowing": ["khó nuốt", "nuốt khó"],
    "difficulty swallowing": ["khó nuốt", "nuốt khó"],
    "heartburn": ["ợ nóng", "nóng rát sau xương ức"],
    "acidic taste": ["vị chua trong miệng"],
    "decreased appetite": ["chán ăn", "ăn kém"],
    "excessive thirst": ["khát nhiều"],
    "frequent urination": ["tiểu nhiều", "đi tiểu thường xuyên"],
    "blood in urine": ["tiểu ra máu", "nước tiểu có máu"],
    "blood in stool": ["đi ngoài ra máu", "phân có máu", "phân nhầy máu", "phân có nhầy máu", "đi ngoài phân nhầy máu"],
    "changes in stool appearance": ["thay đổi tính chất phân", "phân bất thường"],
    "diminished hearing": ["giảm thính lực", "nghe kém"],
    "diminished vision": ["giảm thị lực", "nhìn kém"],
    "double vision": ["nhìn đôi"],
    "blindness": ["mù", "mất thị lực"],
    "eye redness": ["đỏ mắt", "mắt đỏ"],
    "foreign body sensation in eye": ["cộm mắt", "cảm giác dị vật trong mắt"],
    "fluid in ear": ["dịch trong tai", "chảy dịch tai"],
    "fainting": ["ngất", "xỉu"],
    "delusions or hallucinations": ["hoang tưởng", "ảo giác"],
    "disturbance of memory": ["rối loạn trí nhớ", "giảm trí nhớ"],
    "drug abuse": ["lạm dụng thuốc", "lạm dụng chất"],
    "abusing alcohol": ["lạm dụng rượu", "uống rượu nhiều"],
    "ache all over": ["đau nhức toàn thân", "đau mỏi toàn thân"],
    "allergic reaction": ["dị ứng", "phản ứng dị ứng"],
    "abnormal appearing skin": ["da bất thường", "bất thường trên da"],
    "abnormal involuntary movements": ["cử động không tự chủ", "vận động bất thường"],
    "abnormal movement of eyelid": ["mí mắt co giật", "cử động mí mắt bất thường"],
    "acne or pimples": ["mụn trứng cá", "mụn bọc", "mụn mủ"],
    "back cramps or spasms": ["co thắt lưng", "chuột rút lưng"],
    "blood clots during menstrual periods": ["máu cục khi hành kinh", "kinh nguyệt có máu cục"],
    "diaper rash": ["hăm tã"],
    "dischromic patches": ["mảng đổi màu da", "da đổi màu", "mảng trắng loang", "da loang màu", "loang da"],
    "easy bruising": ["dễ bầm tím", "dễ xuất hiện vết bầm"],
    "elevated intraocular pressure": ["tăng nhãn áp", "áp lực mắt tăng"],
    "excessive anger": ["dễ tức giận", "giận dữ quá mức"],
    "excessive body weight": ["thừa cân", "béo phì"],
    "excessive daytime sleepiness": ["buồn ngủ ban ngày nhiều", "ngủ gà ban ngày"],
    "excessive sweating": ["đổ mồ hôi nhiều", "tăng tiết mồ hôi"],
    "excessive urination at night": ["tiểu đêm nhiều", "đi tiểu nhiều ban đêm"],
    "excessive worrying": ["lo lắng quá mức", "lo âu nhiều"],
    "eyelid lesion or rash": ["tổn thương mí mắt", "phát ban mí mắt"],
    "feeling ill": ["cảm thấy mệt", "khó chịu trong người"],
    "flu-like syndrome": ["triệu chứng giống cúm", "hội chứng giống cúm"],
    "fluid retention": ["giữ nước", "ứ dịch", "phù"],
    "focal weakness": ["yếu khu trú", "yếu một vùng cơ thể"],
    "frontal headache": ["đau đầu vùng trán", "đau trán"],
    "hemoptysis": ["ho ra máu"],
    "hot flashes": ["bốc hỏa"],
    "foul smell of urine": ["nước tiểu hôi", "tiểu hôi"],
    "hurts to breath": ["đau khi thở", "thở đau"],
    "increased heart rate": ["tim đập nhanh", "mạch nhanh"],
    "infant feeding problem": ["trẻ bú kém", "vấn đề ăn bú ở trẻ"],
    "infertility": ["vô sinh", "hiếm muộn"],
    "intermenstrual bleeding": ["ra máu giữa kỳ kinh", "chảy máu giữa chu kỳ"],
    "involuntary urination": ["tiểu không tự chủ", "són tiểu"],
    "irregular heartbeat": ["nhịp tim không đều", "loạn nhịp"],
    "itchiness of eye": ["ngứa mắt"],
    "itching of skin": ["ngứa da"],
    "itching of the anus": ["ngứa hậu môn"],
    "itchy ear(s)": ["ngứa tai"],
    "itchy scalp": ["ngứa da đầu"],
    "jaundice": ["vàng da", "vàng mắt"],
    "lacrimation": ["chảy nước mắt"],
    "lip swelling": ["sưng môi"],
    "loss of sensation": ["mất cảm giác", "giảm cảm giác"],
    "low self-esteem": ["tự ti", "mặc cảm"],
    "low urine output": ["tiểu ít", "lượng nước tiểu ít"],
    "melena": ["đi ngoài phân đen", "phân đen"],
    "mouth ulcer": ["loét miệng", "lở miệng"],
}

AUTO_BODY_PARTS = {
    "abdomen": ["bụng"],
    "abdominal": ["bụng"],
    "belly": ["bụng"],
    "stomach": ["dạ dày"],
    "back": ["lưng"],
    "chest": ["ngực"],
    "ribcage": ["lồng ngực"],
    "head": ["đầu"],
    "ear": ["tai"],
    "eye": ["mắt"],
    "eyelid": ["mí mắt"],
    "face": ["mặt"],
    "facial": ["mặt"],
    "jaw": ["hàm"],
    "mouth": ["miệng"],
    "gum": ["nướu", "lợi"],
    "gums": ["nướu", "lợi"],
    "tooth": ["răng"],
    "throat": ["họng"],
    "neck": ["cổ", "gáy"],
    "arm": ["tay", "cánh tay"],
    "elbow": ["khuỷu tay"],
    "hand": ["bàn tay"],
    "finger": ["ngón tay"],
    "hip": ["hông"],
    "knee": ["gối"],
    "ankle": ["cổ chân", "mắt cá chân"],
    "foot": ["bàn chân"],
    "toe": ["ngón chân"],
    "leg": ["chân"],
    "shoulder": ["vai"],
    "breast": ["vú"],
    "pelvic": ["vùng chậu"],
    "groin": ["bẹn"],
    "flank": ["hông lưng"],
}


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
    has_rhinitis_pattern = has_any_symptom(active_symptoms, ["continuous sneezing", "coryza", "runny nose", "congestion", "watering from eyes"])

    if has_lower_airway_warning:
        return None
    if has_phlegm:
        return "thuốc long đờm / giảm ho"
    if has_rhinitis_pattern and not has_fever:
        return "thuốc kháng histamin"
    if has_fever:
        return "thuốc giảm đau hạ sốt"
    return None


def general_fever_pain_rule_drug_group(active_symptoms: set[str]) -> str | None:
    # Sốt kèm đau mỏi người, đau đầu hoặc đau khớp nhưng không có yếu tố dịch tễ vùng sốt rét
    has_fever = has_any_symptom(active_symptoms, ["fever", "mild fever", "high fever"])
    has_pain = has_any_symptom(active_symptoms, ["muscle_pain", "headache", "joint_pain", "back_pain"])
    if has_fever and has_pain:
        return "thuốc giảm đau hạ sốt"
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


def emergency_red_flag_from_notes(notes: str) -> str | None:
    """Dấu hiệu CẤP CỨU/khủng hoảng nhận từ mô tả thô (không phụ thuộc feature trích được).
    Trả về thông điệp cảnh báo nếu phát hiện; None nếu không. Ưu tiên AN TOÀN: thà cảnh báo thừa.
    """
    t = normalize(notes or "")
    def has(*ps): return any(p in t for p in ps)

    GO = " Đây có thể là CẤP CỨU; gọi 115 hoặc đến cơ sở y tế ngay, KHÔNG tự dùng thuốc theo gợi ý."

    # 1) Ý định tự tử / tự hại -> thông điệp hỗ trợ khủng hoảng (ưu tiên cao nhất)
    if has("tu tu", "tu sat", "muon chet", "ket thuc cuoc doi", "tu hai", "hai ban than",
           "cat tay cho", "khong muon song"):
        return ("Bạn đang mô tả ý định tự tử/tự hại. Bạn không đơn độc — hãy liên hệ NGAY người thân "
                "tin cậy hoặc đường dây hỗ trợ tâm lý (vd Ngày Mai 096 306 1414) hoặc gọi cấp cứu 115. "
                "Hệ thống này KHÔNG thay thế hỗ trợ y tế/khủng hoảng.")

    # 2) Ngộ độc / quá liều
    if has("ngo doc", "qua lieu", "uong nham", "thuoc tru sau", "uong thuoc sau", "uong nhieu thuoc",
           "uong hoa chat", "uong nham thuoc"):
        return "Nghi ngộ độc/quá liều." + GO

    # 3) Phản vệ / phù mạch (dị ứng nặng)
    angioedema = has("sung moi", "sung luoi", "phu moi", "phu luoi", "phu mat", "sung mat",
                     "hong nghen", "co hong nghen", "phu mach", "sung hong")
    allergic_trigger = has("an tom", "an hai san", "ong dot", "ong chich", "uong thuoc la", "sau khi tiem",
                           "noi me day", "man khap nguoi", "noi man khap")
    severe_resp_or_shock = has("kho tho", "tho rit", "tut huyet ap", "choang", "ngat")
    if (angioedema and severe_resp_or_shock) or (allergic_trigger and severe_resp_or_shock and angioedema) \
       or (allergic_trigger and has("tut huyet ap", "ngat", "soc")):
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

    # 9) Cấp cứu sản khoa: thai + chảy máu/đau bụng
    if has("mang thai", "co thai", "dang bau", "co bau", "thai ", "thai nhi", "bau "):
        if has("chay mau", "ra mau", "ra dich nau", "dau bung", "dau quan", "dau lung du doi"):
            return "Có thai kèm chảy máu/đau bụng — nguy cơ cấp cứu sản khoa (sảy thai/thai ngoài tử cung)." + GO

    # ── P0 (2026-06-15): bổ sung cờ đỏ còn lọt, đo bằng scripts/independent_probe.py.
    # Dùng affirmative_mention (aff) để phủ định "không sụt cân"/"không co giật"/"không tê"
    # KHÔNG kích hoạt cờ đỏ sai (P0.6 near-miss).
    SEE = " Hãy đi khám bác sĩ sớm để được đánh giá, KHÔNG tự dùng thuốc theo gợi ý."
    def aff(*ps): return affirmative_mention(t, ps)

    # 10) Đột quỵ (FAST): méo miệng / yếu-liệt nửa người / nói khó khởi phát đột ngột
    if aff("meo mieng", "lech mat", "lech mieng", "mieng meo",
           "yeu nua nguoi", "liet nua nguoi", "te nua nguoi", "yeu mot ben nguoi", "liet mot ben nguoi") \
       or (aff("noi kho", "noi ngong", "kho noi", "noi dap") and has("dot ngot")):
        return "Dấu hiệu nghi ĐỘT QUỴ (méo miệng, yếu/liệt nửa người, nói khó)." + GO

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
    GO = " Đây có thể là CẤP CỨU; gọi 115 hoặc đến cơ sở y tế ngay, KHÔNG tự dùng thuốc theo gợi ý."

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


# Admin-managed extra symptoms (file-backed) and dynamic symptoms endpoint
ADMIN_SYMPTOMS_PATH = PROJECT_ROOT / "data" / "admin_symptoms.json"


def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_\-]", "", s)
    return s or secrets.token_urlsafe(6)


def load_admin_symptoms() -> list:
    try:
        if ADMIN_SYMPTOMS_PATH.exists():
            return json.loads(ADMIN_SYMPTOMS_PATH.read_text(encoding="utf-8")) or []
    except Exception:
        pass
    return []


def save_admin_symptoms(items: list) -> None:
    ADMIN_SYMPTOMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ADMIN_SYMPTOMS_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


@app.route('/api/admin/symptoms', methods=['POST'])
def admin_add_symptom():
    data = request.get_json(silent=True) or {}
    label_vi = (data.get('label_vi') or data.get('label') or '').strip()
    label_en = (data.get('label_en') or data.get('label_en') or '').strip()
    note = (data.get('note') or data.get('note') or '').strip()
    if not label_vi or not label_en:
        return jsonify({"error": "Vui lòng cung cấp label_vi và label_en."}), 400
    admin = load_admin_symptoms()
    candidate_id = data.get('id') or slugify(label_en)
    # ensure unique id
    if any(str(a.get('id')) == str(candidate_id) for a in admin):
        candidate_id = f"{candidate_id}_{secrets.token_hex(3)}"
    item = {"id": candidate_id, "label_vi": label_vi, "label_en": label_en, "note": note}
    admin.append(item)
    save_admin_symptoms(admin)
    return jsonify(item), 201


@app.route('/api/admin/symptoms/<string:item_id>', methods=['PUT'])
def admin_update_symptom(item_id):
    data = request.get_json(silent=True) or {}
    admin = load_admin_symptoms()
    for i, it in enumerate(admin):
        if str(it.get('id')) == str(item_id):
            it['label_vi'] = (data.get('label_vi') or data.get('label') or it.get('label_vi') or '').strip()
            it['label_en'] = (data.get('label_en') or it.get('label_en') or '').strip() or it.get('label_en')
            it['note'] = (data.get('note') or it.get('note') or '').strip()
            admin[i] = it
            save_admin_symptoms(admin)
            return jsonify(it), 200
    return jsonify({"error": "Không tìm thấy mục"}), 404


@app.route('/api/admin/symptoms/<string:item_id>', methods=['DELETE'])
def admin_delete_symptom(item_id):
    admin = load_admin_symptoms()
    new = [it for it in admin if str(it.get('id')) != str(item_id)]
    if len(new) == len(admin):
        return jsonify({"error": "Không tìm thấy mục"}), 404
    save_admin_symptoms(new)
    return jsonify({"message": "Đã xóa"}), 200


@app.route('/api/symptoms', methods=['GET','POST'])
def add_symptom_public():
    if request.method == 'GET':
        try:
            base = build_readable_symptoms() or []
        except Exception:
            base = []
        admin = load_admin_symptoms()
        existing_ids = {str(s.get('id')) for s in base if isinstance(s, dict) and s.get('id')}
        for a in admin:
            if str(a.get('id')) not in existing_ids:
                base.append({
                    'id': a.get('id'),
                    'label': a.get('label_vi') or a.get('label') or a.get('label_en') or '',
                    'label_vi': a.get('label_vi') or a.get('label') or '',
                    'label_en': a.get('label_en') or '',
                    'note': a.get('note') or ''
                })
        return jsonify({"symptoms": base})

    data = request.get_json(silent=True) or {}
    label_vi = (data.get('label_vi') or data.get('label') or '').strip()
    label_en = (data.get('label_en') or data.get('label_en') or '').strip()
    note = (data.get('note') or data.get('note') or '').strip()
    if not label_vi or not label_en:
        return jsonify({"error": "Vui lòng cung cấp label_vi và label_en."}), 400
    admin = load_admin_symptoms()
    candidate_id = data.get('id') or slugify(label_en)
    if any(str(a.get('id')) == str(candidate_id) for a in admin):
        candidate_id = f"{candidate_id}_{secrets.token_hex(3)}"
    item = {"id": candidate_id, "label_vi": label_vi, "label_en": label_en, "note": note}
    admin.append(item)
    save_admin_symptoms(admin)
    return jsonify(item), 201


@app.route('/api/symptoms/<string:item_id>', methods=['PUT'])
def update_symptom_public(item_id):
    data = request.get_json(silent=True) or {}
    admin = load_admin_symptoms()
    for i, it in enumerate(admin):
        if str(it.get('id')) == str(item_id):
            it['label_vi'] = (data.get('label_vi') or data.get('label') or it.get('label_vi') or '').strip()
            it['label_en'] = (data.get('label_en') or it.get('label_en') or '').strip() or it.get('label_en')
            it['note'] = (data.get('note') or it.get('note') or '').strip()
            admin[i] = it
            save_admin_symptoms(admin)
            return jsonify(it), 200
    return jsonify({"error": "Không tìm thấy mục"}), 404


@app.route('/api/symptoms/<string:item_id>', methods=['DELETE'])
def delete_symptom_public(item_id):
    admin = load_admin_symptoms()
    new = [it for it in admin if str(it.get('id')) != str(item_id)]
    if len(new) == len(admin):
        return jsonify({"error": "Không tìm thấy mục"}), 404
    save_admin_symptoms(new)
    return jsonify({"message": "Đã xóa"}), 200


@app.route('/api/symptoms', methods=['GET'])
def get_symptoms():
    # Build base readable symptoms from internal model/features if available
    try:
        base = build_readable_symptoms() or []
    except Exception:
        base = []
    # Load admin-provided symptoms and append (avoid id duplicates)
    admin = load_admin_symptoms()
    existing_ids = {str(s.get('id')) for s in base if isinstance(s, dict) and s.get('id')}
    for a in admin:
        if str(a.get('id')) not in existing_ids:
            base.append({
                'id': a.get('id'),
                'label': a.get('label_vi') or a.get('label') or a.get('label_en') or '',
                'label_vi': a.get('label_vi') or a.get('label') or '',
                'label_en': a.get('label_en') or '',
                'note': a.get('note') or ''
            })
    return jsonify({"symptoms": base})


@app.get("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get('/index.html')
def index_html():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.get('/styles.css')
def styles_css():
    return send_from_directory(FRONTEND_DIR, 'styles.css')


@app.get('/script.js')
def script_js():
    return send_from_directory(FRONTEND_DIR, 'script.js')


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
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or len(password) < 6:
        return jsonify({"error": "Vui lòng nhập đủ thông tin (Mật khẩu từ 6 ký tự)"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email này đã được đăng ký."}), 409
    new_user = User(email=email, full_name=name)
    new_user.set_password(password)
    
    db.session.add(new_user)
    db.session.commit()

    token = jwt.encode({'user': email, 'role': 'User', 'exp': datetime.now(timezone.utc) + timedelta(hours=24)}, app.config['SECRET_KEY'], algorithm="HS256")
    
    return jsonify({'message': 'Đăng ký thành công', 'token': token, 'user': {'name': new_user.full_name, 'email': email}}), 201

# --- BẮT ĐẦU: BỘ API XÁC THỰC, TÀI KHOẢN & HỒ SƠ ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if email == "admin@gmail.com" and password == "123456":
        token = jwt.encode({'user': email, 'role': 'Admin', 'exp': datetime.now(timezone.utc) + timedelta(hours=24)}, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({'message': 'Đăng nhập thành công', 'token': token, 'user': {'name': 'Bác sĩ Toàn (Admin)', 'email': email}}), 200
    
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        token = jwt.encode({'user': email, 'role': 'User', 'exp': datetime.now(timezone.utc) + timedelta(hours=24)}, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({'message': 'Đăng nhập thành công', 'token': token, 'user': {'name': user.full_name, 'email': email}}), 200

    return jsonify({'message': 'Sai email hoặc mật khẩu'}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    return jsonify({'message': 'Đăng xuất thành công'}), 200


@app.route('/api/auth/me', methods=['GET'])
def auth_me():

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "): 
        return jsonify({"error": "Chưa đăng nhập"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        return jsonify({"user": {"email": payload['user'], "name": "Người dùng hệ thống"}})
    except Exception:
        return jsonify({"error": "Token hết hạn"}), 401


@app.route('/api/users/change-password', methods=['PUT'])
def change_password():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "): 
        return jsonify({"error": "Chưa đăng nhập"}), 401
    token = auth_header.split(" ")[1]
    
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        email = payload['user']
    except Exception:
        return jsonify({"error": "Token không hợp lệ"}), 401

    if email == "admin@gmail.com":
        return jsonify({"message": "Đổi mật khẩu admin thành công (giả lập)!"}), 200

    user = User.query.filter_by(email=email).first()
    if not user: return jsonify({"error": "Người dùng không tồn tại"}), 404
    
    data = request.get_json()
    if not user.check_password(data.get('old_password')):
        return jsonify({"error": "Mật khẩu cũ không chính xác!"}), 400

    user.set_password(data.get('new_password'))
    db.session.commit()
    return jsonify({"message": "Đổi mật khẩu thành công!"}), 200


@app.route('/api/users/profile', methods=['GET', 'PUT'])
def profile():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "): return jsonify({"error": "Chưa đăng nhập"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        email = payload['user']
    except Exception:
        return jsonify({"error": "Token không hợp lệ"}), 401

    user = User.query.filter_by(email=email).first()
    
    if request.method == 'GET':
        if email == "admin@gmail.com":
            return jsonify({"fullName": "Bác sĩ Trần Văn Toàn", "email": email, "phoneNumber": "0901234567", "specialty": "Quản trị hệ thống"}), 200
        if user:
            return jsonify({"fullName": user.full_name, "email": email, "phoneNumber": user.phone_number, "specialty": user.specialty}), 200
        return jsonify({"fullName": "Người dùng", "email": email}), 200

    if request.method == 'PUT':
        data = request.get_json()
        if email == "admin@gmail.com":
            return jsonify({"message": "Cập nhật hồ sơ Admin thành công!"}), 200
        if user:
            user.full_name = data.get("fullName", user.full_name)
            user.phone_number = data.get("phoneNumber", user.phone_number)
            user.specialty = data.get("specialty", user.specialty)
            db.session.commit()
            return jsonify({"message": "Cập nhật hồ sơ thành công!"}), 200
        return jsonify({"error": "Không tìm thấy tài khoản trong DB"}), 404
# --- KẾT THÚC: BỘ API XÁC THỰC, TÀI KHOẢN & HỒ SƠ ---


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
        return jsonify({
            "error": _emergency,
            "display_title": "⚠️ Cần hỗ trợ y tế khẩn cấp",
            "needs_more_input": True,
            "confidence": None,
            "label_type": LABEL_TYPE,
            "score_type": "emergency",
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
# API QLÝ NHÓM THUỐC (SCRUM-44)
@app.route('/api/drug-groups', methods=['GET'])
def get_drug_groups():
    groups = NhomThuoc.query.order_by(NhomThuoc.id.desc()).all()
    return jsonify([g.to_dict() for g in groups]), 200


@app.route('/api/drug-groups', methods=['POST'])
def add_drug_group():
    data = request.get_json(silent=True) or {}
    ten_nhom = (data.get('ten_nhom') or '').strip()
    mo_ta = (data.get('mo_ta') or '').strip()

    if not ten_nhom:
        return jsonify({"error": "Vui lòng nhập tên nhóm thuốc."}), 400

    existed = NhomThuoc.query.filter(db.func.lower(NhomThuoc.ten_nhom) == ten_nhom.lower()).first()
    if existed:
        return jsonify({"error": "Tên nhóm thuốc đã tồn tại."}), 409

    new_group = NhomThuoc(ten_nhom=ten_nhom, mo_ta=mo_ta)
    db.session.add(new_group)
    db.session.commit()
    return jsonify({"message": "Thêm nhóm thuốc thành công!", "data": new_group.to_dict()}), 201


@app.route('/api/drug-groups/<int:id>', methods=['PUT'])
def update_drug_group(id):
    group = NhomThuoc.query.get(id)
    if not group:
        return jsonify({"error": "Không tìm thấy nhóm thuốc."}), 404

    data = request.get_json(silent=True) or {}
    ten_nhom = (data.get('ten_nhom') or '').strip()
    mo_ta = (data.get('mo_ta') or '').strip()

    if not ten_nhom:
        return jsonify({"error": "Vui lòng nhập tên nhóm thuốc."}), 400

    existed = NhomThuoc.query.filter(
        db.func.lower(NhomThuoc.ten_nhom) == ten_nhom.lower(),
        NhomThuoc.id != id
    ).first()
    if existed:
        return jsonify({"error": "Tên nhóm thuốc đã tồn tại."}), 409

    group.ten_nhom = ten_nhom
    group.mo_ta = mo_ta
    db.session.commit()
    return jsonify({"message": "Cập nhật nhóm thuốc thành công!", "data": group.to_dict()}), 200


@app.route('/api/drug-groups/<int:id>', methods=['DELETE'])
def delete_drug_group(id):
    group = NhomThuoc.query.get(id)
    if group:
        db.session.delete(group)
        db.session.commit()
        return jsonify({"message": "Đã xóa nhóm thuốc!"}), 200
    return jsonify({"error": "Không tìm thấy nhóm thuốc"}), 404


# ===================================================================
# API CRUD QUẢN LÝ THUỐC (SCRUM-47)
# ===================================================================

@app.route('/api/thuoc', methods=['GET'])
def get_all_thuoc():
    """Lấy danh sách thuốc. Query: ?nhom_thuoc_id=<int> để lọc theo nhóm."""
    nhom_id = request.args.get('nhom_thuoc_id', type=int)
    query = Thuoc.query.filter_by(nhom_thuoc_id=nhom_id) if nhom_id else Thuoc.query
    return jsonify([t.to_dict() for t in query.all()]), 200


@app.route('/api/thuoc/<int:id>', methods=['GET'])
def get_thuoc(id):
    """Lấy chi tiết một thuốc theo ID."""
    thuoc = Thuoc.query.get(id)
    if not thuoc:
        return jsonify({"error": "Không tìm thấy thuốc"}), 404
    return jsonify(thuoc.to_dict()), 200


@app.route('/api/thuoc', methods=['POST'])
def add_thuoc():
    """
    Thêm thuốc mới.
    Required: ten_thuoc, nhom_thuoc_id
    Optional: hoat_chat, ham_luong, dang_bao_che, hang_san_xuat,
              nuoc_san_xuat, so_dang_ky, gia_tham_khao, don_vi_tinh, mo_ta
    """
    data = request.get_json() or {}

    # --- validation ---
    if not data.get('ten_thuoc', '').strip():
        return jsonify({"error": "Vui lòng nhập tên thuốc"}), 400
    if not data.get('nhom_thuoc_id'):
        return jsonify({"error": "Vui lòng chọn nhóm thuốc"}), 400
    if not NhomThuoc.query.get(data['nhom_thuoc_id']):
        return jsonify({"error": "Nhóm thuốc không tồn tại"}), 404

    thuoc = Thuoc(
        ten_thuoc    = data['ten_thuoc'].strip(),
        hoat_chat    = data.get('hoat_chat'),
        ham_luong    = data.get('ham_luong'),
        dang_bao_che = data.get('dang_bao_che'),
        hang_san_xuat= data.get('hang_san_xuat'),
        nuoc_san_xuat= data.get('nuoc_san_xuat'),
        so_dang_ky   = data.get('so_dang_ky'),
        gia_tham_khao= data.get('gia_tham_khao'),
        don_vi_tinh  = data.get('don_vi_tinh'),
        mo_ta        = data.get('mo_ta'),
        nhom_thuoc_id= data['nhom_thuoc_id'],
    )
    try:
        db.session.add(thuoc)
        db.session.commit()
        return jsonify({"message": "Thêm thuốc thành công!", "thuoc": thuoc.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Lỗi khi thêm thuốc: {str(e)}"}), 500


@app.route('/api/thuoc/<int:id>', methods=['PUT'])
def update_thuoc(id):
    """Cập nhật thông tin thuốc. Chỉ cần gửi các field muốn thay đổi."""
    thuoc = Thuoc.query.get(id)
    if not thuoc:
        return jsonify({"error": "Không tìm thấy thuốc"}), 404

    data = request.get_json() or {}

    # Nếu đổi nhóm thuốc, kiểm tra nhóm mới tồn tại
    if 'nhom_thuoc_id' in data:
        if not NhomThuoc.query.get(data['nhom_thuoc_id']):
            return jsonify({"error": "Nhóm thuốc không tồn tại"}), 404
        thuoc.nhom_thuoc_id = data['nhom_thuoc_id']

    updatable = ['ten_thuoc', 'hoat_chat', 'ham_luong', 'dang_bao_che',
                 'hang_san_xuat', 'nuoc_san_xuat', 'so_dang_ky',
                 'gia_tham_khao', 'don_vi_tinh', 'mo_ta']
    for field in updatable:
        if field in data:
            setattr(thuoc, field, data[field])

    try:
        db.session.commit()
        return jsonify({"message": "Cập nhật thuốc thành công!", "thuoc": thuoc.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Lỗi khi cập nhật thuốc: {str(e)}"}), 500


@app.route('/api/thuoc/<int:id>', methods=['DELETE'])
def delete_thuoc(id):
    """Xóa một thuốc."""
    thuoc = Thuoc.query.get(id)
    if not thuoc:
        return jsonify({"error": "Không tìm thấy thuốc"}), 404
    try:
        db.session.delete(thuoc)
        db.session.commit()
        return jsonify({"message": "Xóa thuốc thành công!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Lỗi khi xóa thuốc: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)
