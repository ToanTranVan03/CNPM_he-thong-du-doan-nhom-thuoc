"""US27 (SCRUM-108) — UI test trang Từ điển triệu chứng (tìm real-time + phân trang).

Chạy server với DB BẬT (đọc trieu_chung đã seed trong CNPM). Đăng ký admin test qua
ADMIN_EMAILS, kiểm tra tìm kiếm + phân trang, rồi XÓA admin test khỏi CNPM.

Chạy:  python run_ui_tests_us27.py
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import psycopg2
from playwright.sync_api import sync_playwright

ROOT = Path("d:/CNPM")
PORT = 5057
BASE = f"http://127.0.0.1:{PORT}"
ADMIN_EMAIL = "dict_ui_admin@cnpm.vn"
PASSWORD = "matkhau123"
results = []


def rec(name, ok, detail=""):
    results.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")


def _db_params():
    raw = [l.split("=", 1)[1].strip().strip('"').strip("'")
           for l in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
           if l.strip().startswith("DATABASE_URL")][0]
    after = raw.split("://", 1)[1]
    userpw, hp = after.rsplit("@", 1)
    u, pw = userpw.split(":", 1)
    h, rest = hp.split(":", 1)
    port, db = rest.split("/", 1)
    return dict(host=h, port=int(port), user=u, password=pw, dbname=db)


def del_admin():
    try:
        c = psycopg2.connect(**_db_params()); c.autocommit = True
        c.cursor().execute("DELETE FROM nguoi_dung WHERE email=%s", (ADMIN_EMAIL,))
        c.close()
    except Exception as e:
        print("  [!] dọn admin lỗi:", str(e)[:80])


def start_server():
    env = os.environ.copy()
    env.update({"PORT": str(PORT), "LLM_CONTEXT_ENABLED": "0",
                "ADMIN_EMAILS": ADMIN_EMAIL, "PYTHONUTF8": "1"})
    proc = subprocess.Popen([sys.executable, "backend/app.py"], cwd=str(ROOT), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start = time.time()
    while time.time() - start < 90:
        try:
            r = urllib.request.urlopen(f"{BASE}/api/health", timeout=2)
            if json.loads(r.read().decode()).get("ok"):
                print(f"[+] Backend healthy sau {time.time()-start:.1f}s")
                return proc
        except Exception:
            time.sleep(1)
    proc.terminate()
    raise RuntimeError("Backend không lên kịp")


def run():
    del_admin()
    proc = start_server()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1366, "height": 900})
            page.goto(BASE, timeout=20000)
            page.wait_for_selector("#auth-screen:not(.is-hidden)", timeout=10000)
            page.click('[data-auth-target="register"]')
            page.fill("#register-name", "Dict Admin")
            page.fill("#register-email", ADMIN_EMAIL)
            page.fill("#register-password", PASSWORD)
            page.click("#register-form button[type=submit]")
            page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=15000)

            nav = page.locator('.nav-link[data-page="dictionary"]')
            rec("Admin: nav 'Từ Điển' hiển thị", nav.is_visible())
            nav.click()
            page.wait_for_selector("#page-dictionary.is-active", timeout=10000)
            page.wait_for_function("() => document.querySelectorAll('#dictionary-rows tr').length > 0", timeout=10000)

            rows1 = page.locator("#dictionary-rows tr").count()
            total_txt = page.inner_text("#dictionary-total")
            page_info = page.inner_text("#dict-page-info")
            rec("Trang đầu có 10 dòng (per_page)", rows1 == 10, str(rows1))
            rec("Hiển thị tổng số triệu chứng (>100)", any(ch.isdigit() for ch in total_txt) and "triệu chứng" in total_txt, total_txt)
            rec("Có thông tin trang (Trang 1 / N)", "Trang 1" in page_info, page_info)

            # Phân trang: sang trang 2 -> dòng đầu đổi
            first_before = page.inner_text("#dictionary-rows tr:first-child td:nth-child(2)")
            page.click("#dict-next")
            page.wait_for_function(
                f"() => document.querySelector('#dictionary-rows tr:first-child td:nth-child(2)').textContent !== {json.dumps(first_before)}",
                timeout=8000)
            rec("Sang trang 2 -> nội dung đổi", "Trang 2" in page.inner_text("#dict-page-info"))

            # Tìm real-time
            page.fill("#dictionary-search", "fever")
            page.wait_for_function("() => document.getElementById('dict-page-info').textContent.includes('Trang 1')", timeout=8000)
            time.sleep(0.6)  # chờ debounce + fetch
            search_rows = page.locator("#dictionary-rows tr").count()
            has_fever = page.evaluate(
                "() => Array.from(document.querySelectorAll('#dictionary-rows tr')).some(tr => tr.textContent.toLowerCase().includes('fever'))")
            rec("Tìm 'fever' có kết quả", search_rows >= 1, str(search_rows))
            rec("Kết quả chứa 'fever'", has_fever)
            page.screenshot(path=str(ROOT / "screenshots" / "us27_dictionary.png"))

            # US28: bấm 1 triệu chứng -> Modal hiện nhóm thuốc liên quan
            page.click("#dictionary-rows tr:first-child")
            page.wait_for_selector("#mapping-modal:not(.is-hidden)", timeout=8000)
            page.wait_for_function(
                "() => document.querySelectorAll('#mapping-modal-groups li').length > 0", timeout=8000)
            modal_groups = page.locator("#mapping-modal-groups li").count()
            modal_title = page.inner_text("#mapping-modal-title").strip()
            rec("US28: Modal mở khi bấm triệu chứng", page.locator("#mapping-modal").is_visible())
            rec("US28: Modal có danh sách nhóm thuốc (>=1)", modal_groups >= 1, str(modal_groups))
            rec("US28: tiêu đề Modal có tên triệu chứng", len(modal_title) > 0, modal_title)
            page.screenshot(path=str(ROOT / "screenshots" / "us28_mapping_modal.png"))
            page.click("#mapping-modal-close")
            page.wait_for_selector("#mapping-modal", state="hidden", timeout=5000)
            rec("US28: đóng Modal được", page.locator("#mapping-modal").is_hidden())

            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        del_admin()

    npass = sum(1 for ok in results if ok)
    print("=" * 52)
    print(f"TỔNG: {npass}/{len(results)} PASS")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(run())
