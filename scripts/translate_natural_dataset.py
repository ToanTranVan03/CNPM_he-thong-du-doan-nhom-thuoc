"""Dịch mô tả triệu chứng EN->VI để dựng data train tiếng Việt tự nhiên (Hạng mục A2).

Provider mặc định: NLLB offline (facebook/nllb-200-distilled-600M) — miễn phí, chạy local,
không cần API key. License CC-BY-NC (dùng cho đồ án/nghiên cứu nội bộ). Lần đầu chạy sẽ tự
tải model (~2.4GB) về cache HuggingFace, các lần sau offline hoàn toàn.

Có cache (JSONL append-only) theo text_hash: rerun KHÔNG dịch lại câu đã có.
Xuất schema trung gian (audit-friendly), KHÔNG phải schema train cuối — build script riêng
(build_vietnamese_natural_dataset.py) mới đổi sang schema train.

Ví dụ:
  # Dry-run kiểm tra chất lượng 30 câu (in EN/VI cạnh nhau, ưu tiên câu có phủ định)
  python scripts/translate_natural_dataset.py --sources gretel_train --limit 30 --review-print 30
  # Chạy đầy đủ train + test (test đánh dấu split=holdout, không bao giờ vào train)
  python scripts/translate_natural_dataset.py --sources gretel_train,gretel_test
"""
import argparse
import csv
import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

# tên nguồn -> (file jsonl, split). gretel_test LUÔN là holdout, không được vào train.
SOURCES = {
    "gretel_train": (RAW / "gretel_symptom_to_diagnosis_train.jsonl", "train"),
    "gretel_test": (RAW / "gretel_symptom_to_diagnosis_test.jsonl", "holdout"),
}

DEFAULT_OUT = ROOT / "data" / "vietnamese_natural_all.csv"
DEFAULT_CACHE = ROOT / "data" / "translation_cache.jsonl"
DEFAULT_MODEL = "facebook/nllb-200-distilled-600M"

FIELDS = [
    "source_id", "source_dataset", "split", "text_en", "text_vi",
    "chan_doan_du_kien", "translation_provider", "translation_status", "text_hash",
]

NEGATION_HINTS = (" no ", " not ", " without ", "n't ", "denies", "negative for", "absence of")

# Glossary y khoa CÓ ĐIỀU KIỆN: (từ khóa EN, cụm VI sai, cụm VI đúng).
# Chỉ sửa khi câu EN chứa từ khóa -> tránh phá các ca tiếng Việt hợp lệ
# (vd "âm đạo" đúng cho ca tiết niệu/phụ khoa, chỉ sai khi nguồn là "sinus").
GLOSSARY = [
    ("sinus", "âm đạo", "xoang"),
    ("rash", "mụn trứng cá", "phát ban"),
    ("rashes", "mụn trứng cá", "phát ban"),
    ("limb", "chi nhánh", "tay chân"),
    ("limb", "xương chân", "tay chân"),
    ("chill", "chớp lạnh", "ớn lạnh"),
    ("chill", "cảm lạnh", "ớn lạnh"),
    ("cloud", "mây", "đục"),
    ("cramp", "rắc rối", "chuột rút"),
    ("lightheaded", "sốc", "choáng váng"),
    ("flak", "vùi", "bong tróc"),
    ("flak", "nhăn", "bong tróc"),
    ("flake", "vùi", "bong tróc"),
    ("phlegm", "đờm dãi", "đờm"),
    ("blister", "mụn bướm", "mụn nước"),
    ("urin", "Urin", "Nước tiểu"),
    ("urin", "urine", "nước tiểu"),
]


def text_hash(s: str) -> str:
    return hashlib.sha1(s.strip().encode("utf-8")).hexdigest()[:16]


def split_sentences(text: str) -> list[str]:
    """Tách câu theo dấu kết câu để NLLB dịch từng câu (chống bỏ sót mệnh đề)."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def apply_glossary(en_text: str, vi_text: str) -> str:
    en_low = en_text.lower()
    for en_kw, vi_wrong, vi_right in GLOSSARY:
        if en_kw in en_low and vi_wrong in vi_text:
            vi_text = vi_text.replace(vi_wrong, vi_right)
    return vi_text


def read_source(name: str, limit: int | None) -> list[dict]:
    path, split = SOURCES[name]
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            en = d["input_text"].strip()
            dx = d["output_text"].strip().lower()
            rows.append({
                "source_id": f"{name}:{i}",
                "source_dataset": name,
                "split": split,
                "text_en": en,
                "chan_doan_du_kien": dx,
                "text_hash": text_hash(en),
            })
            if limit and len(rows) >= limit:
                break
    return rows


def load_cache(path: Path) -> dict[str, str]:
    """Cache mức CÂU: key = sent_hash ('h'), value = bản dịch VI."""
    cache = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                if "h" in d:  # bỏ qua dòng schema cũ (text-level) nếu có
                    cache[d["h"]] = d["vi"]
    return cache


class NLLBTranslator:
    """Wrapper NLLB EN->VI. Lazy import torch/transformers để --help không cần model."""

    def __init__(self, model_name=DEFAULT_MODEL, src="eng_Latn", tgt="vie_Latn", device=None):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.torch = torch
        print(f"[NLLB] load {model_name} ... (lần đầu sẽ tải ~2.4GB)", flush=True)
        t0 = time.time()
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        self.tok.src_lang = src
        self.tgt_id = self.tok.convert_tokens_to_ids(tgt)
        print(f"[NLLB] sẵn sàng trên {self.device} ({time.time() - t0:.1f}s)", flush=True)

    def translate_batch(self, texts: list[str], max_length=400, num_beams=4) -> list[str]:
        enc = self.tok(texts, return_tensors="pt", padding=True, truncation=True,
                       max_length=max_length).to(self.device)
        with self.torch.no_grad():
            gen = self.model.generate(**enc, forced_bos_token_id=self.tgt_id,
                                      max_length=max_length, num_beams=num_beams)
        return [s.strip() for s in self.tok.batch_decode(gen, skip_special_tokens=True)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="gretel_train,gretel_test",
                    help="Danh sách nguồn, phân tách bằng dấu phẩy. Có: " + ", ".join(SOURCES))
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--provider", default="nllb", choices=["nllb"],
                    help="Hiện chỉ hỗ trợ nllb offline; chừa chỗ cho provider khác.")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=None, help="Giới hạn số câu mỗi nguồn (dry-run).")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--review-print", type=int, default=0,
                    help="In N cặp EN/VI để soi chất lượng (ưu tiên câu có phủ định).")
    args = ap.parse_args()

    src_names = [s.strip() for s in args.sources.split(",") if s.strip()]
    for name in src_names:
        if name not in SOURCES:
            sys.exit(f"Nguồn không hợp lệ: {name}. Có: {', '.join(SOURCES)}")

    # 1. đọc nguồn; tách CÂU để dịch từng câu (chống bỏ sót mệnh đề)
    all_rows = []
    for name in src_names:
        all_rows.extend(read_source(name, args.limit))
    for r in all_rows:
        r["sentences"] = split_sentences(r["text_en"])
    uniq_sents = {}  # sent_hash -> câu EN
    for r in all_rows:
        for s in r["sentences"]:
            uniq_sents.setdefault(text_hash(s), s)
    print(f"Tổng dòng: {len(all_rows)} | câu (sentence) EN duy nhất: {len(uniq_sents)}")

    # 2. dịch các CÂU chưa có trong cache
    cache = load_cache(args.cache)
    todo = [(h, en) for h, en in uniq_sents.items() if h not in cache]
    print(f"Cache hit: {len(uniq_sents) - len(todo)} | cần dịch mới: {len(todo)}")

    if todo:
        tr = NLLBTranslator(args.model) if args.provider == "nllb" else None
        args.cache.parent.mkdir(parents=True, exist_ok=True)
        with open(args.cache, "a", encoding="utf-8") as cf:
            for i in range(0, len(todo), args.batch_size):
                chunk = todo[i:i + args.batch_size]
                vis = tr.translate_batch([en for _, en in chunk])
                for (h, en), vi in zip(chunk, vis):
                    cache[h] = vi
                    cf.write(json.dumps({"h": h, "en": en, "vi": vi,
                                         "provider": args.provider}, ensure_ascii=False) + "\n")
                cf.flush()
                print(f"  dịch {min(i + args.batch_size, len(todo))}/{len(todo)}", flush=True)

    # 3. ghép câu -> text_vi từng dòng + áp glossary y khoa
    row_vi = {}
    for r in all_rows:
        pieces = [cache.get(text_hash(s), "") for s in r["sentences"]]
        vi = " ".join(p for p in pieces if p).strip()
        if vi:
            vi = apply_glossary(r["text_en"], vi)
        row_vi[r["source_id"]] = vi

    # 4. ghi output CSV (atomic: temp -> replace)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in all_rows:
            vi = row_vi[r["source_id"]]
            w.writerow({
                "source_id": r["source_id"],
                "source_dataset": r["source_dataset"],
                "split": r["split"],
                "text_en": r["text_en"],
                "text_vi": vi,
                "chan_doan_du_kien": r["chan_doan_du_kien"],
                "translation_provider": args.provider,
                "translation_status": "ok" if vi else "missing",
                "text_hash": r["text_hash"],
            })
    tmp.replace(args.out)

    n_ok = sum(1 for r in all_rows if row_vi[r["source_id"]])
    print(f"\nGhi {len(all_rows)} dòng -> {args.out}  (dịch ok: {n_ok})")

    # manifest
    manifest = {
        "provider": args.provider, "model": args.model,
        "sources": src_names, "rows": len(all_rows), "unique_sentences": len(uniq_sents),
        "translated_ok": n_ok, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    mpath = args.out.with_name("vietnamese_natural_manifest.json")
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Manifest -> {mpath}")

    # 4. review-print: soi chất lượng (ưu tiên câu có phủ định)
    if args.review_print:
        neg = [r for r in all_rows if any(k in (" " + r["text_en"].lower() + " ") for k in NEGATION_HINTS)]
        rest = [r for r in all_rows if r not in neg]
        sample = (neg + rest)[:args.review_print]
        print(f"\n===== SOI CHẤT LƯỢNG {len(sample)} câu (phủ định trước: {len(neg)}) =====")
        for r in sample:
            print(f"\n[{r['source_id']}] dx={r['chan_doan_du_kien']}")
            print(f"  EN: {r['text_en']}")
            print(f"  VI: {row_vi.get(r['source_id']) or '(chưa dịch)'}")


if __name__ == "__main__":
    main()
