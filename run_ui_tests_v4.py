import asyncio
import os
import sys
import subprocess
import time
import urllib.request
import json
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

CASES_V4 = [
    # NHÓM A — Ngữ cảnh PHẢI kích hoạt (trọng tâm vòng 4)
    {
        "id": 1,
        "desc": "Tôi bị đau đầu, buồn nôn sau khi va đập vào đầu",
        "expected": "emergency",
        "type": "group_a",
        "reason": "Nghi chấn thương sọ não sau va đập đầu, phải báo cấp cứu và không kê thuốc giảm đau",
    },
    {
        "id": 2,
        "desc": "Tôi nôn ói và chóng mặt sau khi ngã đập đầu",
        "expected": "emergency",
        "type": "group_a",
        "reason": "Nghi chấn thương sọ não sau ngã đập đầu, phải báo cấp cứu",
    },
    {
        "id": 3,
        "desc": "Bị đánh vào đầu, giờ đau đầu và chóng mặt",
        "expected": "emergency",
        "type": "group_a",
        "reason": "Nghi chấn thương sọ não sau bị đánh vào đầu, phải báo cấp cứu",
    },
    {
        "id": 4,
        "desc": "Tôi bị đau đầu, buồn nôn sau khi uống rượu nhiều",
        "expected": "needs_more",
        "type": "group_a",
        "reason": "Không kê paracetamol/giảm đau do tương tác độc gan với rượu nhiều",
    },
    {
        "id": 5,
        "desc": "Đau đầu, mệt sau khi nhậu xỉn tối qua",
        "expected": "needs_more",
        "type": "group_a",
        "reason": "Không kê giảm đau vô điều kiện, nhắc nhở rượu/gan",
    },
    {
        "id": 6,
        "desc": "Tôi bị đau đầu, buồn nôn sau khi chạy bộ",
        "expected": "normal",
        "type": "group_a",
        "reason": "Bình thường, nhưng phần Lưu ý/Chăm sóc có nội dung nghỉ ngơi, bù nước/oresol và theo dõi mất nước",
    },

    # NHÓM B — Ngữ cảnh KHÔNG được kích hoạt (chống báo động giả)
    {
        "id": 7,
        "desc": "Tôi bị đau đầu, buồn nôn, không có va đập vào đầu",
        "expected": "normal",
        "type": "group_b",
        "reason": "Không có va đập đầu, không được báo cấp cứu chấn thương đầu",
    },
    {
        "id": 8,
        "desc": "Tôi đau đầu, buồn nôn sau bữa tiệc nhưng không uống rượu",
        "expected": "normal",
        "type": "group_b",
        "reason": "Không uống rượu, không được chặn giảm đau vì rượu",
    },
    {
        "id": 9,
        "desc": "Tôi bị đập vào đầu gối, đau đầu gối nhiều",
        "expected": "normal",
        "type": "group_b",
        "reason": "Đập vào đầu gối (chân), không phải đầu, không được báo cấp cứu chấn thương đầu",
    },

    # NHÓM C — Regression vòng 3 (phải vẫn đúng)
    {
        "id": 10,
        "desc": "Sốt thành cơn, rét run rồi vã mồ hôi, vừa đi vùng rừng núi về",
        "expected_drug": "sốt rét",
        "avoid_drug": "kháng sinh",
        "type": "group_c",
        "reason": "Nghi sốt rét, phải kê thuốc điều trị sốt rét chứ không phải kháng sinh",
    },
    {
        "id": 11,
        "desc": "Mệt mỏi, da xanh xao, chóng mặt, móng tay giòn",
        "expected_drug": "vitamin và khoáng chất",
        "avoid_drug": "tim mạch/huyết áp",
        "type": "group_c",
        "reason": "Nghi thiếu máu, phải kê vitamin và khoáng chất chứ không phải tim mạch",
    },

    # NHÓM D — Regression cổng an toàn cũ (phải vẫn đúng)
    {
        "id": 12,
        "desc": "Đột nhiên nói đớ, yếu tay phải, méo một bên mặt",
        "expected": "emergency",
        "type": "group_d",
        "reason": "Đột quỵ, phải báo cấp cứu",
    },
    {
        "id": 13,
        "desc": "Đau ngực dữ dội lan ra tay trái, vã mồ hôi, khó thở",
        "expected": "emergency",
        "type": "group_d",
        "reason": "Nhồi máu cơ tim, phải báo cấp cứu",
    },
    {
        "id": 14,
        "desc": "Tôi bị ho có đờm vàng, sổ mũi, rát họng",
        "expected_drug": "long đờm",
        "type": "group_d",
        "reason": "Ho đờm thông thường, gợi ý nhóm long đờm/giảm ho, không báo cấp cứu"
    }
]

async def run_tests():
    # 1. Start backend if not running
    backend_started = False
    proc = None
    start_time = time.time()
    
    print("[*] Probing if backend is running at http://127.0.0.1:5000...")
    try:
        req = urllib.request.urlopen("http://127.0.0.1:5000/api/health", timeout=2)
        health_data = json.loads(req.read().decode("utf-8"))
        print(f"[+] Backend already running: {health_data}")
    except Exception:
        print("[!] Backend not running. Starting backend/app.py...")
        # Start backend/app.py in background
        proc = subprocess.Popen([sys.executable, "backend/app.py"], cwd="d:/CNPM", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        backend_started = True
        
        # Wait for port 5000 to be open and healthy
        healthy = False
        for attempt in range(60): # 2 mins max
            time.sleep(2)
            try:
                req = urllib.request.urlopen("http://127.0.0.1:5000/api/health", timeout=2)
                health_data = json.loads(req.read().decode("utf-8"))
                if health_data.get("ok"):
                    healthy = True
                    print(f"[+] Backend is healthy after {time.time() - start_time:.1f}s")
                    break
            except Exception:
                pass
            print(f"    Waiting for backend to boot (attempt {attempt+1}/60)...")
        
        if not healthy:
            print("[-] Error: Backend failed to boot on port 5000.")
            if proc:
                proc.terminate()
            return

    boot_duration = time.time() - start_time
    
    # 2. Check SBERT or Fallback
    sbert_status = "SBERT hoạt động (SBERT thật)"
    try:
        import sentence_transformers, torch
    except ImportError:
        sbert_status = "fallback (không SBERT)"

    print(f"[*] Môi trường: {sbert_status}")

    # Create screenshots dir
    os.makedirs("screenshots", exist_ok=True)

    # 3. Playwright testing
    async with async_playwright() as p:
        print("[*] Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        console_errors = []
        page.on("pageerror", lambda err: console_errors.append(str(err)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" and "422" not in msg.text and "409" not in msg.text else None)

        print("[*] Loading application...")
        await page.goto("http://127.0.0.1:5000", timeout=20000)
        await page.screenshot(path="screenshots/v4_01_login.png")

        print("[*] Authenticating (Register / Login)...")
        try:
            # Click "Tạo tài khoản" to register
            await page.click("button[data-auth-target='register']", force=True)
            await page.wait_for_selector("div[data-auth-view='register']:not(.is-hidden)", timeout=3000)
            
            await page.fill("#register-name", "Antigravity V4")
            await page.fill("#register-email", "anti.v4@test.com")
            await page.fill("#register-password", "test123456")
            await page.click("#register-form button[type='submit']", force=True)
            await page.wait_for_timeout(1000)
            
            reg_err = await page.inner_text("#register-message")
            if reg_err and "đã được đăng ký" in reg_err:
                raise Exception("Email already registered")
            
            await page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=5000)
            print("[+] Registration successful.")
        except Exception:
            print("[!] Registration failed or already registered. Attempting login...")
            try:
                await page.click("button[data-auth-target='login']", force=True)
                await page.wait_for_selector("div[data-auth-view='login']:not(.is-hidden)", timeout=3000)
                await page.fill("#login-email", "anti.v4@test.com")
                await page.fill("#login-password", "test123456")
                await page.click("#login-form button[type='submit']", force=True)
                await page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=5000)
                print("[+] Login successful.")
            except Exception as e:
                print(f"[-] Authentication failed: {e}")
                await page.screenshot(path="screenshots/v4_auth_failed.png")
                await browser.close()
                if proc:
                    proc.terminate()
                return

        await page.screenshot(path="screenshots/v4_02_home.png")

        # 4. Run the 14 cases
        print("[*] Running 14 test cases from test plan...")
        results = []
        
        for case in CASES_V4:
            cid = case["id"]
            desc = case["desc"]
            ctype = case["type"]
            
            # Go back to Home
            await page.click("aside.app-sidebar button[data-page='home']", force=True)
            await page.wait_for_selector("#page-home.is-active", timeout=5000)
            
            # Clear case
            await page.click("#clear-case", force=True)
            
            # Fill text
            await page.fill("#case-description", desc)
            
            # Submit
            await page.click("#diagnosis-form button[type='submit']", force=True)
            await page.wait_for_timeout(1500)
            
            # Read UI values
            got_title = ""
            got_subtitle = ""
            got_confidence = ""
            got_note = ""
            got_medications = ""
            got_precautions = ""
            got_care = ""
            got_warning = ""
            got_drug_group = ""
            got_medication_name = ""
            got_diagnosis = ""
            
            try:
                await page.wait_for_selector("#page-result.is-active", timeout=10000)
                got_title = (await page.inner_text("#result-title")).strip()
                got_subtitle = (await page.inner_text("#result-subtitle")).strip()
                got_confidence = (await page.inner_text("#confidence-value")).strip()
                got_note = (await page.inner_text("#result-note")).strip()
                got_medications = (await page.inner_text("#medication-list")).strip()
                got_precautions = (await page.inner_text("#precaution-list")).strip()
                got_care = (await page.inner_text("#care-list")).strip()
                got_warning = (await page.inner_text("#warning-text")).strip()
                
                got_diagnosis = (await page.inner_text("#summary-diagnosis")).strip()
                got_medication_name = (await page.inner_text("#summary-medication-name")).strip()
                got_drug_group = (await page.inner_text("#summary-drug-group")).strip()
            except Exception as e:
                got_title = "Error reading UI"
                got_note = f"Error: {e}"

            # Take screenshot
            screenshot_path = f"screenshots/v4_{cid:02d}.png"
            await page.screenshot(path=screenshot_path)

            # Determine PASS/FAIL
            passed = False
            reason = ""
            is_emergency = "cấp cứu" in got_note.lower() or "115" in got_note.lower()
            is_warned = "Chưa đủ" in got_title or "Chưa đủ" in got_drug_group or "cần thêm" in got_title.lower() or "không nhận diện" in got_title.lower()
            
            # Check according to expected state
            if ctype == "group_a":
                expected_state = case["expected"]
                if expected_state == "emergency":
                    # Must be emergency, must not suggest medications
                    if is_emergency and ("Chưa đủ" in got_medication_name or got_medication_name == "" or "chưa có" in got_medications.lower() or "không hiển thị" in got_medications.lower()):
                        passed = True
                    else:
                        passed = False
                        reason = f"Kỳ vọng CẤP CỨU và KHÔNG kê thuốc. Nhận: emergency={is_emergency}, thuốc={got_medication_name}"
                elif expected_state == "needs_more":
                    # Must show needs more info, not emergency, and must contain alcohol caution
                    has_alcohol_warn = any(x in got_note.lower() or x in got_warning.lower() or x in got_precautions.lower() for x in ["rượu", "gan", "alcohol"])
                    if is_warned and not is_emergency and has_alcohol_warn:
                        passed = True
                    else:
                        passed = False
                        reason = f"Kỳ vọng CẦN THÊM THÔNG TIN, KHÔNG cấp cứu và có cảnh báo rượu. Nhận: warned={is_warned}, emergency={is_emergency}, alcohol_warn={has_alcohol_warn}"
                elif expected_state == "normal":
                    # Must show normal result (not warned, not emergency) and care guidelines must contain dehydration/rest
                    has_care_guidance = any(x in got_care.lower() for x in ["nghỉ", "nước", "oresol", "ors", "mất nước"])
                    if not is_warned and not is_emergency and has_care_guidance:
                        passed = True
                    else:
                        passed = False
                        reason = f"Kỳ vọng GỢI Ý NHÓM kèm hướng dẫn bù nước/chăm sóc. Nhận: warned={is_warned}, emergency={is_emergency}, care_guidance={has_care_guidance}"

            elif ctype == "group_b":
                # Must NOT be emergency, must not be blocked (is normal prediction)
                if not is_emergency and not is_warned:
                    # Additional checks:
                    if cid == 7: # không va đập đầu
                        if "giảm đau" in got_drug_group.lower():
                            passed = True
                        else:
                            passed = False
                            reason = f"Kỳ vọng không cấp cứu và gợi ý nhóm giảm đau. Nhận: {got_drug_group}"
                    elif cid == 8: # không uống rượu
                        if "giảm đau" in got_drug_group.lower():
                            passed = True
                        else:
                            passed = False
                            reason = f"Kỳ vọng không bị chặn rượu và gợi ý nhóm giảm đau. Nhận: {got_drug_group}"
                    elif cid == 9: # đập vào đầu gối
                        if "kháng viêm" in got_drug_group.lower() or "nsaid" in got_drug_group.lower():
                            passed = True
                        else:
                            passed = False
                            reason = f"Kỳ vọng không cấp cứu chấn thương đầu và gợi ý nhóm nsaid/kháng viêm. Nhận: {got_drug_group}"
                else:
                    passed = False
                    reason = f"Bị báo động giả cấp cứu hoặc bị chặn nhầm. Nhận: warned={is_warned}, emergency={is_emergency}"

            elif ctype == "group_c":
                # Regression tests for malaria & anemia
                expected_drug = case["expected_drug"]
                avoid_drug = case["avoid_drug"]
                if expected_drug.lower() in got_drug_group.lower() and avoid_drug.lower() not in got_drug_group.lower():
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng gợi ý '{expected_drug}' và tránh '{avoid_drug}'. Nhận: {got_drug_group}"

            elif ctype == "group_d":
                expected_state = case.get("expected")
                if expected_state == "emergency":
                    if is_emergency:
                        passed = True
                    else:
                        passed = False
                        reason = "Không phát hiện dấu hiệu cấp cứu."
                else: # expected_drug
                    expected_drug = case["expected_drug"]
                    if expected_drug.lower() in got_drug_group.lower() and not is_emergency:
                        passed = True
                    else:
                        passed = False
                        reason = f"Kỳ vọng gợi ý '{expected_drug}' và không cấp cứu. Nhận: {got_drug_group} (emergency={is_emergency})"

            status = "PASS" if passed else "FAIL"
            print(f"Ca #{cid:02d} ({ctype}): {status} | Mô tả: '{desc[:30]}...' | Nhận: {got_drug_group} | Trạng thái: Title='{got_title}', Emergency={is_emergency}, Warned={is_warned} | {reason}")
            
            results.append({
                "id": cid,
                "desc": desc,
                "type": ctype,
                "actual_group": got_drug_group,
                "confidence": got_confidence,
                "warning": got_warning,
                "note": got_note,
                "is_emergency": is_emergency,
                "is_warned": is_warned,
                "status": status,
                "reason": reason
            })

        # 5. UI/UX Checklist Verification
        print("[*] Running UI/UX Checklist tests...")
        ui_checklist = {}

        # 5.1 Clear case button
        try:
            await page.click("aside.app-sidebar button[data-page='home']", force=True)
            await page.wait_for_selector("#page-home.is-active", timeout=5000)
            await page.fill("#case-description", "Triệu chứng bất kỳ")
            await page.click("#clear-case", force=True)
            val = await page.input_value("#case-description")
            ui_checklist["clear_case_button"] = "PASS" if len(val.strip()) == 0 else "FAIL (Description not cleared)"
        except Exception as e:
            ui_checklist["clear_case_button"] = f"FAIL ({e})"

        # 5.2 Example case button
        try:
            await page.click("#example-case", force=True)
            val = await page.input_value("#case-description")
            ui_checklist["example_case_button"] = "PASS" if len(val.strip()) > 0 else "FAIL (Empty example)"
        except Exception as e:
            ui_checklist["example_case_button"] = f"FAIL ({e})"

        # 5.3 Symptom search and select
        try:
            await page.click("#clear-case", force=True)
            await page.fill("#symptom-search", "ho")
            await page.wait_for_timeout(600)
            chips = await page.query_selector_all(".symptom-chip")
            if len(chips) > 0:
                await chips[0].click(force=True)
                selected_txt = await page.inner_text("#selected-count")
                ui_checklist["symptom_search_select"] = "PASS" if "1" in selected_txt else f"FAIL (Count not updated: {selected_txt})"
            else:
                ui_checklist["symptom_search_select"] = "FAIL (No symptom chips found for 'ho')"
        except Exception as e:
            ui_checklist["symptom_search_select"] = f"FAIL ({e})"

        # 5.4 Save result and history check
        try:
            # Let's predict a normal case
            await page.click("aside.app-sidebar button[data-page='home']", force=True)
            await page.click("#clear-case", force=True)
            await page.fill("#case-description", "Tôi bị ho có đờm vàng, sổ mũi, rát họng")
            await page.click("#diagnosis-form button[type='submit']", force=True)
            await page.wait_for_selector("#page-result.is-active", timeout=10000)
            
            await page.click("#save-result", force=True)
            await page.wait_for_selector("#page-history.is-active", timeout=5000)
            await page.wait_for_timeout(1000)
            cards = await page.query_selector_all(".user-history-card")
            ui_checklist["save_result_history"] = "PASS" if len(cards) > 0 else "FAIL (No history cards found)"
        except Exception as e:
            ui_checklist["save_result_history"] = f"FAIL ({e})"

        # 5.5 Navigation
        try:
            await page.click("aside.app-sidebar button[data-page='home']", force=True)
            h_vis = await page.is_visible("#page-home.is-active")
            
            await page.click("aside.app-sidebar button[data-page='history']", force=True)
            his_vis = await page.is_visible("#page-history.is-active")
            
            await page.click("aside.app-sidebar button[data-page='about']", force=True)
            ab_vis = await page.is_visible("#page-about.is-active")
            
            ui_checklist["sidebar_navigation"] = "PASS" if h_vis and his_vis and ab_vis else f"FAIL (home={h_vis}, history={his_vis}, about={ab_vis})"
        except Exception as e:
            ui_checklist["sidebar_navigation"] = f"FAIL ({e})"

        # 5.6 Responsive Layout & screenshots
        try:
            # Tablet
            await page.set_viewport_size({"width": 768, "height": 1024})
            await page.wait_for_timeout(1000)
            await page.screenshot(path="screenshots/v4_responsive_768.png")
            
            # Mobile
            await page.set_viewport_size({"width": 375, "height": 667})
            await page.wait_for_timeout(1000)
            await page.screenshot(path="screenshots/v4_responsive_375.png")
            bottom_nav_visible = await page.is_visible("nav.bottom-nav")
            
            ui_checklist["responsive_layout"] = "PASS" if bottom_nav_visible else "FAIL (bottom navigation not visible on mobile)"
            
            # Restore size
            await page.set_viewport_size({"width": 1280, "height": 800})
        except Exception as e:
            ui_checklist["responsive_layout"] = f"FAIL ({e})"

        # 5.7 Long input handling (2000 chars)
        try:
            await page.click("aside.app-sidebar button[data-page='home']", force=True)
            await page.click("#clear-case", force=True)
            long_text = "Ho khan và nhức đầu đi kèm với mệt mỏi " * 52 # 2028 chars
            await page.fill("#case-description", long_text)
            # check if char count reflects it
            val = await page.input_value("#case-description")
            # submit
            await page.click("#diagnosis-form button[type='submit']", force=True)
            await page.wait_for_timeout(1500)
            ui_checklist["long_input_handling"] = "PASS" if len(val) >= 2000 else "FAIL (Could not fill 2000 characters)"
        except Exception as e:
            ui_checklist["long_input_handling"] = f"FAIL ({e})"

        # 5.8 Console errors
        errs_count = len(console_errors)
        ui_checklist["no_console_errors"] = "PASS" if errs_count == 0 else f"FAIL ({errs_count} errors logged: {console_errors[:2]})"

        # 6. Generate the markdown report
        print("[*] Generating report docs/ANTIGRAVITY_REPORT_v4.md...")
        
        # Aggregate stats
        total_cases = len(results)
        passed_cases = sum(1 for r in results if r["status"] == "PASS")
        
        by_type = {}
        for r in results:
            t = r["type"]
            by_type.setdefault(t, {"total": 0, "passed": 0})
            by_type[t]["total"] += 1
            if r["status"] == "PASS":
                by_type[t]["passed"] += 1
                
        # Count failures in groups
        fails_a = sum(1 for r in results if r["type"] == "group_a" and r["status"] == "FAIL")
        fails_b = sum(1 for r in results if r["type"] == "group_b" and r["status"] == "FAIL")
        fails_c = sum(1 for r in results if r["type"] == "group_c" and r["status"] == "FAIL")
        fails_d = sum(1 for r in results if r["type"] == "group_d" and r["status"] == "FAIL")
        
        serious_fails = fails_a + fails_b + fails_c + fails_d
        success_status = "ĐẠT" if serious_fails == 0 else "CHƯA ĐẠT"

        import datetime
        vn_date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        report_md = f"""# Báo cáo kết quả Test UI cho Antigravity — Vòng 4

[Antigravity UI Test V4 - {vn_date}]

## 1. Môi trường kiểm thử
- **Trạng thái mô hình**: `{sbert_status}`
- **Thời gian khởi động hệ thống**: `{boot_duration:.1f} giây`
- **Tài khoản test**: Họ tên `Antigravity V4`, Email `anti.v4@test.com`, Mật khẩu `test123456`

## 2. Bảng kết quả từng ca

| # | Mô tả bệnh | Nhóm thuốc trả về | Có cảnh báo/cấp cứu? | Kết quả | Chi tiết / Lý do |
|---|---|---|---|---|---|
"""
        for r in results:
            warn_info = "CẤP CỨU" if r["is_emergency"] else ("CẦN THÊM TT" if r["is_warned"] else "Không")
            report_md += f"| {r['id']} | {r['desc']} | `{r['actual_group']}` | {warn_info} | **{r['status']}** | {r['reason'] or 'Khớp kỳ vọng'} |\n"

        report_md += f"""
## 3. Tổng hợp thống kê

- **Tổng số ca test**: {passed_cases}/{total_cases} PASS
- **Nhóm A (Ngữ cảnh PHẢI kích hoạt):** {by_type.get('group_a', {}).get('passed', 0)}/{by_type.get('group_a', {}).get('total', 0)} PASS
- **Nhóm B (Ngữ cảnh KHÔNG được kích hoạt):** {by_type.get('group_b', {}).get('passed', 0)}/{by_type.get('group_b', {}).get('total', 0)} PASS
- **Nhóm C (Regression vòng 3):** {by_type.get('group_c', {}).get('passed', 0)}/{by_type.get('group_c', {}).get('total', 0)} PASS
- **Nhóm D (Regression cổng an toàn cũ):** {by_type.get('group_d', {}).get('passed', 0)}/{by_type.get('group_d', {}).get('total', 0)} PASS
- **Số ca FAIL nghiêm trọng:** `{serious_fails}`

> [!IMPORTANT]
> **Kết luận chung:** **{success_status}**
> (Tiêu chí ĐẠT: Nhóm A an toàn, Nhóm B không bị báo động giả, các nhóm C và D không bị thoái lui).

## 4. Nhận xét UI/UX & Responsive

| Tính năng / Checklist | Kết quả kiểm thử | Nhận xét chi tiết |
|---|---|---|
"""
        for k, v in ui_checklist.items():
            report_md += f"| `{k}` | **{v}** | Kiểm tra tự động bằng Playwright |\n"

        report_md += """
### Hình ảnh chụp màn hình kiểm thử:
- **Màn hình đăng nhập/đăng ký:** ![Login Screen](/screenshots/v4_01_login.png)
- **Màn hình chính (Home):** ![Home Screen](/screenshots/v4_02_home.png)
- **Responsive Tablet (768px):** ![Responsive 768px](/screenshots/v4_responsive_768.png)
- **Responsive Mobile (375px):** ![Responsive 375px](/screenshots/v4_responsive_375.png)

## 5. Đề xuất & Các ca cần tối ưu tiếp theo

"""
        failed_cases = [r for r in results if r["status"] == "FAIL"]
        if failed_cases:
            report_md += "Các ca bị sai cần hiệu chỉnh:\n"
            for fc in failed_cases:
                report_md += f"- Ca #{fc['id']}: `{fc['desc']}` -> Trả về: `{fc['actual_group']}` | Cấp cứu: {fc['is_emergency']} | Lý do: {fc['reason']}\n"
        else:
            report_md += "Tất cả các ca kiểm thử hoạt động chính xác theo đúng tài liệu thiết kế. Hệ thống phân tích tốt ngữ cảnh hoàn cảnh nhân-quả, ngăn chặn được độc gan paracetamol khi uống rượu, cảnh báo đúng chấn thương sọ não, và không gây báo động giả.\n"

        with open("docs/ANTIGRAVITY_REPORT_v4.md", "w", encoding="utf-8") as f:
            f.write(report_md)
            
        print("[+] Generated docs/ANTIGRAVITY_REPORT_v4.md successfully!")
        
        await browser.close()
        
    # Shutdown backend process if we started it
    if backend_started and proc:
        print("[*] Terminating backend process...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        print("[+] Backend process stopped.")

if __name__ == "__main__":
    asyncio.run(run_tests())
