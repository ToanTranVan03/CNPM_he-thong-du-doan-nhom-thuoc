import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SymptomSearchModel:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            token_pattern=r"(?u)\b[\w.()'-]+\b",
            lowercase=True,
            ngram_range=(1, 2),
        )
        self.symptom_matrix = None
        self.classes_ = []
        self.common_symptoms_ = []
        self.treatments_ = {}

    def fit(self, records):
        self.classes_ = [record["disease"] for record in records]
        self.common_symptoms_ = [record["common_symptom"] for record in records]
        self.treatments_ = {record["disease"]: record.get("treatment", "") for record in records}
        self.symptom_matrix = self.vectorizer.fit_transform(self.common_symptoms_)
        return self

    def _as_text_list(self, inputs):
        if isinstance(inputs, str):
            return [inputs]
        return [str(item) for item in inputs]

    def _scores(self, inputs):
        texts = self._as_text_list(inputs)
        query_matrix = self.vectorizer.transform(texts)
        return cosine_similarity(query_matrix, self.symptom_matrix)

    def predict(self, inputs):
        scores = self._scores(inputs)
        return [self.classes_[row.argmax()] for row in scores]

    def predict_proba(self, inputs):
        return self._scores(inputs)


def split_symptom_phrases(text: str) -> list[str]:
    raw_parts = re.split(r",|;|\band\b|\bor\b", str(text), flags=re.IGNORECASE)
    phrases = []
    seen = set()
    for part in raw_parts:
        phrase = re.sub(r"\s+", " ", part.strip(" .:-")).strip()
        if len(phrase) < 3:
            continue
        key = phrase.lower()
        if key not in seen:
            seen.add(key)
            phrases.append(phrase)
    return phrases

