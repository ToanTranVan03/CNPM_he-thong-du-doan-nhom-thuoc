import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import app


def mapping_source(feature: str) -> str:
    lookup_key = app.symptom_lookup_key(feature)
    manual = app.VI_SYMPTOM_KEYWORDS.get(feature) or app.VI_SYMPTOM_KEYWORDS.get(lookup_key)
    auto = app.auto_symptom_keywords(feature)
    if manual and auto:
        return "manual+auto"
    if manual:
        return "manual"
    if auto:
        return "auto"
    return "unmapped"


def main() -> None:
    rows = []
    source_counts = {}
    for feature in app.features:
        keywords = app.symptom_keywords(feature)
        source = mapping_source(feature)
        source_counts[source] = source_counts.get(source, 0) + 1
        rows.append(
            {
                "feature_en": feature,
                "label_vi": app.symptom_label_vi(feature),
                "keywords_vi": "; ".join(keywords),
                "mapping_source": source,
            }
        )

    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    csv_path = docs_dir / "symptom_mapping_audit.csv"
    json_path = docs_dir / "symptom_mapping_audit_summary.json"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["feature_en", "label_vi", "keywords_vi", "mapping_source"],
        )
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "features": len(app.features),
        "mapped": sum(count for source, count in source_counts.items() if source != "unmapped"),
        "unmapped": source_counts.get("unmapped", 0),
        "source_counts": source_counts,
    }
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"CSV: {csv_path}")
    print(f"Summary: {json_path}")


if __name__ == "__main__":
    main()
