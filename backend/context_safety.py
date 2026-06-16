"""Tầng NGỮ CẢNH - AN TOÀN: đọc CẢ CÂU mô tả (không chỉ túi triệu chứng) để bắt các yếu tố
quyết định an toàn mà tầng trích triệu chứng bỏ qua:

- Bệnh nền (loét dạ dày, suy thận, suy gan, hen, suy tim, rối loạn đông máu)
- Thuốc đang dùng (chống đông/kháng tiểu cầu) -> tương tác
- Tuổi (sơ sinh/nhũ nhi, trẻ em, người cao tuổi)
- Thai kỳ / cho con bú
- Nhân quả dị ứng thuốc ("sau khi uống X nổi mề đay")
- Dấu hiệu PHẢN VỆ (sưng môi/lưỡi/họng + khó thở) -> cấp cứu

Chống chỉ định kinh điển (vd NSAID với loét dạ dày/suy thận/chống đông) -> CHẶN gợi ý.
Lexicon tiếng Việt đã bỏ dấu (khớp với normalize của app). Mọi thứ deterministic, test được.
"""
from __future__ import annotations

import re
import unicodedata


def norm(value: str) -> str:
    text = (value or "").replace("_", " ").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s().]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def low(value: str) -> str:
    """Lowercase GIỮ DẤU (để phân biệt va chạm dấu: 'gân'≠'gan', 'thận'≠'than')."""
    return re.sub(r"\s+", " ", (value or "").replace("_", " ").lower()).strip()


# Bệnh GAN/THẬN dò bằng text GIỮ DẤU (tránh va chạm dấu: 'gân'≠'gan', 'thân/than'≠'thận').
HEPATIC_DIA = ("suy gan", "xơ gan", "viêm gan", "bệnh gan", "men gan cao", "gan nhiễm mỡ", "gan nhiem mo")
RENAL_DIA = ("suy thận", "bệnh thận", "thận yếu", "suy giảm chức năng thận", "chạy thận",
             "lọc máu", "yếu thận", "hư thận")


def _has_any(t: str, keys) -> bool:
    return any(k in t for k in keys)


# ── Lexicon (đã bỏ dấu) ───────────────────────────────────────────────────────
COMORBIDITY = {
    "peptic_ulcer": ("loet da day", "loet ta trang", "loet da day ta trang", "viem loet da day",
                     "xuat huyet tieu hoa", "xuat huyet da day", "trao nguoc loet"),
    "renal": ("suy than", "benh than man", "suy than man", "chay than", "loc mau", "than yeu"),
    "hepatic": ("suy gan", "xo gan", "viem gan", "benh gan", "men gan cao", "gan nhiem mo nang"),
    "asthma": ("hen suyen", "hen phe quan", "co dia hen"),
    "heart_failure": ("suy tim", "benh tim mach nang"),
    "bleeding": ("roi loan dong mau", "giam tieu cau", "de chay mau", "hemophilia", "mau kho dong"),
}
COMORBIDITY_VI = {
    "peptic_ulcer": "loét/xuất huyết dạ dày", "renal": "suy thận", "hepatic": "bệnh gan",
    "asthma": "hen suyễn", "heart_failure": "suy tim", "bleeding": "rối loạn đông máu",
}

ANTICOAGULANT = ("warfarin", "sintrom", "acenocoumarol", "thuoc chong dong", "khang dong",
                 "khang tieu cau", "clopidogrel", "plavix", "rivaroxaban", "dabigatran",
                 "apixaban", "xarelto", "dang dung aspirin", "aspirin lieu thap",
                 "loang mau", "lam loang mau", "thuoc loang mau", "chong dong mau", "lam long mau")

PREGNANCY = ("mang thai", "co thai", "co bau", "ba bau", "thai ky", "dang bau", "mang bau", "bau bi",
             "cho con bu", "dang cho con bu", "san phu", "thai nhi", "co em be", "co be trong bung",
             "be trong bung", "em be trong bung", "co bau bi")

ALLERGY_SIGN = ("me day", "man do", "man ngua", "phat ban", "ngua khap", "noi man", "di ung", "noi ban")
ALLERGY_CAUSE = ("sau khi uong", "sau khi dung", "sau uong", "sau dung", "uong thuoc xong",
                 "dung thuoc xong", "sau khi tiem", "sau tiem")

SWELLING = ("sung moi", "sung luoi", "sung hong", "sung mat", "sung thanh quan", "phu mat", "sung co hong")
BREATHING = ("kho tho", "kho nuot", "tho rit", "tuc nguc", "nghet tho", "khan tieng dot ngot")
ANAPHYLAXIS_DIRECT = ("phan ve", "soc phan ve")


def detect_comorbidities(notes_raw: str) -> set[str]:
    t = norm(notes_raw)
    flags = {flag for flag, keys in COMORBIDITY.items()
             if flag not in ("hepatic", "renal") and _has_any(t, keys)}
    low_t = low(notes_raw)  # gan/thận dò GIỮ DẤU để tránh va chạm dấu
    if _has_any(low_t, HEPATIC_DIA):
        flags.add("hepatic")
    if _has_any(low_t, RENAL_DIA):
        flags.add("renal")
    return flags


def on_anticoagulant(t: str) -> bool:
    return _has_any(t, ANTICOAGULANT)


def is_pregnant(t: str) -> bool:
    return _has_any(t, PREGNANCY) or bool(re.search(r"thai\s*\d+\s*tuan", t))


def drug_allergy_cause(t: str) -> bool:
    return _has_any(t, ALLERGY_CAUSE) and _has_any(t, ALLERGY_SIGN)


def age_flag(t: str) -> str | None:
    """Trả 'infant' | 'child' | 'elderly' | None."""
    if _has_any(t, ("so sinh", "tre so sinh", "nhu nhi", "tre duoi 1 tuoi", "be moi sinh")):
        return "infant"
    # "X thang tuoi"/"be X thang" -> nhũ nhi (<1 tuổi)
    if re.search(r"\d+\s*thang(\s*tuoi)?", t) and _has_any(t, ("be", "tre", "con", "chau", "em be", "thang tuoi")):
        return "infant"
    if _has_any(t, ("nguoi gia", "cao tuoi", "lon tuoi", "cu ong", "cu ba", "ong cu", "ba cu",
                    "cu nha", "cu ba", "cu gia", "tuoi gia", "lao nien")):
        return "elderly"
    # "ngoài/trên/hơn N (tuổi)" -> người lớn tuổi (vd "mẹ tôi ngoài 70 rồi")
    m_old = re.search(r"(?:ngoai|tren|hon)\s*(\d{2})", t)
    if m_old and int(m_old.group(1)) >= 60:
        return "elderly"
    # "X tuoi" -> phân theo số + ngữ cảnh
    child_ctx = _has_any(t, ("be ", "tre ", "chau ", "con toi", "con em", "em be", "tre em", "tre nho", "thang cu", "thang be"))
    for m in re.finditer(r"(\d{1,3})\s*tuoi", t):
        age = int(m.group(1))
        if age >= 65:
            return "elderly"
        if age <= 12 and child_ctx:
            return "child"
        if age <= 5:
            return "child"
    if child_ctx and re.search(r"\btre em\b|\btre nho\b", t):
        return "child"
    return None


# ── Cổng cấp cứu phản vệ (gọi ở tầng emergency) ───────────────────────────────
def emergency_message(notes: str) -> str | None:
    t = norm(notes)
    if _has_any(t, ANAPHYLAXIS_DIRECT):
        return ("Nghi PHẢN VỆ (sốc phản vệ) — đây là CẤP CỨU. Gọi 115 hoặc đến cơ sở y tế gần nhất "
                "NGAY. Nếu có bút tiêm adrenaline (epinephrine) theo chỉ định, dùng ngay.")
    if _has_any(t, SWELLING) and _has_any(t, BREATHING):
        return ("Sưng môi/lưỡi/họng kèm khó thở/khó nuốt là dấu hiệu PHẢN VỆ — CẤP CỨU. Gọi 115 hoặc "
                "đến cơ sở y tế NGAY, không tự dùng thuốc.")
    return None


# ── Tổng hợp cảnh báo ngữ cảnh cho 1 nhóm thuốc dự đoán ───────────────────────
def safety_overrides(prediction: str | None, notes: str) -> dict:
    """Trả {'block': bool, 'reasons': [str], 'allergy': bool}.
    block=True -> chống chỉ định cứng, phải chặn gợi ý (đẩy sang cần-bác-sĩ).
    """
    t = norm(notes)
    g = (prediction or "").lower()
    reasons: list[str] = []
    block = False

    como = detect_comorbidities(notes)
    anticoag = on_anticoagulant(t)
    preg = is_pregnant(t)
    age = age_flag(t)
    allergy = drug_allergy_cause(t)

    is_nsaid = "khang viem khong steroid" in norm(g) or "nsaid" in norm(g)
    is_analgesic = "giam dau ha sot" in norm(g)

    # 1) NSAID — chống chỉ định kinh điển
    if is_nsaid:
        hit = [COMORBIDITY_VI[k] for k in ("peptic_ulcer", "renal", "hepatic", "asthma", "heart_failure", "bleeding") if k in como]
        if hit:
            block = True
            reasons.append(
                f"⚠️ Nhóm kháng viêm không steroid (NSAID) CHỐNG CHỈ ĐỊNH/thận trọng cao với bệnh nền của bạn "
                f"({', '.join(hit)}). KHÔNG tự dùng — cần bác sĩ đánh giá."
            )
        if anticoag:
            block = True
            reasons.append(
                "⚠️ Bạn đang dùng thuốc CHỐNG ĐÔNG/kháng tiểu cầu: NSAID/aspirin làm tăng mạnh nguy cơ "
                "CHẢY MÁU (tiêu hóa, não). Tuyệt đối không tự dùng — hỏi bác sĩ."
            )

    # 2) Paracetamol/giảm đau hạ sốt + bệnh gan
    if is_analgesic and "hepatic" in como:
        block = True
        reasons.append(
            "⚠️ Có bệnh gan: paracetamol (acetaminophen) có thể gây ĐỘC GAN. Cần bác sĩ tư vấn liều/loại thuốc, không tự dùng."
        )

    # 3) Đang dùng chống đông + bất kỳ nhóm giảm đau -> nhắc nguy cơ chảy máu
    if anticoag and is_analgesic:
        reasons.append(
            "Bạn đang dùng thuốc chống đông: cân nhắc kỹ thuốc giảm đau (ưu tiên paracetamol đúng liều, "
            "tránh aspirin/NSAID) — nên hỏi bác sĩ/dược sĩ."
        )

    # 4) Thai kỳ
    if preg:
        if is_nsaid:
            block = True
            reasons.append("⚠️ Đang mang thai: NSAID CHỐNG CHỈ ĐỊNH (nhất là 3 tháng cuối). Cần bác sĩ sản khoa.")
        else:
            reasons.append(
                "Đang mang thai/cho con bú: NHIỀU thuốc chống chỉ định — KHÔNG tự dùng bất kỳ thuốc nào, "
                "hãy hỏi bác sĩ sản khoa trước."
            )

    # 5) Tuổi
    if age == "infant":
        block = True
        reasons.append("Trẻ sơ sinh/nhũ nhi: KHÔNG tự dùng thuốc; cần khám bác sĩ nhi NGAY (sốt/bệnh ở lứa tuổi này rất cần đánh giá).")
    elif age == "child":
        reasons.append("Trẻ em: liều theo cân nặng/tuổi và nhiều thuốc người lớn không phù hợp — cần hỏi bác sĩ/dược sĩ nhi.")
    elif age == "elderly":
        reasons.append("Người cao tuổi: tăng nguy cơ tác dụng phụ/tương tác (thận, dạ dày, tim mạch) — thận trọng, nên hỏi bác sĩ trước khi dùng.")

    return {"block": block, "reasons": reasons, "allergy": allergy}


def drug_allergy_message() -> str:
    return (
        "Nghi DỊ ỨNG THUỐC (triệu chứng xuất hiện SAU khi dùng thuốc): NGỪNG NGAY thuốc nghi ngờ, "
        "ghi nhớ tên thuốc để không dùng lại; nếu có sưng môi/lưỡi/khó thở phải đi CẤP CỨU. "
        "Thuốc kháng histamin chỉ giảm triệu chứng nhẹ — cần bác sĩ đánh giá mức độ dị ứng."
    )
