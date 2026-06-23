# Smoke test giao diện Verde — chụp màn các trang chính + bắt lỗi console.
import asyncio, os, sys, time
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.environ.get("BASE", "http://127.0.0.1:5050")
OUT = os.path.join(os.path.dirname(__file__), "..", "screenshots", "verde")
os.makedirs(OUT, exist_ok=True)
EMAIL = f"verde{int(time.time())}@test.com"

errors = []
results = []

def log(step, ok, extra=""):
    results.append((step, ok, extra))
    print(("  OK " if ok else "  !! ") + step + ("  " + extra if extra else ""))

async def shot(page, name):
    await page.screenshot(path=os.path.join(OUT, name))

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()
        page.on("pageerror", lambda e: errors.append("PAGEERROR: " + str(e)))
        page.on("console", lambda m: errors.append("CONSOLE: " + m.text) if m.type == "error" else None)

        # 1) Login screen
        try:
            await page.goto(BASE, timeout=20000)
            await page.wait_for_timeout(1200)
            await shot(page, "01_auth.png")
            log("mở app + màn auth", True)
        except Exception as e:
            log("mở app", False, str(e)); await browser.close(); return

        # 2) Register
        try:
            await page.click("button[data-auth-target='register']", force=True)
            await page.wait_for_selector("div[data-auth-view='register']:not(.is-hidden)", timeout=4000)
            await page.fill("#register-name", "Verde Test")
            await page.fill("#register-email", EMAIL)
            await page.fill("#register-password", "123456")
            await shot(page, "02_register.png")
            await page.click("#register-form button[type='submit']", force=True)
            await page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=8000)
            await page.wait_for_timeout(1500)
            log("đăng ký + vào app", True)
        except Exception as e:
            log("đăng ký", False, str(e))

        # 3) Home
        try:
            await page.wait_for_selector("#page-home.is-active", timeout=5000)
            await shot(page, "03_home.png")
            log("trang chủ hiển thị", True)
        except Exception as e:
            log("trang chủ", False, str(e))

        # 4) Nhập + chọn chip
        try:
            await page.fill("#case-description", "Sốt cao, ho khan, đau rát họng, sổ mũi 2 ngày nay")
            await page.wait_for_timeout(500)
            chips = await page.query_selector_all(".symptom-chip")
            ids = []
            for c in chips[:3]:
                sid = await c.get_attribute("data-symptom")
                if sid:
                    ids.append(sid)
            for sid in ids:
                el = await page.query_selector(f".symptom-chip[data-symptom='{sid}']")
                if el:
                    await el.click()
                    await page.wait_for_timeout(200)
            await page.wait_for_timeout(300)
            await shot(page, "04_home_filled.png")
            log(f"nhập mô tả + chọn {min(3,len(chips))} chip (tổng {len(chips)} chip)", True)
        except Exception as e:
            log("nhập + chọn chip", False, str(e))

        # 5) Dự đoán -> kết quả
        try:
            await page.click("#diagnosis-form button[type='submit']", force=True)
            await page.wait_for_selector("#page-result.is-active", timeout=15000)
            await page.wait_for_timeout(1500)
            await shot(page, "05_result.png")
            title = await page.text_content("#result-title")
            conf = await page.text_content("#confidence-value")
            log(f"dự đoán → kết quả (nhóm='{(title or '').strip()[:40]}', tin cậy={conf})", True)
        except Exception as e:
            log("dự đoán/kết quả", False, str(e))

        # 6) History
        try:
            await page.click("[data-page='history']", force=True)
            await page.wait_for_selector("#page-history.is-active", timeout=5000)
            await page.wait_for_timeout(800)
            await shot(page, "06_history.png")
            log("lịch sử dự đoán", True)
        except Exception as e:
            log("lịch sử", False, str(e))

        # 7) Profile + đổi tên + đổi mật khẩu (chức năng thật)
        try:
            await page.click("[data-page='about']", force=True)
            await page.wait_for_selector("#page-about.is-active", timeout=5000)
            await page.wait_for_timeout(600)
            await shot(page, "07_profile.png")
            log("hồ sơ", True)
        except Exception as e:
            log("hồ sơ", False, str(e))
        try:
            await page.fill("#profile-name-input", "Verde Test Đã Đổi")
            await page.click("#profile-info-form button[type='submit']", force=True)
            await page.wait_for_timeout(900)
            m1 = (await page.text_content("#profile-info-message")) or ""
            log(f"đổi tên: '{m1.strip()}'", "lưu" in m1.lower() or "đã" in m1.lower())
        except Exception as e:
            log("đổi tên", False, str(e))
        try:
            await page.fill("#profile-current-pw", "123456")
            await page.fill("#profile-new-pw", "abc123456")
            await page.fill("#profile-confirm-pw", "abc123456")
            await page.click("#profile-password-form button[type='submit']", force=True)
            await page.wait_for_timeout(900)
            m2 = (await page.text_content("#profile-pw-message")) or ""
            await shot(page, "07b_profile_done.png")
            log(f"đổi mật khẩu: '{m2.strip()}'", "thành công" in m2.lower())
        except Exception as e:
            log("đổi mật khẩu", False, str(e))

        # 8) Dark mode
        try:
            await page.click("[data-page='home']", force=True)
            await page.wait_for_timeout(400)
            tt = await page.query_selector(".app-sidebar .theme-toggle")
            if tt:
                await tt.click()
                await page.wait_for_timeout(700)
            await shot(page, "08_home_dark.png")
            theme = await page.get_attribute("html", "data-theme")
            log(f"dark mode (data-theme={theme})", True)
        except Exception as e:
            log("dark mode", False, str(e))

        # 9) Admin (nếu có quyền) — kiểm tra dropdown
        try:
            admin_wrap = await page.query_selector(".nav-admin:not(.is-hidden)")
            if admin_wrap:
                await admin_wrap.hover()
                await page.wait_for_timeout(500)
                await shot(page, "09_admin_dropdown.png")
                log("tài khoản admin: dropdown Quản Trị hiện", True)
            else:
                log("tài khoản user thường: menu Quản Trị ẩn (đúng phân quyền)", True)
        except Exception as e:
            log("kiểm tra admin", False, str(e))

        await browser.close()

    print("\n==== TỔNG KẾT ====")
    ok = sum(1 for _, o, _ in results if o)
    print(f"Đạt {ok}/{len(results)} bước.")
    print(f"Lỗi console/page: {len(errors)}")
    for e in errors[:15]:
        print("   - " + e[:160])
    print(f"Ảnh lưu tại: screenshots/verde/")

asyncio.run(main())
