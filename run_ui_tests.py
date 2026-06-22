import asyncio
import os
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

async def run_test():
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        console_errors = []
        page.on("pageerror", lambda err: console_errors.append(str(err)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        print("[1] Opening application...")
        try:
            await page.goto("http://127.0.0.1:5000", timeout=10000)
            print("Khởi động: OK")
        except Exception as e:
            print(f"Khởi động: Lỗi ({e})")
            await browser.close()
            return

        # Screenshot of login screen
        os.makedirs("screenshots", exist_ok=True)
        await page.screenshot(path="screenshots/01_login_screen.png")

        print("[2] Registering account...")
        try:
            # Click "Tạo tài khoản" to switch to register view
            await page.click("button[data-auth-target='register']", force=True)
            await page.wait_for_selector("div[data-auth-view='register']:not(.is-hidden)", timeout=3000)
            
            # Fill form
            await page.fill("#register-name", "UI Test")
            await page.fill("#register-email", "uitest@test.com")
            await page.fill("#register-password", "test123456")
            
            await page.screenshot(path="screenshots/02_register_filled.png")
            
            # Submit
            await page.click("#register-form button[type='submit']", force=True)
            
            # Wait a bit or check if error appears
            await page.wait_for_timeout(1000)
            reg_err = await page.inner_text("#register-message")
            if reg_err and "đã được đăng ký" in reg_err:
                print(f"Registration message: '{reg_err}'. Proceeding to login instead.")
                raise Exception("Email already registered")
            
            # Wait for redirection/authenticated state (app shell visible)
            await page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=5000)
            print("Đăng ký/đăng nhập: OK")
        except Exception as e:
            print(f"Đăng ký thất bại hoặc đã tồn tại: {e}")
            await page.screenshot(path="screenshots/02_register_failed.png")
            print("Trying to login instead...")
            try:
                await page.click("button[data-auth-target='login']", force=True)
                await page.wait_for_selector("div[data-auth-view='login']:not(.is-hidden)", timeout=3000)
                await page.fill("#login-email", "uitest@test.com")
                await page.fill("#login-password", "test123456")
                await page.click("#login-form button[type='submit']", force=True)
                await page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=5000)
                print("Đăng ký/đăng nhập: OK (Login successful)")
            except Exception as e2:
                print(f"Đăng nhập tài khoản cũ cũng lỗi: {e2}")
                await page.screenshot(path="screenshots/02_login_failed.png")
                await browser.close()
                return

        await page.screenshot(path="screenshots/03_authenticated_home.png")

        # Define 3a test cases
        cases_3a = [
            {"id": 1, "desc": "Tôi bị ho, sốt và đau họng mấy ngày nay", "expected": "thuốc giảm đau hạ sốt"},
            {"id": 2, "desc": "Ngứa da, nổi mẩn đỏ, hắt hơi liên tục", "expected": "thuốc kháng histamin"},
            {"id": 3, "desc": "Sốt cao, rét run, đau cơ, vừa đi vùng sốt rét về", "expected": "thuốc điều trị sốt rét"},
            {"id": 4, "desc": "Ợ chua, nóng rát vùng thượng vị, đau dạ dày sau ăn", "expected": "thuốc điều trị dạ dày"},
            {"id": 5, "desc": "Bệnh nhân sốt cao, ho có đờm, đau ngực, khó thở", "expected": "thuốc kháng sinh"},
        ]

        pass_3a = 0
        results_3a = []

        print("[3a] Testing Case 3a...")
        for c in cases_3a:
            # Go back to home page
            await page.click("aside.app-sidebar button[data-page='home']", force=True)
            await page.wait_for_selector("#page-home.is-active", timeout=5000)
            
            # Clear case
            await page.click("#clear-case", force=True)
            
            # Enter description
            await page.fill("#case-description", c["desc"])
            
            # Click predict
            await page.click("#diagnosis-form button[type='submit']", force=True)
            
            # Wait for page-result to be active
            await page.wait_for_selector("#page-result.is-active", timeout=10000)
            await page.wait_for_timeout(1000) # Wait for page contents to render
            
            # Get text from result title or summary drug group
            result_txt = await page.inner_text("#result-title")
            drug_group_txt = await page.inner_text("#summary-drug-group")
            
            # Save screenshot
            await page.screenshot(path=f"screenshots/case_3a_{c['id']}.png")
            
            # Check if expected is in result_txt or drug_group_txt
            matched = (c["expected"].lower() in result_txt.lower()) or (c["expected"].lower() in drug_group_txt.lower())
            
            if matched:
                pass_3a += 1
                status = "PASS"
            else:
                status = "FAIL"
            
            print(f"Case {c['id']}: '{c['desc']}' -> Expected: '{c['expected']}' | Got title: '{result_txt}', group: '{drug_group_txt}' -> {status}")
            results_3a.append((c["id"], status, result_txt, drug_group_txt))

        # Define 3b test cases (sau khi vá tầng dịch VN->EN: kỳ vọng ĐÚNG)
        cases_3b = [
            {"id": 6, "desc": "Tiểu buốt, tiểu rắt, đau bụng dưới", "expected": "thuốc kháng sinh"},
            {"id": 7, "desc": "Đau đầu dữ dội từng cơn, buồn nôn, sợ ánh sáng", "expected": "thuốc giảm đau hạ sốt"},
        ]
        results_3b = {}
        pass_3b = 0

        print("[3b] Testing Case 3b...")
        for c in cases_3b:
            await page.click("aside.app-sidebar button[data-page='home']", force=True)
            await page.wait_for_selector("#page-home.is-active", timeout=5000)
            await page.click("#clear-case", force=True)
            await page.fill("#case-description", c["desc"])
            await page.click("#diagnosis-form button[type='submit']", force=True)
            await page.wait_for_selector("#page-result.is-active", timeout=10000)
            await page.wait_for_timeout(1000)

            result_txt = await page.inner_text("#result-title")
            drug_group_txt = await page.inner_text("#summary-drug-group")
            await page.screenshot(path=f"screenshots/case_3b_{c['id']}.png")

            actual = drug_group_txt if drug_group_txt != "Chưa đủ dữ liệu để gợi ý thuốc" else result_txt
            matched = c["expected"].lower() in result_txt.lower() or c["expected"].lower() in drug_group_txt.lower()
            status = "PASS" if matched else "FAIL"
            if matched:
                pass_3b += 1
            results_3b[c["id"]] = (status, actual)
            print(f"Case {c['id']}: '{c['desc']}' -> Expected: '{c['expected']}' | Got: '{actual}' -> {status}")

        # Section 4: general UI/UX testing
        print("[4] Testing Section 4 (UI/UX checklist)...")
        checklist = {}

        # 4.1: Example button
        try:
            await page.click("aside.app-sidebar button[data-page='home']", force=True)
            await page.wait_for_selector("#page-home.is-active", timeout=5000)
            await page.click("#clear-case", force=True)
            await page.click("#example-case", force=True)
            val = await page.input_value("#case-description")
            if len(val.strip()) > 0:
                checklist["example-case"] = "PASS"
            else:
                checklist["example-case"] = "FAIL"
        except Exception as e:
            checklist["example-case"] = f"FAIL ({e})"

        # 4.2: Clear button
        try:
            await page.click("#clear-case", force=True)
            val = await page.input_value("#case-description")
            if len(val.strip()) == 0:
                checklist["clear-case"] = "PASS"
            else:
                checklist["clear-case"] = "FAIL"
        except Exception as e:
            checklist["clear-case"] = f"FAIL ({e})"

        # 4.3: Symptom search and select
        try:
            # Let's search "ho" and select the chip
            await page.fill("#symptom-search", "ho")
            await page.wait_for_timeout(500) # wait for render
            chips = await page.query_selector_all(".symptom-chip")
            if len(chips) > 0:
                await chips[0].click(force=True)
                selected_txt = await page.inner_text("#selected-count")
                if "1" in selected_txt:
                    checklist["symptom-search"] = "PASS"
                else:
                    checklist["symptom-search"] = f"FAIL (Selected count not updated: {selected_txt})"
            else:
                checklist["symptom-search"] = "FAIL (No symptom chips found)"
        except Exception as e:
            checklist["symptom-search"] = f"FAIL ({e})"

        # 4.4: Save result
        try:
            # Run Case 1 first to get a successful prediction state (sets currentResult)
            await page.click("aside.app-sidebar button[data-page='home']", force=True)
            await page.wait_for_selector("#page-home.is-active", timeout=5000)
            await page.click("#clear-case", force=True)
            await page.fill("#case-description", "Tôi bị ho, sốt và đau họng mấy ngày nay")
            await page.click("#diagnosis-form button[type='submit']", force=True)
            await page.wait_for_selector("#page-result.is-active", timeout=10000)
            await page.wait_for_timeout(1000)

            # Click save result
            await page.click("#save-result", force=True)
            await page.wait_for_selector("#page-history.is-active", timeout=5000)
            await page.wait_for_timeout(500)
            
            cards = await page.query_selector_all(".user-history-card")
            if len(cards) > 0:
                checklist["save-result"] = "PASS"
            else:
                checklist["save-result"] = "FAIL (No history cards found after save)"
        except Exception as e:
            checklist["save-result"] = f"FAIL ({e})"

        # 4.5: History search
        try:
            # Search the card we just saved
            await page.fill("#history-search", "giảm đau")
            await page.wait_for_timeout(500)
            visible_cards = await page.query_selector_all(".user-history-card:not(.is-hidden)")
            
            if len(visible_cards) > 0:
                checklist["history-page"] = "PASS"
            else:
                checklist["history-page"] = "FAIL (No cards found after searching history)"
        except Exception as e:
            checklist["history-page"] = f"FAIL ({e})"

        # 4.6: Navigation (using sidebar on desktop)
        try:
            await page.click("aside.app-sidebar button[data-page='home']", force=True)
            home_active = await page.is_visible("#page-home.is-active")
            
            await page.click("aside.app-sidebar button[data-page='history']", force=True)
            history_active = await page.is_visible("#page-history.is-active")
            
            await page.click("aside.app-sidebar button[data-page='result']", force=True)
            result_active = await page.is_visible("#page-result.is-active")
            
            await page.click("aside.app-sidebar button[data-page='about']", force=True)
            about_active = await page.is_visible("#page-about.is-active")
            
            if home_active and history_active and result_active and about_active:
                checklist["navigation"] = "PASS"
            else:
                checklist["navigation"] = f"FAIL (home={home_active}, history={history_active}, result={result_active}, about={about_active})"
        except Exception as e:
            checklist["navigation"] = f"FAIL ({e})"

        # 4.7: Logout
        try:
            # Navigate to about page first to expose profile-logout-button
            await page.click("aside.app-sidebar button[data-page='about']", force=True)
            await page.wait_for_selector("#page-about.is-active", timeout=5000)
            
            # Click logout
            await page.click("#profile-logout-button", force=True)
            await page.wait_for_selector(".auth-screen:not(.is-hidden)", timeout=5000)
            
            # Re-login
            await page.fill("#login-email", "uitest@test.com")
            await page.fill("#login-password", "test123456")
            await page.click("#login-form button[type='submit']", force=True)
            await page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=5000)
            checklist["logout"] = "PASS"
        except Exception as e:
            checklist["logout"] = f"FAIL ({e})"

        # 4.8: Validation (empty note)
        try:
            await page.click("aside.app-sidebar button[data-page='home']", force=True)
            await page.wait_for_selector("#page-home.is-active", timeout=5000)
            await page.click("#clear-case", force=True)
            await page.click("#diagnosis-form button[type='submit']", force=True)
            await page.wait_for_timeout(1000)
            
            msg = await page.inner_text("#form-message")
            checklist["validation-empty"] = "PASS" if len(msg.strip()) > 0 else "FAIL (No message shown)"
            print(f"Empty submit message: '{msg}'")
        except Exception as e:
            checklist["validation-empty"] = f"FAIL ({e})"

        # 4.9: Meaningless notes
        try:
            await page.click("#clear-case", force=True)
            await page.fill("#case-description", "aaaa bbbb")
            await page.click("#diagnosis-form button[type='submit']", force=True)
            await page.wait_for_timeout(1000)
            msg = await page.inner_text("#form-message")
            if "không nhận diện được triệu chứng" in msg.lower() or "không nhận dạng được" in msg.lower() or "không nhận diện được triệu chứng phù hợp với tập train" in msg.lower():
                checklist["meaningless-notes"] = "PASS"
            else:
                checklist["meaningless-notes"] = f"FAIL (Message: '{msg}')"
            print(f"Meaningless notes message: '{msg}'")
        except Exception as e:
            checklist["meaningless-notes"] = f"FAIL ({e})"

        # 4.10: Responsive layout
        try:
            # Set viewport to mobile size
            await page.set_viewport_size({"width": 375, "height": 667})
            await page.wait_for_timeout(1000)
            
            # Check if bottom-nav is visible
            bottom_visible = await page.is_visible("nav.bottom-nav")
            
            # Navigate on mobile bottom nav
            await page.click("nav.bottom-nav button[data-page='history']", force=True)
            await page.wait_for_timeout(500)
            history_active_mobile = await page.is_visible("#page-history.is-active")
            
            if bottom_visible and history_active_mobile:
                checklist["responsive"] = "PASS"
            else:
                checklist["responsive"] = f"FAIL (bottom_visible={bottom_visible}, history_active_mobile={history_active_mobile})"
            
            # Restore viewport
            await page.set_viewport_size({"width": 1280, "height": 800})
        except Exception as e:
            checklist["responsive"] = f"FAIL ({e})"

        pass_ui = sum(1 for status in checklist.values() if status == "PASS")
        
        print("\n=== UI/UX CHECKLIST RESULTS ===")
        for k, v in checklist.items():
            print(f"{k}: {v}")
        print(f"Passed: {pass_ui}/10")

        # Let's output a summary report to a text file
        with open("screenshots/test_report.txt", "w", encoding="utf-8") as f:
            f.write(f"Khởi động: OK\n")
            f.write(f"Đăng ký/đăng nhập: OK\n")
            f.write(f"Mục 3a: {pass_3a}/5 PASS\n")
            for r in results_3a:
                f.write(f"  - Case {r[0]}: {r[1]} (Title: {r[2]}, Group: {r[3]})\n")
            f.write(f"Mục 3b: {pass_3b}/2 PASS | case6 -> {results_3b.get(6)} | case7 -> {results_3b.get(7)}\n")
            f.write(f"Mục 4 (UI/UX): {pass_ui}/10 PASS\n")
            for k, v in checklist.items():
                f.write(f"  - {k}: {v}\n")
            
            errs_count = len(console_errors)
            if errs_count > 0:
                f.write(f"Lỗi console/crash: Có {errs_count} lỗi được ghi nhận:\n")
                for err in console_errors[:5]:
                    f.write(f"  - {err}\n")
            else:
                f.write(f"Lỗi console/crash: Không có lỗi nghiêm trọng\n")

        print("Done running UI tests.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_test())
