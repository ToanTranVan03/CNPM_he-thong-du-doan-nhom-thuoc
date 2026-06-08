"""Khớp triệu chứng theo NGỮ NGHĨA bằng SBERT tiếng Việt.

Bổ sung cho khớp từ khóa cứng: câu lạ cùng nghĩa ("tịt mũi" ~ "nghẹt mũi",
"cổ phình to" ~ "bướu cổ") vẫn được nhận ra mà không cần liệt kê hết biến thể.

Thiết kế graceful: nếu chưa cài sentence-transformers hoặc tải model lỗi thì
is_available()=False và app.py tự động dùng đường khớp từ khóa như cũ.

app.py giữ quyền quyết định feature canonical: nó truyền vào danh sách cặp
(cụm tiếng Việt, feature tiếng Anh chuẩn) qua build_index().
"""
from __future__ import annotations
import os
import re

# Cho phép đổi model qua biến môi trường; có danh sách dự phòng.
_MODEL_CANDIDATES = [
    os.environ.get("VI_SBERT_MODEL", "keepitreal/vietnamese-sbert"),
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
]

_model = None
_available: bool | None = None
_phrase_embs = None          # numpy array [n_phrases, dim], đã chuẩn hoá L2
_phrase_features: list[str] = []   # feature canonical song song với từng phrase


def _load_model():
    global _model, _available
    if _available is not None:
        return _available
    for name in _MODEL_CANDIDATES:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(name)
            _available = True
            return True
        except Exception:
            continue
    _available = False
    return False


def is_available() -> bool:
    return bool(_load_model())


def build_index(pairs: list[tuple[str, str]]) -> bool:
    """pairs: (cụm_tiếng_việt, feature_canonical). Mã hoá & lưu để so khớp."""
    global _phrase_embs, _phrase_features
    if not _load_model() or not pairs:
        return False
    phrases = [p for p, _ in pairs]
    _phrase_features = [f for _, f in pairs]
    _phrase_embs = _model.encode(
        phrases, normalize_embeddings=True, convert_to_numpy=True, batch_size=64
    )
    return True


def _split_clauses(text: str) -> list[str]:
    parts = re.split(r"[,.;\n/]|\bvà\b|\brồi\b|\bkèm\b|\bvới\b", text)
    return [p.strip() for p in (parts or []) if len(p.strip()) >= 2]


def match(text: str, threshold: float = 0.6) -> set[str]:
    """Trả về tập feature canonical mà một mệnh đề trong text gần nghĩa vượt ngưỡng."""
    if not _available or _phrase_embs is None:
        return set()
    clauses = _split_clauses(text)
    if not clauses:
        return set()
    embs = _model.encode(clauses, normalize_embeddings=True, convert_to_numpy=True)
    sims = embs @ _phrase_embs.T  # cosine vì đã chuẩn hoá
    found = set()
    for i in range(sims.shape[0]):
        row = sims[i]
        j = int(row.argmax())
        if float(row[j]) >= threshold:
            found.add(_phrase_features[j])
    return found
