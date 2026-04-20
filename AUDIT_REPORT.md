# TVS TCMS – Comprehensive Application Audit

**Audit date:** 20 April 2026
**Auditor:** Cascade (automated static + artifact review)
**Scope:** `/Users/danielhanson/CascadeProjects/Wages-App` @ HEAD (dev mirror of `/opt/tvstcms`)
**Method:** Static analysis only — no code changes, no DB writes. Findings verified by grep / file reads / log inspection.

---

## 0. Executive Summary

The app is functional and being used in anger for daily runs, wages, expenses and HMRC MTD sandbox submissions. The architecture (blueprint routes → service layer → SQLite) is reasonable and the recent unified-styling/mobile work has paid off. The most urgent issues are:

1. **CSRF bug breaks "Add Selected Jobs"** in the payslip→runsheet missing-jobs modal (400 Bad Request — root cause confirmed: `static/js/missing-jobs.js` does not send `X-CSRFToken`).
2. **Dead legacy code** (`new_web_app.py`, 2611 LOC) still sitting at repo root pointing at an old DB path — confusing and a landmine for anyone running it by accident.
3. **Runsheet import failures** are the dominant error type in the logs (hundreds of "Failed to import … Unknown error" entries since the Camelot change-over; many multi-driver PDFs silently extract 0 jobs).
4. **Inline-style cleanup is ~30 % done** — 98 matches across 12 templates still violate the "no inline styles" rule.
5. **No automated test suite** — zero unit/integration coverage for any critical path (HMRC submission, expense CRUD, runsheet import, payslip parsing, auto-sync).
6. **Credentials/tokens at repo root** are gitignored, but `credentials.json` and `token.json` live alongside the code; a single accidental `git add -f` would leak them. Recommend moving to `secrets/` outside the app directory (or `~/.tvstcms/`).

MTD Q1 (due 5 August 2026) is achievable, but production credentials still need HMRC sign-off and at least the submission flow wants a smoke-test harness before live use.

---

## 1. Code Quality

### 1.1 Inline styles (violates the no-inline-styles rule)

98 `style="…"` attributes across 12 templates. Priority files:

| File | Matches |
|---|---|
| `@/Users/danielhanson/CascadeProjects/Wages-App/templates/expenses.html` | 21 |
| `@/Users/danielhanson/CascadeProjects/Wages-App/templates/reports.html` | 15 |
| `@/Users/danielhanson/CascadeProjects/Wages-App/templates/runsheets.html` | 15 |
| `@/Users/danielhanson/CascadeProjects/Wages-App/templates/settings/system.html` | 14 |
| `@/Users/danielhanson/CascadeProjects/Wages-App/templates/settings/sync.html` | 11 |
| `@/Users/danielhanson/CascadeProjects/Wages-App/templates/runsheet_testing.html` | 8 |
| `@/Users/danielhanson/CascadeProjects/Wages-App/templates/wages.html` | 5 |
| `@/Users/danielhanson/CascadeProjects/Wages-App/templates/base.html` | 3 |
| `@/Users/danielhanson/CascadeProjects/Wages-App/templates/settings/attendance.html` | 3 |
| `@/Users/danielhanson/CascadeProjects/Wages-App/templates/mtd_sandbox.html` | 1 |
| `@/Users/danielhanson/CascadeProjects/Wages-App/templates/settings/profile.html` | 1 |
| `@/Users/danielhanson/CascadeProjects/Wages-App/templates/verbal_pay_manager.html` | 1 |

`static/js/missing-jobs.js:81` also emits inline `style="width:50px"` via JS — should be a CSS class.

### 1.2 Error-handling smells

- **28 bare `except:` clauses** across 14 Python files. Highest concentration:
  - `@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_reports.py` (6)
  - `@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_data.py` (4)
  - `@/Users/danielhanson/CascadeProjects/Wages-App/app/models/recurring_template.py` (3)
  - `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_client.py` (2)
- **384 `except Exception as e:`** blocks — most do call `logger.error`, but a spot-check found several in `api_reports.py`, `api_data.py` and `recurring_template.py` that only `pass` silently. Full list to be produced before fix phase with a one-liner: `rg -n "except.*:\s*$\n\s*pass" app/`.
- `logger.error(f'…: {e}')` pattern is used widely ✓ — but very few calls use `exc_info=True` so stack traces are lost. `api_hmrc.py` is a good exception (uses `exc_info=True`).

### 1.3 Hardcoded paths / magic values

- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/periodic_sync.py:81` — `logging.FileHandler('logs/periodic_sync.log')` is relative, should use `Config.LOG_DIR`.
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/periodic_sync.py:358,444,500,538,595` — `subprocess.run([sys.executable, 'scripts/production/…', …])` uses CWD-relative script paths. Works if the service always runs from repo root; fragile otherwise. Wrap in `Config.BASE_DIR / 'scripts/production/…'`.
- `/pdfs/runsheets` mentioned only in comments and `.env`, not hardcoded in Python — ✓.
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/config.py:51` — `UPLOAD_FOLDER = 'PaySlips'` fallback is legacy; production should never fall through.
- **`new_web_app.py:21`** — hardcoded `DB_PATH = "data/payslips.db"` (wrong path — current is `data/database/payslips.db`). File should be deleted.
- **`token.json`, `credentials.json`** at repo root — gitignored, but unusual placement; a `GMAIL_CREDENTIALS=secrets/credentials.json` env var would be safer.

### 1.4 Hardcoded URLs / credentials

- No hardcoded passwords or secrets found. ✓
- OAuth / HMRC URLs are correctly swapped by `HMRC_ENVIRONMENT`. ✓
- `GOOGLE_MAPS_API_KEY` defaults to empty string — feature degrades gracefully.
- `HMRC_REDIRECT_URI` defaults to `http://localhost:5000/api/hmrc/auth/callback` (note: port 5000, but the app actually runs on 5001 per `start_web.sh`). Could mis-route in dev. Worth aligning.

### 1.5 TODO / FIXME comments

Only one tracked TODO in `app/`:
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_hmrc.py:812` — quarterly period type DB update placeholder.

### 1.6 Duplicate / dead code

- **`@/Users/danielhanson/CascadeProjects/Wages-App/new_web_app.py`** (2611 lines, 82 KB) — legacy monolithic Flask app that predates the blueprint refactor. No longer imported. **Recommend delete.**
- `camelot_runsheet_parser.py` exists in both `scripts/production/` and `scripts/testing/` — check which is authoritative.
- `scripts/` root contains 18 one-shot Python scripts (`add_current_year_home_office.py`, `batch_estimate_all_missing_mileage.py`, etc.) that look like completed migrations. Candidates for `legacy_archive/`.
- `legacy_archive/` already holds 581 items — healthy practice, but ensure `.gitignore` keeps it out of prod deploys if size is a concern.

### 1.7 Naming / imports

- Python files are uniformly `snake_case` ✓.
- JS files under `static/js/` mix conventions: `missing-jobs.js` (kebab) vs `mtd-sandbox.js` (kebab) vs `app.js`/`base.js`/`analytics.js` (flat). Not strictly a violation of the rule since the rule says kebab-case for JS, but a few files (`settings-sync.js` ✓, `recurring-templates.js` ✓) are already right. Minor.
- No obvious unused imports in a spot-check; a full lint pass (`ruff check app/`) has not been run.

---

## 2. Security

### 2.1 Authentication

- All non-public routes are protected by a global `before_request` handler (`@/Users/danielhanson/CascadeProjects/Wages-App/app/auth_protection.py:17`). The only explicit `@login_required` usages are in `api_verbal_pay.py`, `auth.py`, `api_settings.py` — the rest rely on the global guard. This is fine but means a bug in `protect_all_routes` could silently open everything. Consider belt-and-braces: also add `@login_required` on the blueprints.
- Public endpoints listed: `auth.login`, `auth.logout`, `static`, `main.privacy`, `main.terms`. Public prefixes: `/static/`, `/login`, `/logout`, `/privacy`, `/terms`. **HMRC OAuth callback (`/api/hmrc/auth/callback`) is NOT in the public list.** It relies on the browser still holding the session cookie after the HMRC redirect, which usually works because SameSite=Lax permits top-level nav cookies, but there is a code path (`@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_hmrc.py:112`) that explicitly tries to "restore user session" — which can't run if the `before_request` guard has already redirected to login. Confirm this has been hit successfully in sandbox OAuth.

### 2.2 CSRF

- `CSRFProtect(app)` is active (`app/__init__.py:58`). ✓
- `csrf-token` meta tag is emitted in `templates/base.html:9` and `templates/auth/login.html:6`. ✓
- Helper `static/js/csrf-helper.js` provides `getJSONHeaders()`.
- **Bug:** `@/Users/danielhanson/CascadeProjects/Wages-App/static/js/missing-jobs.js:175` POSTs JSON **without** the CSRF header → 400 Bad Request. Root cause of the "Add Selected Jobs" failure.
- **6 `csrf.exempt` decorators** in `app/routes/api_hmrc_sandbox.py` — acceptable for the sandbox, but flag for removal before production flip.
- `app/routes/api_runsheets.py`, `api_route_planning.py`, `api_expenses.py` contain several POST/PUT/DELETE endpoints — the ones called from legacy/non-helper JS need auditing for missing CSRF headers (same bug pattern as missing-jobs.js).

### 2.3 File upload validation

- `Config.ALLOWED_EXTENSIONS = {'pdf'}` ✓
- `MAX_CONTENT_LENGTH = 50 MB` ✓
- No MIME sniffing — files are trusted by extension only. For PDFs this is low risk but a magic-bytes check in `api_upload.py` would be trivial to add.

### 2.4 SQL injection

- Majority of queries are parameterised ✓.
- **36 `cursor.execute(f"…")` calls** across 6 files. Most interpolate internally-built fragments (e.g. `date_filter` built from placeholders + params) which is fine.
- **Real SQLi exposures** (user input interpolated directly):
  - `@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_data.py:1987-1989` — `year` / `month` from request JSON injected into SQL with no cast/validation. Authenticated users only, but still worth fixing (`int(year)` first, or switch to `?`).
- `app/routes/api_reports.py` f-string calls need the same spot-check.

### 2.5 Credential / session management

- `SECRET_KEY` enforced from env ✓ (raises on missing).
- `SESSION_COOKIE_SECURE` is `False` in `app/__init__.py:54` (hardcoded comment says "True for production https") — the Config class sets it correctly from `FLASK_ENV`, but the factory overwrites it post-hoc. **Bug: session cookies are sent over HTTP in production.** Should delete lines 52-55 of `app/__init__.py` and rely on `Config` alone.
- `SESSION_COOKIE_HTTPONLY = True` ✓
- `SESSION_COOKIE_SAMESITE = 'Lax'` ✓
- Password hashes via werkzeug (confirmed in `models/user.py`). ✓
- Rate limiting on login and HMRC routes ✓ (20/hour).

### 2.6 Routes without auth (documented public)

Confirmed: `/login`, `/logout`, `/privacy`, `/terms`, `/static/*`. HMRC callback is semi-public (relies on session cookie). No other unprotected routes found.

---

## 3. Database

### 3.1 Schema health

- All tables inspected have `INTEGER PRIMARY KEY AUTOINCREMENT` or natural PK (`settings.key`, `runsheet_daily_data.date`). ✓
- **Indexes: only 4 total** across the whole DB (2 in `migrations/005_hmrc_sandbox_test_users.sql`, 2 in `models/mileage.py`). Tables almost certainly needing indexes based on query patterns in the code:
  - `run_sheet_jobs(date)` — used in nearly every report query
  - `run_sheet_jobs(status)`
  - `run_sheet_jobs(job_number)`
  - `payslips(tax_year)`, `payslips(week_number, tax_year)`
  - `job_items(payslip_id)`, `job_items(customer_name)`
  - `expenses(date)`, `expenses(category_id)`, `expenses(tax_year)`
- Many columns that should be `NOT NULL` are nullable (`expenses.category_id` is NOT NULL ✓ but `description` NULL, `run_sheet_jobs` has no NOT NULL constraints at all).
- `verbal_pay_confirmations.updated_at` is added in-code via ALTER TABLE (`database.py:88`) — migration-in-code is fragile and should live in `migrations/`.

### 3.2 Date format inconsistency

Confirmed issue:
- `payslips.date` stored as **DD/MM/YYYY** (UK form)
- `run_sheet_jobs.date` stored as **DD/MM/YYYY**
- `expenses.date` stored as **YYYY-MM-DD** (ISO, matching HMRC expectations)
- `attendance.date` stored as **YYYY-MM-DD**

Report SQL routinely uses `substr(date, 7, 4) = ?` to extract year — this ONLY works for DD/MM/YYYY. Any query joining across expenses and runsheets has to reformat. Long term: normalise everything to ISO-8601 in a migration + keep a formatter helper for UK display.

### 3.3 Migrations

- `migrations/001_initial_schema.sql` … `006_add_nino_to_hmrc_tables.sql` — numbered and run via `app/services/migration_runner.py`. ✓
- `init_database()` still creates most tables in code (`app/database.py:34`). This duplicates responsibility with the migrations folder and means schema drift can happen. Recommend: have `init_database()` only create the `schema_migrations` tracking table; all real DDL in migrations.

### 3.4 Backup strategy

- `Config.DATABASE_BACKUP_DIR = data/database/backups` and `BACKUP_RETENTION_DAYS = 30` ✓
- `logs/backup.log` exists but is only 800 bytes — **backups appear not to be running regularly.** No cron/systemd timer was found in the repo for DB backups; the scripts-folder `backup_*.sh` may exist on prod only.
- Recommend: sqlite online `.backup` hourly + nightly copy off-box.

### 3.5 Orphaned records

- `run_sheet_jobs` has no FK to a runsheets-metadata table (there isn't one — runsheets are PDFs on disk). So "orphaned jobs" = jobs whose date has no corresponding PDF. A count is easy: `SELECT COUNT(DISTINCT date) FROM run_sheet_jobs WHERE date NOT IN (SELECT … );`. Not audited live.
- `job_items.payslip_id` should have a FK + `ON DELETE CASCADE` — currently relies on app-level discipline.

---

## 4. Sync System

### 4.1 Scheduling

- Daily start at `sync_start_time` (default 19:00, configurable in settings) plus every-15-min retry window that auto-clears when tomorrow's runsheet is in DB. Payslips: Tuesdays 06:00–14:00. Pause/resume, retry with exponential backoff, health endpoint all present. ✓
- Scheduler runs in a daemon thread inside the Flask process (`app/services/periodic_sync.py:164-166`). Fine for a single-worker gunicorn; will double-schedule under multi-worker. Current deploy is single-worker so safe.

### 4.2 Observed failure modes (from `logs/periodic_sync.log`, `logs/error.log`)

- **Most common error:** `Failed to import <filename>.pdf: Unknown error` with stdout showing "Extracted 0 unique jobs for Daniel Hanson" — Camelot parser cannot find Daniel's rows in some multi-driver PDFs (e.g. `4387234.pdf`, `Runsheet_Andrius_Zala_14042026.pdf`). The sync reports these as errors even though it's "correct" behaviour (PDF is for another driver).
- **Noise:** Thousands of `invalid pdf header: b'0.57 '` WARNING lines from pdfminer — upstream PDF format issue, benign, but is drowning real errors.
- `DH_11-04-2026.pdf`, `DH_12-04-2026.pdf`, `DH_13-04-2026.pdf`, `DH_14-04-2026.pdf` — these are Daniel's PDFs but the importer reports "No jobs imported". Needs investigation (parser regression or actually empty days?).
- The log file `periodic_sync.log` is 1.3 MB, `error.log` 365 KB — rotation is NOT working for these.

### 4.3 Edge-case coverage in `sync_latest()`

- ✓ Handles "no runsheets yet"
- ✓ Prevents duplicate instance via `current_state == 'running'` check
- ✓ Resets tracking at midnight
- ⚠ `schedule.once()` is called at `app/services/periodic_sync.py:206` — `schedule` library has no `once()`; this will throw an AttributeError on pause-with-duration. Easy to miss because `duration_minutes=None` is the usual path.
- ⚠ Retry logic is not bounded across days — `self.retry_count` only resets on success or at daily start; a sync that never succeeds would exhaust 3 retries and then go silent.
- ⚠ When download succeeds with 0 new files, the "no file paths tracked" fallback path (`--recent-minutes 10`) runs — harmless but can cause re-import attempts.

### 4.4 File-path tracking fix

- `📁` emoji parsing (`app/services/periodic_sync.py:377-384`) is implemented ✓
- Logs confirm paths are being tracked: `📋 Tracked 40 file paths for import` appears in recent runs.

### 4.5 NAS / dual-write

- No evidence in the Python code of writing runsheets to a secondary NAS location. If this is required, it's being done at the shell/mount level (`/Volumes/pdfs` vs `/pdfs`).

### 4.6 Log rotation

- `app/logging_config.py` sets RotatingFileHandler (10 MB × 5). ✓ for app.log/api.log (api.log.1..api.log.5 present).
- `periodic_sync.log`, `error.log`, `errors.log` are created with plain `FileHandler` → never rotate. Recommend unifying under `setup_logging()`.

---

## 5. HMRC MTD Integration

### 5.1 Endpoint coverage

Audited `app/routes/api_hmrc.py` — present:

| Endpoint | Route |
|---|---|
| OAuth start | `/api/hmrc/auth/start` |
| OAuth callback | `/api/hmrc/auth/callback` |
| Auth status / disconnect | `/api/hmrc/auth/status`, `/auth/disconnect` |
| Test connection | `/api/hmrc/test-connection` |
| Obligations (live + stored) | `/obligations`, `/obligations/stored`, `/obligations/final-declaration` |
| Period preview / submit | `/period/preview`, `/period/submit` |
| Businesses list / detail | `/businesses`, `/business/<id>` |
| Quarterly period type PUT | `/business/<id>/quarterly-period-type` (has the TODO) |
| Calculations list / retrieve | `/calculations/list`, `/calculations/<id>` |
| Self-employment periods / annual summary | `/self-employment/periods`, `/self-employment/annual-summary` |
| Final declaration status / calculate / submit | `/final-declaration/*` |
| Property business obligations + submit | `/property/obligations`, `/property/submit` |
| BSAS trigger + retrieve | `/bsas/trigger`, `/bsas/<id>` |
| Losses create + list | `/losses/create`, `/losses/list` |
| Export (audit trail) | `/export` |
| Submissions list | `/submissions` |

All 9 required MTD API domains are covered. ✓

### 5.2 Sandbox/production switch

- `Config.HMRC_ENVIRONMENT` drives both base URL and auth URLs via `@property` methods. ✓
- Sandbox-only blueprint (`api_hmrc_sandbox.py`) is registered unconditionally (`__init__.py:158,187`) with the warning comment "Remove before production". **Risk: this gets forgotten.** Gate the registration on `if Config.HMRC_ENVIRONMENT != 'production':` now.

### 5.3 MTD compliance elements

- Mandatory disclaimer / declaration / lock after submission / export / software notice — `templates/settings/hmrc.html` contains the UI strings; not 100 % verified against the MTD notice requirements checklist. Worth a formal tick-off.
- `/api/hmrc/export` exists ✓.
- Digital records "lock after submission" — no evidence of a DB flag being set on `hmrc_submissions` to prevent post-submission edits of the underlying data. **Gap.**
- No evidence of the MTD-required "fraud prevention headers" (Gov-Client-*/Gov-Vendor-*) being sent on production calls. **Critical for prod.** Search `api_hmrc.py` / `services/hmrc_client.py` for these before flipping.

### 5.4 Q1 submission readiness

- Sandbox test scripts exist (`scripts/test_q1_submission.py`, `scripts/test_final_declaration.py`, `scripts/test_create_business.py`) — good.
- Production credentials: per the brief, submitted 14 April 2026, awaiting HMRC approval. Until approval arrives, no live submission possible.
- Expense category → HMRC box mapping is seeded in `@/Users/danielhanson/CascadeProjects/Wages-App/app/database.py:135-149` and looks correct for boxes 20–29.

---

## 6. Expense Management

### 6.1 CRUD

- `api_expenses.py` (14 KB) covers list/create/update/delete + bulk import from bank CSV via `api_bank_import.py` + recurring via `api_recurring.py`. ✓
- Date format: stored as ISO YYYY-MM-DD ✓, but the frontend `expenses.js` needs verification that it posts ISO (the base.js has a date-normaliser — confirm it runs before submit on mobile Safari). Historical iOS DataTransfer issue was reverted per the brief.

### 6.2 Receipt upload

- Endpoint exists; max 50 MB; PDF-only by extension. Images for receipts? Check — the `ALLOWED_EXTENSIONS` dict is `{'pdf'}` only. **Bug suspected: receipt upload from iOS camera (which returns JPEG/HEIC) would be rejected.** Recent work added camera capture — verify the allowlist was extended or the camera handler converts to PDF.

### 6.3 Recurring

- Full template matching system in place (confidence scoring, auto-import). ✓
- No evidence of a scheduled job that creates next-month's recurring expense automatically — matching is triggered on bank statement import only.

---

## 7. Runsheet Management

### 7.1 Status / completion

- `api_runsheets.py` (34 KB) handles status updates. No obvious bugs by inspection.

### 7.2 Missing-jobs modal (BROKEN)

Root cause found. `@/Users/danielhanson/CascadeProjects/Wages-App/static/js/missing-jobs.js:175-181`:

```js
const response = await fetch('/api/payslips/add-missing-jobs', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'   // ← missing X-CSRFToken
    },
    body: JSON.stringify({ jobs: selectedJobs })
});
```

Fix: replace `headers` with `getJSONHeaders()` from `csrf-helper.js` and ensure `csrf-helper.js` is loaded on the wages page. One-line change.

### 7.3 Address validation

- `scripts/production/validate_addresses.py` exists but is a batch tool, not inline validation. The parser uses post-processing regexes per customer (PayPoint, VISTA, etc.). Good-enough.

### 7.4 Route planning / analytics

- `api_route_planning.py` (40 KB) — large surface area, uses Google Maps API. If API key missing, endpoints fail gracefully (returns JSON error). No indication of test coverage.

---

## 8. Reporting

### 8.1 Coverage

- Daily / weekly / monthly / quarterly / yearly via `api_reports.py` and `api_data.py` (the custom report generator). All tax-year-aware via `substr(date, 7, 4)` pattern.
- Tax year boundary — uses calendar year in many places rather than UK tax year (6 April – 5 April). The expense system has a `tax_year` column; reports sometimes use it, sometimes use `substr(date, …) = year`. **Inconsistency.**
- VAT: `expenses.vat_amount` column exists, but there's no VAT-registered aggregation (the user is VAT-unregistered, so likely correct).

### 8.2 PDF export

- Uses `reportlab` — confirmed in `api_data.py:1948-1952`.

### 8.3 Company-specific weeks

- `app/utils/company_calendar.py` implements the Sunday-Saturday week structure aligned to the first Saturday 22/03/2025. ✓ (already debugged earlier this year.)

---

## 9. Mobile Experience

Not empirically tested this audit; observations from code:

- `unified-styles.css` + Bootstrap 5.3 framework ✓.
- Touch targets / font-size-16 / iPhone 16 Pro Max breakpoints — present per unified-styles work.
- Inline `style="width:50px"` in `missing-jobs.js` breaks the "no inline styles" + mobile rules.
- iOS camera capture: see §6.2 — extension allowlist might block the upload, recent revert suggests it's still broken.
- All fetch/XHR calls needing CSRF have historically been a weak point — add a project-wide wrapper (see Phase 2 roadmap).

---

## 10. Performance

### 10.1 Slow queries (predicted)

- Reports over full history do `SELECT … FROM run_sheet_jobs WHERE …` with no indexes. At current volumes (~15 k runsheet jobs, ~14 k job_items, hundreds of payslips) it is already a few hundred ms per complex query; will get worse.
- `job_items JOIN payslips` without indexes on `job_items.payslip_id` — N+1-ish.

### 10.2 JS bundle

- 27 JS files in `static/js/`, loaded piecemeal per page. No bundler. Biggest individual file is `app.js` / `base.js`. Size is fine; no action needed.

### 10.3 Polling

- Settings/sync page auto-refreshes every 30 s. Reasonable.
- Weekly summary etc. fetch on navigation only. Fine.

---

## 11. Error Handling & Logging

### 11.1 Log files present

| File | Size | Rotation |
|---|---|---|
| `access.log` | 1.9 MB | ✗ |
| `api.log` + `.1..5` | 10 MB × 6 | ✓ |
| `app.log` | 1.8 MB | ✗ (configured for rotation but no `.1` present — recent restart) |
| `error.log` | 365 KB | ✗ |
| `errors.log` | 951 KB | ✗ (duplicate of error.log — confusion) |
| `periodic_sync.log` | 1.3 MB | ✗ |
| `hmrc.log` | 93 KB | ✗ |
| `settings.log` | 185 KB | ✗ |
| `runsheet_sync.log` + `_error` + `_progress` | 200 KB | ✗ |
| `separated_sync.log` | 576 B | dead |

### 11.2 Repeated errors

- "invalid pdf header: b'0.57 '" — pdfminer warning, every runsheet-import run.
- "Failed to import <file>: Unknown error" — the dominant real error; see §4.2.

### 11.3 User-facing error pages

- No custom 404/500/403 templates found under `templates/errors/`. Stock Flask error pages are shown.

---

## 12. Testing

### 12.1 Present

- `scripts/test_q1_submission.py`, `scripts/test_final_declaration.py`, `scripts/test_create_business.py` — ad-hoc MTD scripts, not pytest.
- `scripts/testing/test_camelot_extraction.py`, `test_runsheet_extraction.py` — ad-hoc parser tests.
- **No `pytest` suite, no `tests/` directory, no CI config.**

### 12.2 Critical paths that need tests (ranked)

1. HMRC period submission happy path + token refresh (sandbox).
2. Runsheet import for each customer-specific parser (freeze golden-output fixtures).
3. Payslip parsing against a representative payslip fixture.
4. Expense CRUD + CSRF/auth guard smoke tests.
5. `periodic_sync.sync_latest()` with mocked subprocess results.

---

## PART 2 — What Needs Finishing

Explicit partial work uncovered:

| # | Feature | Status | Owner work remaining |
|---|---|---|---|
| 1 | Payslip → runsheet "Add Selected Jobs" | **Broken (400)** | One-line CSRF fix in `static/js/missing-jobs.js` |
| 2 | iOS camera capture for receipts | Reverted | Decide: extend `ALLOWED_EXTENSIONS` to `{pdf,jpg,jpeg,heic,png}` + server-side convert to PDF, OR strip camera UI |
| 3 | Inline-styles cleanup | ~30 % done | 98 matches across 12 templates (§1.1) |
| 4 | HMRC production credentials | Awaiting HMRC approval | Nothing to do until they arrive; remove sandbox blueprint + `csrf.exempt` on flip |
| 5 | Quarterly period type DB persistence | TODO placeholder | `api_hmrc.py:812` — wire up `businesses` table writes |
| 6 | Fraud prevention headers on HMRC calls | Unknown / missing | **Must** be done before production flip |
| 7 | Lock-after-submission of digital records | Missing | Add `locked_at` column to submissions, enforce in UI + API |
| 8 | Log rotation for periodic_sync/error/errors/hmrc | Missing | Route all loggers through `logging_config.setup_logging()` |
| 9 | DB backups automation | Unknown (only 800 B in backup.log) | Confirm cron on prod; add repo-side script + systemd timer |
| 10 | Delete `new_web_app.py` | Legacy dead code | Delete + verify no imports |
| 11 | Gate `sandbox_bp` registration | Risk until flip | `if HMRC_ENVIRONMENT != 'production'` guard |
| 12 | Session cookie Secure override in `__init__.py` | Bug | Remove lines 52-55 of `app/__init__.py`, trust Config |
| 13 | Default `HMRC_REDIRECT_URI` points to port 5000 | Minor mismatch | Align default to 5001 or remove default |
