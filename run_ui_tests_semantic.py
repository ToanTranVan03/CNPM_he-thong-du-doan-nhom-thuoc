"""UI test (Playwright) với câu tiếng Việt LẠ — kiểm chứng lớp ngữ nghĩa end-to-end.

Khác run_ui_tests.py: dùng bộ câu hoàn toàn mới (khác v1/v2) để đo generalization
qua đúng trình duyệt + frontend + /api/predict + SBERT.

Cần backend đang chạy ở http://127.0.0.1:5000 (khởi động chậm vì tải/load model SBERT).
"""
import asyncio, sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

# Câu LẠ (phrasing mới hoàn toàn) | nhóm kỳ vọng | also_ok '|' | loại
CASES = [
    ("Mũi tắc tịt, hắt xì cả buổi sáng, chảy nước mũi trong", "thuốc kháng histamin", "thuốc thông mũi", "normal"),
    ("Bụng trên đau cồn cào lúc đói, hay ợ chua", "thuốc điều trị dạ dày", "", "normal"),
    ("Đi cầu phân lỏng nhiều lần, người mệt lả, khát khô họng", "bù dịch và điện giải", "", "normal"),
    ("Khớp gối sưng đau, đi lại khó, sáng dậy cứng khớp", "thuốc kháng viêm không steroid", "thuốc giảm đau hạ sốt", "normal"),
    ("Lên cơn hen, thở rít, nặng ngực khó thở", "thuốc giãn phế quản", "", "normal"),
    ("Uống nước hoài vẫn khát, đi tiểu liên tục, sút ký nhanh", "thuốc điều trị đái tháo đường", "", "normal"),
    ("Răng sâu nhức buốt, lợi sưng đau", "thuốc giảm đau nha khoa", "thuốc giảm đau hạ sốt", "normal"),
    ("Tê rần hai bàn tay, đau buốt như kim châm chạy dọc tay", "thuốc chống co giật/đau thần kinh", "", "normal"),
    ("Hồi hộp đánh trống ngực, đau thắt ngực khi leo dốc", "thuốc tim mạch/huyết áp", "", "normal"),
    ("Mẩn ngứa nổi khắp người sau khi uống thuốc lạ", "thuốc kháng histamin", "", "normal"),
    ("Đột nhiên nói đớ, yếu tay phải, méo một bên mặt", "WARN", "", "safety"),
    ("Trong người thấy oải oải khó tả", "WARN", "", "vague"),
]


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await (await browser.new_context(viewport={"width": 1280, "height": 800})).new_page()
        await page.goto("http://127.0.0.1:5000", timeout=20000)

        # Đăng nhập (đăng ký nếu chưa có)
        try:
            await page.click("button[data-auth-target='register']", force=True)
            await page.fill("#register-name", "Sem Test")
            await page.fill("#register-email", "semtest@test.com")
            await page.fill("#register-password", "test123456")
            await page.click("#register-form button[type='submit']", force=True)
            await page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=5000)
        except Exception:
            await page.click("button[data-auth-target='login']", force=True)
            await page.fill("#login-email", "semtest@test.com")
            await page.fill("#login-password", "test123456")
            await page.click("#login-form button[type='submit']", force=True)
            await page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=8000)

        ok = 0
        lines = []
        for i, (desc, exp, also, loai) in enumerate(CASES, 1):
            await page.click("aside.app-sidebar button[data-page='home']", force=True)
            await page.wait_for_selector("#page-home.is-active", timeout=5000)
            await page.click("#clear-case", force=True)
            await page.fill("#case-description", desc)
            await page.click("#diagnosis-form button[type='submit']", force=True)
            await page.wait_for_timeout(1500)
            got, warned = "", False
            if await page.is_visible("#page-result.is-active"):
                got = (await page.inner_text("#summary-drug-group")).strip()
                title = (await page.inner_text("#result-title")).strip()
                if "Chưa đủ" in title or "Chưa đủ" in got:
                    warned = True
            else:
                warned = True
                try:
                    got = (await page.inner_text("#form-message")).strip()[:40]
                except Exception:
                    got = "(warn)"
            accept = {exp, *[a for a in [also] if a]}
            passed = (warned if exp == "WARN" else (any(a and a in got for a in accept)))
            ok += int(passed)
            await page.screenshot(path=f"screenshots/sem_{i:02d}.png")
            lines.append(f"  {'PASS' if passed else 'FAIL'} [{loai}] {desc[:42]}\n        kỳ vọng={exp} | nhận={got[:46]}")

        print(f"UI SEMANTIC TEST (câu lạ): {ok}/{len(CASES)} PASS")
        print("\n".join(lines))
        with open("screenshots/sem_test_report.txt", "w", encoding="utf-8") as f:
            f.write(f"UI SEMANTIC TEST (cau la): {ok}/{len(CASES)} PASS\n")
            f.write("\n".join(lines))
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
