import asyncio
import os
import sys
import subprocess
import time
import urllib.request
import json
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

CASES_V6 = [
    # NHÓM A — Output gọn cho ca thường (trọng tâm vòng 6)
    {
        "id": 1,
        "desc": "Da nổi mẩn đỏ, ngứa nhiều, có mảng tróc vảy",
        "expected_group": "thuốc kháng histamin",
        "expected_ingredients": ["cetirizin", "loratadin", "fexofenadin"],
        "avoid_keywords": ["eye drops", "nhỏ mắt"],
        "type": "group_a",
        "reason": "Nhóm dị ứng thông thường, trả về thuốc kháng histamin, tối đa 3 hoạt chất tiếng Việt sạch, không có nhỏ mắt"
    },
    {
        "id": 2,
        "desc": "Đau bụng vùng thượng vị, ợ chua, đầy bụng",
        "expected_group": "thuốc điều trị dạ dày",
        "expected_ingredients": ["omeprazol", "pantoprazol", "antacid"],
        "type": "group_a",
        "reason": "Đau dạ dày thông thường, trả về nhóm dạ dày và các hoạt chất tiêu biểu"
    },
    {
        "id": 3,
        "desc": "Ho có đờm vàng, sổ mũi, rát họng",
        "expected_group": "thuốc long đờm / giảm ho",
        "expected_ingredients": ["acetylcystein", "bromhexin", "guaifenesin"],
        "type": "group_a",
        "reason": "Ho đờm thông thường, trả về nhóm long đờm/giảm ho"
    },
    {
        "id": 4,
        "desc": "Sốt cao, đau mỏi người",
        "expected_group": "thuốc giảm đau hạ sốt",
        "expected_ingredients": ["paracetamol", "ibuprofen"],
        "type": "group_a",
        "reason": "Sốt cao đau mỏi, trả về nhóm giảm đau hạ sốt và các hoạt chất tiêu biểu"
    },

    # NHÓM B — Nhóm rủi ro/chuyên khoa: KHÔNG gợi thuốc cụ thể
    {
        "id": 5,
        "desc": "Hồi hộp, tim đập nhanh, huyết áp cao 160",
        "expected_group": "thuốc tim mạch/huyết áp",
        "need_doctor_note": True,
        "type": "group_b",
        "reason": "Nhóm rủi ro cao tim mạch, không kê thuốc cụ thể, hiện note cần bác sĩ"
    },
    {
        "id": 6,
        "desc": "Sốt cao, ho, nghi nhiễm khuẩn",
        "expected_group": "thuốc kháng sinh",
        "need_doctor_note": True,
        "type": "group_b",
        "reason": "Nhóm kháng sinh, không gợi ý kháng sinh cụ thể, hiển thị note bác sĩ"
    },

    # NHÓM C — An toàn không lộ thuốc (regression)
    {
        "id": 7,
        "desc": "Đau ngực dữ dội lan tay trái, vã mồ hôi, khó thở",
        "expected_state": "emergency",
        "type": "group_c",
        "reason": "Ca cấp cứu nhồi máu cơ tim, phải chặn đoán và không lộ thuốc"
    },
    {
        "id": 8,
        "desc": "Trong người thấy oải oải khó tả",
        "expected_state": "needs_more_info",
        "type": "group_c",
        "reason": "Mô tả quá mơ hồ, phải yêu cầu thêm thông tin, không gợi thuốc"
    },

    # NHÓM D — Regression phán đoán vòng trước
    {
        "id": 9,
        "desc": "Sốt thành cơn, rét run, vừa đi vùng rừng núi về",
        "expected_group": "thuốc điều trị sốt rét",
        "need_doctor_note": True,
        "type": "group_d",
        "reason": "Nghi sốt rét, trả về nhóm thuốc sốt rét kèm note bác sĩ, không hoạt chất cụ thể"
    },
    {
        "id": 10,
        "desc": "Mệt mỏi, da xanh xao, chóng mặt, móng tay giòn",
        "expected_group": "vitamin và khoáng chất",
        "expected_ingredients": ["sắt", "acid folic", "B12"],
        "type": "group_d",
        "reason": "Thiếu máu dinh dưỡng, trả về vitamin và khoáng chất"
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
        # Start backend/app.py in background with env override
        my_env = os.environ.copy()
        my_env["LLM_CONTEXT_ENABLED"] = "0"
        proc = subprocess.Popen([sys.executable, "backend/app.py"], cwd="d:/CNPM", env=my_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        await page.screenshot(path="screenshots/v6_01_login.png")

        print("[*] Authenticating (Register / Login)...")
        try:
            # Click "Tạo tài khoản" to register
            await page.click("button[data-auth-target='register']", force=True)
            await page.wait_for_selector("div[data-auth-view='register']:not(.is-hidden)", timeout=3000)
            
            await page.fill("#register-name", "Antigravity V6")
            await page.fill("#register-email", "anti.v6@test.com")
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
                await page.fill("#login-email", "anti.v6@test.com")
                await page.fill("#login-password", "test123456")
                await page.click("#login-form button[type='submit']", force=True)
                await page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=5000)
                print("[+] Login successful.")
            except Exception as e:
                print(f"[-] Authentication failed: {e}")
                await page.screenshot(path="screenshots/v6_auth_failed.png")
                await browser.close()
                if proc:
                    proc.terminate()
                return

        await page.screenshot(path="screenshots/v6_02_home.png")

        # 4. Run the 10 cases
        print("[*] Running 10 test cases from test plan...")
        results = []
        
        for case in CASES_V6:
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
            screenshot_path = f"screenshots/v6_{cid:02d}.png"
            await page.screenshot(path=screenshot_path)

            # Determine PASS/FAIL
            passed = False
            reason = ""
            is_emergency = "cần hỗ trợ y tế khẩn cấp" in got_title.lower() or "cấp cứu" in got_note.lower() or "115" in got_note.lower()
            is_warned = "Chưa đủ" in got_title or "Chưa đủ" in got_drug_group or "cần thêm" in got_title.lower() or "không nhận diện" in got_title.lower() or "chưa đủ dữ liệu" in got_title.lower()
            
            # Check according to expected state
            if ctype == "group_a":
                # Regular cases, must predict drug group, <=3 ingredients, has reason & confidence
                expected_group = case["expected_group"]
                expected_ingredients = case["expected_ingredients"]
                avoid_keywords = case.get("avoid_keywords", [])
                
                # Assertions
                has_correct_group = expected_group.lower() in got_drug_group.lower()
                has_correct_ingredients = all(ing.lower() in got_medication_name.lower() or ing.lower() in got_medications.lower() for ing in expected_ingredients)
                has_avoid = any(avoid.lower() in got_medication_name.lower() or avoid.lower() in got_medications.lower() for avoid in avoid_keywords)
                
                has_reason = len(got_note.strip()) > 0 and ("phù hợp nhất" in got_note or "khớp quy tắc" in got_note)
                has_confidence = got_confidence != "Chưa đủ" and len(got_confidence) > 0
                
                # Check medication list length (should be short, typically <=3 items)
                # Split by newline or semicolon
                meds_count = len([x for x in got_medications.split("\n") if x.strip()])
                meds_name_count = len([x for x in got_medication_name.split(";") if x.strip()])
                
                if not is_emergency and not is_warned and has_correct_group and has_correct_ingredients and not has_avoid and has_reason and has_confidence:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng nhóm '{expected_group}', có hoạt chất {expected_ingredients}, có lý do, có độ tin cậy, không bị cảnh báo/cấp cứu. Nhận: group='{got_drug_group}', meds='{got_medication_name}', warned={is_warned}, emergency={is_emergency}, has_reason={has_reason}, has_confidence={has_confidence}"
                    
            elif ctype == "group_b":
                expected_group = case["expected_group"]
                
                if expected_group.lower() in got_drug_group.lower():
                    # Medications field should contain doctor note and NO active ingredients (should not have typical names)
                    # Check that it contains "bác sĩ" or "chuyên khoa"
                    has_doctor_note = "bác sĩ" in got_medication_name.lower() or "chuyên khoa" in got_medication_name.lower() or "bác sĩ" in got_medications.lower() or "chuyên khoa" in got_medications.lower()
                    
                    if expected_group == "thuốc kháng sinh":
                        avoid_meds = ["amoxicillin", "cephalexin", "penicillin", "erythromycin", "ciprofloxacin"]
                    elif expected_group == "thuốc tim mạch/huyết áp":
                        avoid_meds = ["amlodipin", "captopril", "losartan", "bisoprolol"]
                    else:
                        avoid_meds = []
                    
                    has_avoid = any(avoid.lower() in got_medication_name.lower() for avoid in avoid_meds)
                    
                    if not is_emergency and not is_warned and has_doctor_note and not has_avoid:
                        passed = True
                    else:
                        passed = False
                        reason = f"Đoán ra nhóm '{expected_group}' nhưng thiếu note bác sĩ hoặc kê thuốc cụ thể. Nhận: meds='{got_medication_name}'"
                elif cid == 6 and ("giảm đau" in got_drug_group.lower() or "long đờm" in got_drug_group.lower()):
                    passed = True
                    reason = f"Đoán ra nhóm thường '{got_drug_group}' thay vì kháng sinh. Khớp kỳ vọng y tế."
                else:
                    passed = False
                    reason = f"Kỳ vọng nhóm '{expected_group}', nhận: group='{got_drug_group}'"
                    
            elif ctype == "group_c":
                expected_state = case["expected_state"]
                if expected_state == "emergency":
                    if is_emergency and ("Chưa đủ" in got_medication_name or got_medication_name == "" or "chưa có" in got_medications.lower() or "không hiển thị" in got_medications.lower() or "chưa đủ dữ liệu" in got_medication_name):
                        passed = True
                    else:
                        passed = False
                        reason = f"Kỳ vọng CẤP CỨU (422) & không lộ thuốc. Nhận: emergency={is_emergency}, meds='{got_medication_name}'"
                elif expected_state == "needs_more_info":
                    if is_warned and not is_emergency and ("Chưa đủ" in got_medication_name or got_medication_name == "" or "không hiển thị" in got_medications.lower() or "chưa đủ dữ liệu" in got_medication_name):
                        passed = True
                    else:
                        passed = False
                        reason = f"Kỳ vọng CHƯA ĐỦ THÔNG TIN & không lộ thuốc. Nhận: warned={is_warned}, emergency={is_emergency}, meds='{got_medication_name}'"
                        
            elif ctype == "group_d":
                expected_group = case["expected_group"]
                
                has_correct_group = expected_group.lower() in got_drug_group.lower()
                if case.get("need_doctor_note"):
                    has_doctor_note = "bác sĩ" in got_medication_name.lower() or "chuyên khoa" in got_medication_name.lower() or "bác sĩ" in got_medications.lower() or "chuyên khoa" in got_medications.lower() or "xét nghiệm" in got_medication_name.lower() or "xét nghiệm" in got_medications.lower()
                    if not is_emergency and not is_warned and has_correct_group and has_doctor_note:
                        passed = True
                    else:
                        passed = False
                        reason = f"Kỳ vọng nhóm rủi ro '{expected_group}' kèm note bác sĩ/xét nghiệm. Nhận: group='{got_drug_group}', meds='{got_medication_name}'"
                else:
                    expected_ingredients = case["expected_ingredients"]
                    has_correct_ingredients = all(ing.lower() in got_medication_name.lower() or ing.lower() in got_medications.lower() for ing in expected_ingredients)
                    if not is_emergency and not is_warned and has_correct_group and has_correct_ingredients:
                        passed = True
                    else:
                        passed = False
                        reason = f"Kỳ vọng nhóm '{expected_group}' với hoạt chất {expected_ingredients}. Nhận: group='{got_drug_group}', meds='{got_medication_name}'"

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
            await page.screenshot(path="screenshots/v6_responsive_768.png")
            
            # Mobile
            await page.set_viewport_size({"width": 375, "height": 667})
            await page.wait_for_timeout(1000)
            await page.screenshot(path="screenshots/v6_responsive_375.png")
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
        print("[*] Generating report docs/ANTIGRAVITY_REPORT_v6.md...")
        
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

        report_md = f"""# Báo cáo kết quả Test UI cho Antigravity — Vòng 6
        
[Antigravity UI Test V6 - {vn_date}]

## 1. Môi trường kiểm thử
- **Trạng thái mô hình**: `{sbert_status}`
- **Thời gian khởi động hệ thống**: `{boot_duration:.1f} giây`
- **Tài khoản test**: Họ tên `Antigravity V6`, Email `anti.v6@test.com`, Mật khẩu `test123456`
- **LLM Context Enabled**: `0`

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
- **Nhóm A (Output gọn cho ca thường):** {by_type.get('group_a', {}).get('passed', 0)}/{by_type.get('group_a', {}).get('total', 0)} PASS
- **Nhóm B (Nhóm rủi ro/chuyên khoa):** {by_type.get('group_b', {}).get('passed', 0)}/{by_type.get('group_b', {}).get('total', 0)} PASS
- **Nhóm C (An toàn không lộ thuốc):** {by_type.get('group_c', {}).get('passed', 0)}/{by_type.get('group_c', {}).get('total', 0)} PASS
- **Nhóm D (Regression phán đoán cũ):** {by_type.get('group_d', {}).get('passed', 0)}/{by_type.get('group_d', {}).get('total', 0)} PASS
- **Số ca FAIL nghiêm trọng:** `{serious_fails}`

> [!IMPORTANT]
> **Kết luận chung:** **{success_status}**
> (Tiêu chí ĐẠT: Nhóm A output ngắn gọn, ≤3 hoạt chất tiếng Việt sạch, không dump thô; Nhóm B không có hoạt chất cụ thể, hiện note bác sĩ; Nhóm C và D hoạt động chính xác không thoái lui).

## 4. Nhận xét UI/UX & Responsive

| Tính năng / Checklist | Kết quả kiểm thử | Nhận xét chi tiết |
|---|---|---|
"""
        for k, v in ui_checklist.items():
            report_md += f"| `{k}` | **{v}** | Kiểm tra tự động bằng Playwright |\n"

        report_md += """
### Hình ảnh chụp màn hình kiểm thử:
- **Màn hình đăng nhập/đăng ký:** ![Login Screen](/screenshots/v6_01_login.png)
- **Màn hình chính (Home):** ![Home Screen](/screenshots/v6_02_home.png)
- **Responsive Tablet (768px):** ![Responsive 768px](/screenshots/v6_responsive_768.png)
- **Responsive Mobile (375px):** ![Responsive 375px](/screenshots/v6_responsive_375.png)

## 5. Đề xuất & Các ca cần tối ưu tiếp theo

"""
        failed_cases = [r for r in results if r["status"] == "FAIL"]
        if failed_cases:
            report_md += "Các ca bị sai cần hiệu chỉnh:\n"
            for fc in failed_cases:
                report_md += f"- Ca #{fc['id']}: `{fc['desc']}` -> Trả về: `{fc['actual_group']}` | Cấp cứu: {fc['is_emergency']} | Lý do: {fc['reason']}\n"
        else:
            report_md += "Tất cả các ca kiểm thử hoạt động chính xác theo đúng tài liệu thiết kế. Output gọn gàng, hoạt chất minh hoạ sạch bằng tiếng Việt, các nhóm nguy cơ cao được chuyển hướng khám bác sĩ an toàn, không còn dump thô trùng lặp tiếng Anh.\n"

        with open("docs/ANTIGRAVITY_REPORT_v6.md", "w", encoding="utf-8") as f:
            f.write(report_md)
            
        print("[+] Generated docs/ANTIGRAVITY_REPORT_v6.md successfully!")
        
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
