# Sync Migration Plan

**Strategy:** Strangle the existing sync flows one component at a time, lowest-risk first. Every step leaves the app working. No "big-bang" rewrite.

---

## What can stay as-is (no rewrite)

These are battle-tested and the redesign keeps them as library calls:

- `scripts/production/import_run_sheets.py` — the parsing engine. We expose `RunSheetImporter.import_run_sheet(path)` as a function call instead of via subprocess. No code change in this file (or only a `__main__` guard tidy).
- `scripts/production/extract_payslips.py` — same treatment.
- `scripts/production/camelot_runsheet_parser.py` — keep. Already correctly restricts to first 2 lines.
- `scripts/production/validate_addresses.py` — keep, called by orchestrator.
- `app/services/sync_helpers.py:get_latest_runsheet_date`, `get_latest_payslip_week`, `is_runsheet_for_tomorrow_present` — keep, now used as the single source of truth.
- The `settings` table and `SettingsModel` — keep.
- The Gmail OAuth + service-account auth in `download_runsheets_gmail.py` — extract to `email_ingestor.py` unchanged.

---

## What needs to be replaced

| Component | Replacement | Risk |
|---|---|---|
| `PeriodicSyncService` (`app/services/periodic_sync.py`, 1094 lines) | `app/services/sync/orchestrator.py` + `scheduler.py` | Medium |
| `scripts/sync_master.py` | 5-line wrapper around orchestrator | Low |
| `app/services/separated_sync.py` | Delete | None (unused) |
| `app/services/runsheet_sync_service.py` | `app/services/sync/pay_sync.py` | Low |
| `download_runsheets_gmail.py --missing` subject-regex | `email_ingestor.fetch_runsheets()` (no subject parsing) | Low |
| `api_upload.process_single_runsheet` (broken organize/sync subprocess calls) | `orchestrator.ingest_uploaded_file(path)` | Medium |
| `_get_unprocessed_runsheets`, `_sync_recent_*` (dead code in `periodic_sync.py`) | Delete | None |
| Three copies of pay-sync UPDATE SQL | One copy in `pay_sync.py` | Low |
| Subprocess + stdout sniffing | Function calls returning typed values | Low |

---

## Rollout order

Each phase is independent, ships green, and is reversible.

### Phase 0 — Safety net (½ day)

Before touching code:

1. Snapshot prod DB (`payslips.db`) and `RUNSHEETS_DIR` (rsync to a dated folder).
2. Document current state of `settings` table.
3. Add a `git tag pre-sync-rebuild` on `main`.
4. Confirm `tests/` runs clean: `pytest -q`.

**Verify:** snapshot mountable, tag pushed, tests green.

### Phase 1 — Fix the deterministic bugs (½ day, no architecture change)

Lowest risk. These fixes pay for themselves immediately even if the rest of the migration stalls.

1. **Manual upload to NAS** — in `api_upload.process_single_runsheet`, after a successful import, copy the PDF from `data/processing/manual/...` to `<RUNSHEETS_DIR>/<YYYY>/<MM-Month>/DH_DD-MM-YYYY.pdf` using the date already extracted by the importer. Drop the calls to the missing `organize_uploaded_runsheets.py` and `sync_runsheets_with_payslips.py`.
2. **`--missing` subject regex** — replace the date-from-subject parser with: download every email returned by the Gmail query, let `organize_pdf` sort it. Subject filtering removed.
3. **`AUTO_SYNC_ENABLED` default** — set to `False` on prod (`.env`) so cron is the single trigger; set to `True` only on dev. Prevents the dual-orchestrator race today, ahead of the redesign.

**Tests:**

- `tests/sync/test_manual_upload_to_nas.py` — uploads a fixture PDF, asserts the file ends up under `RUNSHEETS_DIR`.
- `tests/sync/test_missing_no_subject_date.py` — feeds a fake Gmail message with subject `"Warrington - Run Sheets"` (no date), asserts the PDF is downloaded.

**Verify:** drag-and-drop a historical PDF on settings page → file shows under `RUNSHEETS_DIR`. Force-run cron — David-style email gets imported.

### Phase 2 — Build the orchestrator alongside the old code (1–2 days)

New code only. Old code untouched. Feature flag `USE_NEW_SYNC=False` controls which path runs.

1. Add `app/services/sync/` package with:
   - `state_store.py` + migration `migrations/008_sync_runs.sql` (table `sync_runs`).
   - `email_ingestor.py` (lift Gmail logic out of `download_runsheets_gmail.py`).
   - `local_ingestor.py` (lift `_get_unprocessed_runsheets`).
   - `pdf_router.py` (lift `organize_pdf` + `find_driver_pages`).
   - `db_importer.py` (calls `RunSheetImporter` + `extract_payslips_from_file`).
   - `pay_sync.py` (one copy of the UPDATE).
   - `notifier.py` (one copy of notification logic).
   - `orchestrator.py` (`run_sync`, `ingest_uploaded_file`, `night_watchdog`, `is_tomorrow_present` re-export).
2. Add `app/routes/api_sync_v2.py`:
   - `POST /api/sync/run`
   - `POST /api/sync/upload`
   - `GET /api/sync/runs/<id>`
   - `GET /api/sync/status`
3. Wire APScheduler in `app/__init__.py` behind the flag, with a SQLAlchemy/SQLite job store at `data/database/scheduler.db`.

**Tests:**

- `tests/sync/test_orchestrator_holly_single.py`
- `tests/sync/test_orchestrator_david_multi.py`
- `tests/sync/test_orchestrator_concurrency_lock.py`
- `tests/sync/test_orchestrator_watchdog.py`
- `tests/sync/test_pay_sync_idempotent.py`

**Verify:** `USE_NEW_SYNC=True python -c "from app.services.sync.orchestrator import run_sync; ..."` runs end-to-end on a copy of the prod DB.

### Phase 3 — Cut the manual-button trigger over (1 hr)

Lowest-traffic flow, easiest rollback.

1. Change the **Run Sync Now** button in `templates/settings/sync.html` to call `POST /api/sync/run` instead of `/api/data/run-master-sync`.
2. Keep `/api/data/run-master-sync` working for now (cron still uses `sync_master.py`).

**Verify:** click the button on dev → `sync_runs` row appears, status `completed`, log line written.

### Phase 4 — Cut the upload trigger over (1 hr)

1. Change `api_upload.process_single_runsheet` to call `orchestrator.ingest_uploaded_file(file_path)` instead of `subprocess.run(import_run_sheets...)`.
2. Delete the broken `organize_uploaded_runsheets.py` / `sync_runsheets_with_payslips.py` subprocess calls (made redundant by Phase 1, now formally removed).

**Verify:** drag-drop on dev → file appears at canonical NAS path, DB shows job, `manually_uploaded=1`.

### Phase 5 — Cut the cron / auto trigger over (½ day)

The riskiest cut, done last when the orchestrator is proven.

1. Make `scripts/sync_master.py` a 5-line wrapper:
   ```python
   from app.services.sync.orchestrator import run_sync, SyncTrigger
   result = run_sync(trigger=SyncTrigger.CRON)
   sys.exit(0 if not result.errors else 1)
   ```
2. On prod, flip `AUTO_SYNC_ENABLED=True` and rely on APScheduler in-process — **or** keep cron and disable APScheduler. Pick one. (Recommendation: keep cron initially; APScheduler is for dev convenience.)
3. Watch `sync.log` for one full evening cycle.

**Verify:** check the next-morning state of `sync_runs`. Tomorrow's runsheet present, watchdog row absent.

### Phase 6 — Delete the old code (½ day)

Only after Phase 5 has run cleanly for at least 7 days.

Delete:

- `app/services/periodic_sync.py`
- `app/services/separated_sync.py`
- `app/services/runsheet_sync_service.py`
- `app/services/sync_helpers.py:sync_payslips_to_runsheets` (replaced by `pay_sync`)
- Old `/api/data/periodic-sync/*` and `/api/data/run-master-sync` routes
- `_sync_recent_runsheets`, `_sync_recent_payslips`, `attempt_gmail_sync`, etc.
- `data/processing/manual/` (after one final scan to confirm empty)

Update:

- `app/routes/api_data.py` to drop the deleted routes.
- `templates/settings/sync.html` JS to drop calls to the removed endpoints.
- `app/__init__.py` to drop the `periodic_sync_service` import.

Remove `USE_NEW_SYNC` flag.

**Verify:** `pytest -q` green; full sync cycle clean.

---

## Rollback per phase

| Phase | Rollback |
|---|---|
| 1 | Revert the 3 commits. |
| 2 | Leave `USE_NEW_SYNC=False`; new code is dormant. |
| 3 | Restore `runMasterSyncManual()` JS to call `/api/data/run-master-sync`. |
| 4 | Restore `process_single_runsheet` to the Phase-1 subprocess version. |
| 5 | Restore old `scripts/sync_master.py`. Keep cron pointing at it. |
| 6 | Restore from `pre-sync-rebuild` tag. |

---

## Tests to write or update

New (under `tests/sync/`):

- `test_email_ingestor.py` — mocked Gmail, asserts no subject filtering.
- `test_pdf_router.py` — fixture PDFs (Holly single, David multi, payslip, garbage), asserts classification + canonical paths.
- `test_db_importer.py` — calls importer as library, asserts `new_jobs` count + `manually_uploaded` flag respected on re-import.
- `test_pay_sync.py` — first run updates N rows, second run updates 0, PayPoint Van Stock Audit set to £0.
- `test_orchestrator_*.py` — see test matrix in `SYNC_REDESIGN.md` §10.
- `test_watchdog.py` — frozen-time at 23:00 with empty DB → notifier called once.
- `test_concurrency.py` — two parallel `run_sync` calls → second raises `SyncBusy`.

Update:

- `tests/test_api_data.py` (if exists) to remove tests of deleted endpoints.

Coverage target: every public function on `orchestrator.py` has at least one test; every error path has at least one negative test.

---

## Verification commands

After each phase, run on the box you changed:

```bash
# Tests pass
pytest -q tests/sync/

# Orchestrator end-to-end (dry run)
python -c "from app.services.sync.orchestrator import run_sync, SyncTrigger; \
           print(run_sync(SyncTrigger.MANUAL, dry_run=True))"

# Tomorrow's runsheet present?
python -c "from app.services.sync.orchestrator import is_tomorrow_present; \
           print('tomorrow present:', is_tomorrow_present())"

# Sync runs visible
sqlite3 data/database/payslips.db \
  'SELECT id, trigger, status, runsheets_imported, started_at FROM sync_runs ORDER BY id DESC LIMIT 5;'

# Tail unified log
tail -n 50 logs/sync.log
```

---

## Estimated effort

| Phase | Effort |
|---|---|
| 0 — Safety net | ½ day |
| 1 — Deterministic-bug fixes | ½ day |
| 2 — Build orchestrator (flagged off) | 1–2 days |
| 3 — Manual button cut-over | 1 hr |
| 4 — Upload cut-over | 1 hr |
| 5 — Cron / auto cut-over | ½ day |
| 6 — Delete old code | ½ day |
| **Total** | **~4–5 days of focused work**, but Phase 1 alone unblocks the worst pain in half a day |

---

## Decision points before starting

The redesign doc (`SYNC_REDESIGN.md` §13) lists the open questions. Before Phase 2 begins, lock in:

1. APScheduler vs keeping `schedule` library (recommend APScheduler — durable jobs).
2. Cron vs in-process scheduler on prod (recommend cron-only on prod, in-process on dev).
3. Pushover/ntfy for watchdog, or Gmail-only.
4. `_other/` retention policy (recommend 30 days with a daily prune job).
5. Whether to keep `USE_NEW_SYNC` as a permanent kill-switch or remove after Phase 6 (recommend remove).
