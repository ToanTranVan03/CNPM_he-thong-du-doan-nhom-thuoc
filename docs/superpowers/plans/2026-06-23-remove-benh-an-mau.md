# Remove Sample Medical Records Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the `benh_an_mau` table and every backend, frontend, seed, documentation, and test surface that supports sample medical records while preserving manual medical-description entry and prediction history.

**Architecture:** Remove the feature vertically from PostgreSQL, SQLAlchemy, Flask, and the static frontend. Use a focused, idempotent migration script for the existing PostgreSQL table, and add narrow regression checks proving the table and routes stay absent. Keep the unrelated static “Dùng thử ví dụ” onboarding action.

**Tech Stack:** Python 3, Flask, Flask-SQLAlchemy/SQLAlchemy, PostgreSQL, vanilla JavaScript, HTML, CSS, PowerShell test commands.

**Design spec:** `docs/superpowers/specs/2026-06-23-remove-benh-an-mau-design.md`

---

## File map

- Modify `backend/models.py`: remove `BenhAnMau` and its expected-table entry.
- Modify `backend/app.py`: remove the three sample-record routes.
- Create `scripts/remove_benh_an_mau.py`: idempotently drop the legacy table from the configured database.
- Create `scripts/test_remove_benh_an_mau.py`: verify the migration helper on an isolated SQLite database, including a second no-op run.
- Modify `scripts/test_db_models.py`: assert `db.create_all()` does not recreate `benh_an_mau`.
- Modify `frontend/index.html`: remove the picker, admin navigation item, and admin page.
- Modify `frontend/script.js`: remove sample feature state, API calls, page routing, and event handlers.
- Modify `frontend/styles.css`: remove sample-only styles.
- Modify `README.md`: remove the obsolete seed command.
- Delete `scripts/seed_benh_an_mau.py`: obsolete seed utility.
- Delete `scripts/test_benh_an_mau.py`: obsolete feature test.
- Delete `run_ui_tests_us29.py`: obsolete feature UI test.

### Task 1: Prevent SQLAlchemy from recreating the table

**Files:**
- Modify: `scripts/test_db_models.py:82-87`
- Modify: `backend/models.py:294-321`

- [ ] **Step 1: Add a failing schema regression check**

Immediately after the existing expected-table check in `scripts/test_db_models.py`, add:

```python
check("không tạo lại bảng benh_an_mau", "benh_an_mau" not in tables)
```

- [ ] **Step 2: Run the schema test and verify the new check fails**

Run:

```powershell
python scripts/test_db_models.py
```

Expected: the new `không tạo lại bảng benh_an_mau` check reports `FAIL` because `BenhAnMau` is still registered in SQLAlchemy metadata.

- [ ] **Step 3: Remove the model and expected-table entry**

Delete the complete `BenhAnMau` class from `backend/models.py` and remove only this string from `EXPECTED_TABLES`:

```python
"benh_an_mau",
```

Do not alter `MoTaBenhAn` or any of its relationships.

- [ ] **Step 4: Run the schema test and verify it passes**

Run:

```powershell
python scripts/test_db_models.py
```

Expected: exit code `0`; all checks pass, including `không tạo lại bảng benh_an_mau`.

- [ ] **Step 5: Commit the schema/model change**

```powershell
git add -- backend/models.py scripts/test_db_models.py
git commit -m "refactor(db): remove sample medical record model"
```

### Task 2: Add and test the destructive database migration

**Files:**
- Create: `scripts/remove_benh_an_mau.py`
- Create: `scripts/test_remove_benh_an_mau.py`

- [ ] **Step 1: Write the failing migration test**

Create `scripts/test_remove_benh_an_mau.py`:

```python
"""Regression test for the idempotent benh_an_mau removal migration."""

import sys
from pathlib import Path

import sqlalchemy as sa

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from remove_benh_an_mau import drop_benh_an_mau  # noqa: E402


def main():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(sa.text(
            "CREATE TABLE benh_an_mau (ma_benh_an_mau INTEGER PRIMARY KEY, tieu_de VARCHAR(255))"
        ))
        connection.execute(sa.text(
            "INSERT INTO benh_an_mau (ma_benh_an_mau, tieu_de) VALUES (1, 'seed')"
        ))

    existed, removed_rows = drop_benh_an_mau(engine)
    assert existed is True
    assert removed_rows == 1
    assert not sa.inspect(engine).has_table("benh_an_mau")

    existed_again, removed_rows_again = drop_benh_an_mau(engine)
    assert existed_again is False
    assert removed_rows_again == 0
    print("PASS: migration xóa bảng và chạy lặp lại an toàn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the test and verify it fails because the migration module is absent**

Run:

```powershell
python scripts/test_remove_benh_an_mau.py
```

Expected: non-zero exit with `ModuleNotFoundError: No module named 'remove_benh_an_mau'`.

- [ ] **Step 3: Implement the idempotent migration**

Create `scripts/remove_benh_an_mau.py`:

```python
"""Drop the obsolete benh_an_mau table from DATABASE_URL.

Safe to run repeatedly. This migration intentionally deletes the five seed rows
because the product feature has been removed.
"""

import sys
from pathlib import Path

import sqlalchemy as sa

ROOT = Path(__file__).resolve().parent.parent


def load_env_url():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL") and "=" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def drop_benh_an_mau(engine):
    with engine.begin() as connection:
        if not sa.inspect(connection).has_table("benh_an_mau"):
            return False, 0
        removed_rows = connection.execute(
            sa.text("SELECT count(*) FROM benh_an_mau")
        ).scalar_one()
        connection.execute(sa.text("DROP TABLE IF EXISTS benh_an_mau"))
    return True, removed_rows


def main():
    url = load_env_url()
    if not url:
        print("Không tìm thấy DATABASE_URL trong .env")
        return 1
    try:
        engine = sa.create_engine(url)
        existed, removed_rows = drop_benh_an_mau(engine)
    except Exception as exc:
        print(f"Không thể xóa bảng benh_an_mau: {type(exc).__name__}")
        return 1
    if existed:
        print(f"Đã xóa bảng benh_an_mau ({removed_rows} dòng).")
    else:
        print("Bảng benh_an_mau không tồn tại; không cần thay đổi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the isolated migration test twice**

Run:

```powershell
python scripts/test_remove_benh_an_mau.py
python scripts/test_remove_benh_an_mau.py
```

Expected: both invocations exit `0` and print `PASS: migration xóa bảng và chạy lặp lại an toàn`.

- [ ] **Step 5: Commit the migration and its test**

```powershell
git add -- scripts/remove_benh_an_mau.py scripts/test_remove_benh_an_mau.py
git commit -m "chore(db): add sample record removal migration"
```

Do not run the migration against PostgreSQL until Task 6, after the application code no longer references the table.

### Task 3: Remove the Flask API surface

**Files:**
- Modify: `backend/app.py:3607-3655`

- [ ] **Step 1: Run a route-absence assertion and verify it fails**

Run:

```powershell
@'
import sys
sys.path.insert(0, "backend")
import app
rules = {rule.rule for rule in app.app.url_map.iter_rules()}
obsolete = {rule for rule in rules if "benh-an-mau" in rule}
assert not obsolete, f"obsolete routes remain: {sorted(obsolete)}"
'@ | python -
```

Expected: `AssertionError` listing the three current routes.

- [ ] **Step 2: Delete the complete US29 Flask route block**

Remove the three decorated functions:

```text
list_benh_an_mau
create_benh_an_mau
delete_benh_an_mau
```

Do not change `_require_admin_db()` because other admin endpoints use it.

- [ ] **Step 3: Re-run the route-absence assertion**

Run the command from Step 1 again.

Expected: exit code `0` with no output.

- [ ] **Step 4: Compile the backend**

Run:

```powershell
python -m py_compile backend/app.py backend/models.py
```

Expected: exit code `0` with no output.

- [ ] **Step 5: Commit the backend removal**

```powershell
git add -- backend/app.py
git commit -m "refactor(api): remove sample medical record endpoints"
```

### Task 4: Remove the frontend feature while preserving manual entry

**Files:**
- Modify: `frontend/index.html:164-170,274-282,610-640`
- Modify: `frontend/script.js:138-143,199-223,1372-1507`
- Modify: `frontend/styles.css:1642-1684`

- [ ] **Step 1: Record the currently present feature selectors**

Run:

```powershell
rg -n 'sample-picker|sample-select|page-samples|sample-form|samples-list|loadSamplePicker|loadSamples|deleteSample' frontend
```

Expected: matches in all three frontend files, proving the removal assertion would currently fail.

- [ ] **Step 2: Remove sample markup from `frontend/index.html`**

Delete:

- the admin navigation button with `data-page="samples"`;
- the `#sample-picker` block from the home-page tip card;
- the complete `#page-samples` section.

Keep `#case-description`, `#clear-case`, `#example-case`, and the tip-card writing guidance.

- [ ] **Step 3: Remove sample JavaScript from `frontend/script.js`**

Delete:

- `loadSamplePicker()` from the authentication/app initialization path;
- `"samples"` from `ADMIN_PAGES`;
- the `showPage()` branch that calls `loadSamples()`;
- all declarations and functions from the US29 block, including `sampleCache`, `fetchSamples`, `loadSamplePicker`, `renderSamplesAdmin`, `loadSamples`, `deleteSample`, and the form/select event listeners.

Keep the unrelated `sampleCase` constant and `exampleButton` handler; they implement the approved static onboarding example.

- [ ] **Step 4: Remove sample-only CSS from `frontend/styles.css`**

Delete `.sample-picker` and `.sample-form` rules. If a grouped selector includes both sample-only selectors and a reusable selector, remove only the sample selectors and retain any reusable declaration.

- [ ] **Step 5: Assert that the removed selectors are gone**

Run:

```powershell
$matches = rg -n 'sample-picker|sample-select|page-samples|sample-form|samples-list|loadSamplePicker|loadSamples|deleteSample' frontend
if ($LASTEXITCODE -eq 0) { $matches; exit 1 }
exit 0
```

Expected: exit code `0` and no matches.

- [ ] **Step 6: Perform JavaScript and HTML sanity checks**

Run:

```powershell
node --check frontend/script.js
rg -n 'id="case-description"|id="example-case"' frontend/index.html
```

Expected: JavaScript check exits `0`; HTML search returns both retained manual-entry controls.

- [ ] **Step 7: Commit the frontend removal**

```powershell
git add -- frontend/index.html frontend/script.js frontend/styles.css
git commit -m "refactor(ui): remove sample medical record screens"
```

### Task 5: Delete obsolete utilities and documentation

**Files:**
- Delete: `scripts/seed_benh_an_mau.py`
- Delete: `scripts/test_benh_an_mau.py`
- Delete: `run_ui_tests_us29.py`
- Modify: `README.md:68-76`

- [ ] **Step 1: Delete the three feature-only files**

Delete only the files listed above. Do not delete general database, prediction, or UI tests.

- [ ] **Step 2: Remove the seed command from README**

Delete this line:

```text
python scripts/seed_benh_an_mau.py # nạp bệnh án mẫu
```

- [ ] **Step 3: Search for stale runtime references**

Run:

```powershell
rg -n -i 'BenhAnMau|api/benh-an-mau|api/admin/benh-an-mau|seed_benh_an_mau|page-samples|sample-picker' backend frontend scripts README.md run_ui_tests*.py
```

Expected: no matches. References in the approved spec, implementation plan, and removal migration are allowed and are outside this runtime search.

- [ ] **Step 4: Commit the cleanup**

```powershell
git add -- README.md scripts/seed_benh_an_mau.py scripts/test_benh_an_mau.py run_ui_tests_us29.py
git commit -m "chore: remove obsolete sample record assets"
```

### Task 6: Verify regressions and migrate the configured PostgreSQL database

**Files:**
- No source changes expected.

- [ ] **Step 1: Run focused automated checks**

Run:

```powershell
python scripts/test_remove_benh_an_mau.py
python scripts/test_db_models.py
python scripts/test_db_integration.py
python scripts/test_history_feedback_db.py
python -m py_compile backend/app.py backend/models.py scripts/remove_benh_an_mau.py
node --check frontend/script.js
```

Expected: every command exits `0`; script summaries report zero failures.

- [ ] **Step 2: Capture unaffected PostgreSQL row counts**

Before the destructive migration, query and note counts for:

```sql
SELECT count(*) FROM mo_ta_benh_an;
SELECT count(*) FROM ket_qua_du_doan;
SELECT count(*) FROM lich_su_du_doan;
```

Do not print or expose `DATABASE_URL`.

- [ ] **Step 3: Run the migration against the configured PostgreSQL database**

Run:

```powershell
python scripts/remove_benh_an_mau.py
python scripts/remove_benh_an_mau.py
```

Expected: first invocation reports deletion of the table and its 5 seed rows; second invocation reports that the table does not exist and exits `0`.

- [ ] **Step 4: Verify database integrity after migration**

Check through SQLAlchemy metadata queries:

- `benh_an_mau` is absent;
- `mo_ta_benh_an`, `ket_qua_du_doan`, and `lich_su_du_doan` counts equal the values captured in Step 2.

Expected: all assertions pass.

- [ ] **Step 5: Run the application and verify the manual-entry UI**

Start the Flask application on an available local port. Use `browser:control-in-app-browser` to verify:

- login and open Trang chủ;
- no **Nạp bệnh án mẫu** control is visible;
- no **Bệnh án mẫu** admin navigation item is visible;
- type a description manually and submit it;
- use **Dùng thử ví dụ** and confirm it still fills the text area;
- confirm a prediction result renders without browser console errors.

- [ ] **Step 6: Perform final repository checks**

Run:

```powershell
git diff --check
git status --short
rg -n -i 'BenhAnMau|api/benh-an-mau|api/admin/benh-an-mau|seed_benh_an_mau|page-samples|sample-picker' backend frontend scripts README.md run_ui_tests*.py
```

Expected: no whitespace errors; no stale runtime references; only known unrelated user files remain untracked or modified.

- [ ] **Step 7: Commit any verification-only adjustment if required**

If verification required a source correction, stage only those scoped files and commit:

```powershell
git commit -m "test: verify manual medical record entry flow"
```

If no files changed, do not create an empty commit.
