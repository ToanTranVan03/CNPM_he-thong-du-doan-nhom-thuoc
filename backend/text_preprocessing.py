"""Utilities for Vietnamese text preprocessing in the backend."""

import re
import unicodedata
from collections.abc import Iterable


# Stop-words scoped to function words: conjunctions, prepositions, particles,
# auxiliaries and common filler words. Negation and time/causal words are kept
# out of this set because they change medical meaning.
VIETNAMESE_STOP_WORDS = frozenset(
    {
        "ai",
        "anh",
        "bao",
        "bằng",
        "bị",
        "bởi",
        "các",
        "cái",
        "cần",
        "càng",
        "cho",
        "chị",
        "chỉ",
        "chúng",
        "có",
        "của",
        "cùng",
        "cũng",
        "đã",
        "đang",
        "đây",
        "để",
        "đến",
        "đều",
        "đi",
        "đó",
        "được",
        "em",
        "gì",
        "hay",
        "hơn",
        "là",
        "lại",
        "lên",
        "mà",
        "mình",
        "một",
        "nào",
        "này",
        "nên",
        "nếu",
        "ngay",
        "người",
        "nhé",
        "như",
        "nhưng",
        "những",
        "nữa",
        "ở",
        "ra",
        "rằng",
        "rất",
        "rồi",
        "sẽ",
        "thì",
        "theo",
        "tôi",
        "tới",
        "trên",
        "và",
        "vào",
        "vẫn",
        "về",
        "vì",
        "với",
        "vừa",
    }
)


def _strip_accents(value: str) -> str:
    text = unicodedata.normalize("NFD", value)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


def _tokenize_vietnamese_text(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def remove_vietnamese_stop_words(
    text: str,
    *,
    extra_stop_words: Iterable[str] | None = None,
    accent_insensitive: bool = False,
) -> str:
    """Return Vietnamese text with common function stop-words removed.

    The function is intentionally not wired into symptom extraction by default:
    words like "không", "chưa", "sau", and "trước" can change clinical meaning,
    so callers should decide where this preprocessing is safe to apply.
    """
    if not text:
        return ""

    stop_words = set(VIETNAMESE_STOP_WORDS)
    if extra_stop_words:
        stop_words.update(word.strip().lower() for word in extra_stop_words if str(word).strip())

    tokens = _tokenize_vietnamese_text(text)
    if accent_insensitive:
        normalized_stop_words = {_strip_accents(word) for word in stop_words}
        kept = [token for token in tokens if _strip_accents(token) not in normalized_stop_words]
    else:
        kept = [token for token in tokens if token not in stop_words]

    return " ".join(kept)
