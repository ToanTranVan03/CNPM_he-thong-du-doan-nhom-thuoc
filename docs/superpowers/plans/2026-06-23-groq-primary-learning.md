# Groq Primary and Learning Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bổ sung chế độ test trong đó Groq Compound là bộ phán đoán nhóm thuốc chính có thể tìm nguồn ngoài, vẫn chịu cổng an toàn nội bộ, đồng thời ghi mọi phán đoán vào hàng đợi dữ liệu học có kiểm duyệt.

**Architecture:** Tách kết nối/validate Groq và lưu ứng viên học thành hai module nhỏ, sau đó tích hợp một nhánh có feature flag vào đầu pipeline `/api/predict` sau cổng cấp cứu. Output Groq đi qua các rule chống chỉ định hiện có; mọi lỗi chuyển về pipeline nội bộ. Một CLI riêng kiểm duyệt và xuất duy nhất mẫu `approved` sang CSV tương thích `train_model.py`.

**Tech Stack:** Python 3, Flask, OpenAI-compatible Groq API, JSONL/CSV, JavaScript thuần, unittest.mock và test scripts hiện có.

---

## Cấu trúc file

- Create `backend/groq_primary.py`: cấu hình runtime, prompt, gọi Compound, parse và validate response.
- Create `backend/learning_candidates.py`: redact dữ liệu nhận dạng, tạo hash, append JSONL an toàn, đọc/cập nhật trạng thái và xuất CSV.
- Modify `backend/app.py`: gọi Groq sau cổng cấp cứu, áp dụng cổng chống chỉ định, fallback và ghi candidate.
- Create `scripts/test_groq_primary.py`: unit test client/schema không gọi mạng.
- Create `scripts/test_learning_candidates.py`: unit test redact/append/deduplicate/export.
- Create `scripts/test_groq_primary_integration.py`: integration test `/api/predict` bằng stub.
- Create `scripts/review_groq_candidates.py`: CLI list/approve/reject/export.
- Modify `frontend/index.html`: vùng hiển thị nguồn ngoài.
- Modify `frontend/script.js`: render nguồn bằng DOM API an toàn.
- Modify `frontend/styles.css`: style tối thiểu cho nguồn.
- Create `scripts/test_groq_frontend_contract.py`: kiểm tra contract DOM/JS tĩnh.
- Modify `.env.example` hoặc create nếu repository chưa có: mô tả biến cấu hình không chứa khóa thật.
- Modify `.gitignore`: bỏ qua file candidate runtime, giữ nguyên thay đổi `figma_assets/` của người dùng.
- Modify `README.md`: cách bật/tắt, duyệt, xuất và rollback chế độ test.

## Task 1: Client Groq Compound có schema chặt

**Files:**
- Create: `backend/groq_primary.py`
- Create: `scripts/test_groq_primary.py`

- [ ] **Step 1: Viết test thất bại cho feature flag và cấu hình**

Test các trường hợp: mặc định tắt; thiếu key/base/model trả `None`; `GROQ_PRIMARY_TEST_MODE=1` bật; timeout bị kẹp trong `1..60` giây. Mọi test dùng `patch.dict(os.environ, ..., clear=False)` và không đọc/in khóa thật.

- [ ] **Step 2: Chạy test để xác nhận thất bại**

Run: `python scripts/test_groq_primary.py`

Expected: FAIL vì chưa có module `groq_primary`.

- [ ] **Step 3: Cài đặt cấu hình runtime tối thiểu**

Public interface:

```python
def is_enabled() -> bool: ...
def classify(notes: str, selected_symptoms: list[str]) -> dict | None: ...
```

Không cache biến môi trường lúc import để test và việc bật/tắt rõ ràng.

- [ ] **Step 4: Viết test thất bại cho schema output**

Bao phủ:

- JSON hợp lệ có `symptoms_vi`, `negated_vi`, `drug_group`, `rationale`, `confidence`, `needs_clinician`, `sources`, `red_flags`.
- `confidence` ngoài `0..1`, group rỗng, URL không phải HTTP(S), enum cờ đỏ lạ, list quá dài và string quá dài đều bị từ chối.
- Markdown fence được gỡ trước khi parse.
- Field thừa bị bỏ qua.
- Prompt-injection trong notes chỉ được nhúng như JSON string.

- [ ] **Step 5: Cài đặt validator và prompt**

Giới hạn đề xuất:

```python
MAX_NOTES = 2000
MAX_GROUP = 160
MAX_RATIONALE = 800
MAX_SYMPTOMS = 30
MAX_SOURCES = 8
ALLOWED_RED_FLAGS = {...enum đang dùng trong llm_context.py...}
```

Prompt cấm chẩn đoán chắc chắn, tên thuốc/liều/phác đồ; yêu cầu ưu tiên nguồn y khoa chính thống và chỉ trả JSON.

- [ ] **Step 6: Viết test thất bại cho gọi API/fallback**

Mock OpenAI client cho HTTP thành công, timeout, exception, content hỏng và response không có choice. Xác nhận exception không thoát khỏi `classify`.

- [ ] **Step 7: Cài đặt gọi `groq/compound`**

Dùng `OpenAI(api_key=..., base_url=..., timeout=...)`. Không dùng `response_format` nếu Compound không hỗ trợ; parse content bằng bộ parser chắc tay. `temperature=0`, giới hạn output hợp lý. Không log prompt, notes, response thô hoặc khóa.

- [ ] **Step 8: Chạy unit test**

Run: `python scripts/test_groq_primary.py`

Expected: toàn bộ PASS, không có request mạng.

- [ ] **Step 9: Commit**

```powershell
git add backend/groq_primary.py scripts/test_groq_primary.py
git commit -m "feat(llm): add validated Groq primary client"
```

## Task 2: Hàng đợi JSONL và bảo vệ dữ liệu

**Files:**
- Create: `backend/learning_candidates.py`
- Create: `scripts/test_learning_candidates.py`

- [ ] **Step 1: Viết test thất bại cho redaction**

Kiểm tra email, số điện thoại Việt Nam, token dài và chuỗi giống API key bị thay bằng `[REDACTED]`; triệu chứng y tế không bị xóa. Không lưu user email/session token.

- [ ] **Step 2: Chạy test để xác nhận thất bại**

Run: `python scripts/test_learning_candidates.py`

Expected: FAIL vì module chưa tồn tại.

- [ ] **Step 3: Cài đặt schema và redaction**

Public interface:

```python
def build_candidate(*, notes, selected_symptoms, result, disposition, model, prompt_version) -> dict: ...
def append_candidate(candidate: dict, path: Path | None = None) -> bool: ...
def iter_candidates(path: Path | None = None) -> list[dict]: ...
def set_review_status(candidate_id: str, status: str, reviewer: str, note: str = "") -> bool: ...
def export_approved(output_csv: Path, path: Path | None = None) -> dict: ...
```

`input_hash` dùng SHA-256 trên notes đã chuẩn hóa + selected symptoms + proposed group. `review_status` mặc định `pending`.

- [ ] **Step 4: Viết test thất bại cho append đồng thời và JSONL hỏng**

Chạy nhiều thread append vào file tạm; tất cả dòng phải parse được. Dòng hỏng khi đọc phải bị bỏ qua có kiểm soát, không làm mất dòng hợp lệ.

- [ ] **Step 5: Cài đặt append an toàn**

Dùng lock trong tiến trình quanh một lần mở file `a`, một lần `write(json + "\n")` và flush. Không ghi lại toàn file trong đường request.

- [ ] **Step 6: Viết test thất bại cho review/export**

Kiểm tra chỉ `approved` + `safety_disposition == "allowed"` + có nguồn hợp lệ được xuất; `pending`, `rejected`, ca bị chặn và hash trùng không được xuất. CSV phải có `trieu_chung`, `nhom_thuoc`, `source`.

- [ ] **Step 7: Cài đặt review/export**

Khi cập nhật trạng thái, ghi file tạm cùng thư mục rồi `os.replace` để tránh file nửa chừng. Export luôn tạo file mới, không sửa tập train gốc.

- [ ] **Step 8: Chạy unit test**

Run: `python scripts/test_learning_candidates.py`

Expected: toàn bộ PASS.

- [ ] **Step 9: Commit**

```powershell
git add backend/learning_candidates.py scripts/test_learning_candidates.py
git commit -m "feat(data): add reviewed Groq learning queue"
```

## Task 3: Tích hợp Groq vào `/api/predict` và giữ cổng an toàn

**Files:**
- Modify: `backend/app.py:3778`
- Create: `scripts/test_groq_primary_integration.py`

- [ ] **Step 1: Viết integration test thất bại cho thứ tự pipeline**

Import app với `DB_DISABLED=1`. Patch `A.groq_primary.classify` và xác nhận:

- Chế độ tắt: Groq không được gọi, response cũ giữ nguyên.
- Ca cấp cứu: response `422/emergency`, Groq không được gọi.
- Ca thường: Groq được gọi đúng một lần trước model nội bộ.
- Groq `None`: pipeline nội bộ tiếp quản.

- [ ] **Step 2: Chạy test để xác nhận thất bại**

Run: `python scripts/test_groq_primary_integration.py`

Expected: FAIL vì app chưa có nhánh Groq primary.

- [ ] **Step 3: Thêm import fail-safe và helper response**

Trong `app.py`, import hai module trong `try/except`. Tạo helper nhỏ chuyển kết quả Groq đã validate sang contract API hiện có; không nhét toàn bộ logic vào route.

- [ ] **Step 4: Tích hợp sau cổng cấp cứu**

Luồng:

```text
validate input -> emergency gate -> Groq primary (nếu bật)
-> validate -> contraindication/high-risk gates
-> return Groq response hoặc 422
-> nếu Groq lỗi: pipeline hiện tại
```

Kết quả Groq thành công dùng `score_type="groq_primary"`, `input_used="groq_web"`, `top_predictions=[]`, `sources=[...]` và `confidence` đã validate.

- [ ] **Step 5: Viết test thất bại cho chống chỉ định và nhóm ngoài dữ liệu**

Stub Groq trả:

- NSAID + bệnh loét dạ dày: `422`, cảnh báo chống chỉ định.
- Nhóm giảm đau + bệnh gan: `422`.
- Nhóm ngoài `model.classes_`: response không crash, giữ nguyên tên nhóm.
- Nhóm kê đơn/rủi ro cao: yêu cầu bác sĩ, không hiển thị như OTC chắc chắn.
- Red flag do Groq: chỉ chặn khi có tín hiệu chứng thực theo helper hiện có.

- [ ] **Step 6: Áp dụng safety cho kết quả Groq**

Tái sử dụng `is_high_risk_group`, `is_never_suggest_group`, `context_safety.safety_overrides` và các helper cờ đỏ hiện có. Không tạo danh sách safety thứ hai trong module Groq.

- [ ] **Step 7: Viết test thất bại cho logging mọi disposition**

Patch `append_candidate`; xác nhận có candidate cho `allowed`, `blocked_contraindication` và `fallback`. Ca cấp cứu bị chặn trước khi Groq chạy không tạo “phán đoán Groq” giả.

- [ ] **Step 8: Cài đặt ghi candidate fail-open**

Lỗi ghi file không thay đổi HTTP response. Không lưu notes thô ngoài hàm redaction.

- [ ] **Step 9: Chạy integration và regression**

Run:

```powershell
python scripts/test_groq_primary_integration.py
$env:LLM_CONTEXT_ENABLED='0'; $env:DB_DISABLED='1'; python scripts/score_independent_probe.py
```

Expected: integration PASS; independent probe không có regression khi feature flag tắt.

- [ ] **Step 10: Commit**

```powershell
git add backend/app.py scripts/test_groq_primary_integration.py
git commit -m "feat(predict): route test predictions through Groq"
```

## Task 4: Hiển thị nguồn và contract frontend

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/script.js`
- Modify: `frontend/styles.css`
- Create: `scripts/test_groq_frontend_contract.py`

- [ ] **Step 1: Viết contract test thất bại**

Kiểm tra HTML có container `#external-sources`; JS chỉ tạo link bằng `document.createElement`, đặt `textContent`, chỉ nhận URL `http:`/`https:` và thêm `rel="noopener noreferrer"`.

- [ ] **Step 2: Chạy test để xác nhận thất bại**

Run: `python scripts/test_groq_frontend_contract.py`

Expected: FAIL vì container/render function chưa tồn tại.

- [ ] **Step 3: Thêm vùng nguồn vào trang kết quả**

Ẩn vùng khi `sources` rỗng. Khi có nguồn, hiển thị tên miền + tiêu đề; không render HTML do API trả về.

- [ ] **Step 4: Điều chỉnh nhãn kết quả**

Với `score_type="groq_primary"`, tiêu đề xác suất đổi thành “Phán đoán Groq có đối chiếu nguồn”; subtitle không tuyên bố “map sang đặc trưng tiếng Anh” nếu kết quả không dùng model nội bộ.

- [ ] **Step 5: Style tối thiểu và responsive**

Dùng token CSS hiện có; tránh tạo card mới không cần thiết. Link có focus state rõ ràng và wrap URL dài.

- [ ] **Step 6: Chạy contract test**

Run: `python scripts/test_groq_frontend_contract.py`

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add frontend/index.html frontend/script.js frontend/styles.css scripts/test_groq_frontend_contract.py
git commit -m "feat(ui): show sources for Groq predictions"
```

## Task 5: CLI duyệt và xuất mẫu học

**Files:**
- Create: `scripts/review_groq_candidates.py`
- Modify: `scripts/test_learning_candidates.py`

- [ ] **Step 1: Viết test CLI thất bại**

Test subprocess/file tạm cho các lệnh:

```text
list --status pending
approve <id> --reviewer <name> --note <text>
reject <id> --reviewer <name> --note <text>
export --output <csv>
```

ID không tồn tại và status không hợp lệ phải trả exit code khác 0.

- [ ] **Step 2: Cài đặt CLI bằng argparse**

CLI không in notes đầy đủ mặc định; list chỉ hiển thị ID, thời gian, nhóm đề xuất, confidence, disposition và preview đã cắt ngắn.

- [ ] **Step 3: Chạy test**

Run: `python scripts/test_learning_candidates.py`

Expected: PASS.

- [ ] **Step 4: Smoke test CLI trên file tạm**

Run: `python scripts/review_groq_candidates.py --help`

Expected: hiển thị bốn lệnh và không đọc file production.

- [ ] **Step 5: Commit**

```powershell
git add scripts/review_groq_candidates.py scripts/test_learning_candidates.py
git commit -m "feat(admin): add Groq candidate review CLI"
```

## Task 6: Cấu hình, tài liệu và kiểm thử trực tiếp

**Files:**
- Modify: `.gitignore`
- Create or Modify: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Bổ sung ignore an toàn**

Thêm `data/groq_learning_candidates.jsonl` và file tạm liên quan. `.gitignore` đang có thay đổi `figma_assets/` của người dùng: không được đưa hunk đó vào commit này. Stage riêng đúng pattern Groq bằng patch vào index (`git apply --cached`) hoặc xin người dùng cho phép gộp thay đổi trước khi stage cả file.

- [ ] **Step 2: Ghi cấu hình mẫu**

Không chép giá trị từ `.env`. Chỉ thêm tên biến và placeholder:

```dotenv
GROQ_PRIMARY_TEST_MODE=0
GROQ_PRIMARY_MODEL=groq/compound
GROQ_PRIMARY_TIMEOUT=30
GROQ_LEARNING_LOG_ENABLED=1
GROQ_LEARNING_LOG_PATH=data/groq_learning_candidates.jsonl
```

- [ ] **Step 3: Viết hướng dẫn bật/tắt và rollback**

README phải nêu đây là test mode, cách restart server, cách duyệt/export, và cách tắt duy nhất bằng `GROQ_PRIMARY_TEST_MODE=0` rồi restart.

- [ ] **Step 4: Chạy toàn bộ test không mạng**

Run:

```powershell
python scripts/test_groq_primary.py
python scripts/test_learning_candidates.py
python scripts/test_groq_primary_integration.py
python scripts/test_groq_frontend_contract.py
$env:LLM_CONTEXT_ENABLED='0'; $env:DB_DISABLED='1'; python scripts/score_independent_probe.py
```

Expected: tất cả PASS; không gọi Groq thật.

- [ ] **Step 5: Kiểm tra live Groq có giới hạn**

Bật test mode trong tiến trình riêng, không in env/key. Gửi bốn ca: thông thường trong dữ liệu, ngoài dữ liệu, cấp cứu và chống chỉ định. Xác nhận:

- Ca thường có `score_type=groq_primary` và nguồn hợp lệ.
- Ca ngoài dữ liệu không crash.
- Ca cấp cứu không gọi Groq và trả `422`.
- Ca chống chỉ định trả `422` dù Groq đã chọn nhóm.
- File JSONL có candidate `pending` đã redacted.

- [ ] **Step 6: Kiểm thử UI bằng browser**

Mở `http://127.0.0.1:5000`, gửi ca thường, xác nhận nguồn hiển thị, không lỗi console, layout không vỡ ở desktop. Chụp screenshot làm bằng chứng kiểm thử nếu người dùng yêu cầu.

- [ ] **Step 7: Xác minh working tree và secrets**

Run:

```powershell
git diff --check
git status --short
git diff -- .env
rg -n "gsk_|LLM_API_KEY=.*[^<]" --glob '!\.env' --glob '!docs/superpowers/**'
```

Expected: không có secret trong tracked files; `.env` không staged.

- [ ] **Step 8: Commit tài liệu/cấu hình**

Stage tài liệu bình thường và chỉ stage hunk Groq của `.gitignore`; xác nhận bằng `git diff --cached` trước khi commit:

```powershell
git add .env.example README.md
# Stage riêng pattern Groq trong .gitignore; không stage hunk figma_assets của người dùng.
git diff --cached -- .gitignore .env.example README.md
git commit -m "docs: document Groq test mode and rollback"
```

## Task 7: Xác minh hoàn tất

**Files:**
- No code changes expected.

- [ ] **Step 1: Chạy verification mới hoàn toàn**

Chạy lại toàn bộ lệnh Task 6 Step 4 sau mọi commit; không dùng kết quả cũ.

- [ ] **Step 2: Kiểm tra lịch sử và phạm vi commit**

Run:

```powershell
git log --oneline -10
git status --short
git diff HEAD~6..HEAD --stat
```

Expected: chỉ các file trong kế hoạch; không có `.env`, key hoặc dữ liệu candidate runtime trong commit.

- [ ] **Step 3: Bàn giao chế độ test**

Báo rõ test mode đang bật hay tắt, server PID/URL, số test pass, đường dẫn candidate log, lệnh duyệt/export và một lệnh rollback cấu hình. Không push/merge nếu người dùng chưa yêu cầu.
