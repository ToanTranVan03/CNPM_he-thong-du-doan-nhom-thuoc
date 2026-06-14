import csv
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import app


random.seed(20260607)

CASE_GROUPS = [
    {
        "name": "respiratory_mild",
        "expected": "needs_more_or_no_antibiotic",
        "templates": [
            "Tôi bị ho và đau họng từ hôm qua.",
            "Mấy nay tôi ho, cổ họng đau rát, chưa thấy sốt.",
            "Bệnh nhân đau họng, ho khan nhẹ khoảng 2 ngày.",
            "Em bị rát họng với ho lặt vặt, người vẫn tỉnh.",
            "Tôi thấy họng đau, nuốt hơi rát và ho nhẹ.",
        ],
    },
    {
        "name": "respiratory_fever",
        "expected": "antipyretic",
        "templates": [
            "Bệnh nhân sốt nhẹ, ho khan, đau họng trong 2 ngày.",
            "Tôi bị sốt 38 độ, ho và rát họng.",
            "Người bệnh sốt, ho khan, đau họng, hơi mệt.",
            "Tôi sốt nhẹ kèm ho và sổ mũi.",
            "Bé bị sốt nhẹ, ho, cổ họng đau.",
        ],
    },
    {
        "name": "respiratory_phlegm",
        "expected": "cough_expectorant",
        "templates": [
            "Bệnh nhân ho có đờm, đau rát họng, sổ mũi.",
            "Tôi ho đờm, nghẹt mũi, họng hơi rát.",
            "Mấy ngày nay tôi ho có đờm vàng nhạt và sổ mũi.",
            "Người bệnh ho nhiều có đờm, đau họng, chảy nước mũi.",
            "Tôi bị khạc đờm, ho dai dẳng, rát họng.",
        ],
    },
    {
        "name": "gastro_diarrhea",
        "expected": "rehydration",
        "templates": [
            "Bệnh nhân đau bụng, tiêu chảy, buồn nôn.",
            "Tôi bị đau bụng âm ỉ, đi ngoài phân lỏng nhiều lần.",
            "Ăn xong tôi đau bụng, tiêu chảy và hơi buồn nôn.",
            "Người bệnh tiêu chảy, đau bụng quanh rốn, khát nước.",
            "Tôi đi ngoài lỏng từ sáng, bụng đau quặn từng cơn.",
        ],
    },
    {
        "name": "gastro_vomiting",
        "expected": "antiemetic_or_rehydration",
        "templates": [
            "Bệnh nhân buồn nôn, nôn nhiều sau khi ăn thức ăn lạ.",
            "Tôi nôn ói liên tục và đau bụng nhẹ.",
            "Người bệnh buồn nôn, nôn sau bữa tối, người mệt.",
            "Em bị nôn, không muốn ăn, bụng khó chịu.",
            "Tôi nôn vài lần, hơi chóng mặt và khát nước.",
        ],
    },
    {
        "name": "dental",
        "expected": "dental",
        "templates": [
            "Bệnh nhân đau răng, sưng nướu, khó nhai.",
            "Tôi bị nhức răng, lợi sưng và nhai rất đau.",
            "Răng hàm đau, nướu sưng đỏ, ăn uống khó.",
            "Tôi đau răng nhiều, có vẻ sưng lợi.",
            "Người bệnh đau răng, sưng vùng hàm, khó há miệng.",
        ],
    },
    {
        "name": "skin_fungal",
        "expected": "antifungal",
        "templates": [
            "Bệnh nhân ngứa da, phát ban, nổi nốt trên da và có mảng đổi màu da.",
            "Tôi bị ngứa da, nổi mẩn đỏ và có vùng da đổi màu.",
            "Da tôi nổi ban, ngứa nhiều, có mảng trắng loang.",
            "Người bệnh phát ban, ngứa, da bong tróc nhẹ.",
            "Tôi bị nổi nốt trên da, ngứa và mảng da sẫm màu.",
        ],
    },
    {
        "name": "headache_dizzy",
        "expected": "needs_more",
        "templates": [
            "Tôi bị đau đầu, mất ngủ, chóng mặt.",
            "Mấy hôm nay tôi đau đầu, ngủ kém và hơi choáng.",
            "Bệnh nhân đau đầu âm ỉ, chóng mặt, khó ngủ.",
            "Tôi nhức đầu, hoa mắt, đêm ngủ không được.",
            "Người bệnh đau đầu, mệt và mất ngủ.",
        ],
    },
    {
        "name": "ear",
        "expected": "ear_related",
        "templates": [
            "Bệnh nhân đau tai, nghe kém và chảy dịch tai.",
            "Tôi bị đau tai phải, tai có dịch và nghe nhỏ hơn.",
            "Người bệnh đau tai, ù tai, chóng mặt nhẹ.",
            "Tai tôi đau, nghe kém, có cảm giác đầy tai.",
            "Bé đau tai, sốt nhẹ, tai chảy dịch.",
        ],
    },
    {
        "name": "ankle",
        "expected": "ankle_related",
        "templates": [
            "Bệnh nhân đau mắt cá chân và sưng cổ chân.",
            "Tôi bị trẹo chân, cổ chân sưng và đi lại đau.",
            "Mắt cá chân đau, hơi bầm tím sau khi té.",
            "Người bệnh đau cổ chân, sưng mắt cá, khó đi.",
            "Tôi đau bàn chân và sưng cổ chân.",
        ],
    },
    {
        "name": "urinary",
        "expected": "urinary_related",
        "templates": [
            "Tôi bị tiểu buốt, tiểu nhiều lần và nước tiểu hôi.",
            "Bệnh nhân đau bàng quang, mắc tiểu liên tục, tiểu rát.",
            "Tôi đi tiểu rát, nước tiểu sẫm màu.",
            "Người bệnh tiểu buốt, đau hông lưng và sốt nhẹ.",
            "Tôi tiểu ra máu, đau vùng bụng dưới.",
        ],
    },
    {
        "name": "chest_red_flag",
        "expected": "red_flag",
        "templates": [
            "Bệnh nhân đau ngực, khó thở, ho có đờm.",
            "Tôi đau tức ngực, thở hụt hơi và vã mồ hôi.",
            "Người bệnh khó thở, đau ngực, tim đập nhanh.",
            "Tôi bị đau ngực khi hít sâu, ho và sốt.",
            "Bệnh nhân thở gấp, đau ngực, chóng mặt.",
        ],
    },
]

PREFIXES = ["", "Xin hỏi bác sĩ, ", "Dạ ", "Cho tôi hỏi, ", "Mấy hôm nay "]
SUFFIXES = ["", " Tôi hơi lo.", " Không biết nên xử lý sao.", " Triệu chứng làm tôi khó chịu.", " Tôi chưa dùng thuốc gì."]


def make_cases(count: int = 500):
    cases = []
    for index in range(count):
        group = CASE_GROUPS[index % len(CASE_GROUPS)]
        text = random.choice(group["templates"])
        if random.random() < 0.55:
            text = random.choice(PREFIXES) + text
        if random.random() < 0.45:
            text = text + random.choice(SUFFIXES)
        cases.append({"id": index + 1, "group": group["name"], "expected": group["expected"], "text": text})
    random.shuffle(cases)
    return cases


def check_case(case, status, data):
    issues = []
    if status not in (200, 400, 422):
        issues.append(f"unexpected_status_{status}")
    if status in (200, 422):
        summary = data.get("case_summary") or {}
        for field in ("diagnosis", "medication_name", "drug_group"):
            if not summary.get(field):
                issues.append(f"missing_summary_{field}")
        if not data.get("matched_symptoms_vi"):
            issues.append("missing_matched_symptoms")
    if status == 400:
        issues.append("not_recognized")

    summary = data.get("case_summary") or {}
    drug_group = str(summary.get("drug_group", "")).lower()
    diagnosis = str(summary.get("diagnosis", "")).lower()

    expected = case["expected"]
    if expected == "needs_more" and status == 200 and "chưa đủ" not in drug_group:
        issues.append("should_request_more_info")
    if expected == "needs_more_or_no_antibiotic" and "kháng sinh" in drug_group:
        issues.append("unsafe_antibiotic_for_mild_respiratory")
    if expected == "antipyretic" and status == 200 and "giảm đau hạ sốt" not in drug_group:
        issues.append("expected_antipyretic")
    if expected == "cough_expectorant" and status == 200 and "long đờm" not in drug_group:
        issues.append("expected_expectorant")
    if expected == "rehydration" and status == 200 and "bù dịch" not in drug_group:
        issues.append("expected_rehydration")
    if expected == "antiemetic_or_rehydration" and status == 200 and not ("chống nôn" in drug_group or "bù dịch" in drug_group):
        issues.append("expected_antiemetic_or_rehydration")
    if expected == "dental" and status == 200 and not ("răng" in diagnosis or "nướu" in diagnosis or "nha khoa" in drug_group):
        issues.append("expected_dental")
    if expected == "antifungal" and status == 200 and "kháng nấm" not in drug_group:
        issues.append("expected_antifungal")
    if expected == "ear_related" and status == 200 and not ("tai" in diagnosis or "tai" in ";".join(data.get("matched_symptoms_vi", [])).lower()):
        issues.append("expected_ear_related")
    if expected == "ankle_related" and status == 200 and not ("chân" in diagnosis or "chân" in ";".join(data.get("matched_symptoms_vi", [])).lower()):
        issues.append("expected_ankle_related")
    if expected == "red_flag" and status == 200 and not data.get("warning"):
        issues.append("missing_red_flag_warning")

    return issues


def main():
    client = app.test_client()
    results = []
    issue_counts = {}
    status_counts = {}

    for case in make_cases(500):
        response = client.post("/api/predict", json={"notes": case["text"], "symptoms": []})
        status = response.status_code
        status_counts[str(status)] = status_counts.get(str(status), 0) + 1
        data = response.get_json(silent=True) or {}
        issues = check_case(case, status, data)
        for issue in issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        summary = data.get("case_summary") or {}
        results.append(
            {
                "id": case["id"],
                "group": case["group"],
                "expected": case["expected"],
                "text": case["text"],
                "status": status,
                "issues": "; ".join(issues),
                "matched_symptoms": "; ".join(data.get("matched_symptoms_vi", [])),
                "diagnosis": summary.get("diagnosis", ""),
                "medication_name": summary.get("medication_name", ""),
                "drug_group": summary.get("drug_group", ""),
                "display_title": data.get("display_title", ""),
                "confidence": data.get("confidence", ""),
                "score_type": data.get("score_type", ""),
            }
        )

    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    csv_path = docs_dir / "stress_test_500_cases.csv"
    summary_path = docs_dir / "stress_test_500_summary.json"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    failed = [row for row in results if row["issues"]]
    summary = {
        "total": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "status_counts": status_counts,
        "issue_counts": issue_counts,
        "csv": str(csv_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failed:
        print("First failures:")
        for row in failed[:20]:
            print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
