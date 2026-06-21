"""US19 — UI test Dashboard Admin qua trình duyệt (Playwright).

Tự khởi động backend trên cổng riêng với DATA TẠM (seed JSONL) + ADMIN_EMAILS, KHÔNG đụng
data thật. Kiểm tra: admin thấy & xem được Dashboard với số liệu đúng; user thường bị ẩn.

Chạy:  python run_ui_tests_us19.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path("d:/CNPM")
PORT = 5055
BASE = f"http://127.0.0.1:{PORT}"
ADMIN_EMAIL = "admin.us19@pharma.vn"
USER_EMAIL = "user.us19@pharma.vn"
PASSWORD = "matkhau123"

results = []


def rec(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")


def seed(tmp: Path):
    today = datetime.now(timezone.utc)
    d0 = today.date().isoformat()
    d1 = (today - timedelta(days=1)).date().isoformat()
    d2 = (today - timedelta(days=2)).date().isoformat()
    preds = [
        {"ts": f"{d2}T08:00:00+00:00", "status": "suggest", "predicted_group": "thuốc kháng histamin"},
        {"ts": f"{d2}T09:00:00+00:00", "status": "suggest", "predicted_group": "thuốc kháng histamin"},
        {"ts": f"{d1}T10:00:00+00:00", "status": "emergency", "predicted_group": None},
        {"ts": f"{d1}T11:00:00+00:00", "status": "safety_block", "predicted_group": "thuốc kháng sinh"},
        {"ts": f"{d0}T07:30:00+00:00", "status": "suggest", "predicted_group": "thuốc giảm đau hạ sốt"},
    ]
    fb = [
        {"ts": f"{d2}T08:05:00+00:00", "verdict": "APPROVE"},
        {"ts": f"{d2}T09:05:00+00:00", "verdict": "APPROVE"},
        {"ts": f"{d1}T10:05:00+00:00", "verdict": "REJECT", "predicted_group": "thuốc kháng sinh", "note": "Chẩn đoán sai nhóm thuốc"},
        {"ts": f"{d1}T11:05:00+00:00", "verdict": "REJECT", "predicted_group": "thuốc kháng sinh", "note": "sai nhóm, thiếu cảnh báo"},
        {"ts": f"{d0}T07:35:00+00:00", "verdict": "APPROVE"},
    ]
    (tmp / "prediction_log.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in preds), encoding="utf-8")
    (tmp / "feedback.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in fb), encoding="utf-8")
    (tmp / "users.json").write_text(json.dumps({"users": []}, ensure_ascii=False), encoding="utf-8")


def start_server(tmp: Path):
    env = os.environ.copy()
    env.update(
        {
            "PORT": str(PORT),
            "LLM_CONTEXT_ENABLED": "0",
            "DB_DISABLED": "1",  # UI test JSON-mode, không đụng Postgres
            "USERS_PATH": str(tmp / "users.json"),
            "PREDICTION_LOG_PATH": str(tmp / "prediction_log.jsonl"),
            "FEEDBACK_LOG_PATH": str(tmp / "feedback.jsonl"),
            "ADMIN_EMAILS": ADMIN_EMAIL,
            "PYTHONUTF8": "1",
        }
    )
    proc = subprocess.Popen(
        [sys.executable, "backend/app.py"], cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
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


def register(page, name, email):
    page.goto(BASE, timeout=20000)
    page.wait_for_selector("#auth-screen:not(.is-hidden)", timeout=10000)
    page.click('[data-auth-target="register"]')
    page.fill("#register-name", name)
    page.fill("#register-email", email)
    page.fill("#register-password", PASSWORD)
    page.click("#register-form button[type=submit]")
    page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=15000)


def run():
    tmp = Path(tempfile.mkdtemp(prefix="us19_ui_"))
    seed(tmp)
    proc = start_server(tmp)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1366, "height": 850})

            # ── ADMIN ──
            register(page, "Quản trị US19", ADMIN_EMAIL)
            nav = page.locator('.nav-link[data-page="dashboard"]')
            rec("Admin: nav Dashboard hiển thị", nav.is_visible())
            nav.click()
            page.wait_for_selector("#page-dashboard.is-active", timeout=10000)
            page.wait_for_function(
                "document.getElementById('stat-total-predictions').textContent.trim() !== '—'",
                timeout=10000,
            )
            total = page.inner_text("#stat-total-predictions").strip()
            rate = page.inner_text("#stat-agree-rate").strip()
            feedback_total = page.inner_text("#stat-feedback-total").strip()
            top_rows = page.locator("#dashboard-top-groups .prediction-row").count()
            # SCRUM-80: đọc dữ liệu từ chính Chart.js (canvas) để chứng minh thư viện được tích hợp.
            page.wait_for_function("() => !!(window.Chart && Chart.getChart('dashboard-bars-canvas'))", timeout=10000)
            bars_data = page.evaluate("() => Chart.getChart('dashboard-bars-canvas').data.datasets[0].data")
            donut_data = page.evaluate("() => Chart.getChart('dashboard-donut-canvas').data.datasets[0].data")
            rec("Admin: tổng ca dự đoán = 5", total == "5", f"thấy '{total}'")
            rec("Admin: tỷ lệ Đồng ý = 60%", rate == "60%", f"thấy '{rate}'")
            rec("Admin: tổng đánh giá = 5", feedback_total == "5", f"thấy '{feedback_total}'")
            rec("Admin: Chart.js cột có 3 ngày, tổng 5", len(bars_data) == 3 and sum(bars_data) == 5, str(bars_data))
            rec("Admin: Chart.js donut [đồng ý, không] = [3,2]", donut_data == [3, 2], str(donut_data))
            rec("Admin: top nhóm thuốc có dòng", top_rows >= 1, f"thấy {top_rows} dòng")

            # US22: section lý do không đồng ý
            page.wait_for_function("() => !!(window.Chart && Chart.getChart('reject-bars-canvas'))", timeout=10000)
            reject_bars = page.evaluate("() => Chart.getChart('reject-bars-canvas').data.datasets[0].data")
            kw_rows = page.locator("#reject-keywords .prediction-row").count()
            pill = page.inner_text("#reject-total-pill").strip()
            rec("US22: pill '2 lượt không đồng ý'", pill.startswith("2"), pill)
            rec("US22: chart REJECT theo ngày tổng=2", sum(reject_bars) == 2, str(reject_bars))
            rec("US22: có từ khóa lý do (>=1 dòng)", kw_rows >= 1, f"{kw_rows} dòng")
            page.screenshot(path=str(ROOT / "screenshots" / "us22_feedback_dashboard.png"))

            # Lọc theo ngày: chỉ hôm nay -> 1 ca
            d0 = datetime.now(timezone.utc).date().isoformat()
            page.fill("#dashboard-from", d0)
            page.fill("#dashboard-to", d0)
            page.click("#dashboard-refresh")
            page.wait_for_function(
                "document.getElementById('stat-total-predictions').textContent.trim() === '1'",
                timeout=10000,
            )
            rec("Admin: lọc hôm nay -> 1 ca", page.inner_text("#stat-total-predictions").strip() == "1")

            page.click("#logout-button")
            page.wait_for_selector("#auth-screen:not(.is-hidden)", timeout=10000)

            # ── USER THƯỜNG ──
            register(page, "Người dùng US19", USER_EMAIL)
            nav2 = page.locator('.nav-link[data-page="dashboard"]')
            rec("User thường: nav Dashboard bị ẩn", nav2.is_hidden())
            # Cố gọi trực tiếp showPage('dashboard') -> phải bị chặn (về home)
            page.evaluate("showPage('dashboard')")
            time.sleep(0.5)
            blocked = not page.locator("#page-dashboard").evaluate("el => el.classList.contains('is-active')")
            rec("User thường: bị chặn vào Dashboard", blocked)
            page.screenshot(path=str(ROOT / "screenshots" / "us19_user_no_dashboard.png"))

            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    npass = sum(1 for _, ok, _ in results if ok)
    print("=" * 52)
    print(f"TỔNG: {npass}/{len(results)} PASS")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(run())
