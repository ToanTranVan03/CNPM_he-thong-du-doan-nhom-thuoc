# CODEX_FIX_PLAN_v4 - Lexicon ngu canh nguy hiem

> Vai tro Codex: lap plan, khong code. Agent implement phai sua tung buoc, chay verify, va khong them tang LLM cho task nay.

## Muc tieu

- Them lop lexicon notes-aware cho 3 nhom ngu canh nguy hiem: chan thuong dau, ruou + paracetamol/nhom giam dau ha sot, va gang suc/mat nuoc.
- Uu tien an toan: ca nghi chan thuong so nao phai dung o cong cap cuu `422`; ca ruou + nhom giam dau ha sot phai khong ke vo dieu kien; ca gang suc chi them canh bao/cham soc hoac hoi them khi rui ro thap.
- Khong lam regress cac ca dang PASS, dac biet `data/test_vi_cases_v3.csv` va stress test hien co.

## Hien trang can bam

- `backend/app.py:553-559`: `normalize(notes)` bo dau tieng Viet ve ascii, pattern phai viet ascii nhu `va dap`, `dau`, `chay bo`.
- `backend/app.py:1735-1798`: `emergency_red_flag_from_notes(notes)` chay truoc trich trieu chung va truoc model; day la noi dung cho ca cap cuu `422`.
- `backend/app.py:1784-1787`: rule chan thuong dau hien co qua hep, chi bat `nga cao`, `tai nan`, `chan thuong dau`, `chan thuong so nao`, `nga dap dau`, `ta nga` kem mot so dau hieu nang; chua bat `va dap vao dau`.
- `backend/app.py:1801-1853`: da co tien le rule notes-aware `malaria_rule_drug_group(notes, active_symptoms)` va `anemia_rule_drug_group(notes, active_symptoms)`.
- `backend/app.py:2559-2586`: `rule_group` override model va dat `score_type = "rule"`.
- `backend/app.py:2589-2674`: `quality_reasons` la noi tra `needs_more_input=True`/HTTP `422` ma khong ke nhom thuoc.
- `backend/app.py:2676-2727`: guidance sau khi da chap nhan goi y; day la noi chen warning/care dong cho truong hop khong can chan thuoc.
- `backend/app.py:212-223`: `DRUG_GROUP_GUIDANCE["thuoc giam dau ha sot"]` da nhac kiem tra benh gan/uong ruou nhieu, nhung chua co co che chan theo ngu canh notes.

## Hanh vi mong muon

- **Chan thuong dau + dau hieu than kinh/non nao**: tra HTTP `422` tu `emergency_red_flag_from_notes`; `top_predictions=[]`; khong ke bat ky thuoc nao.
- **Ruou manh + he thong sap tra `thuoc giam dau ha sot`**: tra HTTP `422` khong cap cuu, voi message chong chi dinh/can than doc gan; khong hien `Acetaminophen/Paracetamol` nhu goi y dung duoc.
- **Ruou nhe/khong ro muc do + `thuoc giam dau ha sot`**: khong bat buoc chan neu chi la ngu canh yeu, nhung phai them warning/precaution dong ve tranh paracetamol khi vua uong ruou/uong nhieu ruou/benh gan.
- **Gang suc/ra nang + dau dau/buon non**: khong dua vao cap cuu mac dinh; them care/precaution ve nghi, bu nuoc, theo doi mat nuoc/say nang, hoac hoi them ngu canh. Chi tra `422` neu logic san co da thay thieu du lieu hoac co dau hieu nang khac.

## Checklist trien khai

- [ ] **Buoc 1: chup baseline truoc khi sua**
  - Chay `python scripts/eval_vietnamese.py`.
  - Chay `python scripts/eval_vietnamese.py --cases data/test_vi_cases_v3.csv`.
  - Chay `python scripts/stress_test_user_cases.py`.
  - Ghi lai so fail hien tai va cac case lien quan `headache_dizzy`, `w32`, nhom ho/sot nhe, vi cac rule moi de anh huong cac cum nay.

- [ ] **Buoc 2: mo rong cong cap cuu chan thuong dau**
  - File: `backend/app.py`.
  - Vi tri: trong `emergency_red_flag_from_notes(notes)` quanh `backend/app.py:1784-1787`.
  - Cach lam: tach dieu kien thanh 2 nhom ro rang:
    - `head_impact_context`: co mot pattern tac dong vao dau.
    - `post_head_injury_sign`: co dau dau, buon non/non, chong mat, lo mo/bat tinh/roi loan ngon ngu/co giat/yeu liet/mat thang bang.
  - Tra ve message kieu: `Nghi chan thuong dau/chan thuong so nao sau va dap kem dau dau, buon non/non hoac dau hieu than kinh.` + `GO`.
  - Giu rule cu `nga cao`, `tai nan`, `chan thuong so nao` de khong regress.

- [ ] **Buoc 3: them helper notes-aware cho ruou**
  - File: `backend/app.py`.
  - Vi tri de xuat: sau `anemia_rule_drug_group(notes, active_symptoms)` quanh `backend/app.py:1831-1853`, cung cum rule notes-aware.
  - Them helper de xuat:
    - `has_strong_alcohol_context(notes: str) -> bool`: bat ngu canh ruou ro/manh.
    - `has_weak_alcohol_context(notes: str) -> bool`: bat ngu canh ruou yeu de chen warning, khong tu dong chan.
    - `is_negated_context(t: str, pattern: str, negators=("khong", "chua", "khong co")) -> bool`: neu can, dung cua so ngan truoc pattern de tranh `khong uong ruou`.
  - Khong dua helper nay vao `rule_group`, vi ruou khong phai nhom thuoc moi; no la dieu kien an toan can danh gia sau khi biet prediction.

- [ ] **Buoc 4: chan ruou + `thuoc giam dau ha sot` bang quality_reasons**
  - File: `backend/app.py`.
  - Vi tri: sau khi `rule_group` da override prediction (`backend/app.py:2582-2586`) va truoc `needs_more_input = bool(quality_reasons)` (`backend/app.py:2644`).
  - Dieu kien kich hoat:
    - `LABEL_TYPE == "drug_group"`.
    - `prediction == "thuoc giam dau ha sot"` sau khi normalize/so sanh voi chuoi goc dung encoding trong code.
    - `has_strong_alcohol_context(notes)` la `True`.
  - Hanh vi: append `quality_reasons` voi noi dung ro: vua/uong nhieu ruou hoac lam dung ruou lam tang nguy co doc gan, dac biet voi paracetamol/acetaminophen; chua du du lieu de goi y nhom giam dau ha sot an toan; can hoi duoc si/bac si va tranh tu dung.
  - Ket qua: response di vao nhanh `422` tai `backend/app.py:2649-2674`, `medication_name` trong `case_summary` phai la `Chua du du lieu de goi y thuoc`.

- [ ] **Buoc 5: them warning dong cho ruou yeu neu van goi y nhom**
  - File: `backend/app.py`.
  - Vi tri: sau khi tao `guidance = drug_group_guidance(prediction, active_symptoms)` quanh `backend/app.py:2676-2678`, hoac sau khi build `precaution_guidance` quanh `backend/app.py:2688-2692`.
  - Dieu kien: `prediction == "thuoc giam dau ha sot"` va `has_weak_alcohol_context(notes)` nhung khong phai strong block.
  - Hanh vi: prepend/extend `precaution_guidance` va/hoac override `warning` dong bang cau canh bao: khong tu dung paracetamol/acetaminophen neu vua uong ruou, uong ruou nhieu, benh gan, hoac khong ro hoat chat; hoi duoc si/bac si.
  - Giu `DRUG_GROUP_GUIDANCE` static co the them `warning` cho nhom nay, nhung can co warning dong theo notes de test duoc ca co ruou.

- [ ] **Buoc 6: them helper notes-aware cho gang suc/ra nang**
  - File: `backend/app.py`.
  - Vi tri de xuat: cung cum helper notes-aware quanh `backend/app.py:1801-1853`.
  - Them helper de xuat:
    - `has_exertion_heat_context(notes: str) -> bool`.
    - `has_headache_nausea_or_dizzy(active_symptoms: set[str], notes: str) -> bool`.
  - Khong dua vao `emergency_red_flag_from_notes` mac dinh. Chi canh bao/cham soc tru khi co dau hieu nang da duoc rule cap cuu khac bat.

- [ ] **Buoc 7: chen guidance dong cho gang suc**
  - File: `backend/app.py`.
  - Vi tri: sau khi build `treatment_guidance`, `precaution_guidance`, `care_guidance` quanh `backend/app.py:2685-2692`.
  - Dieu kien: `has_exertion_heat_context(notes)` va co `headache/nausea/vomiting/dizziness` trong `active_symptoms` hoac notes.
  - Hanh vi:
    - Them `care_guidance`: nghi noi mat, uong tung ngum nuoc/ores neu ra mo hoi nhieu, theo doi tieu it/khat nhieu/chong mat.
    - Them `precaution_guidance`: di kham/cap cuu neu lo mo, ngat, sot cao, co giat, non lien tuc, dau dau du doi, dau nguc/kho tho.
    - Khong ep `prediction` sang nhom moi va khong chan `thuoc giam dau ha sot` neu khong co rui ro cao.

- [ ] **Buoc 8: cap nhat prompt hoi them neu response 422**
  - File: `backend/app.py`.
  - Vi tri: `suggested_symptoms_for_more_info(active_symptoms)` quanh `backend/app.py:2078-2141` va `more_info_prompt(active_symptoms)` quanh `backend/app.py:2168-2195`.
  - Voi headache/nausea/dizziness, them cau hoi ve:
    - Co chan thuong dau/va dap dau/nga dap dau khong.
    - Co vua uong ruou/uong ruou nhieu/benh gan/thuoc dang dung khong.
    - Co sau chay bo/gang suc/tap nang/ra nang, khat nhieu/tieu it/ra mo hoi nhieu khong.
  - Khong de prompt nay thay the emergency gate; no chi phuc vu ca chua du du lieu.

- [ ] **Buoc 9: them regression coverage bang Flask client hoac CSV**
  - File uu tien: neu co test backend rieng thi them test Flask client cho `/api/predict`; neu khong, them case vao `data/test_vi_cases_v3.csv` chi khi quy uoc expected cua CSV du de dien dat.
  - Luu y: `scripts/eval_vietnamese.py` chi doc `disease_vi` hoac `NEEDS_MORE_INFO`, khong check warning text; cac ca can kiem warning dong nen dung Flask client/assert JSON rieng hoac test script rieng.
  - Khong sua model, metadata, hay them LLM.

- [ ] **Buoc 10: verify day du**
  - Chay `python scripts/eval_vietnamese.py`.
  - Chay `python scripts/eval_vietnamese.py --cases data/test_vi_cases_v3.csv`.
  - Chay `python scripts/stress_test_user_cases.py`.
  - Dieu kien dat:
    - Khong tang fail tren eval chinh va v3.
    - Stress test khong xuat hien issue moi lien quan `unsafe_antibiotic_for_mild_respiratory`, `should_request_more_info`, hoac crash/status la.
    - 3 case bang chung trong task duoc xu ly dung theo bang test mau ben duoi.

## Pattern ascii va dieu kien ket hop

### 1. Chan thuong dau -> `422` cap cuu

- Pattern tac dong vao dau:
  - `va dap vao dau`
  - `bi va dap vao dau`
  - `sau khi va dap vao dau`
  - `dap dau`
  - `nga dap dau`
  - `te dap dau`
  - `dau va vao`
  - `dau bi va`
  - `va dau`
  - `nga va dau`
  - `danh vao dau`
  - `bi danh vao dau`
  - `chan thuong dau`
  - `chan thuong so nao`
- Pattern/dau hieu ket hop:
  - Text: `dau dau`, `nhuc dau`, `buon non`, `non`, `non oi`, `oi`, `chong mat`, `choang`, `lo mo`, `bat tinh`, `ngat`, `lan lon`, `noi kho`, `yeu liet`, `co giat`, `mat thang bang`, `di khong vung`.
  - Hoac `active_symptoms`: `headache`, `frontal headache`, `nausea`, `vomiting`, `dizziness`, `altered sensorium`, `coma`, `slurred speech`, `weakness of one body side`, `loss of balance`, `seizures`.
- Dieu kien: `head_impact_context AND post_head_injury_sign`.
- Giam false-positive:
  - Khong dung pattern don `va`, `dau`, `dau vao`, vi bat nham rat rong.
  - Khong trigger khi chi co chan thuong khong vao dau: `va tay`, `dau chan`, `te xe tray dau goi`.
  - Tranh dua vao cau phu dinh co cum `khong dau dau` vi emergency gate hien chay truoc filter negation; neu them negation, phai test rieng.

### 2. Ruou + `thuoc giam dau ha sot` -> chan hoac warning

- Strong alcohol patterns -> chan `422` neu final prediction la `thuoc giam dau ha sot`:
  - `sau khi uong ruou`
  - `sau khi uong ruou nhieu`
  - `uong ruou nhieu`
  - `uong nhieu ruou`
  - `vua uong ruou`
  - `vua nhau`
  - `sau khi nhau`
  - `nhau nhieu`
  - `say ruou`
  - `qua chen`
  - `lam dung ruou`
  - `nghien ruou`
  - `ruou bia nhieu`
  - `uong bia ruou nhieu`
- Weak alcohol patterns -> them warning dong neu van goi y nhom:
  - `co uong ruou`
  - `uong bia`
  - `ruou bia`
  - `moi uong bia`
- Dieu kien chan: `strong_alcohol_context AND prediction == "thuoc giam dau ha sot"`.
- Dieu kien warning: `weak_alcohol_context AND prediction == "thuoc giam dau ha sot" AND NOT strong`.
- Giam false-positive:
  - Guard phu dinh: khong trigger voi `khong uong ruou`, `khong dung ruou bia`, `chua uong ruou`, `khong nhau`.
  - Khong trigger neu prediction la nhom khac nhu `bu dich va dien giai` hoac `thuoc chong non`, tru khi sau nay co rule rieng.
  - Khong chan toan bo `thuoc giam dau ha sot` chi vi notes co tu `bia` don le; can pattern co hanh dong/uong/nhieu/say.

### 3. Gang suc/ra nang -> guidance/warning, khong cap cuu mac dinh

- Pattern ngu canh:
  - `sau khi chay bo`
  - `chay bo xong`
  - `sau khi tap nang`
  - `tap nang xong`
  - `sau khi gang suc`
  - `gang suc qua`
  - `van dong manh`
  - `sau khi van dong`
  - `ra nang`
  - `phoi nang`
  - `duoi nang`
  - `troi nang`
  - `nang nong`
  - `lam viec ngoai troi`
- Dau hieu ket hop:
  - Text: `dau dau`, `buon non`, `non`, `chong mat`, `choang`, `khat`, `khat nhieu`, `tieu it`, `ra mo hoi nhieu`, `met la`.
  - Hoac `active_symptoms`: `headache`, `frontal headache`, `nausea`, `vomiting`, `dizziness`, `dehydration`, `fatigue`.
- Dieu kien: `exertion_heat_context AND headache_nausea_or_dizzy`.
- Giam false-positive:
  - Khong trigger voi `tap trung`, `tap tho`, `tap hat` vi chi dung pattern `tap nang`, `gang suc`, `van dong`, `chay bo`.
  - Khong ep sang `bu dich va dien giai` neu khong co `dehydration`, tieu it/khat nhieu/ra mo hoi nhieu.
  - Neu co `lo mo`, `ngat`, `sot cao`, `co giat`, `non lien tuc`, chi them warning di cap cuu hoac de rule cap cuu rieng xu ly; khong gop vao rule gang suc thap.

## Ca test mau

### Ca phai kich hoat

- `Tôi bị đau đầu, buồn nôn sau khi va đập vào đầu`
  - Expected: HTTP `422`, `score_type="emergency"`, `top_predictions=[]`, error co y `chan thuong dau/so nao`, khong co goi y `thuoc giam dau ha sot`.
- `Tôi nôn ói và chóng mặt sau khi ngã đập đầu`
  - Expected: HTTP `422`, cong cap cuu.
- `Tôi bị đau đầu, buồn nôn sau khi uống rượu nhiều`
  - Expected: HTTP `422`, `needs_more_input=True`, khong phai `score_type="emergency"` neu chi la canh bao thuoc; error nhac doc gan/paracetamol/ruou.
- `Tôi bị đau đầu, buồn nôn sau khi chạy bộ`
  - Expected: khong cap cuu; response `200` neu he thong du du lieu, va `precautions`/`diets` co y nghi, bu nuoc, theo doi mat nuoc. Chap nhan `422` neu logic thieu du lieu san co kich hoat, nhung khong duoc tra canh bao chan thuong dau hay ruou.

### Ca khong duoc kich hoat de chung minh khong false-positive

- `Tôi bị đau đầu, buồn nôn, không có va đập vào đầu`
  - Expected: khong vao emergency chan thuong dau. Neu negation chua duoc ho tro trong emergency gate, can them guard truoc khi dua vao test chinh.
- `Tôi bị đau đầu sau khi làm việc căng thẳng, không buồn nôn`
  - Expected: khong vao emergency chan thuong dau.
- `Tôi va tay vào cạnh bàn, sau đó hơi đau đầu vì mất ngủ`
  - Expected: khong vao emergency chan thuong dau vi khong co tac dong vao dau.
- `Tôi đau đầu, buồn nôn sau bữa tiệc nhưng không uống rượu`
  - Expected: khong kich hoat alcohol block.
- `Tôi uống một ít bia hôm qua, hôm nay đau đầu nhẹ`
  - Expected: khong strong block; neu prediction la `thuoc giam dau ha sot` thi chi warning dong.
- `Tôi đau đầu khi ngồi làm việc lâu trước máy tính`
  - Expected: khong kich hoat gang suc/ra nang.
- `Tôi tập thở, hơi đau đầu nhẹ`
  - Expected: khong kich hoat gang suc vi khong phai `tap nang/gang suc/chay bo/ra nang`.

## Lenh verify goi y cho implementer

Chay eval bat buoc:

```bash
python scripts/eval_vietnamese.py
python scripts/eval_vietnamese.py --cases data/test_vi_cases_v3.csv
python scripts/stress_test_user_cases.py
```

Chay smoke test truc tiep qua Flask client sau khi sua:

```bash
python - <<'PY'
import sys
sys.path.insert(0, "backend")
import app as A

client = A.app.test_client()
cases = [
    "Tôi bị đau đầu, buồn nôn sau khi va đập vào đầu",
    "Tôi bị đau đầu, buồn nôn sau khi uống rượu nhiều",
    "Tôi bị đau đầu, buồn nôn sau khi chạy bộ",
    "Tôi đau đầu, buồn nôn sau bữa tiệc nhưng không uống rượu",
]
for text in cases:
    r = client.post("/api/predict", json={"notes": text, "symptoms": []})
    data = r.get_json() or {}
    print("STATUS", r.status_code, "|", text)
    print("display_title=", data.get("display_title"))
    print("score_type=", data.get("score_type"), "needs_more=", data.get("needs_more_input"))
    print("disease_vi=", data.get("disease_vi"))
    print("warning=", data.get("warning") or data.get("error"))
    print()
PY
```

Tieu chi pass smoke:

- Ca `va đập vào đầu`: `422` emergency, khong co `disease_vi`.
- Ca `uống rượu nhiều`: `422` non-emergency/quality block, khong goi y paracetamol.
- Ca `chạy bộ`: khong emergency; co noi dung nghi/bu nuoc/theo doi trong guidance neu response `200`.
- Ca `không uống rượu`: khong bi alcohol block.

## Rui ro va cach giam

- False-positive chan thuong dau: giam bang `head_impact_context AND post_head_injury_sign`, khong dung pattern don `va`/`dau`.
- False-positive ruou: giam bang pattern co hanh dong va negation guard; strong block chi ap dung khi final prediction la `thuoc giam dau ha sot`.
- False-positive gang suc: chi chen guidance, khong override prediction va khong cap cuu mac dinh.
- Regression do rule order: khong dua alcohol/exertion vao `rule_group`; chi head trauma vao emergency gate. Rule group hien co `malaria_rule_drug_group` va `anemia_rule_drug_group` giu nguyen thu tu uu tien.
- Encoding/pattern: tat ca pattern trong code dung ascii sau `normalize()`, nhung message UI van giu tieng Viet co dau.
