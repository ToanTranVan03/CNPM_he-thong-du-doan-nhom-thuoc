import asyncio
import os
import sys
import subprocess
import time
import urllib.request
import json
import re
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

CASES_V7 = [
    # NHÓM A — Nhóm KÊ ĐƠN: phải NÊU TÊN NHÓM + cảnh báo
    {
        "id": 1,
        "desc": "Tiểu buốt, tiểu rắt, nước tiểu đục, đau bụng dưới",
        "expected_group": "thuốc kháng sinh",
        "type": "group_a",
        "reason": "Nhóm kháng sinh (kê đơn), cần hiện tên nhóm + cảnh báo đi khám, không hiện hoạt chất cụ thể"
    },
    {
        "id": 2,
        "desc": "Đau ngực trái, khó thở khi gắng sức, hồi hộp đánh trống ngực",
        "expected_group": "thuốc tim mạch/huyết áp",
        "type": "group_a",
        "reason": "Nhóm tim mạch/huyết áp (kê đơn), cần hiện tên nhóm + cảnh báo đi khám, không hiện hoạt chất cụ thể"
    },
    {
        "id": 3,
        "desc": "Đau họng dữ dội, nuốt đau, sốt, amidan sưng có mủ trắng",
        "expected_group": "thuốc kháng sinh",
        "type": "group_a",
        "reason": "Nhóm kháng sinh (kê đơn), cần hiện tên nhóm + cảnh báo đi khám, không hiện hoạt chất cụ thể"
    },
    {
        "id": 4,
        "desc": "Mất ngủ kéo dài nhiều tuần, lo âu, bồn chồn, khó tập trung",
        "expected_group": "thuốc thần kinh/tâm thần",
        "type": "group_a",
        "reason": "Nhóm thần kinh/tâm thần (kê đơn), cần hiện tên nhóm + cảnh báo đi khám, không hiện hoạt chất cụ thể"
    },

    # NHÓM B — "Không bao giờ gợi ý" (ung thư/miễn dịch): KHÔNG nêu như gợi ý
    {
        "id": 5,
        "desc": "Sụt cân nhiều, mệt mỏi kéo dài, nổi hạch, ho ra máu",
        "expected_group": "thuốc/điều trị ung thư",
        "type": "group_b",
        "reason": "Nhóm điều trị ung thư (không bao giờ gợi ý), không được hiện tên nhóm gợi ý, giữ cảnh báo chung chung"
    },

    # NHÓM C — Cấp cứu (regression)
    {
        "id": 6,
        "desc": "Đau ngực dữ dội lan tay trái, vã mồ hôi, khó thở",
        "type": "group_c_emergency",
        "reason": "Ca cấp cứu nhồi máu cơ tim, phải hiển thị cảnh báo cấp cứu khẩn cấp, không có thuốc"
    },
    {
        "id": 7,
        "desc": "Sốt cao, đau đầu dữ dội, cứng gáy, nôn, sợ ánh sáng",
        "type": "group_c_neuro",
        "reason": "Dấu hiệu thần kinh nguy hiểm/cứng cổ gáy, phải cảnh báo cấp cứu/khám ngay, không gợi ý thuốc"
    },

    # NHÓM D — Ca OTC (regression: vẫn gợi ý trực tiếp như cũ)
    {
        "id": 8,
        "desc": "Da nổi mẩn đỏ, ngứa nhiều, hắt hơi sổ mũi",
        "expected_group": "thuốc kháng histamin",
        "expected_ingredients": ["cetirizin", "loratadin", "fexofenadin"],
        "type": "group_d",
        "reason": "Ca OTC dị ứng thông thường, gợi ý trực tiếp nhóm kháng histamin và các hoạt chất"
    },
    {
        "id": 9,
        "desc": "Sốt cao, đau mỏi người",
        "expected_group": "thuốc giảm đau hạ sốt",
        "expected_ingredients": ["paracetamol", "ibuprofen"],
        "type": "group_d",
        "reason": "Ca OTC sốt cao đau mỏi, gợi ý trực tiếp nhóm giảm đau hạ sốt và các hoạt chất"
    }
]

COMMON_DRUGS = [
    "cetirizin", "loratadin", "fexofenadin", "omeprazol", "pantoprazol", "antacid",
    "acetylcystein", "bromhexin", "guaifenesin", "paracetamol", "ibuprofen",
    "amoxicillin", "cephalexin", "penicillin", "erythromycin", "ciprofloxacin",
    "amlodipin", "captopril", "losartan", "bisoprolol", "diazepam", "rotundin",
    "sertralin", "fluoxetin", "olanzapin", "sắt", "acid folic", "b12",
    "artesunat", "chloroquin", "quinin", "methotrexat", "doxorubicin"
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
        my_env = os.environ.copy()
        my_env["LLM_CONTEXT_ENABLED"] = "0"
        proc = subprocess.Popen([sys.executable, "backend/app.py"], cwd="d:/CNPM", env=my_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        backend_started = True
        
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
    
    sbert_status = "SBERT hoạt động (SBERT thật)"
    try:
        import sentence_transformers, torch
    except ImportError:
        sbert_status = "fallback (không SBERT)"

    print(f"[*] Môi trường: {sbert_status}")
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
        await page.screenshot(path="screenshots/v7_01_login.png")

        print("[*] Authenticating (Register / Login for Antigravity V7)...")
        try:
            await page.click("button[data-auth-target='register']", force=True)
            await page.wait_for_selector("div[data-auth-view='register']:not(.is-hidden)", timeout=3000)
            
            await page.fill("#register-name", "Antigravity V7")
            await page.fill("#register-email", "anti.v7@test.com")
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
                await page.fill("#login-email", "anti.v7@test.com")
                await page.fill("#login-password", "test123456")
                await page.click("#login-form button[type='submit']", force=True)
                await page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=5000)
                print("[+] Login successful.")
            except Exception as e:
                print(f"[-] Authentication failed: {e}")
                await page.screenshot(path="screenshots/v7_auth_failed.png")
                await browser.close()
                if proc:
                    proc.terminate()
                return

        await page.screenshot(path="screenshots/v7_02_home.png")

        print("[*] Running 9 test cases from test plan...")
        results = []
        
        for case in CASES_V7:
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
            screenshot_path = f"screenshots/v7_{cid:02d}.png"
            await page.screenshot(path=screenshot_path)

            # Verification logic for report table
            # title hiển thị | có nêu tên nhóm? | có "KÊ ĐƠN"? | có lộ thuốc cụ thể? | PASS/FAIL
            has_group_name = False
            has_ke_don = "kê đơn" in got_note.lower() or "kê đơn" in got_title.lower() or "kê đơn" in got_medication_name.lower() or "kê đơn" in got_medications.lower()
            
            # Check for leaked active ingredients
            exposed_drugs = []
            for drug in COMMON_DRUGS:
                if re.search(r'\b' + re.escape(drug) + r'\b', got_medication_name.lower()) or re.search(r'\b' + re.escape(drug) + r'\b', got_medications.lower()):
                    exposed_drugs.append(drug)
            
            has_exposed_drugs = len(exposed_drugs) > 0

            passed = False
            reason = ""
            
            is_emergency = "cần hỗ trợ y tế khẩn cấp" in got_title.lower() or "cấp cứu" in got_note.lower() or "115" in got_note.lower()
            is_warned = "Chưa đủ" in got_title or "Chưa đủ" in got_drug_group or "cần thêm" in got_title.lower() or "không nhận diện" in got_title.lower() or "chưa đủ dữ liệu" in got_title.lower() or "cần đi khám" in got_title.lower()

            if ctype == "group_a":
                expected_group = case["expected_group"]
                # Group name must be mentioned in display_title
                has_group_name = expected_group.lower() in got_title.lower()
                
                # Expectations: Title contains group name & "khám/bác sĩ", note contains "KÊ ĐƠN", NO exposed drugs
                correct_title = has_group_name and ("khám" in got_title.lower() or "bác sĩ" in got_title.lower())
                correct_note = has_ke_don
                no_leak = not has_exposed_drugs
                
                if correct_title and correct_note and no_leak:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng title chứa '{expected_group}' + khám/bác sĩ (nhận: {correct_title}), note chứa 'KÊ ĐƠN' (nhận: {correct_note}), không lộ thuốc (nhận: lộ {exposed_drugs if has_exposed_drugs else 'Không'})"
                    
            elif ctype == "group_b":
                expected_group = case["expected_group"]
                # Must NOT contain group name in title suggestion
                has_group_name = expected_group.lower() in got_title.lower()
                
                # Expectations: Title does NOT suggest the group, note does NOT say KÊ ĐƠN (keeps it generic), NO exposed drugs
                correct_title = not has_group_name and "chưa đủ" in got_title.lower()
                correct_note = not has_ke_don
                no_leak = not has_exposed_drugs
                
                if correct_title and correct_note and no_leak:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng title giữ chung chung không Suggest nhóm (nhận: Suggest={has_group_name}), không chứa 'KÊ ĐƠN' (nhận: {not correct_note}), không lộ thuốc (nhận: lộ {exposed_drugs if has_exposed_drugs else 'Không'})"
                    
            elif ctype == "group_c_emergency":
                # Emergency: Title is emergency, no group name, no ke_don warning needed, no exposed drugs
                correct_title = is_emergency and "khẩn cấp" in got_title.lower()
                no_leak = not has_exposed_drugs
                
                if correct_title and no_leak:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng trạng thái CẤP CỨU (nhận: emergency={is_emergency}), không lộ thuốc (nhận: lộ {exposed_drugs if has_exposed_drugs else 'Không'})"
                    
            elif ctype == "group_c_neuro":
                # Neuro signs: Danger signs warning, no group suggestion, no exposed drugs
                correct_note = "thần kinh nguy hiểm" in got_note.lower() or "cứng cổ" in got_note.lower() or "cấp cứu" in got_note.lower() or "đến cơ sở y tế" in got_note.lower()
                no_leak = not has_exposed_drugs
                
                if correct_note and no_leak:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng cảnh báo thần kinh nguy hiểm/cấp cứu trong note (nhận: {correct_note}), không lộ thuốc (nhận: lộ {exposed_drugs if has_exposed_drugs else 'Không'})"
                    
            elif ctype == "group_d":
                expected_group = case["expected_group"]
                expected_ingredients = case["expected_ingredients"]
                
                has_group_name = expected_group.lower() in got_title.lower() or expected_group.lower() in got_drug_group.lower()
                # OTC: suggests group directly, has correct ingredients
                has_correct_ingredients = all(ing.lower() in got_medication_name.lower() or ing.lower() in got_medications.lower() for ing in expected_ingredients)
                
                if has_group_name and has_correct_ingredients and not is_emergency and not is_warned:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng nhóm OTC '{expected_group}' (nhận: {has_group_name}), hoạt chất {expected_ingredients} (nhận: {has_correct_ingredients}), không bị cảnh báo/cấp cứu (nhận: warned={is_warned}, emergency={is_emergency})"

            status = "PASS" if passed else "FAIL"
            print(f"Ca #{cid:02d} ({ctype}): {status} | Mô tả: '{desc[:30]}...' | Title: '{got_title}' | {reason}")
            
            results.append({
                "id": cid,
                "desc": desc,
                "type": ctype,
                "got_title": got_title,
                "has_group_name": "Có" if has_group_name else "Không",
                "has_ke_don": "Có" if has_ke_don else "Không",
                "has_exposed_drugs": "Có (LỘ)" if has_exposed_drugs else "Không (AN TOÀN)",
                "exposed_drugs": exposed_drugs,
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
            await page.screenshot(path="screenshots/v7_responsive_768.png")
            
            # Mobile
            await page.set_viewport_size({"width": 375, "height": 667})
            await page.wait_for_timeout(1000)
            await page.screenshot(path="screenshots/v7_responsive_375.png")
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
            val = await page.input_value("#case-description")
            await page.click("#diagnosis-form button[type='submit']", force=True)
            await page.wait_for_timeout(1500)
            ui_checklist["long_input_handling"] = "PASS" if len(val) >= 2000 else "FAIL (Could not fill 2000 characters)"
        except Exception as e:
            ui_checklist["long_input_handling"] = f"FAIL ({e})"

        # 5.8 Console errors
        errs_count = len(console_errors)
        ui_checklist["no_console_errors"] = "PASS" if errs_count == 0 else f"FAIL ({errs_count} errors logged: {console_errors[:2]})"

        # 6. Generate the markdown report
        print("[*] Generating report docs/ANTIGRAVITY_REPORT_v7.md...")
        
        total_cases = len(results)
        passed_cases = sum(1 for r in results if r["status"] == "PASS")
        serious_fails = total_cases - passed_cases
        success_status = "ĐẠT" if serious_fails == 0 else "CHƯA ĐẠT"

        import datetime
        vn_date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        report_md = f"""# Báo cáo kết quả Test UI cho Antigravity — Vòng 7

[Antigravity UI Test V7 - {vn_date}]

## 1. Môi trường kiểm thử
- **Trạng thái mô hình**: `{sbert_status}`
- **Thời gian khởi động hệ thống**: `{boot_duration:.1f} giây`
- **Tài khoản test**: Họ tên `Antigravity V7`, Email `anti.v7@test.com`, Mật khẩu `test123456`
- **LLM Context Enabled**: `0`

## 2. Bảng kết quả từng ca

| # | Mô tả bệnh | Title hiển thị | Có nêu tên nhóm? | Có "KÊ ĐƠN"? | Có lộ thuốc cụ thể? | Kết quả | Chi tiết / Lý do |
|---|---|---|---|---|---|---|---|
"""
        for r in results:
            report_md += f"| {r['id']} | {r['desc']} | `{r['got_title']}` | {r['has_group_name']} | {r['has_ke_don']} | {r['has_exposed_drugs']} | **{r['status']}** | {r['reason'] or 'Khớp kỳ vọng'} |\n"

        report_md += f"""
## 3. Tổng hợp thống kê

- **Tổng số ca test**: {passed_cases}/{total_cases} PASS
- **Số ca FAIL nghiêm trọng:** `{serious_fails}`

> [!IMPORTANT]
> **Kết luận chung:** **{success_status}**
> (Tiêu chí ĐẠT: Nhóm A hiển thị đúng tên nhóm + từ chối/cảnh báo kê đơn an toàn, không lộ hoạt chất cụ thể; Nhóm B không gợi ý/nêu tên nhóm điều trị ung thư; Nhóm C/neuro giữ vững an toàn; Nhóm D vẫn đề xuất nhóm OTC và hoạt chất bình thường).

## 4. Nhận xét UI/UX & Responsive

| Tính năng / Checklist | Giao diện | Nhận xét chi tiết |
|---|---|---|
"""
        for k, v in ui_checklist.items():
            report_md += f"| `{k}` | **{v}** | Kiểm tra tự động bằng Playwright |\n"

        report_md += """
### Hình ảnh chụp màn hình kiểm thử:
- **Màn hình đăng nhập/đăng ký:** ![Login Screen](/screenshots/v7_01_login.png)
- **Màn hình chính (Home):** ![Home Screen](/screenshots/v7_02_home.png)
- **Responsive Tablet (768px):** ![Responsive 768px](/screenshots/v7_responsive_768.png)
- **Responsive Mobile (375px):** ![Responsive 375px](/screenshots/v7_responsive_375.png)

## 5. Đề xuất & Các ca cần tối ưu tiếp theo

"""
        failed_cases = [r for r in results if r["status"] == "FAIL"]
        if failed_cases:
            report_md += "Các ca bị sai cần hiệu chỉnh:\n"
            for fc in failed_cases:
                report_md += f"- Ca #{fc['id']}: `{fc['desc']}` -> Title: `{fc['got_title']}` | Lý do: {fc['reason']}\n"
        else:
            report_md += "Tất cả các ca kiểm thử hoạt động chính xác theo đúng tài liệu thiết kế của Vòng 7. Sự cải thiện về mặt UX từ chối nhóm kê đơn hoạt động cực tốt: hiện tên nhóm đi kèm cảnh báo KÊ ĐƠN rõ ràng mà vẫn tuyệt đối bảo mật, không rò rỉ hoạt chất cụ thể. Ca ung thư và cấp cứu được giữ an toàn tối đa. Ca OTC vẫn được gợi ý trực tiếp như bình thường.\n"

        with open("docs/ANTIGRAVITY_REPORT_v7.md", "w", encoding="utf-8") as f:
            f.write(report_md)
            
        print("[+] Generated docs/ANTIGRAVITY_REPORT_v7.md successfully!")
        
        await browser.close()
        
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
