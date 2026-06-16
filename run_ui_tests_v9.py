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

CASES_V9 = [
    # NHÓM A — CHỐNG CHỈ ĐỊNH theo bệnh nền/tương tác (phải CHẶN)
    {
        "id": 1,
        "desc": "Ông tôi 80 tuổi, suy thận mạn, đau khớp gối nhiều",
        "expected_group": "thuốc kháng viêm không steroid",
        "type": "group_a",
        "reason_keywords": ["suy than", "benh than", "khong tu dung", "chong chi dinh"],
        "reason": "Chống chỉ định NSAID với suy thận mạn"
    },
    {
        "id": 2,
        "desc": "Tôi bị loét dạ dày tá tràng, mấy nay đau lưng nhiều",
        "expected_group": "thuốc kháng viêm không steroid",
        "type": "group_a",
        "reason_keywords": ["loet da day", "loet ta trang", "chong chi dinh"],
        "reason": "Chống chỉ định NSAID với loét dạ dày tá tràng"
    },
    {
        "id": 3,
        "desc": "Tôi đang uống warfarin chống đông, giờ đau khớp gối sưng",
        "expected_group": "thuốc kháng viêm không steroid",
        "type": "group_a",
        "reason_keywords": ["chong dong", "khang tieu cau", "chay mau"],
        "reason": "Tương tác NSAID + thuốc chống đông gây nguy cơ chảy máu"
    },
    {
        "id": 4,
        "desc": "Tôi bị xơ gan, sốt đau đầu đau người",
        "expected_group": "thuốc giảm đau hạ sốt",
        "type": "group_a",
        "reason_keywords": ["gan", "doc gan", "paracetamol"],
        "reason": "Bệnh gan chống chỉ định/cảnh báo dùng paracetamol độc gan"
    },

    # NHÓM B — Cấp cứu / dị ứng theo nhân quả
    {
        "id": 5,
        "desc": "Ăn tôm xong sưng môi, ngứa, khó thở",
        "type": "group_b_emergency",
        "reason": "Nghi phản vệ (sưng môi + khó thở), phải báo cấp cứu khẩn cấp"
    },
    {
        "id": 6,
        "desc": "Sau khi uống amoxicillin tôi nổi mề đay ngứa khắp người",
        "type": "group_b_allergy",
        "reason_keywords": ["di ung thuoc", "ngung ngay", "nghi ngo"],
        "reason": "Dị ứng thuốc: mề đay sau khi uống thuốc, cần ngừng ngay"
    },

    # NHÓM C — Tuổi / thai kỳ
    {
        "id": 7,
        "desc": "Tôi đang mang thai 8 tuần, sốt cao, đau nhức người",
        "type": "group_c_pregnancy",
        "reason_keywords": ["thai ky", "mang thai", "san khoa"],
        "reason": "Cảnh báo an toàn thai kỳ, chuyển khám sản khoa"
    },
    {
        "id": 8,
        "desc": "Con tôi 5 tháng tuổi, sốt 38.5 độ, bỏ bú",
        "type": "group_c_infant",
        "reason_keywords": ["so sinh", "nhu nhi", "nhi khoa", "kham bac si"],
        "reason": "Cảnh báo an toàn nhũ nhi (5 tháng), chuyển khám nhi"
    },
    {
        "id": 9,
        "desc": "Bé 2 tuổi nhà tôi bị táo bón mấy ngày",
        "type": "group_c_child",
        "reason_keywords": ["tre em", "nhi khoa", "duoc si"],
        "reason": "Cảnh báo an toàn trẻ em (2 tuổi), tư vấn liều nhi khoa"
    },

    # NHÓM D — KHÔNG false-positive + regression (vẫn gợi ý bình thường)
    {
        "id": 10,
        "desc": "Viêm gân cổ tay, đau khi cử động, sưng nhẹ",
        "expected_group": "thuốc kháng viêm không steroid",
        "expected_ingredients": ["ibuprofen", "naproxen", "diclofenac"],
        "type": "group_d",
        "reason": "Viêm gân không bị chặn nhầm bởi xơ gan/suy gan (gân ≠ gan), gợi ý NSAID bình thường"
    },
    {
        "id": 11,
        "desc": "Da nổi mẩn đỏ, ngứa nhiều, hắt hơi sổ mũi",
        "expected_group": "thuốc kháng histamin",
        "expected_ingredients": ["cetirizin", "loratadin", "fexofenadin"],
        "type": "group_d",
        "reason": "OTC dị ứng thông thường gợi ý kháng histamin trực tiếp"
    },
    {
        "id": 12,
        "desc": "Sốt cao, đau mỏi người",
        "expected_group": "thuốc giảm đau hạ sốt",
        "expected_ingredients": ["paracetamol", "ibuprofen"],
        "type": "group_d",
        "reason": "OTC sốt đau mỏi thông thường gợi ý giảm đau hạ sốt trực tiếp"
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

def clean_vietnamese_signs(text: str) -> str:
    text = (text or "").lower()
    # Remove signs
    import unicodedata
    normalized = unicodedata.normalize("NFD", text)
    cleaned = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    cleaned = cleaned.replace("đ", "d")
    return cleaned

async def run_tests():
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
        await page.screenshot(path="screenshots/v9_01_login.png")

        print("[*] Authenticating (Register / Login for Antigravity V9)...")
        try:
            await page.click("button[data-auth-target='register']", force=True)
            await page.wait_for_selector("div[data-auth-view='register']:not(.is-hidden)", timeout=3000)
            
            await page.fill("#register-name", "Antigravity V9")
            await page.fill("#register-email", "anti.v9@test.com")
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
                await page.fill("#login-email", "anti.v9@test.com")
                await page.fill("#login-password", "test123456")
                await page.click("#login-form button[type='submit']", force=True)
                await page.wait_for_selector(".app-shell:not(.is-hidden)", timeout=5000)
                print("[+] Login successful.")
            except Exception as e:
                print(f"[-] Authentication failed: {e}")
                await page.screenshot(path="screenshots/v9_auth_failed.png")
                await browser.close()
                if proc:
                    proc.terminate()
                return

        await page.screenshot(path="screenshots/v9_02_home.png")

        print("[*] Running 12 test cases from test plan...")
        results = []
        
        for case in CASES_V9:
            cid = case["id"]
            desc = case["desc"]
            ctype = case["type"]
            
            await page.click("aside.app-sidebar button[data-page='home']", force=True)
            await page.wait_for_selector("#page-home.is-active", timeout=5000)
            await page.click("#clear-case", force=True)
            await page.fill("#case-description", desc)
            await page.click("#diagnosis-form button[type='submit']", force=True)
            await page.wait_for_timeout(1500)
            
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

            screenshot_path = f"screenshots/v9_{cid:02d}.png"
            await page.screenshot(path=screenshot_path)

            # Verification details for the V9 report columns:
            # output | chặn đúng? | lộ thuốc chống chỉ định? | false-positive? | PASS/FAIL
            is_blocked = "Chưa đủ" in got_title or "Chưa đủ" in got_drug_group or "cần thêm" in got_title.lower() or "không nhận diện" in got_title.lower() or "chưa đủ dữ liệu" in got_title.lower() or "cần đi khám" in got_title.lower() or "cảnh báo an toàn" in got_title.lower() or "khẩn cấp" in got_title.lower()
            is_emergency = "cần hỗ trợ y tế khẩn cấp" in got_title.lower() or "cấp cứu" in got_note.lower() or "115" in got_note.lower()
            
            exposed_drugs = []
            for drug in COMMON_DRUGS:
                if re.search(r'\b' + re.escape(drug) + r'\b', got_medication_name.lower()) or re.search(r'\b' + re.escape(drug) + r'\b', got_medications.lower()):
                    exposed_drugs.append(drug)
            
            has_exposed_drugs = len(exposed_drugs) > 0

            passed = False
            chan_dung = "Không"
            lo_thuoc = "Có (LỘ)" if has_exposed_drugs else "Không (AN TOÀN)"
            false_positive = "Không"
            reason = ""

            note_cleaned = clean_vietnamese_signs(got_note + " " + got_title + " " + got_warning + " " + got_medications)

            if ctype == "group_a":
                # Chống chỉ định
                chan_dung = "Có" if is_blocked else "Không"
                correct_title = "cảnh báo an toàn" in got_title.lower()
                correct_keywords = any(clean_vietnamese_signs(kw) in note_cleaned for kw in case["reason_keywords"])
                no_leak = not has_exposed_drugs
                
                if correct_title and correct_keywords and no_leak and is_blocked:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng title 'Cảnh báo an toàn' (nhận: {got_title}), keyword {case['reason_keywords']} (nhận: {correct_keywords}), không lộ thuốc ({lo_thuoc})"

            elif ctype == "group_b_emergency":
                # Emergency
                chan_dung = "Có" if is_blocked else "Không"
                correct_title = is_emergency and "khẩn cấp" in got_title.lower()
                no_leak = not has_exposed_drugs
                
                if correct_title and no_leak:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng CẤP CỨU khẩn cấp (nhận: {got_title}), không lộ thuốc ({lo_thuoc})"

            elif ctype == "group_b_allergy":
                # Dị ứng
                chan_dung = "Có" if is_blocked else "Không"
                correct_title = "cảnh báo an toàn" in got_title.lower()
                correct_keywords = any(clean_vietnamese_signs(kw) in note_cleaned for kw in case["reason_keywords"])
                no_leak = not has_exposed_drugs
                
                if correct_title and correct_keywords and no_leak:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng title 'Cảnh báo an toàn' (nhận: {got_title}), keyword dị ứng {case['reason_keywords']} (nhận: {correct_keywords}), không lộ thuốc ({lo_thuoc})"

            elif ctype in ["group_c_pregnancy", "group_c_infant", "group_c_child"]:
                # Thai kỳ / tuổi
                chan_dung = "Có" if is_blocked else "Không"
                correct_keywords = any(clean_vietnamese_signs(kw) in note_cleaned for kw in case["reason_keywords"])
                no_leak = not has_exposed_drugs
                
                if correct_keywords and no_leak and is_blocked:
                    passed = True
                else:
                    passed = False
                    reason = f"Kỳ vọng chặn + ghi chú có {case['reason_keywords']} (nhận: {correct_keywords}), không lộ thuốc ({lo_thuoc})"

            elif ctype == "group_d":
                # OTC (không được chặn nhầm)
                chan_dung = "Không (Gợi ý trực tiếp)"
                correct_group = case["expected_group"].lower() in got_title.lower() or case["expected_group"].lower() in got_drug_group.lower()
                correct_ingredients = any(ing.lower() in got_medication_name.lower() or ing.lower() in got_medications.lower() for ing in case["expected_ingredients"])
                
                if is_blocked:
                    false_positive = "Có (CHẶN NHẦM)"
                    passed = False
                    reason = "Bị chặn nhầm (False Positive)"
                else:
                    if correct_group and correct_ingredients:
                        passed = True
                    else:
                        passed = False
                        reason = f"Kỳ vọng gợi ý nhóm '{case['expected_group']}' + hoạt chất {case['expected_ingredients']}"

            status = "PASS" if passed else "FAIL"
            print(f"Ca #{cid:02d} ({ctype}): {status} | Mô tả: '{desc[:30]}...' | Title: '{got_title}' | {reason}")
            
            results.append({
                "id": cid,
                "desc": desc,
                "type": ctype,
                "got_title": got_title,
                "chan_dung": chan_dung,
                "lo_thuoc": lo_thuoc,
                "false_positive": false_positive,
                "status": status,
                "reason": reason
            })

        print("[*] Running UI/UX Checklist tests...")
        ui_checklist = {}

        try:
            await page.click("aside.app-sidebar button[data-page='home']", force=True)
            await page.wait_for_selector("#page-home.is-active", timeout=5000)
            await page.fill("#case-description", "Triệu chứng bất kỳ")
            await page.click("#clear-case", force=True)
            val = await page.input_value("#case-description")
            ui_checklist["clear_case_button"] = "PASS" if len(val.strip()) == 0 else "FAIL (Description not cleared)"
        except Exception as e:
            ui_checklist["clear_case_button"] = f"FAIL ({e})"

        try:
            await page.click("#example-case", force=True)
            val = await page.input_value("#case-description")
            ui_checklist["example_case_button"] = "PASS" if len(val.strip()) > 0 else "FAIL (Empty example)"
        except Exception as e:
            ui_checklist["example_case_button"] = f"FAIL ({e})"

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

        try:
            await page.set_viewport_size({"width": 768, "height": 1024})
            await page.wait_for_timeout(1000)
            await page.screenshot(path="screenshots/v9_responsive_768.png")
            
            await page.set_viewport_size({"width": 375, "height": 667})
            await page.wait_for_timeout(1000)
            await page.screenshot(path="screenshots/v9_responsive_375.png")
            bottom_nav_visible = await page.is_visible("nav.bottom-nav")
            
            ui_checklist["responsive_layout"] = "PASS" if bottom_nav_visible else "FAIL (bottom navigation not visible on mobile)"
            
            await page.set_viewport_size({"width": 1280, "height": 800})
        except Exception as e:
            ui_checklist["responsive_layout"] = f"FAIL ({e})"

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

        errs_count = len(console_errors)
        ui_checklist["no_console_errors"] = "PASS" if errs_count == 0 else f"FAIL ({errs_count} errors logged: {console_errors[:2]})"

        print("[*] Generating report docs/ANTIGRAVITY_REPORT_v9.md...")
        
        total_cases = len(results)
        passed_cases = sum(1 for r in results if r["status"] == "PASS")
        serious_fails = total_cases - passed_cases
        success_status = "ĐẠT" if serious_fails == 0 else "CHƯA ĐẠT"

        import datetime
        vn_date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        report_md = f"""# Báo cáo kết quả Test UI cho Antigravity — Vòng 9

[Antigravity UI Test V9 - {vn_date}]

## 1. Môi trường kiểm thử
- **Trạng thái mô hình**: `{sbert_status}`
- **Thời gian khởi động hệ thống**: `{boot_duration:.1f} giây`
- **Tài khoản test**: Họ tên `Antigravity V9`, Email `anti.v9@test.com`, Mật khẩu `test123456`
- **LLM Context Enabled**: `0`

## 2. Bảng kết quả từng ca

| # | Mô tả bệnh | Output | Chặn đúng? | Lộ thuốc chống chỉ định? | False-positive? | Kết quả | Chi tiết / Lý do |
|---|---|---|---|---|---|---|---|
"""
        for r in results:
            report_md += f"| {r['id']} | {r['desc']} | `{r['got_title']}` | {r['chan_dung']} | {r['lo_thuoc']} | {r['false_positive']} | **{r['status']}** | {r['reason'] or 'Khớp kỳ vọng'} |\n"

        report_md += f"""
## 3. Tổng hợp thống kê

- **Tổng số ca test**: {passed_cases}/{total_cases} PASS
- **Số ca FAIL nghiêm trọng:** `{serious_fails}`

> [!IMPORTANT]
> **Kết luận chung:** **{success_status}**
> (Tiêu chí ĐẠT: A chặn hết chống chỉ định và không lộ thuốc; B cấp cứu/dị ứng chính xác; C cảnh báo an toàn thai kỳ/tuổi; D không chặn nhầm viêm gân và OTC hoạt động bình thường).

## 4. Nhận xét UI/UX & Responsive

| Tính năng / Checklist | Giao diện | Nhận xét chi tiết |
|---|---|---|
"""
        for k, v in ui_checklist.items():
            report_md += f"| `{k}` | **{v}** | Kiểm tra tự động bằng Playwright |\n"

        report_md += """
### Hình ảnh chụp màn hình kiểm thử:
- **Màn hình đăng nhập/đăng ký:** ![Login Screen](/screenshots/v9_01_login.png)
- **Màn hình chính (Home):** ![Home Screen](/screenshots/v9_02_home.png)
- **Responsive Tablet (768px):** ![Responsive 768px](/screenshots/v9_responsive_768.png)
- **Responsive Mobile (375px):** ![Responsive 375px](/screenshots/v9_responsive_375.png)

## 5. Đề xuất & Các ca cần tối ưu tiếp theo

"""
        failed_cases = [r for r in results if r["status"] == "FAIL"]
        if failed_cases:
            report_md += "Các ca bị sai cần hiệu chỉnh:\n"
            for fc in failed_cases:
                report_md += f"- Ca #{fc['id']}: `{fc['desc']}` -> Output: `{fc['got_title']}` | Lý do: {fc['reason']}\n"
        else:
            report_md += "Tất cả các ca kiểm thử hoạt động chính xác theo đúng tài liệu thiết kế của Vòng 9. Tầng ngữ cảnh - an toàn hoạt động tuyệt vời, nhận diện chính xác bệnh nền chống chỉ định (suy thận, loét dạ dày), tương tác thuốc chống đông, dị ứng thuốc và độ tuổi nhạy cảm để chặn hiển thị hoạt chất và cảnh báo đi khám rõ ràng. Không xảy ra hiện tượng chặn nhầm gân/gan.\n"

        with open("docs/ANTIGRAVITY_REPORT_v9.md", "w", encoding="utf-8") as f:
            f.write(report_md)
            
        print("[+] Generated docs/ANTIGRAVITY_REPORT_v9.md successfully!")
        
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
