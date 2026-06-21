import sys
from pathlib import Path

# File đang nằm ở thư mục gốc CNPM2b
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"

sys.path.insert(0, str(BACKEND_DIR))

from scoring_service import (
    calculate_group_match_score,
    rank_drug_groups
)


def test_calculate_group_match_score_75_percent():
    found_symptoms = [
        "sot",
        "ho",
        "dom",
        "kho_tho"
    ]

    group_symptoms = [
        "ho",
        "dom",
        "kho_tho"
    ]

    result = calculate_group_match_score(
        found_symptoms,
        group_symptoms
    )

    assert result["score"] == 75.0
    assert result["matched_count"] == 3
    assert result["input_count"] == 4


def test_calculate_group_match_score_100_percent():
    found_symptoms = [
        "ho",
        "kho_tho"
    ]

    group_symptoms = [
        "ho",
        "kho_tho",
        "dom"
    ]

    result = calculate_group_match_score(
        found_symptoms,
        group_symptoms
    )

    assert result["score"] == 100.0
    assert result["matched_count"] == 2


def test_calculate_group_match_score_0_percent():
    found_symptoms = [
        "ho",
        "sot"
    ]

    group_symptoms = [
        "ngua",
        "hat_hoi"
    ]

    result = calculate_group_match_score(
        found_symptoms,
        group_symptoms
    )

    assert result["score"] == 0.0
    assert result["matched_count"] == 0


def test_rank_drug_groups_descending():
    found_symptoms = [
        "sot",
        "ho",
        "dom",
        "kho_tho"
    ]

    drug_groups = [
        {
            "group": "thuốc dị ứng",
            "symptoms": [
                "ngua",
                "hat_hoi"
            ]
        },
        {
            "group": "thuốc giãn phế quản",
            "symptoms": [
                "ho",
                "dom",
                "kho_tho"
            ]
        },
        {
            "group": "thuốc hạ sốt",
            "symptoms": [
                "sot"
            ]
        }
    ]

    results = rank_drug_groups(
        found_symptoms,
        drug_groups
    )

    assert results[0]["group"] == "thuốc giãn phế quản"
    assert results[0]["score"] == 75.0

    assert results[1]["group"] == "thuốc hạ sốt"
    assert results[1]["score"] == 25.0

    assert results[2]["group"] == "thuốc dị ứng"
    assert results[2]["score"] == 0.0