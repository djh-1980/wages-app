# TVS TCMS – Forward Roadmap

Companion to `AUDIT_REPORT.md` (20 April 2026). Parts 1 & 2 live there; Parts 3 & 4 are below.

---

## PART 3 — Future Feature Ideas

Each feature is scored **Value (1–10)** (impact on a sole-trader EPOS engineer's day-to-day), **Complexity (1–10)** (engineering effort), and **Strategic importance** (H/M/L for the business).

| # | Feature | Value | Complexity | Strategic | Notes |
|---|---|---|---|---|---|
| 1 | **Automatic mileage tracking** (phone GPS → daily miles, auto-fill runsheet) | 9 | 7 | H | Biggest pain point. Could be a cheap PWA using `navigator.geolocation` + background sync, or integrate Life360/Google Maps Timeline CSV. |
| 2 | **OCR receipt auto-categorisation** (scan → merchant + amount + category) | 9 | 6 | H | Pair Tesseract / Apple Vision + the existing recurring-template matcher; huge expense-entry time saver. |
| 3 | **Real-time tax estimator widget** on dashboard (current tax owed based on YTD income/expenses) | 8 | 4 | H | Uses data already in the DB; pure calculation. Good comfort-blanket before MTD Q1. |
| 4 | **Photo documentation per job** (attach site photos, visible on runsheet row) | 8 | 5 | M | EPOS engineers often need proof-of-visit. New table `job_photos` + simple upload UI. |
| 5 | **SMS push notifications** for new runsheets (Twilio / GOV.UK Notify) | 7 | 3 | M | Currently email-only. Low complexity if Twilio account exists. |
| 6 | **Google Maps route optimisation** (TSP across today's jobs) | 7 | 6 | M | Foundations are in `api_route_planning.py`; finishing an optimised tour and deep-linking to Apple/Google Maps would be high-impact. |
| 7 | **Offline mode** (PWA with IndexedDB for runsheet + job status edits when on-site) | 7 | 8 | M | Needed when on-site with no signal. Non-trivial: requires service worker + sync-queue. |
| 8 | **Vehicle maintenance tracker** (MOT, service intervals, reminders) | 6 | 3 | M | Small table + dashboard reminders. Cheap win. |
| 9 | **Tool / equipment inventory** (serials, allocation to jobs) | 5 | 4 | L | Nice-to-have, not a top sole-trader concern. |
| 10 | **Time tracking per job** (start/stop timer on job card, feed time-on-site into reports) | 6 | 3 | M | Useful for validating agreed rates. |
| 11 | **Client invoicing module** (if ever billing outside Paypoint/SASER payroll) | 4 | 7 | L | Low priority while 100 % agency work. |
| 12 | **Weather integration** for planning (rain warning → reschedule outdoor installs) | 4 | 2 | L | Free Met Office API. Dashboard widget only. |
| 13 | **Voice-to-text job notes** | 5 | 3 | L | iOS Safari has native dictation — probably no code change required. |
| 14 | **Bank reconciliation improvements** (match payslip deposits vs bank, flag missing) | 6 | 4 | M | Builds on the recurring-templates matcher. |
| 15 | **Accounting-software export** (FreeAgent / Xero CSV or API) | 5 | 5 | L | Probably unnecessary if MTD submissions go direct from TCMS. |
| 16 | **Dashboard widgets** (customisable KPIs — jobs this week, earnings vs target, YTD tax, miles) | 7 | 4 | M | Good framing for future features. |

### Top 3 by value ÷ complexity (ROI)

1. **Real-time tax estimator** (8/4 = 2.0) — essentially free given existing data.
2. **SMS notifications** (7/3 = 2.33) — tiny codebase change.
3. **Vehicle maintenance tracker** (6/3 = 2.0) — trivial schema, big peace-of-mind.

### Top 3 by strategic value

1. Automatic mileage tracking
2. OCR receipt auto-categorisation
3. Real-time tax estimator

---

## PART 4 — Plan of Action

All effort estimates are for a solo engineer pair-programming with an AI assistant. Estimates are rough and deliberately conservative.

### Phase 1 — Critical Fixes (this week, ~1 day total)

MTD Q1 deadline is 5 August 2026. Everything below is low-risk, high-urgency.

| # | Task | Effort | Dependencies | Definition of Done |
|---|---|---|---|---|
| 1.1 | Fix "Add Selected Jobs" CSRF bug | 15 min | none | `missing-jobs.js` uses `getJSONHeaders()`; page loads `csrf-helper.js`; manual retest returns 200 and inserts rows into `run_sheet_jobs` |
| 1.2 | Fix session cookie Secure override | 10 min | none | Delete lines 52-55 of `app/__init__.py`; confirm `SESSION_COOKIE_SECURE` is True when `FLASK_ENV=production` |
| 1.3 | Gate `sandbox_bp` and `csrf.exempt` behind `HMRC_ENVIRONMENT != 'production'` | 30 min | none | Blueprint not registered when env is production; integration test via env flip |
| 1.4 | Add fraud prevention headers to HMRC client | 3–4 h | HMRC spec | All live HMRC requests include `Gov-Client-*` + `Gov-Vendor-*` per [HMRC Fraud Prevention guidance]; unit test asserts presence |
| 1.5 | Delete `new_web_app.py` | 5 min | none | File removed; `grep -r new_web_app` returns nothing; app still boots |
| 1.6 | Fix `schedule.once()` AttributeError in pause-with-duration | 10 min | none | Replace with `schedule.every().day.at(time).do(...).tag('auto-resume')` + clear on resume; manual test |
| 1.7 | Lock-after-submission flag on digital records (MTD compliance) | 3 h | 1.4 | Add `locked_at` on `hmrc_submissions`; UI hides edit buttons; API refuses writes when any covering submission is locked |
| 1.8 | Investigate "No jobs imported from DH_*.pdf" regression | 1–2 h | none | Either root-caused parser fix or confirmed those days genuinely had no Daniel jobs; fix or close |

**Phase 1 output:** working missing-jobs modal, MTD-compliant lock + fraud headers, production session safety, clean sandbox gating.

### Phase 2 — Polish & Stability (next 2 weeks, ~3–4 days)

| # | Task | Effort | Dependencies | Definition of Done |
|---|---|---|---|---|
| 2.1 | Inline-styles cleanup (§1.1 of audit) | 1 day | none | All 98 matches removed from the 12 templates; replaced by utility classes or `unified-styles.css` rules; visual diff unchanged |
| 2.2 | iOS camera receipt upload — decide & ship | 4 h | none | Either (a) extend allowlist + server-side convert to PDF via `pypdf`/`img2pdf`, or (b) remove camera UI. Works on iPhone Safari. |
| 2.3 | Centralise logging (rotate periodic_sync/error/hmrc) | 2 h | none | All FileHandlers use `setup_logging()`; max 10 MB × 5; drop duplicate `error.log` vs `errors.log` |
| 2.4 | Add indexes to `run_sheet_jobs`, `job_items`, `expenses` (migration `007_indexes.sql`) | 1 h | none | New migration committed and applied; `EXPLAIN QUERY PLAN` shows index use for report queries |
| 2.5 | Replace 28 bare `except:` with typed exceptions + `logger.error` | 3 h | none | `rg "except:\s*$" app/` returns 0 matches |
| 2.6 | Fix SQLi f-string in `api_data.py:1987-1989` (PDF custom reports) | 30 min | none | Values cast to `int()` before use or switched to `?` placeholders |
| 2.7 | Move `init_database` DDL into migrations (`007_…`, `008_…`) | 3 h | 2.4 | `database.py:init_database()` only creates `schema_migrations` table |
| 2.8 | Custom 404/500/403 error pages | 1 h | none | Branded, link back to dashboard |
| 2.9 | Delete redundant one-shot scripts in `scripts/` root; move to `legacy_archive/` | 30 min | none | `scripts/` root contains only active tools |
| 2.10 | Audit remaining JS POSTs for missing CSRF headers, fix in bulk | 2 h | 1.1 | All `fetch(..., {method:'POST'…})` calls go through `getJSONHeaders()` |

### Phase 3 — Testing & Monitoring (month 1, ~5–6 days)

| # | Task | Effort | Dependencies | Definition of Done |
|---|---|---|---|---|
| 3.1 | Bootstrap `pytest` + first 10 smoke tests (app boot, auth, key endpoints 200/401) | 1 day | none | `pytest` green; GitHub Actions CI running on push |
| 3.2 | Golden-fixture parser tests for 16 customer parsers | 1.5 days | 3.1 | One small PDF fixture per customer in `tests/fixtures/`; tests assert exact job rows |
| 3.3 | HMRC sandbox submission end-to-end test (mocked OAuth tokens) | 1 day | 3.1 | `pytest -m hmrc` submits a dummy period against sandbox and asserts receipt id; skipped by default in CI |
| 3.4 | Expense CRUD + recurring-match test suite | 4 h | 3.1 | Covers create / update / delete / category mapping / recurring template matching |
| 3.5 | `periodic_sync.sync_latest()` unit test with mocked subprocess | 4 h | 3.1 | Covers: no-op when paused, tomorrow-already-in-db, download-fails, import-fails |
| 3.6 | DB backup cron + off-box copy | 4 h | none | Hourly sqlite `.backup` + nightly rsync to secondary; `backup.log` shows activity; tested restore |
| 3.7 | Basic uptime + disk alerting (healthchecks.io or simple curl+cron) | 2 h | none | Ping on successful sync; alert email if sync hasn't run in 24 h or disk < 1 GB |
| 3.8 | Single consolidated `/healthz` + `/readyz` endpoints for external monitoring | 1 h | none | Returns JSON: db ok, gmail auth, disk free, sync age |

### Phase 4 — New Features (ongoing)

Ordered by ROI (value ÷ complexity):

| # | Feature | Effort | Dependencies |
|---|---|---|---|
| 4.1 | Real-time tax estimator dashboard widget | 1–2 days | none |
| 4.2 | SMS runsheet notifications (Twilio) | 0.5 day | Twilio account + env var |
| 4.3 | OCR receipt auto-categorisation (Tesseract / Apple Vision) | 4–6 days | 2.2 (camera upload working) |

Pick one at a time; each is a self-contained branch.

---

## Recommended Order of Work

1. Phase 1.1, 1.2, 1.5, 1.6 (low-risk cleanup + the CSRF fix that unblocks daily use) — **today**
2. Phase 1.3, 1.4, 1.7 (MTD compliance pre-work for production flip) — **this week**
3. Phase 1.8 (parser regression investigation) — **this week**
4. Phase 2 polish in any order — **next fortnight**
5. Phase 3 testing/monitoring — **before Q1 submission (August 2026)**
6. Phase 4 features — **post-Q1**

---

## Top 5 Immediate Actions (for PR summary)

1. **Fix CSRF header on `missing-jobs.js`** — single-line change restores the broken "Add Selected Jobs" flow. (`@/Users/danielhanson/CascadeProjects/Wages-App/static/js/missing-jobs.js:175-181`)
2. **Remove the `SESSION_COOKIE_SECURE = False` override** in `@/Users/danielhanson/CascadeProjects/Wages-App/app/__init__.py:52-55` — prod currently sends session cookies over HTTP.
3. **Gate the HMRC sandbox blueprint** behind `HMRC_ENVIRONMENT != 'production'` in `@/Users/danielhanson/CascadeProjects/Wages-App/app/__init__.py:158,187`.
4. **Add HMRC fraud-prevention headers** to `app/services/hmrc_client.py` before flipping to production — MTD will reject submissions without them.
5. **Delete `new_web_app.py`** and the orphaned one-shot scripts in `scripts/` root — reduces confusion and accidental-run risk.
