"""US15 + US18 (port) — UI end-to-end qua trình duyệt.

Dữ liệu TẠM & TRỐNG ban đầu (không seed): tự dự đoán thật trên UI -> ghi lịch sử,
bấm "Đồng ý" -> ghi feedback, rồi mở Dashboard thấy số THẬT (không phải seed).

Chạy:  python run_ui_tests_us15_18.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path("d:/CNPM")
PORT = 5056
BASE = f"http://127.0.0.1:{PORT}"
ADMIN_EMAIL = "admin.e2e@pharma.vn"
PASSWORD = "matkhau123"
OTC = "tôi bị đau đầu, sổ mũi, hắt hơi mấy hôm nay"

results = []


def rec(name, ok, detail=""):
    results.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")


def start_server(tmp: Path):
    env = os.environ.copy()
    env.update({
        "PORT": str(PORT), "LLM_CONTEXT_ENABLED": "0", "DB_DISABLED": "1",
        "USERS_PATH": str(tmp / "users.json"),
        "PREDICTION_LOG_PATH": str(tmp / "prediction_log.jsonl"),
        "FEEDBACK_LOG_PATH": str(tmp / "feedback.jsonl"),
        "ADMIN_EMAILS": ADMIN_EMAIL, "PYTHONUTF8": "1",
    })
    (tmp / "users.json").write_text(json.dumps({"users": []}), encoding="utf-8")
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
    tmp = Path(tempfile.mkdtemp(prefix="us15_18_ui_"))
    proc = start_server(tmp)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1366, "height": 850})

            # Đăng ký admin (qua ADMIN_EMAILS) -> vào app.
            page.goto(BASE, timeout=20000)
            page.wait_for_selector("#auth-screen:not(.is-hidden)", timeout=10000)
            page.click('[data-auth-target="register"]')
            page.fill("#register-name", "Admin E2E")
            page.fill("#register-email", ADMIN_EMAIL)
            page.fill("#register-password", PASSWORD)
            page.click("#register-form button[type=submit]")
            page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=15000)

            # US15: dự đoán thật trên UI.
            page.fill("#case-description", OTC)
            page.click("#diagnosis-form button[type=submit]")
            page.wait_for_selector("#page-result.is-active", timeout=20000)
            rec("US15: dự đoán xong, ra trang kết quả", True)

            # US18: box feedback hiện -> bấm Đồng ý -> hiện cảm ơn.
            fb_visible = page.locator("#feedback-box").is_visible()
            rec("US18: box feedback hiển thị", fb_visible)
            page.click("#feedback-approve")
            page.wait_for_selector("#feedback-thanks:not(.is-hidden)", timeout=8000)
            rec("US18: bấm Đồng ý -> hiện cảm ơn", True)
            page.screenshot(path=str(ROOT / "screenshots" / "us18_feedback.png"))

            # US19 tích hợp: Dashboard hiện số THẬT (1 ca, 100% đồng ý).
            page.click('.nav-link[data-page="dashboard"]')
            page.wait_for_selector("#page-dashboard.is-active", timeout=10000)
            page.wait_for_function(
                "document.getElementById('stat-total-predictions').textContent.trim() !== '—'",
                timeout=10000)
            total = page.inner_text("#stat-total-predictions").strip()
            rate = page.inner_text("#stat-agree-rate").strip()
            rec("US19: tổng ca dự đoán >= 1 (số thật)", total not in ("—", "0"), f"thấy '{total}'")
            rec("US19: tỷ lệ Đồng ý = 100%", rate == "100%", f"thấy '{rate}'")
            page.screenshot(path=str(ROOT / "screenshots" / "us15_18_19_dashboard_real.png"))

            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    npass = sum(1 for ok in results if ok)
    print("=" * 52)
    print(f"TỔNG: {npass}/{len(results)} PASS")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(run())
