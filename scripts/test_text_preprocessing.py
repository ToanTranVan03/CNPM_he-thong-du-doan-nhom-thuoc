"""Unit/regression tests for backend text preprocessing helpers.

Run: python scripts/test_text_preprocessing.py
"""

import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from text_preprocessing import remove_vietnamese_stop_words  # noqa: E402


def check(name: str, actual: str, expected: str) -> bool:
    ok = actual == expected
    print(f"{'OK' if ok else 'FAIL'} {name}: {actual!r}")
    if not ok:
        print(f"  expected: {expected!r}")
    return ok


def check_condition(name: str, condition: bool, detail: str) -> bool:
    print(f"{'OK' if condition else 'FAIL'} {name}: {detail}")
    return condition


def normalization_checks() -> list[bool]:
    # Keep app import deterministic and avoid loading semantic models.
    os.environ.setdefault("SEMANTIC_MATCH", "0")
    import app as A  # noqa: E402
    import context_safety  # noqa: E402

    return [
        check(
            "normalize removes accents, punctuation and extra spaces",
            A.normalize("  Đau   MẮT__và, nhìn   mờ!! "),
            "dau mat va nhin mo",
        ),
        check(
            "normalize_exact keeps Vietnamese accents",
            A.normalize_exact("  Đau   MẮT__và, nhìn   mờ!! "),
            "đau mắt và nhìn mờ",
        ),
        check(
            "normalize_email removes all whitespace and lowercases",
            A.normalize_email("  Admin @GMAIL.COM "),
            "admin@gmail.com",
        ),
        check(
            "context_safety.norm normalizes broadly",
            context_safety.norm("  Suy   THẬN_mạn!!! "),
            "suy than man",
        ),
        check(
            "context_safety.low lowercases but keeps accents",
            context_safety.low("  Viêm   gân_gối  "),
            "viêm gân gối",
        ),
        check_condition(
            "accent-preserving normalization keeps gan/gân distinct",
            context_safety.low("gan gân thận than") == "gan gân thận than",
            context_safety.low("gan gân thận than"),
        ),
    ]


def integration_checks() -> list[bool]:
    # Keep this test deterministic and avoid loading semantic models.
    os.environ.setdefault("SEMANTIC_MATCH", "0")
    import app as A  # noqa: E402

    stopword_bridge = A.ordered_symptoms_from_text("Tôi đau ở họng và ho")
    stopword_labels = [A.symptom_label_vi(item).lower() for item in stopword_bridge]
    negated = A.ordered_symptoms_from_text("Tôi không sốt nhưng ho")
    negated_labels = [A.symptom_label_vi(item).lower() for item in negated]
    eye_case = A.ordered_symptoms_from_text(
        "\u0111au m\u1eaft v\u00e0 nh\u00ecn m\u1edd m\u1eaft c\u00f3 d\u1ea5u hi\u1ec7u \u0111\u1ecf"
    )
    eye_labels = [A.symptom_label_vi(item).lower() for item in eye_case]

    return [
        check_condition(
            "stop-word bridge still detects sore throat",
            any("họng" in label for label in stopword_labels),
            ", ".join(stopword_labels),
        ),
        check_condition(
            "original matching still detects cough",
            any(label == "ho" for label in stopword_labels),
            ", ".join(stopword_labels),
        ),
        check_condition(
            "negation filtering remains downstream",
            any(label == "ho" for label in negated_labels) and not any("sốt" in label for label in negated_labels),
            ", ".join(negated_labels),
        ),
        check_condition(
            "eye phrase does not collide with muscle wasting",
            not any("teo cơ" == label for label in eye_labels),
            ", ".join(eye_labels),
        ),
        check_condition(
            "eye redness phrase is recognized",
            any("đỏ mắt" in label or "mắt đỏ" in label for label in eye_labels),
            ", ".join(eye_labels),
        ),
    ]


def main() -> int:
    results = [
        check(
            "remove conjunctions and prepositions",
            remove_vietnamese_stop_words("Tôi bị ho và đau họng với sốt nhẹ"),
            "ho đau họng sốt nhẹ",
        ),
        check(
            "keep negation and time context",
            remove_vietnamese_stop_words("Tôi không sốt sau khi uống thuốc"),
            "không sốt sau khi uống thuốc",
        ),
        check(
            "extra stop words",
            remove_vietnamese_stop_words("Bệnh nhân ho nhiều", extra_stop_words={"bệnh", "nhân"}),
            "ho nhiều",
        ),
        check(
            "accent insensitive",
            remove_vietnamese_stop_words("Toi bi ho va dau hong", accent_insensitive=True),
            "ho dau hong",
        ),
    ]
    results.extend(normalization_checks())
    results.extend(integration_checks())
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
