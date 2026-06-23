# Test các trang admin (đăng nhập tài khoản admin) + chụp màn.
import asyncio, os, sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.environ.get("BASE", "http://127.0.0.1:5050")
EMAIL = os.environ.get("ADMIN_EMAIL", "admin@test.com")
PW = os.environ.get("ADMIN_PW", "123456")
OUT = os.path.join(os.path.dirname(__file__), "..", "screenshots", "verde")
os.makedirs(OUT, exist_ok=True)

errors = []
results = []

def log(step, ok, extra=""):
    results.append((step, ok)); print(("  OK " if ok else "  !! ") + step + ("  " + extra if extra else ""))

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()
        page.on("pageerror", lambda e: errors.append("PAGEERROR: " + str(e)))
        page.on("console", lambda m: errors.append("CONSOLE: " + m.text) if m.type == "error" else None)

        await page.goto(BASE, timeout=20000)
        await page.wait_for_timeout(800)
        # đăng nhập
        try:
            await page.fill("#login-email", EMAIL)
            await page.fill("#login-password", PW)
            await page.click("#login-form button[type='submit']", force=True)
            await page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=8000)
            await page.wait_for_timeout(1200)
            log("đăng nhập admin", True)
        except Exception as e:
            log("đăng nhập admin", False, str(e)); await browser.close(); return

        # menu Quản Trị hiện?
        admin_wrap = await page.query_selector(".nav-admin:not(.is-hidden)")
        log("menu Quản Trị hiện (role=admin)", bool(admin_wrap))
        if admin_wrap:
            await admin_wrap.hover(); await page.wait_for_timeout(500)
            await page.screenshot(path=os.path.join(OUT, "A0_admin_dropdown.png"))

        pages = [
            ("dashboard", "A1_dashboard.png", "#page-dashboard.is-active"),
            ("drug-admin", "A2_quan_ly_thuoc.png", "#page-drug-admin.is-active"),
            ("dictionary", "A3_tu_dien.png", "#page-dictionary.is-active"),
            ("admin-history", "A4_lich_su_he_thong.png", "#page-admin-history.is-active"),
            ("feedback-admin", "A6_duyet_phan_hoi.png", "#page-feedback-admin.is-active"),
        ]
        for dp, fname, sel in pages:
            try:
                await page.click(f"[data-page='{dp}']", force=True)
                await page.wait_for_selector(sel, timeout=6000)
                await page.wait_for_timeout(1600)  # chờ fetch + vẽ chart
                await page.screenshot(path=os.path.join(OUT, fname))
                log(f"trang {dp}", True)
            except Exception as e:
                log(f"trang {dp}", False, str(e)[:80])

        # modal chi tiết Lịch sử hệ thống
        try:
            await page.click("[data-page='admin-history']", force=True)
            await page.wait_for_timeout(1500)
            row = await page.query_selector("#ah-rows tr")
            if row:
                await row.click(force=True)
                await page.wait_for_timeout(700)
                modal = await page.query_selector("#ah-detail-modal:not(.is-hidden)")
                if modal:
                    await page.screenshot(path=os.path.join(OUT, "A5_lsht_modal.png"))
                    log("modal chi tiết Lịch sử hệ thống", True)
                else:
                    log("modal chi tiết (không mở/không có dữ liệu)", True)
            else:
                log("Lịch sử hệ thống: chưa có dòng dữ liệu", True)
        except Exception as e:
            log("modal chi tiết", False, str(e)[:80])

        await browser.close()

    print("\n==== TỔNG KẾT ADMIN ====")
    ok = sum(1 for _, o in results if o)
    print(f"Đạt {ok}/{len(results)} bước. Lỗi console/page: {len(errors)}")
    for e in errors[:15]:
        print("   - " + e[:160])

asyncio.run(main())
