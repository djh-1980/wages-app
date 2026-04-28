# TVS TCMS — Audit & Roadmap Progress

**Session:** 20 Apr 2026 (late evening) → 21 Apr 2026 (00:14 GMT+1)
**Working docs:** `AUDIT_REPORT.md`, `ROADMAP.md` at repo root

---

## Snapshot

- **Phase 1 (Critical fixes) — 100 % done.** 8/8 shipped, smoke-tested.
- **Phase 2 (Polish & stability) — 7/10 done.** The high-impact items landed; three grind/risk items deferred.
- **Phase 3 (Testing & monitoring) — not started.**
- **Phase 4 (Features) — not started.**

App boots cleanly at v2.7.0, 294 routes registered, migrations 001-008 applied, dev server exercised live from iPhone.

---

## Phase 1 — shipped ✅

| # | Task | Where |
|---|---|---|
| 1.1 | CSRF header on missing-jobs "Add Selected Jobs" POST | `static/js/missing-jobs.js:175-179` |
| 1.2 | Removed `SESSION_COOKIE_SECURE = False` override so prod cookies are HTTPS-only | `app/__init__.py:49-54` |
| 1.3 | HMRC sandbox blueprint gated on `HMRC_ENVIRONMENT != 'production'` | `app/__init__.py:184-193` |
| 1.4 | Full WEB_APP_VIA_SERVER HMRC fraud-prevention headers (client IP from X-Forwarded-For, vendor IP cached from ipify, browser context captured via JS → Flask session) | new `app/services/hmrc_fraud_headers.py`, new `static/js/hmrc-fraud-headers.js`, new `/api/hmrc/fraud-headers/record` endpoint; wired into `hmrc.html` + `mtd_sandbox.html` |
| 1.5 | Deleted legacy 2611-line `new_web_app.py`; fixed `scripts/utilities/deploy_to_debian.sh` gunicorn entrypoint | |
| 1.6 | Removed non-existent `schedule.once()` call in `pause_sync()` — auto-resume already works via `sync_latest()` check | `app/services/periodic_sync.py:197-210` |
| 1.7 | HMRC digital-records lock: migration 007 adds `locked_at`, `period_start_date`, `period_end_date` to `hmrc_submissions`; `app/services/hmrc_lock.py` enforces 409 on edit/delete of expenses in a submitted period; `_store_submission` records period + calls `lock_submission` on success | migration 007, new `hmrc_lock.py`, `api_expenses.py`, `api_hmrc.py:_store_submission` |
| 1.8 | Runsheet-importer exit code 2 for "no new jobs" (was 1 = treated as failure); periodic_sync treats code 2 as info → stops spamming `error.log` | `scripts/production/import_run_sheets.py:2613`, `app/services/periodic_sync.py:521-525` |

### Verified live
- `POST /api/payslips/add-missing-jobs 200` — 78 jobs committed from one payslip via the fixed modal.
- `POST /api/expenses/upload-receipt 200` → `POST /api/expenses/add 200` → receipt viewable — full iPhone camera flow working.

---

## Phase 2 — 7/10 done

| # | Task | Status | Where |
|---|---|---|---|
| 2.1 | Inline-styles cleanup (98 matches, 12 templates) | ⏸ deferred | — |
| 2.2 | iOS camera receipt upload rebuild (native `capture="environment"` + FileReader thumbnails) | ✅ | `templates/expenses.html:305-355`, `static/js/expenses.js` ~75 LOC new / 135 LOC deleted, `static/css/expenses.css` +`.receipt-thumb` |
| 2.3 | `periodic_sync` logger now rotates (10 MB × 5); removed duplicate FileHandler | ✅ | `app/logging_config.py:108-125`, `app/services/periodic_sync.py:79-81` |
| 2.4 | 8 new DB indexes on expenses, recurring_templates, hmrc_submissions, run_sheet_jobs(date,status), job_items(client), verbal_pay_confirmations, email_audit_log | ✅ | migration `008_performance_indexes.sql` |
| 2.5 | Replace 28 bare `except:` with typed + logged | ⏸ deferred | 14 files |
| 2.6 | SQLi fix in PDF custom-report DNCO endpoint — year/month now `?` placeholders, both branches pass the param list | ✅ | `app/routes/api_data.py:1987-2016` |
| 2.7 | Move `init_database()` DDL into migrations | ⏸ deferred | `app/database.py:34-269` |
| 2.8 | Branded 403/404/500 error pages + JSON fallback for `/api/` | ✅ | new `templates/errors/error.html`, `app/__init__.py:205-242` |
| 2.9 | 11 one-shot scripts archived with README | ✅ | `legacy_archive/scripts_one_shots_20260420/` |
| 2.10 | CSRF audit across all JS — fixed 6 missing `X-CSRFToken` headers across 3 files | ✅ | `static/js/mileage-batch-estimation.js` (4), `weekly-summary.js` (1), `runsheets.js` (1) |

### Bonus
- Date-sort fix in `get_latest_runsheet_date()` — filters out 68 malformed `DD/MM/YY` rows that were sorting *above* real `DD/MM/YYYY` rows because `"26" > "2026"` lexicographically. Explains why sync log occasionally showed a March date as "latest". `app/services/sync_helpers.py:27-34`.

---

## What's left

### Phase 2 deferred
- **2.1 Inline-styles cleanup** — 98 matches across 12 templates. Biggest file: `templates/expenses.html` (21). Mechanical grind, ~1 day.
- **2.5 Bare except cleanup** — 28 occurrences in 14 files. Each one needs a read of context to choose the right exception type. ~2-3 h.
- **2.7 `init_database()` → migrations** — single source of truth for schema. ~1-2 h, medium risk (need the baseline migration to be correct for fresh deploys).

### Phase 3 — not started
- **3.1 pytest harness** — ~half a day to stand up + 10 smoke tests covering login, CSRF, fraud-headers endpoint, expense lock, HMRC submission happy path.
- **3.2 Golden-fixture parser tests** for 16 customer parsers — ~1.5 days.
- **3.3 HMRC sandbox end-to-end test** — ~1 day.
- **3.4 Expense CRUD + recurring-match tests** — ~4 h.
- **3.5 `periodic_sync.sync_latest()` unit test** with mocked subprocess — ~4 h.
- **3.6 DB backup cron + off-box copy** — ~4 h (confirm prod cron, add repo script + systemd timer, test restore).
- **3.7 Basic uptime/disk alerting** — ~2 h.
- **3.8 `/healthz` + `/readyz` endpoints** — ~1 h.

### Phase 4 — not started (features)
Top 3 ROI per audit:
- **4.1 Real-time tax estimator dashboard widget** — ~1-2 days. Uses existing payslip + expense data; shows "You owe HMRC ≈ £X this tax year". No new dependencies. Highest user value per LOC.
- **4.2 SMS runsheet notifications** (Twilio) — ~0.5 day. Needs Twilio account + env var.
- **4.3 OCR receipt auto-categorisation** — ~4-6 days. Depends on 2.2 (iOS camera, now done ✓). Significant effort but very high sole-trader value.

---

## Known unresolved items (not yet fixed)

1. **`scripts/utilities/deploy_to_debian.sh` specifies 2 gunicorn workers.** The in-process `periodic_sync` thread would run twice under 2 workers. Prod is actually running 1 worker (per the `fix_production.sh` migration), so not an active issue, but the deploy script is wrong. Fix: drop to 1 worker or move the scheduler to a separate systemd unit.
2. **`HMRC_REDIRECT_URI` default in `app/config.py:71`** points to port 5000; dev server runs on 5001. Minor — only matters if `.env` is missing.
3. **68 malformed `DD/MM/YY` rows** in `run_sheet_jobs` are now filtered out of the "latest date" lookup, but still exist in the table. One-off data cleanup job to convert them to `DD/MM/YYYY` would be nice.
4. **`logs/errors.log` (plural) duplicates `error.log`** — both get ERROR-level entries but from different handlers. Consolidate under one.
5. **MTD compliance outstanding** (for production flip only):
   - Fraud-prevention headers done ✓ but untested against live HMRC.
   - Lock-after-submission done ✓ but UI doesn't yet show a "locked" badge on expense rows — server refuses the edit, but the frontend currently just shows a generic error.
   - Software-notice in app footer not verified against MTD checklist.

---

## Quick restart cheat-sheet

```bash
# From repo root
./start_web.sh             # dev server on :5001
# Hit in Safari: http://192.168.4.237:5001/expenses (your LAN IP + port)

# Run migrations manually
./venv/bin/python -c "from app.services.migration_runner import MigrationRunner; print(MigrationRunner().run_migrations())"

# Boot smoke test
./venv/bin/python -c "from app import create_app; print(len(list(create_app().url_map.iter_rules())), 'routes')"
```

---

## Pickup points for tomorrow

Easiest starting points, in order of ROI:

1. **Phase 4.1 tax estimator dashboard** — highest visible value, data is all already in the DB, low risk.
2. **Phase 3.1 pytest harness** — before building more features, lock in what works today so regressions can't sneak in.
3. **2.7 init_database → migrations** — unblocks any future schema work.
4. **2.5 bare excepts** — hygiene.
5. **2.1 inline styles** — cosmetic grind; do it in the background while thinking about feature work.
