# Sync System Redesign

**Goal:** One reliable, observable, idempotent sync orchestrator. Three triggers (cron, button, upload) — one code path.

---

## 1. Architecture

```
                  +------------------------------------+
                  |        SyncOrchestrator            |
                  |  (app/services/sync/orchestrator)  |
                  +------------------------------------+
                          |        |         |
              ingest()    |        | run()   |  upload(file)
                          v        v         v
            +----------------+ +----------------+ +----------------+
            | EmailIngestor  | | LocalIngestor  | | UploadIngestor |
            | (Gmail API)    | | (NAS scan)     | | (HTTP upload)  |
            +----------------+ +----------------+ +----------------+
                          \      |       /
                           v     v      v
                       +-------------------+
                       |   PdfRouter       |  classify by header (Daniel/other),
                       |                   |  extract date, move to canonical path
                       +-------------------+
                                |
                                v
                       +-------------------+
                       |   DbImporter      |  import_run_sheets / extract_payslips
                       |  (library calls,  |  imported as functions, not subprocess
                       |   no subprocess)  |
                       +-------------------+
                                |
                                v
                       +-------------------+
                       |  PaySync          |  payslip -> runsheet UPDATE (single SQL)
                       +-------------------+
                                |
                                v
                       +-------------------+
                       |  StateStore       |  one row in `sync_runs`,
                       |  + Notifier       |  notification only here
                       +-------------------+
```

### Module breakdown

| Module | Purpose |
|---|---|
| `app/services/sync/orchestrator.py` | The one-and-only orchestrator. Public API: `run_sync(trigger, scope)`, `ingest_uploaded_file(path)`, `is_tomorrow_present()`, `night_watchdog()`. |
| `app/services/sync/email_ingestor.py` | Wraps Gmail. **No date-from-subject parsing.** Pulls every email matching the runsheet/payslip queries; returns `[(message_id, attachment_bytes, suggested_filename)]`. |
| `app/services/sync/local_ingestor.py` | Yields PDFs already in `Config.RUNSHEETS_DIR` not in DB (`source_file` set). Replaces `_get_unprocessed_runsheets`. |
| `app/services/sync/pdf_router.py` | For each PDF: open with pdfplumber once, classify (`is_for_driver`), extract date from page header, move to `<RUNSHEETS_DIR>/<YYYY>/<MM-Month>/DH_DD-MM-YYYY.pdf` (or `<RUNSHEETS_DIR>/_other/<original>` for non-Daniel), return canonical path + metadata. |
| `app/services/sync/db_importer.py` | Calls existing `RunSheetImporter` and `extract_payslips` **as library functions** (no subprocess). Returns counts. Maps `RunSheetImporter` exceptions to typed errors. |
| `app/services/sync/pay_sync.py` | The pay UPDATE. **One** implementation. Replaces three duplicates. |
| `app/services/sync/state_store.py` | New table `sync_runs (id, started_at, finished_at, trigger, status, runsheets_downloaded, runsheets_imported, payslips_imported, jobs_synced, errors_json)` + helpers. |
| `app/services/sync/notifier.py` | Single notification entry point. Decides on type: success / new-files / error / watchdog. |
| `app/services/sync/scheduler.py` | Replaces the `schedule` library. Uses APScheduler with a SQLAlchemy job store (so schedules survive restarts). |
| `app/routes/api_sync.py` | Thin wrappers around orchestrator. Replaces `api_data.run-master-sync`, `api_data.periodic-sync/*`, `api_upload.process-local`, `api_upload.hybrid-sync`. |

`scripts/sync_master.py` becomes a 5-line wrapper that imports `run_sync` and calls it. Cron keeps working without code change to crontab.

`scripts/production/download_runsheets_gmail.py` shrinks to a thin CLI wrapper around `email_ingestor` + `pdf_router` + `db_importer`. Subject-regex skipping in `--missing` is **deleted**.

---

## 2. The single sync orchestrator

```python
# app/services/sync/orchestrator.py  (sketch, not final code)

class SyncTrigger(Enum):
    AUTO = 'auto'         # scheduler tick
    MANUAL = 'manual'     # /api/sync/run
    UPLOAD = 'upload'     # /api/upload/files
    WATCHDOG = 'watchdog' # 23:00 health check
    CRON = 'cron'         # legacy entry point

class SyncScope(Enum):
    RUNSHEETS = 'runsheets'
    PAYSLIPS = 'payslips'
    BOTH = 'both'

@dataclass
class SyncResult:
    run_id: int
    runsheets_downloaded: int
    runsheets_imported: int
    payslips_downloaded: int
    payslips_imported: int
    jobs_synced: int
    errors: list[str]
    tomorrow_present: bool

def run_sync(trigger: SyncTrigger, scope: SyncScope = SyncScope.BOTH,
             dry_run: bool = False) -> SyncResult:
    """Single entry point. All three flows call this."""
    with sync_lock(trigger):           # advisory file lock — see §5
        run_id = state_store.start_run(trigger)
        result = SyncResult(run_id=run_id, ...)
        try:
            if scope in (RUNSHEETS, BOTH):
                result += _do_runsheets(dry_run)
            if scope in (PAYSLIPS, BOTH) and _payslip_window_open():
                result += _do_payslips(dry_run)
            result.tomorrow_present = is_tomorrow_present()
        except Exception as e:
            result.errors.append(str(e))
            log.exception('sync failed')
        finally:
            state_store.finish_run(run_id, result)
            notifier.maybe_notify(result, trigger)
        return result
```

`_do_runsheets()`:

1. `pdfs = email_ingestor.fetch_runsheets(since=newest_db_date - 1 day)`
2. `pdfs += local_ingestor.scan_unimported(Config.RUNSHEETS_DIR)`
3. `for pdf in pdfs: routed = pdf_router.route(pdf)`
4. `for routed in driver_pdfs(routed): db_importer.import_runsheet(routed.path)`

Crucially: **no stdout sniffing**. All counts come back as typed return values.

---

## 3. Retry policy

Keep it simple — schedule, not exponential-backoff math sprinkled across the codebase.

- **APScheduler** runs `run_sync(AUTO)` at the user-configured `sync_start_time` and every `sync_interval_minutes` thereafter, **stopping when `is_tomorrow_present()` returns True**.
- The orchestrator itself does *not* retry. Each scheduled tick is the retry.
- One-shot retry-on-Gmail-rate-limit handled inside `email_ingestor` (try once, sleep 2s, try once more). Rate-limit retries are not in the orchestrator's responsibility.
- **23:00 watchdog**: APScheduler runs `night_watchdog()` daily. If `not is_tomorrow_present()` → notifier sends a "tomorrow's runsheet still missing" email/push. This is the loud-failure mode.

---

## 4. Multi-PDF handling (David's format)

Move the driver-name decision to **one place**: `pdf_router.classify(pdf_path)`.

```python
class PdfClassification(Enum):
    DRIVER_RUNSHEET = 'driver'        # Daniel's, import
    OTHER_DRIVER    = 'other'         # someone else's, archive
    PAYSLIP         = 'payslip'
    UNKNOWN         = 'unknown'

def classify(pdf_path: Path) -> tuple[PdfClassification, dict]:
    """Open PDF once, look at HEADER lines (first 2 lines of each page).
    Return classification + metadata (date, page_count, driver_pages)."""
```

Rules:

- A PDF is a *driver runsheet* iff `find_driver_pages(pdf, "Daniel Hanson")` returns ≥ 1 page (current implementation, kept).
- Otherwise → `OTHER_DRIVER` → moved to `<RUNSHEETS_DIR>/_other/<original-name>` (we keep them, in case classification was wrong, but they never get imported).
- Replaces the current `manual/` directory which is a dead-end.

David's email arrives with 12 PDFs:

1. Email ingestor downloads all 12 to `<RUNSHEETS_DIR>/_inbox/`.
2. Router classifies each → 1 driver, 11 other.
3. Driver one is renamed to `DH_DD-MM-YYYY.pdf` and moved to year/month folder.
4. The 11 others are moved to `_other/`.
5. `_inbox/` is empty at the end.

Idempotent: re-running the email ingestor with the same Gmail message-id will hit `_inbox/` again, but the router moves files away on each run; if a renamed `DH_*.pdf` already exists with the same date, the new one is dropped (after sha256 compare to be safe).

---

## 5. Concurrency

Single advisory lock for the orchestrator:

```python
LOCK_PATH = Path(Config.DATA_DIR) / '.sync.lock'

@contextmanager
def sync_lock(trigger):
    with open(LOCK_PATH, 'w') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SyncBusy(f"Sync already running, refused {trigger}")
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
```

- File lock works for both in-process scheduler and separate cron-launched Python process.
- Manual sync button shows "Sync already running" instead of starting a second run.
- Manual upload waits for the lock (short timeout, e.g. 30s) before importing — orchestrator processes uploaded files as part of the next run.

---

## 6. Sender / subject handling

Replace the `--missing` subject regex completely. New Gmail query (one query, both senders, no date parsing):

```
has:attachment filename:pdf
  (subject:"run sheet" OR subject:"runsheet" OR subject:"run sheets"
   OR filename:runsheet OR filename:run_sheet)
  newer_than:14d
```

Rationale:

- Gmail's `subject:"run sheet"` is case-insensitive and substring — matches `"WARRINGTON - RUN SHEETS"`, `"warrington - Run Sheets"`, `"Warrington Run Sheets - Monday"`, etc.
- `filename:runsheet` catches anything with `Runsheet_*.pdf` attachments regardless of subject.
- **No filtering by sender**. The router decides what's relevant from PDF content, not the email metadata.
- Backfill option: `--since YYYY-MM-DD` (date arg drives the Gmail `after:` filter, not subject parsing).

---

## 7. Configuration & paths

Everything via `Config`:

- `RUNSHEETS_DIR`, `PAYSLIPS_DIR`, `DATABASE_PATH` — already exist.
- New: `INBOX_DIR = RUNSHEETS_DIR / '_inbox'`, `OTHER_DIR = RUNSHEETS_DIR / '_other'`, `UPLOADS_DIR = Config.DATA_DIR / 'uploads/pending'`.
- Replace bare `data/database/payslips.db` literals in `sync_helpers.py` and `sync_master.py` with `Config.DATABASE_PATH`.
- Replace `data/processing/manual` with `Config.UPLOADS_DIR` (single path).

User-tunable settings (all already in DB or about to be):

| Key | Meaning |
|---|---|
| `sync_start_time` | First auto-sync of the evening (default `19:00`) |
| `sync_interval_minutes` | Retry cadence (default `15`) |
| `sync_window_end_time` | When to stop auto-retrying for the night (default `23:00`) |
| `watchdog_time` | When the watchdog runs (default `23:00`) |
| `payslip_sync_day` / `payslip_sync_start` / `payslip_sync_end` | unchanged |
| `notification_recipient` | unchanged |
| `notify_on_success` / `notify_on_error` / `notify_on_new_files` | mutually exclusive radio rather than three booleans |

---

## 8. Single source of truth

`is_tomorrow_present()` is the only authority. Everything derived:

- `current_state` is computed each render from `sync_runs` (latest row) — no instance variable.
- `runsheet_completed_today` is computed from `is_tomorrow_present()`.
- `next_sync_estimate` is computed from APScheduler's job store.

The flag soup on `PeriodicSyncService` is deleted.

---

## 9. Surfacing failures to the UI

`templates/settings/sync.html` becomes:

1. **Today's status banner**: green if tomorrow's runsheet present; amber if not but window is still open; red if past `watchdog_time` and still missing.
2. **Last 7 sync runs** table from `sync_runs`: trigger, status, downloaded, imported, errors.
3. **"Run Sync Now" button** — calls `POST /api/sync/run`, returns the new `run_id`, page polls `GET /api/sync/runs/<id>` for progress.
4. **Live log tail** — keep the existing `logs/sync.log` view, but every sync writes a single structured line per run with `run_id` so the log is filterable.
5. **Manual upload** — same UI, but progress comes back via the orchestrator's `run_id`, not a fire-and-forget thread.

---

## 10. Testability

All three flows go through `run_sync(trigger, scope)`. Tests can:

- Patch `email_ingestor.fetch_runsheets` to return canned `(filename, bytes)` pairs.
- Patch `pdf_router.classify` to return canned classifications without opening PDFs.
- Patch `db_importer.import_runsheet` to count calls.
- Drive end-to-end with the real DB on a temp file.

Test matrix:

1. Holly single PDF, subject `"MONDAY 9th MARCH 2026"` → 1 import.
2. David multi PDF (12), one Daniel page → 1 import + 11 archived to `_other/`.
3. David multi PDF, no Daniel page → 0 imports + 12 archived; orchestrator returns success but `tomorrow_present=False` — watchdog fires.
4. Email empty (Gmail returned 0 messages) → 0 imports, no error.
5. Gmail auth expired → typed `EmailAuthError`, error notification fires.
6. Manual upload of historical PDF → routed to correct `<YYYY>/<MM-Month>/DH_DD-MM-YYYY.pdf`, `manually_uploaded=1`.
7. Two sync triggers concurrently → second gets `SyncBusy`.
8. Re-running an already-processed PDF → 0 new jobs (importer exit-code-2 path now returns `{"new_jobs": 0}` from a function call).
9. Watchdog at 23:00 with `is_tomorrow_present()=False` → notification sent once, not on every poll.
10. Pay sync runs idempotently — second run produces 0 updates.

A `tests/sync/` package can hold these alongside the existing pytest setup.

---

## 11. Monitoring / alerting

Three notification triggers, in this order of importance:

1. **Watchdog miss** (loud) — `night_watchdog()` at 23:00 finds no tomorrow runsheet → email + (optional) Pushover/ntfy push.
2. **Hard error during a run** — `EmailAuthError`, `DatabaseError`, `IOError on RUNSHEETS_DIR`. Sent immediately, with `run_id` and link to the log.
3. **New jobs imported** — quiet success email summarising counts (existing behaviour, kept under `notify_on_success`).

`notifier.maybe_notify(result, trigger)` is the only emitter. The current `_should_notify` matrix is replaced by:

```python
def maybe_notify(result, trigger):
    if result.errors:
        send_error(result, trigger)
    elif trigger == WATCHDOG and not result.tomorrow_present:
        send_watchdog(result)
    elif (result.runsheets_imported + result.payslips_imported) > 0 and prefs.notify_on_success:
        send_success(result, trigger)
    # silent otherwise
```

---

## 12. What gets deleted

- `app/services/separated_sync.py` (unused).
- `_sync_recent_runsheets`, `_sync_recent_payslips`, `_should_sync` in `periodic_sync.py` (unused).
- `app/services/runsheet_sync_service.py` (third pay-sync copy).
- `attempt_gmail_sync`, `process_all_local_files`, `process_manual_uploads`, `hybrid_sync` in `api_upload.py` (replaced by orchestrator).
- `--missing` subject-regex code path in `download_runsheets_gmail.py:566-687`.
- `data/processing/manual/` directory pattern (replaced by `Config.UPLOADS_DIR` + orchestrator handoff).
- `scripts/organize_uploaded_runsheets.py`, `scripts/sync_runsheets_with_payslips.py` references in `api_upload.py:389-402` (broken anyway).

---

## 13. Open questions for Daniel

1. **Notification channel**: keep Gmail-API email only, or add Pushover/ntfy? Watchdog warrants something more visible than another email.
2. **`_other/` retention**: keep the non-Daniel PDFs forever, or auto-prune after 30 days?
3. **Manual upload of payslips**: today's UI funnels both runsheets and payslips through `/api/upload/files`. OK to keep one endpoint, or split?
4. **Auto-sync on dev box**: should the in-process scheduler still run on the dev workstation, or should `AUTO_SYNC_ENABLED=False` be the default in dev (cron handles prod, dev is manual-only)?
