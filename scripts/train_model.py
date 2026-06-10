import argparse
import csv
import io
import json
import os
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.feature_extraction.text import TfidfVectorizer
from symptom_search_model import SymptomSearchModel, split_symptom_phrases


def read_csv_path(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def read_training_csv(zip_path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open("Training.csv") as training_file:
            text_file = io.TextIOWrapper(training_file, encoding="utf-8-sig", newline="")
            return list(csv.DictReader(text_file))


def read_disease_json(zip_path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open("disease_database_en.json") as json_file:
            data = json.load(json_file)
    records = []
    for row in data:
        disease = str(row.get("disease", "")).strip()
        common_symptom = str(row.get("common_symptom", "")).strip()
        treatment = str(row.get("treatment", "")).strip()
        if disease and common_symptom:
            records.append(
                {
                    "disease": disease,
                    "common_symptom": common_symptom,
                    "treatment": treatment,
                }
            )
    return records


def data_kind(data_path: Path) -> str:
    if data_path.suffix.lower() == ".csv":
        return "mapped_csv"

    with zipfile.ZipFile(data_path) as archive:
        names = set(archive.namelist())
    if "Training.csv" in names:
        return "training_csv"
    if "disease_database_en.json" in names:
        return "disease_json"
    raise ValueError("Data must be a CSV or a zip containing Training.csv/disease_database_en.json.")


def symptoms_to_text(row: dict[str, str]) -> str:
    symptoms = []
    for column, value in row.items():
        if column == "prognosis":
            continue
        try:
            active = int(float(str(value).strip() or "0")) == 1
        except ValueError:
            active = False
        if active:
            symptoms.append(column)
    return " ".join(symptoms)


def split_symptoms(text: str) -> list[str]:
    symptoms = []
    seen = set()
    for part in str(text).replace("|", ";").split(";"):
        symptom = " ".join(part.strip().split())
        if not symptom:
            continue
        key = symptom.lower()
        if key not in seen:
            seen.add(key)
            symptoms.append(symptom)
    return symptoms


def unique_sorted(values) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()}, key=str.lower)


def infer_text_column(rows: list[dict[str, str]], requested: str | None) -> str:
    if requested:
        return requested
    columns = set(rows[0].keys())
    for column in ("trieu_chung", "mo_ta_benh_an", "symptoms", "text"):
        if column in columns:
            return column
    raise ValueError("Could not infer text column. Pass --text-column explicitly.")


def infer_target_column(rows: list[dict[str, str]], requested: str | None) -> str:
    if requested:
        return requested
    columns = set(rows[0].keys())
    for column in ("nhom_thuoc", "chan_doan_du_kien", "prognosis", "label"):
        if column in columns:
            return column
    raise ValueError("Could not infer target column. Pass --target-column explicitly.")


def label_type_for_target(target_column: str) -> str:
    if target_column == "nhom_thuoc":
        return "drug_group"
    if target_column in {"chan_doan_du_kien", "prognosis"}:
        return "disease"
    return target_column


def build_text_classifier(random_state: int, min_class_count: int) -> Pipeline:
    # Hyperparams tinh chỉnh được qua env để thử nghiệm "sắc hơn" (vòng 6 Phần A) mà không
    # đổi chữ ký hàm. Mặc định = cấu hình cũ (tái lập model hiện tại).
    ngram_max = int(os.environ.get("TFIDF_NGRAM_MAX", "2"))
    min_df = int(os.environ.get("TFIDF_MIN_DF", "1"))
    max_df = float(os.environ.get("TFIDF_MAX_DF", "1.0"))
    svm_c = float(os.environ.get("SVM_C", "1.0"))
    svm = LinearSVC(
        C=svm_c,
        class_weight="balanced",
        random_state=random_state,
        max_iter=10000,
    )
    classifier = (
        CalibratedClassifierCV(
            estimator=svm,
            method="sigmoid",
            cv=min(3, min_class_count),
            n_jobs=-1,
        )
        if min_class_count >= 2
        else svm
    )
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    token_pattern=r"(?u)\b[\w.()'-]+\b",
                    lowercase=True,
                    ngram_range=(1, ngram_max),
                    min_df=min_df,
                    max_df=max_df,
                    sublinear_tf=True,
                ),
            ),
            ("svm", classifier),
        ]
    )


def train_json_search(data_path: Path, output_dir: Path) -> None:
    records = read_disease_json(data_path)
    if not records:
        raise ValueError("disease_database_en.json does not contain usable disease records.")

    model = SymptomSearchModel().fit(records)
    feature_map = {}
    for record in records:
        for phrase in split_symptom_phrases(record["common_symptom"]):
            feature_map.setdefault(phrase.lower(), phrase)
    features = sorted(feature_map.values(), key=str.lower)

    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "disease_model.joblib")

    metadata = {
        "model_type": "json_symptom_search",
        "label_type": "disease",
        "input_type": "symptom_text",
        "score_type": "cosine_similarity",
        "accuracy": None,
        "features": features,
        "classes": sorted({record["disease"] for record in records}),
        "rows": len(records),
        "source": str(data_path),
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "classification_report.json").write_text(
        json.dumps(
            {
                "note": "disease_database_en.json has one symptom text per disease, so the saved model uses TF-IDF cosine search instead of a train/test classifier."
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"Rows: {len(records)}")
    print(f"Features: {len(features)}")
    print("Model: TF-IDF symptom search")
    print(f"Classes: {len(metadata['classes'])}")
    print(f"Saved model: {output_dir / 'disease_model.joblib'}")
    print(f"Saved metadata: {output_dir / 'metadata.json'}")


def train_text_rows(
    rows: list[dict[str, str]],
    output_dir: Path,
    test_size: float,
    random_state: int,
    text_column: str,
    target_column: str,
    source: Path,
    features_data: Path | None = None,
) -> None:
    if text_column not in rows[0]:
        raise ValueError(f"CSV does not contain text column '{text_column}'.")
    if target_column not in rows[0]:
        raise ValueError(f"CSV does not contain target column '{target_column}'.")

    examples = [
        (str(row.get(text_column, "")).strip(), str(row.get(target_column, "")).strip())
        for row in rows
    ]
    examples = [(text, label) for text, label in examples if text and label]
    if not examples:
        raise ValueError("No usable training rows after removing blank text/target values.")

    x = [text for text, _ in examples]
    y = [label for _, label in examples]
    class_counts = Counter(y)
    min_class_count = min(class_counts.values())
    stratify = y if min_class_count >= 2 else None

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )

    model = build_text_classifier(random_state, min(Counter(y_train).values()))
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    accuracy = accuracy_score(y_test, predictions)
    report = classification_report(y_test, predictions, output_dict=True, zero_division=0)

    # Danh sách features (từ vựng triệu chứng cho bộ chọn + tầng dịch VN→EN) nên lấy từ
    # data ĐẦY ĐỦ, không bị ảnh hưởng bởi việc khử trùng/cap của tập train. Nếu truyền
    # --features-data thì build từ file đó; nếu không thì build từ rows (bỏ dòng natural).
    feature_rows = read_csv_path(features_data) if features_data else rows
    features = []
    if feature_rows and "trieu_chung" in feature_rows[0]:
        feature_values = []
        for row in feature_rows:
            # Bỏ qua dòng mô tả tự nhiên (cả câu, không phải triệu chứng atomic) để
            # danh sách features không bị phình bởi câu đầy đủ.
            if "natural" in str(row.get("source", "")).lower():
                continue
            feature_values.extend(split_symptoms(row.get("trieu_chung", "")))
        features = unique_sorted(feature_values)

    if not features:
        features = sorted(model.named_steps["tfidf"].get_feature_names_out().tolist(), key=str.lower)

    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "disease_model.joblib")

    metadata = {
        "model_type": "tfidf_linear_svm",
        "label_type": label_type_for_target(target_column),
        "input_type": "symptom_text",
        "score_type": "probability" if hasattr(model, "predict_proba") else "decision",
        "accuracy": accuracy,
        "features": features,
        "classes": sorted(class_counts.keys(), key=str.lower),
        "test_size": test_size,
        "random_state": random_state,
        "rows": len(examples),
        "source": str(source),
        "text_column": text_column,
        "target_column": target_column,
        "class_counts": dict(sorted(class_counts.items(), key=lambda item: item[0].lower())),
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "classification_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Rows: {len(examples)}")
    print(f"Features: {len(features)}")
    print("Model: TF-IDF + Linear SVM")
    print(f"Text column: {text_column}")
    print(f"Target column: {target_column}")
    print(f"Classes: {len(class_counts)}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Saved model: {output_dir / 'disease_model.joblib'}")
    print(f"Saved metadata: {output_dir / 'metadata.json'}")


def train_binary_training_csv(
    data_path: Path,
    output_dir: Path,
    test_size: float,
    random_state: int,
) -> None:
    rows = read_training_csv(data_path)
    if not rows or "prognosis" not in rows[0]:
        raise ValueError("Training.csv must contain a 'prognosis' target column.")

    text_rows = []
    for row in rows:
        converted = dict(row)
        converted["symptom_text"] = symptoms_to_text(row)
        text_rows.append(converted)

    train_text_rows(
        rows=text_rows,
        output_dir=output_dir,
        test_size=test_size,
        random_state=random_state,
        text_column="symptom_text",
        target_column="prognosis",
        source=data_path,
    )


def write_reference_summary(rows: list[dict[str, str]], output_dir: Path, source: Path) -> None:
    by_group = defaultdict(lambda: {"diagnoses": set(), "medications": set(), "symptoms": set()})
    by_diagnosis = defaultdict(lambda: {"groups": set(), "medications": set(), "symptoms": set()})

    for row in rows:
        group = str(row.get("nhom_thuoc", "")).strip()
        diagnosis = str(row.get("chan_doan_du_kien", "")).strip()
        medication = str(row.get("ten_thuoc", "")).strip()
        symptoms = split_symptoms(row.get("trieu_chung", ""))

        if group:
            if diagnosis:
                by_group[group]["diagnoses"].add(diagnosis)
            if medication:
                by_group[group]["medications"].add(medication)
            by_group[group]["symptoms"].update(symptoms)

        if diagnosis:
            if group:
                by_diagnosis[diagnosis]["groups"].add(group)
            if medication:
                by_diagnosis[diagnosis]["medications"].add(medication)
            by_diagnosis[diagnosis]["symptoms"].update(symptoms)

    summary = {
        "source": str(source),
        "drug_groups": {
            group: {
                "diagnoses": unique_sorted(values["diagnoses"])[:50],
                "medications": unique_sorted(values["medications"])[:50],
                "symptoms": unique_sorted(values["symptoms"])[:80],
            }
            for group, values in sorted(by_group.items(), key=lambda item: item[0].lower())
        },
        "diagnoses": {
            diagnosis: {
                "drug_groups": unique_sorted(values["groups"])[:20],
                "medications": unique_sorted(values["medications"])[:50],
                "symptoms": unique_sorted(values["symptoms"])[:80],
            }
            for diagnosis, values in sorted(by_diagnosis.items(), key=lambda item: item[0].lower())
        },
    }
    (output_dir / "mapped_drug_group_reference.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def train(
    data_path: Path,
    output_dir: Path,
    test_size: float,
    random_state: int,
    text_column: str | None,
    target_column: str | None,
    features_data: Path | None = None,
) -> None:
    kind = data_kind(data_path)
    if kind == "disease_json":
        train_json_search(data_path, output_dir)
        return
    if kind == "training_csv":
        train_binary_training_csv(data_path, output_dir, test_size, random_state)
        return

    rows = read_csv_path(data_path)
    if not rows:
        raise ValueError("CSV does not contain any rows.")

    resolved_text_column = infer_text_column(rows, text_column)
    resolved_target_column = infer_target_column(rows, target_column)
    train_text_rows(
        rows=rows,
        output_dir=output_dir,
        test_size=test_size,
        random_state=random_state,
        text_column=resolved_text_column,
        target_column=resolved_target_column,
        source=data_path,
        features_data=features_data,
    )
    if {"nhom_thuoc", "chan_doan_du_kien", "ten_thuoc", "trieu_chung"}.issubset(rows[0].keys()):
        write_reference_summary(rows, output_dir, data_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train TF-IDF + Linear SVM model.")
    parser.add_argument(
        "--data",
        type=Path,
        default=PROJECT_ROOT / "data" / "train_combined.csv",
        help="Đường dẫn data train. Mặc định train_combined.csv (46k, có câu tiếng Việt tự "
        "nhiên + đủ ví dụ sốt rét/kháng virus) — nguồn chuẩn sau audit vòng 6.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "models",
        help="Directory to save trained model files.",
    )
    parser.add_argument("--text-column", default=None)
    parser.add_argument("--target-column", default=None)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--features-data",
        type=Path,
        default=None,
        help="File data đầy đủ để build danh sách features (từ vựng triệu chứng). "
        "Nếu train trên tập đã khử trùng/cap, truyền data gốc vào đây để giữ đủ từ vựng.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(
        args.data,
        args.out,
        args.test_size,
        args.random_state,
        args.text_column,
        args.target_column,
        args.features_data,
    )
