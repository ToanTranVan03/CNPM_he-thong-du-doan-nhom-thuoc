"""PORT — UI test trang Quản lý thuốc (CRUD nhóm thuốc + thuốc) trên nhánh huy.

Server DB BẬT. Admin test qua ADMIN_EMAILS. Kiểm tra: danh sách seed, thêm nhóm + thuốc,
xóa. Dọn admin + item test. Chạy:  python run_ui_tests_drug_admin.py
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
PORT = 5062
BASE = f"http://127.0.0.1:{PORT}"
ADMIN_EMAIL = "drugui_admin@cnpm.vn"
PASSWORD = "matkhau123"
G_NAME = "ZZ Nhóm UI Test"
D_NAME = "ZZ Thuốc UI Test"
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
        cur.execute("DELETE FROM nhom_thuoc WHERE ten_nhom_thuoc=%s", (G_NAME,))
        cur.execute("DELETE FROM thuoc_tham_khao WHERE ten_thuoc=%s", (D_NAME,))
        c.close()
    except Exception as e:
        print("  [!] cleanup lỗi:", str(e)[:80])


def start_server():
    env = os.environ.copy()
    env.update({"PORT": str(PORT), "LLM_CONTEXT_ENABLED": "0", "ADMIN_EMAILS": ADMIN_EMAIL, "PYTHONUTF8": "1"})
    proc = subprocess.Popen([sys.executable, "backend/app.py"], cwd=str(ROOT), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start = time.time()
    while time.time() - start < 120:
        try:
            r = urllib.request.urlopen(f"{BASE}/api/health", timeout=2)
            if json.loads(r.read().decode()).get("ok"):
                print(f"[+] Backend healthy sau {time.time()-start:.1f}s")
                return proc
        except Exception:
            time.sleep(1)
    proc.terminate(); raise RuntimeError("Backend không lên kịp")


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
            page.fill("#register-name", "Drug Admin")
            page.fill("#register-email", ADMIN_EMAIL)
            page.fill("#register-password", PASSWORD)
            page.click("#register-form button[type=submit]")
            page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=15000)

            nav = page.locator('.nav-link[data-page="drug-admin"]')
            rec("Admin: nav 'Quản Lý Thuốc' hiển thị", nav.is_visible())
            nav.click()
            page.wait_for_selector("#page-drug-admin.is-active", timeout=10000)
            page.wait_for_function("() => document.querySelectorAll('#dg-list .admin-list-item').length > 0", timeout=10000)
            g_before = page.locator("#dg-list .admin-list-item").count()
            rec("Danh sách nhóm thuốc có dữ liệu (seed)", g_before >= 10, str(g_before))
            page.wait_for_function("() => document.querySelectorAll('#th-list .admin-list-item').length > 0", timeout=8000)
            rec("Danh sách thuốc có dữ liệu", page.locator("#th-list .admin-list-item").count() > 0)

            # Thêm nhóm
            page.fill("#dg-ten", G_NAME)
            page.fill("#dg-mo-ta", "ghi chú test")
            page.click("#dg-submit")
            page.wait_for_function(
                f"() => document.querySelectorAll('#dg-list .admin-list-item').length === {g_before + 1}", timeout=8000)
            rec("Thêm nhóm -> danh sách tăng 1", page.locator("#dg-list .admin-list-item").count() == g_before + 1)

            # Thêm thuốc gắn nhóm mới
            page.fill("#th-ten", D_NAME)
            page.fill("#th-hoat-chat", "hc-ui")
            page.select_option("#th-nhom", label=G_NAME)
            page.click("#th-form button[type=submit]")
            time.sleep(0.6)
            page.fill("#th-search", D_NAME)
            page.wait_for_function(
                "() => Array.from(document.querySelectorAll('#th-list .admin-list-item strong')).some(s => s.textContent.includes('ZZ Thuốc UI Test'))",
                timeout=8000)
            rec("Thêm thuốc -> tìm thấy trong danh sách", True)
            page.screenshot(path=str(ROOT / "screenshots" / "port_drug_admin.png"))

            # Xóa thuốc test (auto-confirm dialog)
            page.on("dialog", lambda d: d.accept())
            page.evaluate("""() => {
              const it = Array.from(document.querySelectorAll('#th-list .admin-list-item')).find(i => i.querySelector('strong').textContent.includes('ZZ Thuốc UI Test'));
              if (it) it.querySelector('.danger').click();
            }""")
            time.sleep(0.8)
            gone = page.evaluate("() => !Array.from(document.querySelectorAll('#th-list .admin-list-item strong')).some(s => s.textContent.includes('ZZ Thuốc UI Test'))")
            rec("Xóa thuốc test thành công", gone)

            # Feature 3: khu vực import CSV hiển thị trên trang Quản Lý Thuốc
            rec("Feature 3: có khu vực import CSV", page.locator("#import-dg-file").count() == 1 and page.locator("#import-th-btn").is_visible())

            # Feature 4: trang Duyệt Phản Hồi render được
            fbnav = page.locator('.nav-link[data-page="feedback-admin"]')
            rec("Feature 4: nav 'Duyệt Phản Hồi' hiển thị", fbnav.is_visible())
            fbnav.click()
            page.wait_for_selector("#page-feedback-admin.is-active", timeout=10000)
            page.wait_for_timeout(800)
            rec("Feature 4: trang duyệt phản hồi mở + có tabs", page.locator("#fb-tab-pending").is_visible() and page.locator("#fb-pending-pill").is_visible())
            page.screenshot(path=str(ROOT / "screenshots" / "port_feedback_admin.png"))

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
