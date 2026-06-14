"""Scraper nhẹ (requests + BeautifulSoup) cho nguồn dược tiếng Việt.

Đây là TEMPLATE tôn trọng robots/rate-limit. Mặc định chạy ở chế độ --dry-run
(chỉ tải 1 trang để kiểm tra selector), KHÔNG cào ồ ạt.

Ví dụ:
    python scripts/scrape_vn_drugs.py --dry-run
    python scripts/scrape_vn_drugs.py --max-pages 5 --out data/raw/vn_drugs.csv

Quy tắc: delay >=1s/req, User-Agent thật, chỉ lấy dữ liệu công khai phục vụ học tập.
Trước khi cào thật: đọc robots.txt của trang và xin phép nếu cần.
"""
import argparse, csv, time, sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
import urllib.robotparser as robotparser

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept-Language": "vi,en;q=0.8"}

# Cấu hình ví dụ cho trungtamthuoc.com (đổi selector theo trang thực tế khi chạy)
SOURCE = {
    "name": "trungtamthuoc",
    "list_url": "https://trungtamthuoc.com/thuoc",
    "item_selector": "a.product-name, a.title, h3 a",  # nhiều fallback
}


def can_fetch(url: str) -> bool:
    parts = urlparse(url)
    rp = robotparser.RobotFileParser()
    rp.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
    try:
        rp.read()
    except Exception:
        print("  [!] Không đọc được robots.txt — dừng cho an toàn.")
        return False
    return rp.can_fetch(UA, url)


def get(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except Exception as e:
        print(f"  [!] Lỗi tải {url}: {e}")
        return None


def parse_drug_page(soup: BeautifulSoup, url: str) -> dict:
    """Trích thông tin thuốc — selector cần chỉnh theo cấu trúc trang thật."""
    def txt(sel):
        el = soup.select_one(sel)
        return el.get_text(" ", strip=True) if el else ""
    return {
        "ten_thuoc": txt("h1"),
        "hoat_chat": txt(".active-ingredient, .hoat-chat"),
        "nhom_thuoc": txt(".drug-group, .nhom-thuoc"),
        "chi_dinh": txt(".indication, .chi-dinh"),
        "url": url,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Chỉ tải 1 trang list để kiểm tra")
    ap.add_argument("--max-pages", type=int, default=3)
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--out", default="data/raw/vn_drugs.csv")
    args = ap.parse_args()

    list_url = SOURCE["list_url"]
    print(f"Nguồn: {SOURCE['name']} | {list_url}")
    if not can_fetch(list_url):
        print("[X] robots.txt KHÔNG cho phép cào URL này. Dừng.")
        return

    soup = get(list_url)
    if not soup:
        return
    links = []
    for a in soup.select(SOURCE["item_selector"]):
        href = a.get("href")
        if href:
            links.append(urljoin(list_url, href))
    links = list(dict.fromkeys(links))  # khử trùng lặp, giữ thứ tự
    print(f"Tìm thấy {len(links)} link thuốc trên trang đầu.")

    if args.dry_run:
        print("\n[DRY-RUN] 5 link đầu:")
        for u in links[:5]:
            print("  ", u)
        if links:
            print("\n[DRY-RUN] Parse thử trang đầu:")
            ps = get(links[0])
            if ps:
                print("  ", parse_drug_page(ps, links[0]))
        print("\n=> Chỉnh selector trong SOURCE/parse_drug_page cho khớp trang, rồi bỏ --dry-run.")
        return

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, u in enumerate(links[: args.max_pages]):
        print(f"[{i+1}/{min(len(links), args.max_pages)}] {u}")
        ps = get(u)
        if ps:
            rows.append(parse_drug_page(ps, u))
        time.sleep(args.delay)  # lịch sự với server

    if rows:
        with open(out, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nĐã ghi {len(rows)} dòng -> {out}")


if __name__ == "__main__":
    main()
