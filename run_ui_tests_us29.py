"""US29 (SCRUM-116) — UI test bệnh án mẫu: picker Trang Chủ + quản lý admin.

Server DB BẬT. Đăng ký admin test (ADMIN_EMAILS), kiểm tra: nạp mẫu vào ô nhập, thêm +
xóa mẫu trong trang quản lý. Dọn admin + mẫu test sau. Chạy:  python run_ui_tests_us29.py
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
PORT = 5058
BASE = f"http://127.0.0.1:{PORT}"
ADMIN_EMAIL = "bam_ui_admin@cnpm.vn"
PASSWORD = "matkhau123"
NEW_TITLE = "ZZ Mẫu UI Test"
results = []


def rec(name, ok, detail=""):
    results.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")


def _db():
    raw = [l.split("=", 1)[1].strip().strip('"').strip("'")
           for l in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
           if l.strip().startswith("DATABASE_URL")][0]
    after = raw.split("://", 1)[1]
    userpw, hp = after.rsplit("@", 1)
    u, pw = userpw.split(":", 1); h, rest = hp.split(":", 1); port, db = rest.split("/", 1)
    return dict(host=h, port=int(port), user=u, password=pw, dbname=db)


def cleanup_db():
    try:
        c = psycopg2.connect(**_db()); c.autocommit = True; cur = c.cursor()
        cur.execute("DELETE FROM nguoi_dung WHERE email=%s", (ADMIN_EMAIL,))
        cur.execute("DELETE FROM benh_an_mau WHERE tieu_de=%s", (NEW_TITLE,))
        c.close()
    except Exception as e:
        print("  [!] cleanup lỗi:", str(e)[:80])


def start_server():
    env = os.environ.copy()
    env.update({"PORT": str(PORT), "LLM_CONTEXT_ENABLED": "0", "ADMIN_EMAILS": ADMIN_EMAIL, "PYTHONUTF8": "1"})
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
    cleanup_db()
    proc = start_server()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1366, "height": 900})
            page.goto(BASE, timeout=20000)
            page.wait_for_selector("#auth-screen:not(.is-hidden)", timeout=10000)
            page.click('[data-auth-target="register"]')
            page.fill("#register-name", "BAM Admin")
            page.fill("#register-email", ADMIN_EMAIL)
            page.fill("#register-password", PASSWORD)
            page.click("#register-form button[type=submit]")
            page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=15000)

            # SCRUM-119: picker Trang Chủ -> nạp mẫu vào ô nhập
            page.wait_for_selector("#sample-picker:not(.is-hidden)", timeout=10000)
            page.wait_for_function("() => document.querySelectorAll('#sample-select option').length > 1", timeout=8000)
            opts = page.locator("#sample-select option").count()
            rec("SCRUM-119: picker hiện, có mẫu (>1 option)", opts > 1, str(opts))
            val = page.eval_on_selector("#sample-select option:nth-child(2)", "el => el.value")
            page.select_option("#sample-select", val)
            time.sleep(0.3)
            ta = page.input_value("#case-description")
            rec("SCRUM-119: chọn mẫu -> nạp nội dung vào ô nhập", len(ta.strip()) > 0, ta[:40])

            # SCRUM-116: trang quản lý admin
            nav = page.locator('.nav-link[data-page="samples"]')
            rec("Admin: nav 'Bệnh Án Mẫu' hiển thị", nav.is_visible())
            nav.click()
            page.wait_for_selector("#page-samples.is-active", timeout=10000)
            page.wait_for_function("() => document.querySelectorAll('#samples-list .history-card').length >= 5", timeout=8000)
            before = page.locator("#samples-list .history-card").count()
            rec("Danh sách >= 5 mẫu (seed)", before >= 5, str(before))

            # Thêm mẫu
            page.fill("#sample-tieu-de", NEW_TITLE)
            page.fill("#sample-noi-dung", "Bệnh nhân test UI: sốt, ho, đau họng.")
            page.click("#sample-form button[type=submit]")
            page.wait_for_function(
                f"() => document.querySelectorAll('#samples-list .history-card').length === {before + 1}", timeout=8000)
            rec("Thêm mẫu -> danh sách tăng 1", page.locator("#samples-list .history-card").count() == before + 1)
            has_new = page.evaluate(
                f"() => Array.from(document.querySelectorAll('#samples-list h2')).some(h => h.textContent === {json.dumps(NEW_TITLE)})")
            rec("Mẫu mới xuất hiện trong danh sách", has_new)
            page.screenshot(path=str(ROOT / "screenshots" / "us29_benh_an_mau.png"))

            # Xóa mẫu vừa thêm (card cuối có tiêu đề NEW_TITLE)
            page.evaluate(f"""() => {{
              const cards = Array.from(document.querySelectorAll('#samples-list .history-card'));
              const card = cards.find(c => c.querySelector('h2') && c.querySelector('h2').textContent === {json.dumps(NEW_TITLE)});
              if (card) card.querySelector('button').click();
            }}""")
            page.wait_for_function(
                f"() => document.querySelectorAll('#samples-list .history-card').length === {before}", timeout=8000)
            rec("Xóa mẫu -> danh sách trở lại ban đầu", page.locator("#samples-list .history-card").count() == before)

            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        cleanup_db()

    npass = sum(1 for ok in results if ok)
    print("=" * 52)
    print(f"TỔNG: {npass}/{len(results)} PASS")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(run())
