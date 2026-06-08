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
    "constipation": ["táo bón"],
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
    "brittle_nails": ["móng giòn", "móng dễ gãy"],
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
    "headache": ["đau nửa đầu", "đau nửa đầu từng cơn"],
    "stomach_pain": ["đau thượng vị lúc đói", "đau vùng thượng vị"],
    "heartburn": ["nóng rát thượng vị", "nóng rát vùng thượng vị", "ợ nóng"],
    "acidity": ["hay ợ chua", "ợ hơi"],
    "vomiting": ["nôn nhiều", "nôn nhiều lần", "nôn liên tục"],
    "diarrhoea": ["đi ngoài liên tục", "đi ngoài cả ngày", "đi ngoài nhiều lần", "đi ngoài phân lỏng nước"],
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
    "muscle_pain": ["đau mỏi toàn thân", "đau nhức toàn thân", "đau người"],
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
    "blood in stool": ["đi ngoài ra máu", "phân có máu"],
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
    "acne or pimples": ["mụn trứng cá", "mụn"],
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

    # Lớp ngữ nghĩa (fallback): chỉ kích hoạt khi khớp từ khóa thu được ÍT triệu chứng,
    # để giữ độ chính xác cho ca rõ ràng (exact đủ) và cứu ca lạ (exact bỏ sót).
    if SEMANTIC_READY and len(matches) < SEMANTIC_FALLBACK_MAX:
        try:
            matches.update(semantic_matcher.match(text, threshold=SEMANTIC_THRESHOLD))
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

    items = list(references["medications"].get(group, [f"Nhóm thuốc dự đoán: {group}"]))
    if group.lower() != "thuốc kháng histamin":
        return items

    has_eye = has_eye_allergy_symptom(active_symptoms)
    has_nasal = has_nasal_allergy_symptom(active_symptoms)
    if not has_nasal or has_eye:
        return items[:6]

    preferred = []
    for item in items:
        normalized_item = normalize(item)
        if "loratadine" in normalized_item or "cetirizine" in normalized_item:
            extend_unique(preferred, [item])

    return preferred[:3] or [
        "Thuốc trong dữ liệu: Antihistamines (e.g., Loratadine)",
        "Thuốc trong dữ liệu: Oral antihistamines (e.g., Cetirizine)",
    ]


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


def emergency_red_flag_from_notes(notes: str) -> str | None:
    """Dấu hiệu CẤP CỨU hô hấp/tim mạch nhận từ mô tả thô (không phụ thuộc feature).
    Trả về thông điệp cảnh báo nếu phát hiện; None nếu không.
    """
    t = normalize(notes or "")
    # Tím tái / suy hô hấp cấp
    cyanosis = any(p in t for p in ["tim tai", "moi tim", "tim moi", "tim tai mat", "da tim"])
    severe_dyspnea = any(p in t for p in ["kho tho du doi", "kho tho nang", "tho gap", "ngat tho", "khong tho duoc"])
    if cyanosis or (severe_dyspnea and cyanosis):
        return ("Dấu hiệu suy hô hấp cấp (tím tái/khó thở dữ dội). Đây có thể là CẤP CỨU; "
                "gọi cấp cứu hoặc đến cơ sở y tế ngay, KHÔNG tự dùng thuốc.")
    # Nhồi máu cơ tim: đau ngực + (lan tay/hàm | vã mồ hôi | bóp nghẹt)
    chest = any(p in t for p in ["dau nguc", "dau that nguc", "tuc nguc du doi", "nguc bi bop"])
    mi_feat = any(p in t for p in ["lan tay trai", "lan canh tay", "lan ham", "lan vai", "lan ra tay",
                                   "va mo hoi", "bop nghet", "bop chat", "boi hoi"])
    if chest and mi_feat:
        return ("Đau ngực kèm dấu hiệu nghi nhồi máu cơ tim (lan tay/hàm, vã mồ hôi, bóp nghẹt). "
                "Đây có thể là CẤP CỨU; gọi cấp cứu ngay, KHÔNG tự dùng thuốc.")
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


# ── Rule cluster theo logic y khoa chuẩn (2026-06-09, robust hoá) ─────────────
# Mỗi rule yêu cầu tổ hợp triệu chứng đặc hiệu để hạn chế dương tính giả.

def diabetes_rule_drug_group(active_symptoms: set[str]) -> str | None:
    polyuria = has_any_symptom(active_symptoms, ["polyuria", "frequent urination", "excessive urination at night"])
    metabolic = has_any_symptom(active_symptoms, ["weight loss", "excessive hunger", "increased appetite"])
    if polyuria and metabolic:
        return "thuốc điều trị đái tháo đường"
    return None


def thyroid_rule_drug_group(active_symptoms: set[str]) -> str | None:
    # Bướu cổ là dấu hiệu rất đặc hiệu cho bệnh tuyến giáp.
    if has_any_symptom(active_symptoms, ["enlarged thyroid"]):
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


def neuropathic_pain_rule_drug_group(active_symptoms: set[str]) -> str | None:
    nerve_pain = has_any_symptom(active_symptoms, ["Shooting or burning pain, tingling or numbness"])
    paresthesia = has_any_symptom(active_symptoms, ["paresthesia", "loss of sensation"])
    if nerve_pain or (paresthesia and has_any_symptom(active_symptoms, ["Shooting or burning pain, tingling or numbness"])):
        return "thuốc chống co giật/đau thần kinh"
    if nerve_pain and paresthesia:
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


def antiviral_skin_rule_drug_group(active_symptoms: set[str]) -> str | None:
    # Mụn nước/bóng nước kèm sốt hoặc phát ban (thuỷ đậu/zona/herpes) -> kháng virus.
    has_vesicle = has_any_symptom(active_symptoms, ["blister"])
    if has_vesicle and has_any_symptom(active_symptoms, ["fever", "high fever", "mild fever", "skin rash"]):
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
        ["dizziness", "insomnia", "difficulty falling asleep or staying asleep"],
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
        return "; ".join(names[:4])
    return "Chưa có tên thuốc cụ thể trong dữ liệu"


def case_summary(
    notes: str,
    active_symptoms: set[str],
    matched_labels: list[str],
    predicted_group: str | None,
    can_suggest_drug: bool,
) -> dict[str, str]:
    diagnosis = heuristic_diagnosis(active_symptoms) or dataset_diagnosis(active_symptoms) or "Cần bổ sung thông tin"
    diagnosis = DIAGNOSIS_VI.get(diagnosis, diagnosis)
    drug_group = predicted_group if can_suggest_drug and predicted_group else "Chưa đủ dữ liệu để gợi ý thuốc"
    return {
        "description": short_case_description(notes, matched_labels),
        "symptoms": "; ".join(label.lower() for label in matched_labels) if matched_labels else "Chưa nhận diện được",
        "diagnosis": diagnosis,
        "medication_name": medication_names_for_group(predicted_group, can_suggest_drug, active_symptoms),
        "drug_group": drug_group,
    }


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


@app.get("/api/symptoms")
def symptoms():
    return jsonify({"symptoms": readable_symptoms})


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
    unsupported_symptoms = unsupported_symptoms_from_text(notes)
    active_symptoms_order = filter_negated_symptoms(active_symptoms_order, notes)
    active_symptoms = set(active_symptoms_order)

    if not active_symptoms:
        unsupported_labels = [symptom["label_vi"] for symptom in unsupported_symptoms]
        extra = ""
        if unsupported_labels:
            extra = f" Model hiện chưa có đặc trưng cho: {', '.join(unsupported_labels)}."
        return jsonify({"error": f"Không nhận diện được triệu chứng phù hợp với tập train.{extra} Hãy viết rõ hơn hoặc chọn thêm triệu chứng trong danh sách."}), 400

    model_inputs = model_input_candidates(active_symptoms_order)
    probabilities = []
    confidence = None
    prediction = None
    if hasattr(model, "predict_proba"):
        proba_rows = model.predict_proba(model_inputs)
        class_names = model.classes_
        proba = [
            sum(float(row[index]) for row in proba_rows) / len(proba_rows)
            for index in range(len(class_names))
        ]
        ranked = sorted(zip(class_names, proba), key=lambda item: item[1], reverse=True)
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
        confidence = round(float(max(proba)), 4)
    else:
        prediction = model.predict([model_inputs[0]])[0]

    rule_group = (
        diabetes_rule_drug_group(active_symptoms)
        or thyroid_rule_drug_group(active_symptoms)
        or psych_rule_drug_group(active_symptoms)
        or cardiac_rule_drug_group(active_symptoms)
        or bronchodilator_rule_drug_group(active_symptoms)
        or wound_infection_rule_drug_group(active_symptoms)
        or infectious_bloody_diarrhea_rule_drug_group(active_symptoms)
        or urinary_rule_drug_group(active_symptoms)
        or neuropathic_pain_rule_drug_group(active_symptoms)
        or migraine_rule_drug_group(active_symptoms)
        or antiviral_skin_rule_drug_group(active_symptoms)
        or musculoskeletal_nsaid_rule_drug_group(active_symptoms)
        or constipation_rule_drug_group(active_symptoms)
        or dental_rule_drug_group(active_symptoms)
        or gastrointestinal_rule_drug_group(active_symptoms)
        or dermatology_rule_drug_group(active_symptoms)
        or respiratory_rule_drug_group(active_symptoms)
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
    _emergency_msg = emergency_red_flag_from_notes(notes)
    if _emergency_msg:
        quality_reasons.insert(0, _emergency_msg)
    matched_symptoms = active_symptoms_order
    matched_symptom_labels = unique_values([symptom_label_vi(symptom) for symptom in matched_symptoms])
    label_kind_vi = "nhóm thuốc" if LABEL_TYPE == "drug_group" else "bệnh"

    # Khi một rule lâm sàng mạnh đã kích hoạt (score_type=="rule"), không ép "cần thêm
    # thông tin" chỉ vì ít hơn 2 triệu chứng — nhiều ca rõ ràng chỉ có 1 triệu chứng đặc
    # hiệu (táo bón, mụn nước thành chùm, mề đay...). Vẫn giữ ràng buộc cho dự đoán bằng model.
    if score_type != "rule" and len(matched_symptom_labels) < MIN_RELIABLE_SYMPTOMS:
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
    if unsupported_symptoms:
        unsupported_labels = ", ".join(symptom["label_vi"] for symptom in unsupported_symptoms)
        quality_reasons.append(
            f"Có triệu chứng ngoài tập train nên chưa được đưa vào mô hình: {unsupported_labels}."
        )

    needs_more_input = bool(quality_reasons)
    quality_message = " ".join(quality_reasons)
    if needs_more_input:
        quality_message += " Chưa đủ dữ liệu để gợi ý nhóm thuốc an toàn."

    if LABEL_TYPE == "drug_group" and needs_more_input:
        triage = symptom_triage_guidance(active_symptoms)
        summary = case_summary(notes, active_symptoms, matched_symptom_labels, prediction, False)
        return jsonify(
            {
                "error": (
                    f"{quality_message} {more_info_prompt(active_symptoms)}"
                ),
                "case_summary": summary,
                "display_title": "Chưa đủ dữ liệu để gợi ý thuốc",
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

    return jsonify(
        {
            "case_summary": summary,
            "disease": prediction,
            "disease_vi": predicted_label_vi(prediction),
            "display_title": display_title_for_prediction(prediction, needs_more_input),
            "confidence": confidence,
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
            "medications": treatment_guidance[:10],
            "medications_en": treatment_guidance[:10],
            "dataset_treatment": translate_items(references["medications"].get(prediction, [])) if LABEL_TYPE != "drug_group" else references["medications"].get(prediction, []),
            "diets": care_guidance[:10],
            "diets_en": care_guidance[:10],
            "precautions": precaution_guidance[:10],
            "precautions_en": precaution_guidance[:10],
            "workouts": [],
            "workouts_en": references["workouts"].get(prediction, []),
            "warning": guidance["warning"],
            "guidance_source": guidance["guidance_source"],
            "suggested_symptoms": suggested_symptoms_for_more_info(active_symptoms) if needs_more_input else [],
            "top_predictions": probabilities,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)
