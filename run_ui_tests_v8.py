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

CASES_V8 = [
    # NHÓM A1 — Ca OTC đã vá: phải GỢI Ý TRỰC TIẾP đúng nhóm + có hoạt chất
    {
        "id": 1,
        "desc": "Mấy ngày không đi cầu được, phân khô cứng, rặn khó",
        "expected_group": "thuốc nhuận tràng",
        "expected_ingredients": ["macrogol", "lactulose"],
        "type": "group_a1",
        "reason": "Nhóm nhuận tràng (OTC, gợi ý trực tiếp), có hoạt chất; KHÔNG ra 'dạ dày'"
    },
    {
        "id": 2,
        "desc": "Nấm kẽ chân, ngứa, da trắng bợt bong tróc, mùi hôi",
        "expected_group": "thuốc kháng nấm/ký sinh trùng ngoài da",
        "expected_ingredients": ["clotrimazol", "terbinafin"],
        "type": "group_a1",
        "reason": "Nhóm kháng nấm/ký sinh trùng ngoài da; KHÔNG ra 'kháng histamin'"
    },
    {
        "id": 3,
        "desc": "Nhức nửa đầu theo nhịp mạch, sợ ánh sáng, buồn nôn",
        "expected_group": "thuốc giảm đau hạ sốt",
        "expected_ingredients": ["paracetamol", "ibuprofen"],
        "type": "group_a1",
        "reason": "Nhóm giảm đau hạ sốt (migraine); KHÔNG ra 'thuốc chống nôn'"
    },
    {
        "id": 4,
        "desc": "Trẻ đi ngoài tóe nước liên tục, lừ đừ, mắt trũng",
        "expected_group": "bù dịch và điện giải",
        "expected_ingredients": ["oresol", "ors"],
        "type": "group_a1",
        "reason": "Nhóm bù dịch và điện giải (ORS); KHÔNG ra 'kháng virus'"
    },

    # NHÓM A2 — Ca KÊ ĐƠN đã vá: nêu ĐÚNG TÊN NHÓM + cảnh báo
    {
        "id": 5,
        "desc": "Hồi hộp, sụt cân nhanh, run tay, ra nhiều mồ hôi",
        "expected_group": "thuốc nội tiết tuyến giáp",
        "type": "group_a2",
        "reason": "Nêu nhóm nội tiết tuyến giáp + 'đi khám/kê đơn'; KHÔNG ra 'ung thư', không lộ hoạt chất"
    },
    {
        "id": 6,
        "desc": "Mệt mỏi, tăng cân, da khô, rụng tóc, sợ lạnh, cổ hơi to",
        "expected_group": "thuốc nội tiết tuyến giáp",
        "type": "group_a2",
        "reason": "Nêu nhóm nội tiết tuyến giáp + cảnh báo kê đơn; KHÔNG ra 'tim mạch', không lộ hoạt chất"
    },
    {
        "id": 7,
        "desc": "Nổi mụn nước đau rát thành chùm ở môi và quanh miệng",
        "expected_group": "thuốc kháng virus",
        "type": "group_a2",
        "reason": "Nêu nhóm kháng virus + cảnh báo kê đơn; KHÔNG ra 'kháng nấm', không lộ hoạt chất"
    },
    {
        "id": 8,
        "desc": "Tê bì bàn chân hai bên ở người tiểu đường lâu năm",
        "expected_group": "thuốc chống co giật/đau thần kinh",
        "type": "group_a2",
        "reason": "Nêu nhóm chống co giật/đau thần kinh + cảnh báo; KHÔNG ra 'corticosteroid', không lộ hoạt chất"
    },
    {
        "id": 9,
        "desc": "Đau quặn bụng dưới từng cơn, buồn đi ngoài, phân nhầy máu, sốt",
        "expected_group": "thuốc kháng sinh",
        "type": "group_a2",
        "reason": "Nêu nhóm kháng sinh + cảnh báo kê đơn, không lộ hoạt chất"
    },

    # NHÓM B — Chặn đoán bừa (không lệch đề kiểu 'tự tin sai')
    {
        "id": 10,
        "desc": "Trong người thấy khó chịu",
        "type": "group_b",
        "reason": "Cần thêm thông tin (không gợi ý nhóm cụ thể); tuyệt đối KHÔNG ra 'thuốc điều trị đái tháo đường'"
    },

    # NHÓM C — Cố ý NÉ an toàn
    {
        "id": 11,
        "desc": "Bé sốt 39 độ, quấy khóc, bỏ bú",
        "type": "group_c",
        "reason": "Cần thêm thông tin / chuyển khám; KHÔNG tự kê thuốc cho trẻ"
    },
    {
        "id": 12,
        "desc": "Chảy máu chân răng, mệt mỏi, dễ bầm tím",
        "type": "group_c",
        "reason": "Cần thêm thông tin / đi khám (nghi huyết học); KHÔNG tự gợi ý vitamin"
    },

    # NHÓM D — Regression an toàn lõi (không đụng)
    {
        "id": 13,
        "desc": "Đau ngực dữ dội lan tay trái, vã mồ hôi, khó thở",
        "type": "group_d_emergency",
        "reason": "CẤP CỨU (422), title '⚠️ Cần hỗ trợ y tế khẩn cấp', không thuốc"
    },
    {
        "id": 14,
        "desc": "Da nổi mẩn đỏ, ngứa nhiều, hắt hơi sổ mũi",
        "expected_group": "thuốc kháng histamin",
        "expected_ingredients": ["cetirizin", "loratadin", "fexofenadin"],
        "type": "group_d_otc",
        "reason": "Gợi ý TRỰC TIẾP nhóm kháng histamin (200) + hoạt chất"
    },
    {
        "id": 15,
        "desc": "Sụt cân nhiều, mệt mỏi kéo dài, nổi hạch, ho ra máu",
        "expected_group": "thuốc/điều trị ung thư",
        "type": "group_d_never",
        "reason": "Nhóm ung thư KHÔNG bị nêu như gợi ý; chuyển khám chuyên khoa"
    }
]

COMMON_DRUGS = [
    "cetirizin", "loratadin", "fexofenadin", "omeprazol", "pantoprazol", "antacid",
    "acetylcystein", "bromhexin", "guaifenesin", "paracetamol", "ibuprofen",
    "amoxicillin", "cephalexin", "penicillin", "erythromycin", "ciprofloxacin",
    "amlodipin", "captopril", "losartan", "bisoprolol", "diazepam", "rotundin",
    "sertralin", "fluoxetin", "olanzapin", "sắt", "acid folic", "b12",
    "artesunat", "chloroquin", "quinin", "methotrexat", "doxorubicin", "bisacodyl",
    "lactulose", "macrogol", "sorbitol", "clotrimazol", "terbinafin", "oresol",
    "gabapentin", "pregabalin", "levothyroxin", "hydrocortison", "prednisolon"
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
        await page.screenshot(path="screenshots/v8_01_login.png")

        print("[*] Authenticating (Register / Login for Antigravity V8)...")
        try:
            await page.click("button[data-auth-target='register']", force=True)
            await page.wait_for_selector("div[data-auth-view='register']:not(.is-hidden)", timeout=3000)
            
            await page.fill("#register-name", "Antigravity V8")
            await page.fill("#register-email", "anti.v8@test.com")
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
                await page.fill("#login-email", "anti.v8@test.com")
                await page.fill("#login-password", "test123456")
                await page.click("#login-form button[type='submit']", force=True)
                await page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=5000)
                print("[+] Login successful.")
            except Exception as e:
                print(f"[-] Authentication failed: {e}")
                await page.screenshot(path="screenshots/v8_auth_failed.png")
                await browser.close()
                if proc:
                    proc.terminate()
                return

        await page.screenshot(path="screenshots/v8_02_home.png")

        print("[*] Running 15 test cases from test plan...")
        results = []
        
        for case in CASES_V8:
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
            screenshot_path = f"screenshots/v8_{cid:02d}.png"
            await page.screenshot(path=screenshot_path)

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

            if ctype == "group_a1":
                expected_group = case["expected_group"]
                expected_ingredients = case["expected_ingredients"]
                
                has_group_name = expected_group.lower() in got_title.lower() or expected_group.lower() in got_drug_group.lower()
                has_correct_ingredients = any(ing.lower() in got_medication_name.lower() or ing.lower() in got_medications.lower() for ing in expected_ingredients)
                
                if has_group_name and has_correct_ingredients and not is_emergency and not is_warned:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng nhóm OTC '{expected_group}', hoạt chất {expected_ingredients} (nhận: group={got_drug_group}, meds={got_medication_name}, warned={is_warned})"
                    
            elif ctype == "group_a2":
                expected_group = case["expected_group"]
                has_group_name = expected_group.lower() in got_title.lower()
                
                correct_title = has_group_name and ("khám" in got_title.lower() or "bác sĩ" in got_title.lower())
                correct_note = has_ke_don
                no_leak = not has_exposed_drugs
                
                if correct_title and correct_note and no_leak:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng title chứa '{expected_group}' + khám/bác sĩ, note chứa 'KÊ ĐƠN', không lộ thuốc (nhận: title={got_title}, note_kê_đơn={has_ke_don}, lộ={exposed_drugs})"
                    
            elif ctype == "group_b":
                # Expect 'Trong người thấy khó chịu' to be warned and NOT diabetes
                correct_title = is_warned and "đái tháo đường" not in got_title.lower() and "đái tháo đường" not in got_drug_group.lower()
                no_leak = not has_exposed_drugs
                
                if correct_title and no_leak:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng cảnh báo thêm thông tin & không gợi ý đái tháo đường (nhận: title={got_title}, group={got_drug_group})"
                    
            elif ctype == "group_c":
                # Children safety / general checkups -> needs more info
                correct_title = is_warned
                no_leak = not has_exposed_drugs
                
                if correct_title and no_leak:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng chuyển khám / cần thêm thông tin (nhận: title={got_title})"
                    
            elif ctype == "group_d_emergency":
                correct_title = is_emergency and "khẩn cấp" in got_title.lower()
                no_leak = not has_exposed_drugs
                
                if correct_title and no_leak:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng trạng thái CẤP CỨU (nhận: title={got_title})"
                    
            elif ctype == "group_d_otc":
                expected_group = case["expected_group"]
                expected_ingredients = case["expected_ingredients"]
                
                has_group_name = expected_group.lower() in got_title.lower() or expected_group.lower() in got_drug_group.lower()
                has_correct_ingredients = any(ing.lower() in got_medication_name.lower() or ing.lower() in got_medications.lower() for ing in expected_ingredients)
                
                if has_group_name and has_correct_ingredients and not is_emergency and not is_warned:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng nhóm OTC '{expected_group}' (nhận: {got_drug_group})"
                    
            elif ctype == "group_d_never":
                expected_group = case["expected_group"]
                has_group_name = expected_group.lower() in got_title.lower()
                
                correct_title = not has_group_name and "chưa đủ" in got_title.lower()
                no_leak = not has_exposed_drugs
                
                if correct_title and no_leak:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng không Suggest nhóm ung thư (nhận: title={got_title})"

            status = "PASS" if passed else "FAIL"
            print(f"Ca #{cid:02d} ({ctype}): {status} | Mô tả: '{desc[:30]}...' | Title: '{got_title}' | {reason}")
            
            results.append({
                "id": cid,
                "desc": desc,
                "type": ctype,
                "got_title": got_title,
                "got_group": got_drug_group,
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
            await page.screenshot(path="screenshots/v8_responsive_768.png")
            
            # Mobile
            await page.set_viewport_size({"width": 375, "height": 667})
            await page.wait_for_timeout(1000)
            await page.screenshot(path="screenshots/v8_responsive_375.png")
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
        print("[*] Generating report docs/ANTIGRAVITY_REPORT_v8.md...")
        
        total_cases = len(results)
        passed_cases = sum(1 for r in results if r["status"] == "PASS")
        serious_fails = total_cases - passed_cases
        success_status = "ĐẠT" if serious_fails == 0 else "CHƯA ĐẠT"

        import datetime
        vn_date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        report_md = f"""# Báo cáo kết quả Test UI cho Antigravity — Vòng 8

[Antigravity UI Test V8 - {vn_date}]

## 1. Môi trường kiểm thử
- **Trạng thái mô hình**: `{sbert_status}`
- **Thời gian khởi động hệ thống**: `{boot_duration:.1f} giây`
- **Tài khoản test**: Họ tên `Antigravity V8`, Email `anti.v8@test.com`, Mật khẩu `test123456`
- **LLM Context Enabled**: `0`

## 2. Bảng kết quả từng ca

| # | Mô tả bệnh | Nhóm trả về | Đúng nhóm kỳ vọng? | Kê đơn nêu tên + ẩn thuốc? | OTC có hoạt chất? | Kết quả | Chi tiết / Lý do |
|---|---|---|---|---|---|---|---|
"""
        for r in results:
            report_md += f"| {r['id']} | {r['desc']} | `{r['got_group']}` | {r['has_group_name']} | {r['has_ke_don']} | {r['has_exposed_drugs']} | **{r['status']}** | {r['reason'] or 'Khớp kỳ vọng'} |\n"

        report_md += f"""
## 3. Tổng hợp thống kê

- **Tổng số ca test**: {passed_cases}/{total_cases} PASS
- **Số ca FAIL nghiêm trọng:** `{serious_fails}`

> [!IMPORTANT]
> **Kết luận chung:** **{success_status}**
> (Tiêu chí ĐẠT: Nhóm A1 ra đúng nhóm OTC mới + có hoạt chất; Nhóm A2 kê đơn nêu đúng tên nhóm + 'đi khám', không lộ hoạt chất; Nhóm B/C/D hoạt động chính xác không thoái lui).

## 4. Nhận xét UI/UX & Responsive

| Tính năng / Checklist | Giao diện | Nhận xét chi tiết |
|---|---|---|
"""
        for k, v in ui_checklist.items():
            report_md += f"| `{k}` | **{v}** | Kiểm tra tự động bằng Playwright |\n"

        report_md += """
### Hình ảnh chụp màn hình kiểm thử:
- **Màn hình đăng nhập/đăng ký:** ![Login Screen](/screenshots/v8_01_login.png)
- **Màn hình chính (Home):** ![Home Screen](/screenshots/v8_02_home.png)
- **Responsive Tablet (768px):** ![Responsive 768px](/screenshots/v8_responsive_768.png)
- **Responsive Mobile (375px):** ![Responsive 375px](/screenshots/v8_responsive_375.png)

## 5. Đề xuất & Các ca cần tối ưu tiếp theo

"""
        failed_cases = [r for r in results if r["status"] == "FAIL"]
        if failed_cases:
            report_md += "Các ca bị sai cần hiệu chỉnh:\n"
            for fc in failed_cases:
                report_md += f"- Ca #{fc['id']}: `{fc['desc']}` -> Title: `{fc['got_title']}` | Lý do: {fc['reason']}\n"
        else:
            report_md += "Tất cả các ca kiểm thử hoạt động chính xác theo đúng tài liệu thiết kế của Vòng 8. Sự cải thiện về mặt chất lượng dự đoán và tầng trích triệu chứng hoạt động cực kỳ tốt: không còn hiện tượng lệch nhóm thuốc (như tuyến giáp thành ung thư hay nấm da thành kháng histamin). Ca chặn đoán bừa và an toàn nhi khoa vẫn hoạt động ổn định.\n"

        with open("docs/ANTIGRAVITY_REPORT_v8.md", "w", encoding="utf-8") as f:
            f.write(report_md)
            
        print("[+] Generated docs/ANTIGRAVITY_REPORT_v8.md successfully!")
        
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
