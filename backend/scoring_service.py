from typing import Iterable


def normalize_symptom(value: str) -> str:
    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def unique_normalized(values: Iterable[str]) -> list[str]:
    result = []
    seen = set()

    for value in values or []:
        item = normalize_symptom(value)

        if item and item not in seen:
            seen.add(item)
            result.append(item)

    return result


def calculate_group_match_score(found_symptoms: list[str], group_symptoms: list[str]) -> dict:
    """
    SCRUM-63 / Task 32:
    Tính % phù hợp của một nhóm thuốc dựa trên số triệu chứng khớp.

    Công thức:
    score = số triệu chứng khớp / tổng số triệu chứng người dùng nhập * 100
    """

    found = unique_normalized(found_symptoms)
    group = unique_normalized(group_symptoms)

    if not found:
        return {
            "score": 0.0,
            "matched_count": 0,
            "input_count": 0,
            "matched_symptoms": []
        }

    matched = sorted(list(set(found) & set(group)))
    score = round((len(matched) / len(found)) * 100, 2)

    return {
        "score": score,
        "matched_count": len(matched),
        "input_count": len(found),
        "matched_symptoms": matched
    }


def rank_drug_groups(found_symptoms: list[str], drug_groups: list[dict]) -> list[dict]:
    """
    SCRUM-64 / Task 33:
    Tính điểm cho nhiều nhóm thuốc và sắp xếp giảm dần theo score.
    """

    results = []

    for group in drug_groups or []:
        group_name = group.get("group") or group.get("name") or group.get("ten_nhom")
        group_symptoms = group.get("symptoms") or group.get("trieu_chung") or []

        score_info = calculate_group_match_score(found_symptoms, group_symptoms)

        results.append({
            "group": group_name,
            "score": score_info["score"],
            "matched_count": score_info["matched_count"],
            "input_count": score_info["input_count"],
            "matched_symptoms": score_info["matched_symptoms"]
        })

    results.sort(
        key=lambda item: (
            item["score"],
            item["matched_count"]
        ),
        reverse=True
    )

    return results