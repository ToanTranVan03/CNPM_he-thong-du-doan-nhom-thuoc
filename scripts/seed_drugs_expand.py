"""Mở rộng KHO THUỐC: thêm thuốc tham khảo thật (thị trường VN) theo nhóm.

Idempotent: get-or-create nhóm theo tên; bỏ qua thuốc đã có (theo tên), gắn vào nhóm nếu chưa.
Đây là DỮ LIỆU THAM KHẢO (tên + hoạt chất + công dụng ngắn) — KHÔNG phải liều/đơn thuốc.
Chạy:  python scripts/seed_drugs_expand.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app as A  # noqa: E402

# {tên nhóm: [(tên thuốc, hoạt chất, công dụng ngắn), ...]}
DATA = {
    "thuốc giảm đau hạ sốt": [
        ("Panadol", "paracetamol", "Giảm đau, hạ sốt"),
        ("Efferalgan", "paracetamol", "Hạ sốt, giảm đau (viên sủi)"),
        ("Hapacol", "paracetamol", "Giảm đau, hạ sốt"),
        ("Tylenol", "paracetamol", "Giảm đau, hạ sốt"),
        ("Partamol", "paracetamol", "Giảm đau, hạ sốt"),
    ],
    "thuốc kháng viêm không steroid": [
        ("Brufen", "ibuprofen", "Giảm đau, kháng viêm"),
        ("Mobic", "meloxicam", "Kháng viêm xương khớp"),
        ("Voltaren", "diclofenac", "Giảm đau, kháng viêm"),
        ("Naprosyn", "naproxen", "Giảm đau, kháng viêm"),
        ("Celebrex", "celecoxib", "Kháng viêm chọn lọc COX-2"),
        ("Aspirin pH8", "acetylsalicylic acid", "Giảm đau, hạ sốt, kháng viêm"),
    ],
    "thuốc kháng histamin": [
        ("Zyrtec", "cetirizin", "Dị ứng, mề đay"),
        ("Clarityne", "loratadin", "Viêm mũi dị ứng, mề đay"),
        ("Telfast", "fexofenadin", "Dị ứng, mề đay"),
        ("Aerius", "desloratadin", "Viêm mũi dị ứng"),
        ("Theralene", "alimemazin", "Dị ứng, an thần nhẹ"),
        ("Chlorpheniramin", "chlorpheniramin", "Dị ứng"),
    ],
    "thuốc kháng sinh": [
        ("Amoxicillin", "amoxicillin", "Kháng sinh beta-lactam (kê đơn)"),
        ("Augmentin", "amoxicillin + acid clavulanic", "Kháng sinh phối hợp (kê đơn)"),
        ("Zinnat", "cefuroxim", "Kháng sinh cephalosporin (kê đơn)"),
        ("Zithromax", "azithromycin", "Kháng sinh macrolid (kê đơn)"),
        ("Ciprobay", "ciprofloxacin", "Kháng sinh quinolon (kê đơn)"),
        ("Cephalexin", "cefalexin", "Kháng sinh cephalosporin (kê đơn)"),
        ("Klacid", "clarithromycin", "Kháng sinh macrolid (kê đơn)"),
        ("Flagyl", "metronidazol", "Kháng sinh/kháng đơn bào (kê đơn)"),
    ],
    "thuốc điều trị dạ dày": [
        ("Nexium", "esomeprazol", "Ức chế bơm proton, trào ngược"),
        ("Losec", "omeprazol", "Loét/trào ngược dạ dày"),
        ("Pantoloc", "pantoprazol", "Ức chế bơm proton"),
        ("Phosphalugel", "nhôm phosphat", "Trung hòa acid dạ dày"),
        ("Gaviscon", "natri alginat", "Chống trào ngược"),
        ("Yumangel", "almagat", "Kháng acid (chữ Y)"),
    ],
    "thuốc long đờm / giảm ho": [
        ("Acemuc", "acetylcystein", "Long đờm"),
        ("Bisolvon", "bromhexin", "Long đờm"),
        ("Mucosolvan", "ambroxol", "Long đờm"),
        ("Prospan", "cao lá thường xuân", "Long đờm thảo dược"),
        ("Atussin", "dextromethorphan", "Giảm ho khan"),
        ("Terpin codein", "terpin + codein", "Giảm ho (kê đơn)"),
    ],
    "thuốc chống nôn": [
        ("Motilium-M", "domperidon", "Chống nôn, đầy bụng"),
        ("Primperan", "metoclopramid", "Chống nôn"),
        ("Zofran", "ondansetron", "Chống nôn mạnh (kê đơn)"),
        ("Nautamine", "diphenhydramin", "Chống nôn do say tàu xe"),
    ],
    "bù dịch và điện giải": [
        ("Oresol", "glucose + natri + kali clorid", "Bù nước, điện giải"),
        ("Hydrite", "oresol viên sủi", "Bù nước, điện giải"),
    ],
    "thuốc giãn phế quản": [
        ("Ventolin", "salbutamol", "Giãn phế quản (hen, COPD)"),
        ("Berodual", "fenoterol + ipratropium", "Giãn phế quản"),
        ("Symbicort", "budesonid + formoterol", "Dự phòng hen (kê đơn)"),
        ("Theostat", "theophyllin", "Giãn phế quản"),
    ],
    "thuốc kháng nấm/ký sinh trùng ngoài da": [
        ("Nizoral", "ketoconazol", "Kháng nấm da, gàu"),
        ("Canesten", "clotrimazol", "Kháng nấm da"),
        ("Lamisil", "terbinafin", "Nấm da, nấm móng"),
        ("Diflucan", "fluconazol", "Kháng nấm toàn thân (kê đơn)"),
    ],
    "thuốc corticosteroid/chống viêm": [
        ("Medrol", "methylprednisolon", "Kháng viêm corticoid (kê đơn)"),
        ("Prednisolon", "prednisolon", "Kháng viêm corticoid (kê đơn)"),
        ("Dexamethason", "dexamethason", "Kháng viêm mạnh (kê đơn)"),
        ("Gentrisone", "betamethason + gentamicin + clotrimazol", "Kem bôi da kháng viêm"),
    ],
    "vitamin và khoáng chất": [
        ("Vitamin C 500mg", "acid ascorbic", "Bổ sung vitamin C"),
        ("Berocca", "vitamin nhóm B + C + kẽm", "Bổ sung vitamin tổng hợp"),
        ("Calcium Corbiere", "calci + vitamin D", "Bổ sung canxi"),
        ("Ferrovit", "sắt + acid folic", "Bổ sung sắt"),
        ("Zinc Gluconate", "kẽm gluconat", "Bổ sung kẽm"),
        ("Magie-B6", "magie + vitamin B6", "Bổ sung magie"),
    ],
    "thuốc điều trị đái tháo đường": [
        ("Glucophage", "metformin", "Đái tháo đường type 2 (kê đơn)"),
        ("Diamicron MR", "gliclazid", "Đái tháo đường type 2 (kê đơn)"),
        ("Amaryl", "glimepirid", "Đái tháo đường type 2 (kê đơn)"),
        ("Lantus", "insulin glargin", "Insulin nền (kê đơn, tiêm)"),
    ],
    "thuốc tim mạch/huyết áp": [
        ("Amlor", "amlodipin", "Hạ huyết áp (kê đơn)"),
        ("Cozaar", "losartan", "Hạ huyết áp (kê đơn)"),
        ("Concor", "bisoprolol", "Tim mạch, huyết áp (kê đơn)"),
        ("Coversyl", "perindopril", "Hạ huyết áp (kê đơn)"),
        ("Lipitor", "atorvastatin", "Hạ mỡ máu (kê đơn)"),
    ],
    "thuốc thần kinh/tâm thần": [
        ("Stilnox", "zolpidem", "Mất ngủ (kê đơn)"),
        ("Lexomil", "bromazepam", "An thần, lo âu (kê đơn)"),
        ("Amitriptylin", "amitriptylin", "Trầm cảm, đau thần kinh (kê đơn)"),
        ("Seduxen", "diazepam", "An thần (kê đơn)"),
    ],
    "thuốc chống co giật/đau thần kinh": [
        ("Neurontin", "gabapentin", "Đau thần kinh, động kinh (kê đơn)"),
        ("Lyrica", "pregabalin", "Đau thần kinh (kê đơn)"),
        ("Tegretol", "carbamazepin", "Động kinh, đau dây V (kê đơn)"),
        ("Depakine", "natri valproat", "Động kinh (kê đơn)"),
    ],
    "thuốc thông mũi": [
        ("Otrivin", "xylometazolin", "Xịt thông mũi"),
        ("Coldi-B", "oxymetazolin + camphor", "Xịt mũi nghẹt"),
        ("Sudafed", "pseudoephedrin", "Thông mũi đường uống"),
    ],
    "thuốc nhuận tràng": [
        ("Duphalac", "lactulose", "Nhuận tràng thẩm thấu"),
        ("Forlax", "macrogol", "Nhuận tràng"),
        ("Sorbitol", "sorbitol", "Nhuận tràng"),
    ],
    "thuốc chống đông/kháng tiểu cầu": [
        ("Aspirin 81", "acetylsalicylic acid", "Kháng tiểu cầu (kê đơn)"),
        ("Plavix", "clopidogrel", "Kháng tiểu cầu (kê đơn)"),
        ("Xarelto", "rivaroxaban", "Chống đông (kê đơn)"),
        ("Sintrom", "acenocoumarol", "Chống đông kháng vitamin K (kê đơn)"),
    ],
    "thuốc nội tiết tuyến giáp": [
        ("Levothyrox", "levothyroxin", "Suy giáp (kê đơn)"),
        ("Thyrozol", "thiamazol", "Cường giáp (kê đơn)"),
    ],
    "thuốc kháng virus": [
        ("Tamiflu", "oseltamivir", "Cúm (kê đơn)"),
        ("Acyclovir", "acyclovir", "Herpes, zona (kê đơn)"),
        ("Zovirax", "acyclovir", "Herpes, zona (kê đơn)"),
    ],
}


def main():
    if not A.DB_ENABLED:
        print("DB chưa bật — bỏ qua.")
        return 1
    added_drugs = 0
    added_links = 0
    created_groups = 0
    with A.app.app_context():
        for ten_nhom, drugs in DATA.items():
            nhom = A.db.session.query(A.db_models.NhomThuoc).filter_by(ten_nhom_thuoc=ten_nhom).first()
            if not nhom:
                nhom = A.db_models.NhomThuoc(ten_nhom_thuoc=ten_nhom)
                A.db.session.add(nhom)
                A.db.session.flush()
                created_groups += 1
            for ten, hc, cd in drugs:
                t = A.db.session.query(A.db_models.ThuocThamKhao).filter_by(ten_thuoc=ten).first()
                if not t:
                    t = A.db_models.ThuocThamKhao(ten_thuoc=ten, hoat_chat=hc, cong_dung=cd)
                    A.db.session.add(t)
                    A.db.session.flush()
                    added_drugs += 1
                if nhom not in t.nhom_thuoc_list:
                    t.nhom_thuoc_list.append(nhom)
                    added_links += 1
        A.db.session.commit()
        total = A.db.session.query(A.db_models.ThuocThamKhao).count()
    print(f"Đã thêm {added_drugs} thuốc mới, {added_links} liên kết nhóm-thuốc, {created_groups} nhóm mới.")
    print(f"Tổng thuốc trong kho hiện tại: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
