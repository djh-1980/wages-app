# Sync System Audit

**Date:** 2026-04-27
**Scope:** Auto-sync, manual sync, manual upload — end-to-end review.
**Status:** Analysis only. No code changes proposed in this document.

---

## Part 1 — Current State

### 1.0 Trigger / orchestrator inventory

| # | Flow | Entry point | Trigger | Orchestrator |
|---|------|-------------|---------|--------------|
| A | Auto-sync (in-process) | `PeriodicSyncService.start_periodic_sync()` | Flask app startup (`@/Users/danielhanson/CascadeProjects/Wages-App/app/__init__.py:138-141`) | `app/services/periodic_sync.py` |
| B | Manual sync (subprocess) | `runMasterSyncManual()` button → `POST /api/data/run-master-sync` | User click on `templates/settings/sync.html` | `scripts/sync_master.py` |
| C | Manual file upload | `POST /api/upload/files` (drag-and-drop) | User drops PDFs in `templates/settings/sync.html` | `app/routes/api_upload.py` |
| D | Cron (external) | `sync_master.py` invoked by host crontab | OS cron 20:00, 21:00 daily + Tue 09:00, 14:00 (per memory) | `scripts/sync_master.py` |
| E | Legacy/unused | `SeparatedSyncService` | None — never instantiated outside its own module | `app/services/separated_sync.py` |
| F | Legacy/unused | `_sync_recent_runsheets`, `_sync_recent_payslips` | None — defined but never called | `app/services/periodic_sync.py:722-886` |

> Flows A and D both run on production simultaneously (per memory `d5aa0573` the cron schedule was meant to *replace* the periodic service, but `app/__init__.py` still auto-starts it). This is the first major correctness problem.

---

### 1.1 Flow A — Auto-sync (`PeriodicSyncService`)

#### Sequence

1. **Init** — `@/Users/danielhanson/CascadeProjects/Wages-App/app/__init__.py:138-141` imports the global singleton `periodic_sync_service` and calls `start_periodic_sync()` if `AUTO_SYNC_ENABLED` (default `True`).
2. **Config load** — `_load_config()` reads from `settings` table via `SettingsModel.get_setting()` (`@/Users/danielhanson/CascadeProjects/Wages-App/app/services/periodic_sync.py:87-116`). Keys: `sync_start_time`, `sync_interval_minutes`, `payslip_sync_day`, `payslip_sync_start`, `payslip_sync_end`, `notify_on_success`, `notify_on_error_only`, `notify_on_new_files_only`, `auto_sync_runsheets_enabled`, `auto_sync_payslips_enabled`.
3. **Schedule** — `start_periodic_sync()` (`periodic_sync.py:118-158`):
   - registers `_start_daily_sync` at `sync_start_time` (default 19:00),
   - **also** registers `sync_latest` at every 15-minute slot for the next 24 hours via a `for minutes_offset in range(0, 24*60, 15)` loop → 96 separate `schedule.every().day.at(...)` entries tagged `interval-sync`.
4. **`_start_daily_sync`** (`periodic_sync.py:160-175`) clears `interval-sync` tag, runs `sync_latest()` once, then re-registers `every(15).minutes.do(sync_latest).tag('interval-sync')`.
5. **`sync_latest`** (`periodic_sync.py:250-665`):
   - Pause check (`is_paused`, `pause_until`).
   - **Concurrency guard**: returns if `current_state == 'running'`. Sets `current_state = 'running'`.
   - Daily reset at midnight (instance vars `runsheet_completed_today`, `last_runsheet_date_processed`, `last_check_date`).
   - Quick exit if `latest_comparable >= tomorrow_comparable` and clears `interval-sync` (lines 296-310).
   - **Runsheet phase** (`periodic_sync.py:332-401`): `subprocess.run([python, 'scripts/production/download_runsheets_gmail.py', '--runsheets', '--recent'], timeout=120)`. Stdout parsed by string sniffing for `'✓ Downloaded:'`, `'Files saved to:'`, and `'📁'` lines.
   - **Import phase** (`periodic_sync.py:455-565`):
     - If any tracked path → loops calling `import_run_sheets.py --file <path>` per file, parses `Imported (\d+) jobs` from stdout.
     - Else → checks `_get_unprocessed_runsheets()` (scans `Config.RUNSHEETS_DIR` for `DH_*.pdf` not in `run_sheet_jobs.source_file`).
     - Else → falls back to `import_run_sheets.py --recent-minutes 10`.
     - Marks `runsheet_completed_today = True` **only if** `is_runsheet_for_tomorrow_present()` returns True (lines 554-562 — recent fix).
   - **Payslip phase** (`periodic_sync.py:402-453, 567-624`): Tuesday 06–14 window, calls `download_runsheets_gmail.py --payslips --date=YYYY/MM/DD`, then `extract_payslips.py --recent 1`, then `sync_payslips_to_runsheets()` (in-process SQL).
   - **Completion check** `_check_completion_and_stop` (`periodic_sync.py:667-698`) — clears `interval-sync` if tomorrow's runsheet is in DB, sets `current_state = 'completed'`.
   - **Notification** (`periodic_sync.py:646-652, 1051-1083`): only if `runsheets_imported > 0 OR payslips_imported > 0`, then gated by `_should_notify()` flags.

#### State storage

| State | Where | Notes |
|---|---|---|
| `is_running`, `is_paused`, `pause_until` | Instance vars on global singleton | Lost on app restart |
| `current_state` ('idle','running','completed','failed','paused') | Instance var | Lost on restart |
| `runsheet_completed_today`, `payslip_completed_this_week` | Instance vars | Reset at midnight in `sync_latest()` (lines 273-282) |
| `last_runsheet_date_processed`, `last_payslip_week_processed` | Instance vars | Computed from DB on every cycle anyway |
| `retry_count`, `last_error` | Instance vars | Used in `_handle_retry` |
| `sync_history` (last 50 entries) | Instance list | Lost on restart |
| Tomorrow's runsheet present? | Computed from `run_sheet_jobs.date` via `is_runsheet_for_tomorrow_present()` (`@/Users/danielhanson/CascadeProjects/Wages-App/app/services/sync_helpers.py:49-71`) | **Source of truth — but duplicated in `runsheet_completed_today` flag** |
| Schedule jobs | `schedule` library global queue | Tags: `interval-sync`, `retry-sync`, `auto-resume` |
| Config | `settings` table (`setting_key`, `setting_value`) | Only loaded at startup and on config-update API call |
| Notification email backups | `logs/sync_notifications/sync_*.html` | |

#### Error/retry handling

- `_handle_retry(operation)` (`periodic_sync.py:888-897`): exponential backoff `[5,15,30]` minutes, `schedule.every(delay).minutes.do(self.sync_latest).tag('retry-sync')`. Reset on next-day midnight.
- `subprocess.run(..., timeout=120)` for downloads, `timeout=60` for per-file imports, `timeout=600` for fallback bulk import.
- Returncode handling for `import_run_sheets.py`: `0` = success, `2` = ran-but-no-new-jobs (treated as info, per memory `abc032cc`), other = failure.
- Stdout/stderr captured but only logged at DEBUG for stdout, ERROR for stderr.
- Exceptions caught at top of `sync_latest`; appended to `sync_summary['errors']` and `last_error`.

---

### 1.2 Flow B / D — Manual sync (`scripts/sync_master.py`)

#### Sequence (`@/Users/danielhanson/CascadeProjects/Wages-App/scripts/sync_master.py:425-477`)

1. `setup_database()` — creates indexes (idempotent).
2. `download_files()` (lines 63-124):
   - `subprocess.run([python, 'scripts/production/download_runsheets_gmail.py', '--missing'], timeout=120)`. **Different mode** to Flow A's `--recent`.
   - Counts via stdout sniffing `'Downloaded:' in line OR 'Saved:' in line`.
   - Tuesday-only payslip download via `--payslips --date=YYYY/MM/DD`.
3. `import_runsheets()` (lines 141-197): scans `Config.RUNSHEETS_DIR` for files modified in last 5 minutes (informational), then runs `import_run_sheets.py --recent-minutes 15`. Counts via `'jobs imported' in line.lower()`.
4. `import_payslips()` — `extract_payslips.py --recent 7`.
5. `validate_addresses()` — `validate_addresses.py --recent 7`.
6. `sync_pay_data()` — opens its own `sqlite3` connection, runs the same UPDATE statements as `sync_payslips_to_runsheets()`. **Duplicated logic.**
7. `generate_report()` — prints summary.
8. Logs to `app/utils/sync_logger.py` → `logs/sync.log`.

#### Triggers

- **Flow B**: `/api/data/run-master-sync` → subprocess `sys.executable scripts/sync_master.py` (`@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_data.py:2365-2417`), `timeout=300`.
- **Flow D**: host crontab. Per memory `d5aa0573`, schedule is `0 20,21 * * *` and `0 9,14 * * 2`. Cannot be verified from repo (lives in OS).

#### State

- No persistent state. Database mutations only. Re-running is idempotent because `--missing` and `--recent-minutes 15` self-limit.
- `download_runsheets_gmail.py --missing` (`scripts/production/download_runsheets_gmail.py:566-687`) computes missing dates by diffing `run_sheet_jobs.date` against `last 30 days + tomorrow`, minus `attendance.date`.

---

### 1.3 Flow C — Manual upload (`/api/upload/files`)

#### Sequence (`@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_upload.py:73-172, 307-418`)

1. Multipart POST with `files[]`, `type` (default `general`), `auto_process` (default `true`), `overwrite` (default `false`).
2. `validate_upload_file()` — size ≤50MB, MIME via `python-magic`, secure filename.
3. Each file saved to `data/processing/manual/<name>_<timestamp>.pdf` (per `get_upload_path`, lines 61-71).
4. Background thread `process_uploaded_files_background` → `process_uploaded_files` → `auto_detect_and_process` (filename heuristic) or explicit `process_single_runsheet` / `process_single_payslip`.
5. **`process_single_runsheet`** (lines 357-418):
   - `import_run_sheets.py --file <data/processing/manual/...>`.
   - On success: `UPDATE run_sheet_jobs SET manually_uploaded = 1 WHERE source_file = ? AND imported_at >= datetime('now','-1 minute')`.
   - Calls `subprocess.run([python, 'scripts/organize_uploaded_runsheets.py'], timeout=30)` — **this script does not exist in the live tree** (only in `legacy_archive/`). Subprocess returns non-zero, error swallowed because `output` only concatenates stdout.
   - Calls `subprocess.run([python, 'scripts/sync_runsheets_with_payslips.py'], timeout=60)` — **also does not exist**. Same silent swallow.
6. Front-end (`@/Users/danielhanson/CascadeProjects/Wages-App/static/js/file-upload.js:291`) POSTs to `/api/upload/files` with CSRF headers.

#### State

- File on disk under `data/processing/manual/` (never moved).
- DB row in `run_sheet_jobs` with `source_file = <name>_<timestamp>.pdf`, `manually_uploaded = 1`.
- No record in `RUNSHEETS_DIR` (NAS).

---

### 1.4 Shared subprocesses

#### `download_runsheets_gmail.py`

Modes (parsed in `main()` at lines 838-889):

- `--runsheets [--recent] [--date=YYYY/MM/DD]` — Gmail search `has:attachment filename:pdf (subject:"RUN SHEETS" OR subject:runsheet OR filename:runsheet) newer_than:14d` (when `--recent`) or `... after:YYYY-MM-DD`.
- `--payslips [--date=YYYY/MM/DD]` — Gmail search `SASER after:YYYY-MM-DD`, then filtered to messages whose `Date:` header is a Tuesday.
- `--missing` — calls `download_missing_runsheets(30)` which:
  - Computes missing dates from DB (`find_missing_runsheet_dates`, lines 250-306).
  - Searches recent (last 14 days) emails.
  - **Filters emails by parsing the date from the email *Subject*** with regex `(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)\s+(\d{4})` (lines 624-640). If subject does not match this pattern (e.g. `Warrington - Run Sheets` with no date) the email is **silently skipped**.

For `--runsheets --recent`, after download `organize_pdf` is called per attachment:

- Scans **all PDF pages** (`has_driver_name`, lines 72-87) looking for "Daniel Hanson" / "Hanson, Daniel". Slow on 100+ page multi-driver PDFs.
- If not found → moves PDF to `<RUNSHEETS_DIR>/manual/`.
- If found → renames to `DH_DD-MM-YYYY.pdf` under `<RUNSHEETS_DIR>/<YYYY>/<MM-Month>/`.
- Prints `📁 <relative-path>` (line 524) which Flow A relies on for tracking.

`download_attachments` always overwrites existing files (line 451). No de-dupe at download time; de-dupe happens at organise time when `target_path.exists()`.

#### `import_run_sheets.py`

Relevant CLI (`@/Users/danielhanson/CascadeProjects/Wages-App/scripts/production/import_run_sheets.py:2577-2810`):

- `--file <path>` — single file. Exit codes: `0` imported>0, `2` ran-OK-but-0-new (per memory `abc032cc`), `1` real error.
- `--recent N` — last N days by mtime.
- `--recent-minutes N` — last N minutes by mtime (used by both Flow A fallback and Flow B).
- `--unprocessed` — files not in `run_sheet_jobs.source_file` set.
- `--date YYYY-MM-DD`, `--date-range`, `--name`, `--force-reparse`, `--overwrite`.

Multi-driver detection delegated to `CamelotRunsheetParser` (`@/Users/danielhanson/CascadeProjects/Wages-App/scripts/production/camelot_runsheet_parser.py`):

- `find_driver_pages()` (lines 18-62): pre-scans first 2 lines of each page for the driver name. Restricting to first 2 lines is what stops "Hanson, Daniel" leaking from warehouse manifest pages (per memory `abc032cc`).
- `_is_my_table()` (lines 145-165): in pre-filtered mode, trusts the page (`_on_driver_page = True`). Fallback path (no pre-filter) scans first 5 rows of the table for the name.

#### `sync_payslips_to_runsheets()` (Flow A) vs `sync_pay_data()` (Flow B)

Two implementations of the same SQL:

- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/sync_helpers.py:101-238` — used by Flow A. WAL mode, `busy_timeout=60000`, retries 3x.
- `@/Users/danielhanson/CascadeProjects/Wages-App/scripts/sync_master.py:265-365` — used by Flow B. `journal_mode=DELETE`, no retry. Updates only rows where `pay_amount IS NULL` (Flow A's version updates *all* matching rows every time).
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/runsheet_sync_service.py:21-126` — third copy, called by `/api/sync/payslip-to-runsheets` only (UI button on `templates/runsheets.html`?).

---

### 1.5 Database touchpoints

| Table | Reader/writer |
|---|---|
| `run_sheet_jobs` | `import_run_sheets.py` writes; `sync_helpers.sync_payslips_to_runsheets`, `sync_master.sync_pay_data`, `RunsheetSyncService` update; `sync_helpers.get_latest_runsheet_date`, `_get_unprocessed_runsheets`, `find_missing_runsheet_dates` read. |
| `job_items` / `payslips` | `extract_payslips.py` writes; pay-sync UPDATEs read. |
| `attendance` | Read by `find_missing_runsheet_dates` (excludes days off). |
| `settings` | `SettingsModel.get_setting/set_setting` only. |
| `hmrc_submissions` | Locks period dates; not relevant to sync. |

---

## Part 2 — Problems

### 2.1 Single points of failure

1. **Email subject parser (`download_missing_runsheets`)** — `--missing` mode silently skips emails whose subject lacks an English date with `(\d{1,2})(?:st|nd|rd|th)?\s+\w+\s+\d{4}`. Subjects like `Warrington - Run Sheets`, `RUN SHEETS - WARRINGTON`, `warrington - Run Sheets` (no date) are dropped even when they contain tomorrow's PDF. *This is likely the root cause of the cron-only flow returning "0 downloaded".*
2. **Driver-name pre-scan (`organize_pdf` and `find_driver_pages`)** runs PDF-wide text extraction on every attachment. On multi-driver PDFs of 100+ pages this is O(pages) and dominates download time. If pdfplumber chokes on a malformed page the whole organisation step fails for the file (`except: return False`).
3. **Subprocess stdout parsing** — every flow relies on string-sniffing other scripts' stdout (`✓ Downloaded:`, `📁`, `Imported %d jobs`, `Successfully processed: N/M`). Any change to the downstream script's logging silently breaks counting.
4. **Global `schedule` queue** — Flow A registers 96 cron-style entries in process memory plus dynamic `every(N).minutes` entries. There is no persistence; an app restart clears all schedules until the next call to `start_periodic_sync`.
5. **Two missing scripts** — `scripts/organize_uploaded_runsheets.py` and `scripts/sync_runsheets_with_payslips.py` are referenced by `process_single_runsheet` but exist only in `legacy_archive/`. The subprocess returns non-zero, the error is swallowed because the function only checks `import_process.returncode == 0`.

### 2.2 Race conditions

1. **Auto-sync (in-process) vs cron `sync_master.py`** can run concurrently. `current_state == 'running'` guard exists in Flow A only; `sync_master.py` has no awareness of Flow A. Both write to `payslips.db`. WAL mode mitigates but does not eliminate write contention; concurrent imports can produce duplicate `run_sheet_jobs` rows if `source_file` differs only by timestamp suffix.
2. **Manual upload background thread** vs **auto-sync** — `process_single_runsheet` runs in a daemon thread launched from the Flask request. Auto-sync's `sync_latest` runs in another thread (`periodic_sync._run_scheduler`). No mutex.
3. **`schedule.clear('interval-sync')`** is called from multiple decision points (`sync_latest`, `_check_completion_and_stop`, `_start_daily_sync`). If two threads race here we can lose retry jobs.

### 2.3 Silent failures

1. `process_single_runsheet`'s missing-script subprocesses (`organize_uploaded_runsheets.py`, `sync_runsheets_with_payslips.py`) — caller reports success purely from the *import* return code. **This is why manually-uploaded PDFs never get copied to NAS.**
2. `_handle_retry` doesn't surface to the user — retries just re-enqueue silently.
3. `download_runsheets_gmail.py` exits 0 even when 0 emails matched ("⚠️  No run sheet emails found"). Flow A treats this as success and continues to the import phase, which then has nothing to import. No alert.
4. `--missing` mode's subject-regex skip is silent.
5. Notification gating (`@/Users/danielhanson/CascadeProjects/Wages-App/app/services/periodic_sync.py:646`) requires `runsheets_imported > 0 OR payslips_imported > 0` *before* `_should_notify` is consulted, so `notify_on_error_only` cannot fire for a download error that produces zero imports.
6. `_get_unprocessed_runsheets` (`periodic_sync.py:963-994`) only looks for `DH_*.pdf` filenames. Anything in `<RUNSHEETS_DIR>/manual/` (PDFs we couldn't confirm contain Daniel) is excluded forever.

### 2.4 Hardcoded paths

1. `DB_PATH = "data/database/payslips.db"` hardcoded in `app/services/sync_helpers.py:16` (also `app/database.py`). `Config.DATABASE_PATH` exists but is bypassed.
2. `data/processing/manual/`, `data/uploads/pending/`, `logs/sync.log`, `logs/sync_notifications/`, `PaySlips`, `RunSheets` — all hardcoded, not read from `Config`.
3. `process_manual_uploads` (`api_upload.py:511-545`) tests `'PaySlips' in str(directory)` and `'RunSheets' in str(directory)` — string membership against hardcoded directory names. Will silently no-op on systems where folders are named differently.

### 2.5 Duplicated logic

| Logic | Implementations |
|---|---|
| Pay-data UPDATE SQL | `app/services/sync_helpers.py:101-238`, `scripts/sync_master.py:265-365`, `app/services/runsheet_sync_service.py:21-126` |
| Latest-runsheet-date query | `app/services/sync_helpers.py:19-46`, `scripts/production/download_runsheets_gmail.py:250-306` (different format, in-memory date generation), `app/routes/api_data.py:2420-2456`, `app/routes/api_sync.py:18-79` |
| Tomorrow-comparable computation | `periodic_sync.py:296-310, 670-689, 1007-1017`, `separated_sync.py:55-69`, `sync_helpers.py:62-71` |
| Subprocess + stdout sniffing for counts | Every orchestrator |
| Gmail download orchestration | `periodic_sync.sync_latest`, `sync_master.download_files`, `api_upload.attempt_gmail_sync`, `separated_sync.runsheet_workflow`/`payslip_workflow` |

### 2.6 Multiply-tracked "is sync complete?"

For "have we got tomorrow's runsheet" alone:

1. `periodic_sync_service.runsheet_completed_today` (instance flag).
2. `is_runsheet_for_tomorrow_present()` (computed from DB).
3. `current_state` ('completed' / 'idle' / etc.).
4. Presence/absence of `interval-sync` scheduled jobs.
5. `_check_completion_and_stop` recomputes (3) again (`periodic_sync.py:667-698`).

Only (2) is authoritative; the other four can drift after restarts, partial failures, or manual DB edits.

### 2.7 Missing logging

- Flow B doesn't log to `app.logging_config` — uses bare `print()` plus the unified `sync_logger`. `print()` output only reaches `logs/sync.log` if cron's stdout is redirected (`>> logs/sync.log 2>&1` per memory).
- No log line at the moment we *decide not to download* (e.g. outside window, paused, completed).
- No log at the upload background-thread boundary — if it crashes, there's no trace.
- Subprocess timeouts log the error but don't capture partial stdout.
- No correlation ID across the three flows; reading `logs/sync.log` you cannot tell which flow ran.

### 2.8 Incorrect assumptions

1. **"19:00 = email is here"** — Holly often emails 19:30–21:00 and David later still. Flow A's daily 19:00 trigger nominally retries every 15 min, but the 96-entry cron-style schedule is fragile and if `sync_latest` exits early (e.g. on a Camelot timeout) the next slot has to fire to get the import.
2. **"Subject contains a date"** — assumed by `download_missing_runsheets` only. Holly's subjects are usually "MONDAY 9th MARCH 2026" (matches), but David's are "Run sheets" / "Warrington - Run Sheets" (does not match → silently skipped).
3. **"One sender = one PDF"** — assumed by attachment counting (`'Downloaded:' in line`). David's emails attach 10+ PDFs (one per driver). Counted correctly here, but the 10 non-Daniel PDFs are then page-scanned, moved to `manual/`, and forgotten.
4. **"Daniel-Hanson appears on page 1"** — assumed by `has_driver_name` (no, it scans all pages) but the search is slow. Restricting to first 2 lines (in `find_driver_pages`) is correct, but `has_driver_name` still scans everywhere — so `organize_pdf` may classify a warehouse manifest as "yours" if "Daniel Hanson" appears in body text. *(Original "other engineers' jobs" bug surfaced exactly here.)*
5. **"`AUTO_SYNC_ENABLED=True` is the dev pattern, prod uses cron"** — both run on prod; nobody flips the env var.

---

## Part 3 — Actual user requirement

Daniel needs:

1. **Tomorrow's runsheet in the DB before bed**, automatically, regardless of who emailed it (Holly, David, anyone) and regardless of the email's exact subject.
2. **Multiple PDFs per email** (David's format) handled by downloading all, importing only Daniel's, and ignoring the rest without polluting the runsheets folder.
3. **Manual upload** as a reliable fallback that ends up in the same place (NAS) as auto-downloaded PDFs.
4. **Visibility** — one log, one status page, one source of truth for "did we get tomorrow's?".
5. **A loud failure mode** — if no runsheet for tomorrow by 23:00, send a notification (email or push). Right now silent failures dominate.
6. **Idempotence** — re-running any flow should never duplicate jobs, never re-import the same PDF, never overwrite manual edits to addresses/pay.

The single concrete success metric: **after the redesign, Daniel should never need to manually intervene to get tomorrow's runsheet into the DB unless something is genuinely wrong — and when it is, he gets told.**

---

## Answers to the four questions in the brief

1. **Why does sync sometimes not run when an email arrives?**
   - `sync_master.py --missing` silently skips emails whose subject doesn't match its date regex (David's "Warrington - Run Sheets").
   - Flow A's `--recent` does match, but the 19:00 schedule + 15-min retries can be derailed by a Camelot timeout (`timeout=60` per file) and the per-day retry counter resets at midnight, not at task completion.
   - Cron and in-process auto-sync both running can lock the DB and one of them silently fails its UPDATE.

2. **Why does manual upload sometimes work and sometimes not?**
   - The "doesn't end up on NAS" failure is **deterministic, not intermittent** — `scripts/organize_uploaded_runsheets.py` doesn't exist in the live tree; the subprocess always fails; the failure is swallowed.
   - The "imports work" half *does* work, because that step uses `import_run_sheets.py --file`, which is solid.

3. **Why are jobs from other engineers being imported?**
   - Historically: `find_driver_pages` looked across the whole page text. A warehouse manifest page contains "Driver Hanson, Daniel" on line 3, so the page was wrongly accepted. Fix in place: restrict to first 2 lines (`@/Users/danielhanson/CascadeProjects/Wages-App/scripts/production/camelot_runsheet_parser.py:42-47`).
   - Residual risk: `organize_pdf.has_driver_name` still scans **all** pages for any mention of the name and trusts the file as Daniel's purely on a substring hit. A 100-page David PDF with one mention of "Daniel Hanson" in a comment field would be treated as Daniel's runsheet and parsed for jobs that aren't his.

4. **What's the fastest path to a sync system you can trust?**
   - Replace the three orchestrators with **one** sync orchestrator that calls library functions (not subprocesses) and is invoked by all three triggers (auto, manual button, file upload).
   - Remove the email-subject-date dependency: download every matching email, organise every attachment, let `find_driver_pages` decide what's Daniel's.
   - Make "tomorrow in DB" the single source of truth; everything else (flags, schedule jobs, notifications) is derived.
   - Add a single end-of-night watchdog: if `is_runsheet_for_tomorrow_present()` is False at 23:00, fire a notification.
   - Plan in `SYNC_REDESIGN.md`.
