# HMRC Cumulative Period Summary - Audit (Phase 2.1)

**Date:** 2026-04-28
**Reference spec:** Self-Employment Business (MTD) API v5.0, cumulative
period summary endpoints under
`/individuals/business/self-employment/{nino}/{businessId}/period/cumulative/{taxYear}`.

This audit documents the current per-period submission flow and what
must change to migrate to the cumulative model. No code is changed by
this audit.

## 1. Current submission flow (file:line references)

### API client
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_client.py:378-397`
  `HMRCClient.create_period(nino, business_id, tax_year, period_data)` —
  POSTs to the **legacy** non-cumulative endpoint
  `/individuals/business/self-employment/{nino}/{business_id}/period`.
  Tax year not in URL; derived from `periodDates` in the body.
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_client.py:399-413`
  `update_period()` — PUT amendments to per-period endpoint.
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_client.py:322-351`
  `get_period_summary()` / `list_periods()` — GET legacy per-period.
- API version dispatch hard-codes v5.0 for self-employment endpoints
  at `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_client.py:60-76`.
  v5.0 also covers the cumulative routes — no version change needed.

### Period maths / mapping
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_mapper.py:18-58`
  `calculate_quarterly_periods(tax_year)` — returns Q1..Q4 with
  per-quarter `start_date` / `end_date`. Q2 returns Jul–Oct, NOT
  Apr–Oct. This is the key per-quarter assumption that must change.
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_mapper.py:165-191`
  `get_income_for_period(start, end)` — filters payslips by their
  `period_end` between `start` and `end`. For cumulative this needs
  a tax-year-start anchor (always 6 April) instead of `start_date`.
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_mapper.py:194-254`
  `build_period_submission(tax_year, period_id, from_date, to_date)`
  builds a **per-quarter** payload:
  ```
  { periodDates: { periodStartDate, periodEndDate },
    periodIncome: { turnover, other },
    periodExpenses: {...} }
  ```
  Currently this is the legacy schema (matches HMRC's POST /period).
  HMRC's cumulative endpoint expects a **similar shape** but with the
  `periodStartDate` always equal to the tax-year start (06 April) and
  `periodEndDate` equal to the current quarter end, and figures that
  are running totals from 6 April.
- There is **no** `app/services/hmrc_period_calculator.py` — the only
  period maths is in `hmrc_mapper.py` above.

### Routes
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_hmrc.py:395-474`
  `GET /api/hmrc/period/preview` — preview only, builds payload via
  `HMRCMapper.build_period_submission`.
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_hmrc.py:477-587`
  `POST /api/hmrc/period/submit` — calls
  `client.create_period(...)` (legacy), records via
  `_store_submission(...)` into `hmrc_submissions`. Duplicate-check is
  on `(tax_year, period_id, nino, status='submitted')`.
- `_store_submission` already records `period_start_date` and
  `period_end_date` via the migration `007_hmrc_submission_lock.sql`,
  which the cumulative flow can re-use unchanged.

### UI
- `@/Users/danielhanson/CascadeProjects/Wages-App/templates/settings/hmrc.html:137-155`
  Quarterly Obligations tab — list rendered client-side from
  `loadObligations()` in `settings-hmrc.js`.
- `@/Users/danielhanson/CascadeProjects/Wages-App/static/js/settings-hmrc.js:243-296`
  `loadObligations()` renders one card per period with a "Submit"
  button calling `submitPeriod(periodId)`.
- `@/Users/danielhanson/CascadeProjects/Wages-App/static/js/settings-hmrc.js:418+`
  `submitPeriod()` opens the legacy submission flow which lives in
  `static/js/expenses.js`.
- `@/Users/danielhanson/CascadeProjects/Wages-App/static/js/expenses.js:1299-1304`
  builds preview URL `/api/hmrc/period/preview?...`.
- `@/Users/danielhanson/CascadeProjects/Wages-App/static/js/expenses.js:1472-1476`
  POSTs to `/api/hmrc/period/submit` with `{nino, business_id,
  tax_year, period_id, from_date?, to_date?}`.

### Database
- `hmrc_submissions` columns relevant here (migrations 004, 006, 007):
  `id, tax_year, period_id, nino, status, hmrc_receipt_id,
  submission_data (JSON), submission_date, period_start_date,
  period_end_date, locked_at`.
- No `submission_type` column today. We will add one
  (`type TEXT DEFAULT 'period'`) so cumulative rows can be
  distinguished without breaking the legacy lookup.

### Lock & fraud headers — already compliant, do NOT touch
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_lock.py`
  reads `period_start_date` / `period_end_date` directly — works for
  cumulative as long as we still write those columns.
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_fraud_headers.py`
  is invoked by `_make_request` for every call, so any new client
  method gets headers automatically.

## 2. Where the legacy POST /period is used

| Caller | Effect |
| --- | --- |
| `api_hmrc.submit_period` (route) | Direct user submission |
| `expenses.js` MTD modal | Submission UI |
| `settings-hmrc.js` Submit button | Routes through expenses.js |

Nothing else depends on `client.create_period`.

## 3. How quarterly figures are currently calculated — per-quarter

`build_period_submission` aggregates only the data falling in the
quarter's start–end window. Q2 contains Jul–Oct figures; Q3 contains
Oct–Jan; Q4 contains Jan–Apr. **This is the model HMRC has retired.**

For cumulative we must aggregate from `{tax_year}-04-06` up to the
quarter end:

| Period | Cumulative window |
| --- | --- |
| Q1 | 06 Apr → 05 Jul |
| Q2 | 06 Apr → 05 Oct |
| Q3 | 06 Apr → 05 Jan |
| Q4 | 06 Apr → 05 Apr (next yr) |

## 4. What needs to change

### API client (`hmrc_client.py`)
- Add `submit_cumulative_period(nino, business_id, tax_year, period_data)`
  POSTing to `.../period/cumulative/{taxYear}`.
- Add `get_cumulative_period(nino, business_id, tax_year)`
  GET on the same path.
- Both must accept the YYYY-YY tax-year format and pass it through to
  the URL (HMRC requires hyphen form).
- Keep `create_period` / `update_period` untouched for backwards
  compatibility, with a deprecation note.

### Calculation service (NEW `hmrc_cumulative_calculator.py`)
- `calculate_cumulative_totals(tax_year, period_end_date)` returning
  the dict shape HMRC expects:
  ```
  { periodDates: { periodStartDate: '<TY>-04-06',
                   periodEndDate: <period_end_date> },
    periodIncome: { turnover, other },
    periodExpenses: { ... cumulative running totals ... } }
  ```
- Re-uses `hmrc_mapper.map_expenses_to_hmrc_format` for category
  mapping but feeds it the **full** Apr–to-period_end window.
- Re-uses `get_income_for_period` with `start = '<TY>-04-06'`.
- Returns a side-channel `breakdown` (per-quarter contributions) for
  the UI to display "previous quarters' contributions".

### Routes (`api_hmrc.py`)
- New `POST /api/hmrc/period/cumulative/<tax_year>`:
  validates connection, calls calculator, calls
  `submit_cumulative_period`, stores into `hmrc_submissions` with
  `type='cumulative'` and the cumulative `period_start_date` /
  `period_end_date`, calls `lock_submission` on success.
- New `GET /api/hmrc/period/cumulative/<tax_year>`: returns the
  latest stored cumulative submission for the TY.
- Keep legacy `/period/preview` and `/period/submit` (deprecation
  comment only).

### UI
- `templates/settings/hmrc.html` Quarterly Obligations tab: replace
  the per-period Submit button with a "Submit Quarterly Update"
  panel that, on selecting an open obligation, shows:
  - Cumulative totals from `<TY>-04-06` to that obligation's
    `inboundCorrespondenceToDate`.
  - Breakdown table: previous quarters' contributions vs this quarter.
  - "Confirm and Submit" button calling the new cumulative endpoint.
- Submission JS: split off `static/js/hmrc-cumulative.js` rather than
  bolt onto `expenses.js`. Update existing `submitPeriod()` to open
  the new panel.
- After success, lock records is already handled server-side by
  `_store_submission` calling `lock_submission`, so no UI changes
  beyond confirmation.

### Tests
- New `tests/sync/test_hmrc_cumulative.py` per spec (Q1..Q4
  cumulative arithmetic, mocked HMRC submit, lock side effect, fraud
  header presence, GET returns latest).

### Schema (small addition)
- Migration `009_hmrc_submission_type.sql`:
  ```sql
  ALTER TABLE hmrc_submissions
      ADD COLUMN submission_type TEXT NOT NULL DEFAULT 'period';
  ```
  Existing rows stay `period`; new cumulative rows write
  `cumulative`. Lookup index in `008_performance_indexes.sql` does not
  need to change.

## 5. Constraints reconfirmed

- Numeric amounts: HMRC self-employment v5.0 cumulative uses
  **decimal pounds** (same as the legacy /period schema). No
  pounds→pence conversion required. Confirmed against the existing
  `map_expenses_to_hmrc_format` output.
- Tax year must be passed as `YYYY-YY` (e.g. `2025-26`) in the URL.
  `HMRCMapper.format_tax_year_for_hmrc` already handles
  `2025/2026 → 2025-26`.
- Fraud headers: untouched (handled in `_make_request`).
- Digital records lock: untouched (re-uses `period_start_date` /
  `period_end_date` already written by `_store_submission`).

## 6. Stop-point checklist (none triggered)

- ✅ Existing data model supports cumulative without restructuring —
  payslips/expenses are already date-indexed.
- ✅ Spec aligns with sandbox v5.0 — same headers, same auth, same
  field shape, only path + cumulative semantics differ.
- ⚠️ The other "Yes-with-evidence" items in the gap audit are out of
  scope for Phase 2.1; they will be addressed in subsequent phases
  per the user's instruction.

## 7. Implementation order (one commit per part)

1. Migration 009 + `hmrc_cumulative_calculator.py` + unit tests for
   the calculator (no HMRC calls).
2. `hmrc_client.submit_cumulative_period` + `get_cumulative_period`
   + mocked client tests.
3. New routes `POST/GET /api/hmrc/period/cumulative/<tax_year>` +
   route tests (mocked client).
4. UI: `templates/settings/hmrc.html` panel + new
   `static/js/hmrc-cumulative.js`.
5. Update `HMRC_PRODUCTION_CHECKLIST_GAP_AUDIT.md` and run full test
   suite.

End of audit.
