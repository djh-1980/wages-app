# HMRC MTD ITSA Production Checklist — Gap Audit

**Source:** `Software-Approvals-Production-Checklist-2026-04-01.docx` (HMRC, 1 Apr 2026)
**Audited app:** TVS TCMS / TVS Wages
**Audit date:** 28 Apr 2026
**Auditor:** Cascade (read-only audit, no code changed)

Daniel's profile (used to mark questions N/A):

- Self-employed sole trader (UTR 5155358938)
- Self-Employment income only — **no UK Property, no Foreign Property**
- Cash accounting basis only
- Standard quarterly periods (not calendar)
- Customer base: **Individuals only** (not Agents)
- Build type: **Full End-to-End** (in-year + final declaration)
- Sandbox app id: `d1754357-50ed-4c66-83d8-920cee051a0f`

---

## Section 1 — Executive Summary

| Metric | Count |
|---|---|
| Total checklist questions (incl. info rows) | **35** |
| Substantive Yes/No questions | **31** |
| ✅ Yes — confidently evidenced in code | **18** |
| ⚠️ Yes — needs screenshot or sandbox-test log capture | **5** |
| ❌ Gap — code missing, must build before submitting | **5** |
| ➖ N/A — does not apply to Daniel's build | **3** |

**Honest summary:**

We are **not** ready to send the form back today. The biggest blockers
are End-of-Year endpoints HMRC explicitly tests against:

1. **Periods of Account** endpoints (Business Details API) — not implemented at all.
2. **Late Accounting Date Rule** (retrieve/disapply/withdraw) — not implemented.
3. **Cumulative Period Summary** endpoints (Self Employment Business API) — we use the legacy `POST /period` endpoint, not the cumulative variant the checklist calls out.
4. **Update Annual Submission** end-of-year endpoint testing — code path exists (PUT /annual/{taxYear}) but never exercised in sandbox.
5. The UI does not yet drive `intent-to-amend` / `confirm-amendment` flow even though the API client supports it. HMRC will want to see this work end-to-end.

**Estimated effort to close all gaps:** ~3–5 dev days for code + UI, plus
1 day for sandbox test runs and screenshot capture.

We can answer Yes to the everyday flow (auth, fraud headers, period
submit, calculation, final declaration with statement + checkbox, lock,
export) but we cannot in good faith tick every End-of-Year box yet.

---

## Section 2 — General Questions (Table 1, 19 rows)

### G1 — Read process for being granted Production access; testing meets service guide
**Status:** ⚠️ Needs evidence
**Evidence:** Daniel has read the E2E service guide and run sandbox tests; we should preserve a sandbox session log (sample request/response for each API call) before submitting.
**Suggested answer:** **Yes / Yes** — *Comments:* "Both authors have read the MTD IT End to End Service Guide. Sandbox test logs for each in-scope endpoint will be attached on request."

### G2 — Software supports transmission of fraud prevention header data on **all** API calls
**Status:** ✅ Confirmed
**Evidence:** Headers built in `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_fraud_headers.py:230-279` (full WEB_APP_VIA_SERVER set) and applied to every request via `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_client.py:77-82`. Browser-side capture: `static/js/hmrc-fraud-headers.js` POSTs to `/api/hmrc/fraud-headers/record` (`@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_hmrc.py:42-58`).
**Suggested answer:** **Yes** — *Comments:* "Connection method WEB_APP_VIA_SERVER. Browser context captured per-session via `/api/hmrc/fraud-headers/record` and replayed on every HMRC call."

### G3 — When testing, APIs called via software (not just a submission tool)
**Status:** ✅ Confirmed
**Evidence:** All HMRC interactions go through `HMRCClient._make_request` (`hmrc_client.py:38-181`); no Postman/curl-only routes exist in production code. Every UI action triggers a Flask route in `api_hmrc.py` which calls the client.
**Suggested answer:** **Yes** — *Comments:* "All HMRC API calls are made by the application's `HMRCClient` service from the live UI, not from any external testing tool."

### G4 — Customer owns and has access to all records and can export them
**Status:** ✅ Confirmed
**Evidence:** Self-hosted single-tenant app — Daniel owns the SQLite DB outright. Export endpoints:
- HMRC submissions/obligations/declarations JSON: `@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_hmrc.py:1924-2020`
- MTD-format expense export: `@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_expenses.py:297-316`
- Custom report CSV: `@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_reports.py:748-772`
- Runsheets/payslips CSV: `@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_data.py:565-643`
- Settings → Data & Sync → "Backup" provides full DB export.
**Suggested answer:** **Yes** — *Comments:* "Self-hosted application; user owns the SQLite database. CSV/JSON export available for expenses, income, HMRC submissions and full database backup via Settings → Data & Sync."

### G5 — Customer base — Individuals
**Status:** ✅ Yes
**Suggested answer:** **Yes** (Individuals)

### G6 — Customer base — Agents
**Status:** ➖ N/A
**Suggested answer:** **No** — *Comments:* "Sole-trader software for the proprietor's own returns. No agent functionality."

### G7 — Build type
**Status:** ✅ Full End-to-End
**Suggested answer:** "In-Year only: **No**. End-of-Year only: **No**. Full End-to-End product: **Yes**."

### G8 — Building iteratively
**Status:** ✅ No
**Suggested answer:** **No** — *Comments:* "Single full-E2E release; not split into iterative production rollouts."

### G9 — Income types: Self-Employment
**Status:** ✅ Yes
**Suggested answer:** **Yes**

### G10 — Income types: UK Property
**Status:** ➖ N/A — code paths exist (`HMRCClient.submit_uk_property_period`, etc.) but feature is **not** offered to the user (not in nav, no inputs).
**Suggested answer:** **No** — *Comments:* "Software does not collect UK property income; all `business/property/...` code paths are dormant and will be removed before production deploy. See Action Plan A1."

### G11 — Income types: Foreign Property
**Status:** ➖ N/A — never implemented.
**Suggested answer:** **No**

### G12 — Quarterly period type: Standard
**Status:** ✅ Yes
**Evidence:** `HMRCMapper.calculate_quarterly_periods` produces 06-Apr→05-Jul etc. (`@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_mapper.py:19-58`).
**Suggested answer:** **Yes**

### G13 — Quarterly period type: Calendar
**Status:** ➖ N/A
**Suggested answer:** **No** — *Comments:* "Standard quarters only; calendar quarters are not offered in the UI."

### G14 — Accounting types: Cash
**Status:** ✅ Yes (only mode)
**Suggested answer:** **Yes**

### G15 — Accounting types: Accruals
**Status:** ➖ N/A
**Suggested answer:** **No** — *Comments:* "Cash basis only; product is targeted at sole-trader engineers under the cash threshold."

### G16 — Non-mandated income sources: clearly stated and signposted to gov.uk
**Status:** ⚠️ Partial — footer on the HMRC page links to gov.uk software directory (`templates/settings/hmrc.html:580-596`) but it does not explicitly say *"This software does not support non-mandated income types — see..."*. We collect only self-employment, so this disclaimer should be tightened.
**Suggested answer:** **Yes** — *Comments:* "Footer on the HMRC settings page links to https://www.gov.uk/guidance/find-software-thats-compatible-with-making-tax-digital-for-income-tax. Wording will be updated to explicitly state non-supported income types before production go-live (see Action Plan A2)."

### G17 — In-year-only EoY signposting
**Status:** ➖ N/A — full E2E build supports Final Declaration.
**Suggested answer:** **No** — *Comments:* "Not applicable — software supports end-of-year functionality including Final Declaration."

### G18 — Tax calculation viewable any time + disclaimer
**Status:** ✅ Confirmed
**Evidence:** Trigger/list/retrieve calc routes implemented (`api_hmrc.py:1036-1109`, `1294-1505`). Disclaimer text shown in UI:
```@/Users/danielhanson/CascadeProjects/Wages-App/templates/settings/hmrc.html:442-445
                                                <div class="alert alert-warning mt-3">
                                                    <strong><i class="fas fa-exclamation-triangle"></i> MANDATORY HMRC DISCLAIMER</strong>
                                                    <p class="mb-0 mt-2" id="hmrcCalculationDisclaimer">This calculation is only based on information HMRC have received about your income and expenses to <span id="calculationDate"></span>. This may change as we receive further information about you during the tax year.</p>
                                                </div>
```
This is **verbatim** the example wording in the checklist comment column. ✅
**Suggested answer:** **Yes** to "allows view at any time", **Yes** to "presented with a disclaimer", **No** (or blank) to the signpost-to-PTA fallback. *Comments:* "Wording matches HMRC's suggested text exactly. Calculation is exposed under HMRC → Final Declaration tab → Step 2."

### G19 — Software returns and displays appropriate error messages
**Status:** ⚠️ Needs screenshot
**Evidence:** Validation errors parsed structurally (`@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_client.py:148-167`) and surfaced through `showNotification(..., validationErrors)` in `static/js/settings-hmrc.js`. Need to capture a screenshot of a 422 surfaced to the user.
**Suggested answer:** **Yes** — *Comments:* "HMRC error payloads (including 422 field-level `errors[]`) are parsed and rendered to the user via in-page notifications. Screenshot attached."

---

## Section 3 — In-Year Build Stage (Table 2, 9 questions)

### IY1 — Lists & retrieves Business Details (Business Details (MTD) API)
**Status:** ✅ Confirmed
**Evidence:** `HMRCClient.get_business_details` v2.0 (`hmrc_client.py:207-219`), `get_business_detail` (line 221), exposed at `/api/hmrc/businesses` and `/api/hmrc/business/<id>`.
**Suggested answer:** **Yes**

### IY2 — Calendar quarterly Period Type create/amend
**Status:** ➖ N/A
**Evidence:** Endpoint coded (`create_amend_quarterly_period_type`, `hmrc_client.py:235-255`) but unused — we don't offer calendar quarters.
**Suggested answer:** **No** — *Comments:* "Not applicable — software does not support calendar quarters."

### IY3 — Periods of Account (Retrieve/Create/Update) included in in-year build?
**Status:** ❌ **Gap** — endpoint not implemented at all (no `period-of-account` references anywhere in `app/`).
**Suggested answer:** **No** — *Comments:* "Periods of Account endpoints will be exercised at end-of-year (see EOY1 in this checklist), not in-year. Self-employment software."

### IY4 — Retrieve I&E Obligations
**Status:** ✅ Confirmed
**Evidence:** `HMRCClient.get_obligations` (`hmrc_client.py:273-296`) → `/api/hmrc/obligations` (`api_hmrc.py:258-321`), Obligations API v3.0.
**Suggested answer:** **Yes**

### IY5 — Final Declaration Obligation retrieved with I&E Obligations
**Status:** ✅ Confirmed (separate call)
**Evidence:** `get_final_declaration_obligations` (`hmrc_client.py:298-320`) → `/api/hmrc/obligations/final-declaration` (`api_hmrc.py:907-953`). UI fetches both.
**Suggested answer:** **Yes** — *Comments:* "Final Declaration (crystallisation) obligations are retrieved alongside I&E obligations during the obligations refresh."

### IY6 — Quarterly submission populated from digital record (no manual keying)
**Status:** ✅ Confirmed
**Evidence:** `HMRCMapper.build_period_submission` reads expenses from `ExpenseModel` and income from `payslips` table (`@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_mapper.py:194-254`). The submit endpoint (`api_hmrc.py:460-570`) **does not** accept any free-form income/expense fields in the body — only NINO, business id, tax year, period id, optional date range. No manual keying possible. The submission preview page is read-only.
**Suggested answer:** **Yes** — *Comments:* "Quarterly submission body is built server-side from the user's expenses (`expenses` table) and income (`payslips` table). The HTTP `submit` endpoint does not accept user-typed income/expense values — corrections must be made by editing the underlying record. Records covering a submitted period are then locked (see digital-records lock, migration 007)."

### IY7 — Submit & retrieve in-year **cumulative** period summaries (Self-Employment Business + Property APIs)
**Status:** ❌ **Gap** — we currently call `POST /individuals/business/self-employment/{nino}/{businessId}/period` (legacy non-cumulative endpoint) — see `hmrc_client.py:378-397`. The checklist explicitly says "Test all **cumulative** period summary endpoints". v5.0 of the API has separate cumulative endpoints (`PUT .../cumulative/{taxYear}`, `GET .../cumulative/{taxYear}/{submissionId}`) which we have not implemented.
**Suggested answer (honest):** **No** for the cumulative endpoints — *Comments:* "Currently submitting via the non-cumulative `POST /period` endpoint. Cumulative Period Summary endpoints will be added before production access is granted (see Action Plan A3). Property cumulative endpoints not applicable — UK property not supported."

### IY8 — Annual Submission (allowances/adjustments) included in in-year stage
**Status:** ⚠️ Marginal — `update_annual_summary` exists (`hmrc_client.py:430-444`) and `/api/hmrc/self-employment/annual-summary` route exists (`api_hmrc.py:1151-1225`), but it has not been exercised in sandbox.
**Suggested answer:** **No** — *Comments:* "Annual Submission endpoints will be exercised at end-of-year (see EOY3), not in-year." (Cleanest answer; matches our actual usage.)

### IY9 — Trigger / List / Retrieve calculation any time
**Status:** ✅ Confirmed
**Evidence:** `trigger_crystallisation` (`hmrc_client.py:492-524`), `list_calculations` (`hmrc_client.py:446-460`), `retrieve_calculation` (`hmrc_client.py:462-475`), all exposed at `/api/hmrc/calculations/...` and `/api/hmrc/final-declaration/calculate`.
**Suggested answer:** **Yes** — *Comments:* "All three endpoints used during sandbox testing. Screenshots of triggered + retrieved calculation attached."

---

## Section 4 — End of Year Build Stage (Table 3, 10 questions)

### EOY1 — Periods of Account / Late Accounting Date Rule / Accounting Type endpoints
This question has **three** sub-confirmations:

| Sub-question | Status | Notes |
|---|---|---|
| Retrieve / Create / Update Periods of Account | ❌ **Gap** | Not implemented anywhere. Required for self-employment. |
| Retrieve / Disapply / Withdraw **Late Accounting Date Rule** | ❌ **Gap** | Not implemented anywhere. Required for self-employment. |
| Retrieve / Update Accounting Type | ➖ N/A | Only required if we support both cash and accruals. We support cash only. |

**Suggested answer:**
- Periods of Account: **No** (today) — must become **Yes** before submitting form. *Comments:* "Will be implemented before production access requested. See Action Plan A4."
- Late Accounting Date Rule: **No** (today) — must become **Yes**. *Comments:* "Will be implemented before production access requested. See Action Plan A5."
- Accounting Type: **No** — *Comments:* "Software supports cash basis only; not applicable per checklist note."

### EOY2 — Final Declaration Obligations retrieve
**Status:** ✅ Confirmed (same evidence as IY5).
**Suggested answer:** **Yes**

### EOY3 — Submit allowances and adjustments per business source (Annual Submission)
**Status:** ⚠️ Code exists but untested — `update_annual_summary` PUT to `/individuals/business/self-employment/{nino}/{businessId}/annual/{taxYear}` (`hmrc_client.py:430-444`), wired to `api_hmrc.py:1151-1225`. UI: no dedicated page yet. Cash-basis sole traders frequently submit zero allowances, but the endpoint must demonstrably work.
**Suggested answer:** **Yes — but pending sandbox evidence.** *Comments:* "PUT Annual Submission endpoint implemented (`HMRCClient.update_annual_summary`). Sandbox test required before form submission. Trading allowance / adjustments UI to be added (Action Plan A6)."

### EOY4 — BSAS endpoints (per business source) plus List + Trigger
**Status:** ⚠️ Partial — `trigger_bsas` (`hmrc_client.py:586-620`) and `get_bsas_summary` (`hmrc_client.py:622-640`) implemented and routed (`api_hmrc.py:1723-1818`). **List** BSAS and **Submit BSAS adjustments** not implemented; the checklist says "all endpoints for each business source supported, plus List and Trigger". List BSAS is missing.
**Suggested answer:** **No** (today). *Comments:* "Trigger and Retrieve BSAS implemented; List BSAS and Submit BSAS adjustments to be added before production access (Action Plan A7)."

### EOY5 — Create and submit losses (Individual Losses API)
**Status:** ⚠️ Partial — `create_loss` and `list_losses` implemented (`hmrc_client.py:642-687`); UI present (`templates/settings/hmrc.html:314-388`). Missing: Retrieve specific loss, Update loss amount, Delete loss. The checklist says "Testing of **all** endpoints required."
**Suggested answer:** **No** (today). *Comments:* "Create and List implemented. Retrieve, Amend and Delete loss endpoints to be added (Action Plan A8). Cash-basis sole trader has no brought-forward loss in scope, but endpoints must still be exercised in sandbox."

### EOY6 — Trigger calculation with `intent-to-finalise` AND `intent-to-amend`
**Status:** ⚠️ API supports both, UI does not expose `intent-to-amend`
**Evidence:** `HMRCClient.trigger_crystallisation(..., calculation_type)` accepts both (`hmrc_client.py:504`), but `templates/settings/hmrc.html` Step 1 hard-codes the default. We need a UI affordance to also trigger an amendment calculation, or at minimum a sandbox test log showing both.
**Suggested answer:** **Yes — pending UI exposure.** *Comments:* "API client supports both `intent-to-finalise` and `intent-to-amend`. Both will be exercised end-to-end before production access. UI affordance for amendments to be added (Action Plan A9)."

### EOY7 — Display Individual Final Declaration Statement matching E2E service guide wording
**Status:** ⚠️ **Wording mismatch likely** — needs verification.
**Evidence:** Current UI declaration text:
```@/Users/danielhanson/CascadeProjects/Wages-App/templates/settings/hmrc.html:457-460
                                    <div class="alert alert-danger">
                                        <h6><strong>HMRC Declaration Statement</strong></h6>
                                        <p class="mb-0">I confirm that the information I have provided is correct and complete to the best of my knowledge and belief. I understand that I may have to pay financial penalties and face prosecution if I give false information.</p>
                                    </div>
```
HMRC's E2E Service Guide ("Final Declaration Statement — Individuals") prescribes a longer, prescribed wording that explicitly references *"the income I declared in my final declaration is the total of all income for the tax year ending 5 April YYYY"* and the *"correct and complete to the best of my knowledge and belief"* clause. **Our wording is close but not the verbatim required text** and the checklist demands an exact match.
**Action required:** Pull the current Individual Final Declaration Statement from https://developer.service.hmrc.gov.uk/guides/income-tax-mtd-end-to-end-service-guide and replace the alert body text byte-for-byte, then attach a screenshot.
**Suggested answer:** **Yes — pending wording correction and screenshot.** *Comments:* "Final Declaration Statement is displayed on the `Final Declaration` tab, Step 3. Wording will be aligned exactly to the Individual statement in the MTD IT End to End Service Guide before submission. Screenshot attached."

### EOY8 — Display Agent Final Declaration Statement
**Status:** ➖ N/A
**Suggested answer:** **No** — *Comments:* "Software supports Individuals only."

### EOY9 — End user must confirm declaration before Submit becomes available
**Status:** ✅ Confirmed
**Evidence:**
```@/Users/danielhanson/CascadeProjects/Wages-App/templates/settings/hmrc.html:461-469
                                    <div class="form-check mb-3">
                                        <input type="checkbox" class="form-check-input" id="declarationCheckbox">
                                        <label class="form-check-label" for="declarationCheckbox">
                                            <strong>I have read and agree to the above declaration</strong>
                                        </label>
                                    </div>
                                    <button id="submitDeclBtn" class="btn btn-danger" disabled>
                                        <i class="fas fa-file-signature"></i> Submit Final Declaration to HMRC
                                    </button>
```
Plus a second confirmation modal with its own checkbox/disabled-button at lines 628-668.
**Suggested answer:** **Yes** — *Comments:* "Submit button is `disabled` until the declaration checkbox is ticked, then a second confirmation modal also requires acknowledgment. Screenshot attached."

### EOY10 — Submit Final Declaration with `final-declaration` and `confirm-amendment`
**Status:** ⚠️ API supports both (`hmrc_client.py:540`); UI only drives `final-declaration` today.
**Suggested answer:** **Yes — pending sandbox evidence for `confirm-amendment`.** *Comments:* "API client supports both declaration types. Both will be tested in sandbox; UI affordance for `confirm-amendment` to be added alongside the `intent-to-amend` flow (Action Plan A9)."

---

## Section 5 — Screenshots Required

HMRC will want clear screenshots of these flows. Capture each from the live sandbox build before posting the form back.

| # | Screenshot | Page / Route to capture |
|---|---|---|
| 1 | **Tax calculation with mandatory disclaimer** | `/settings/hmrc` → Final Declaration tab → Step 2 (after triggering calc). Confirm disclaimer text matches checklist example wording. |
| 2 | **Individual Final Declaration Statement** (verbatim HMRC wording) | `/settings/hmrc` → Final Declaration tab → Step 3 (after viewing calculation). |
| 3 | **Declaration agree-checkbox + disabled Submit button** | Same screen as (2) — capture before and after ticking the checkbox to show the button enabling. |
| 4 | **Final Declaration confirmation modal** with second checkbox | After clicking Submit Final Declaration on Step 3 — modal `#finalDeclConfirmModal`. |
| 5 | **Quarterly submission flow** | `/settings/hmrc` → Quarterly Obligations tab → click submit on a quarter → confirm response. Capture both "preview" view and "success" toast. |
| 6 | **Digital records lock indication** | `/expenses` → attempt to edit an expense whose date is inside a submitted period → 409 lock message. Capture the warning UI. |
| 7 | **HMRC validation error display** | Trigger a 422 from sandbox (e.g. submit a period with negative turnover) and screenshot the rendered field-level errors. |
| 8 | **Data export functionality** | `/settings/data` → click "Export to CSV" or "Backup database"; also screenshot `/api/hmrc/export` JSON download confirmation. |
| 9 | **Mandatory non-mandated-income / signposting notice** | `/settings/hmrc` footer notice with the gov.uk software directory link. |
| 10 | **Connection / fraud-prevention OAuth** | `/settings/hmrc` → Connect to HMRC → OAuth round-trip success page. |
| 11 | **Obligations list (I&E + Final Declaration)** | `/settings/hmrc` → Quarterly Obligations tab populated. |

---

## Section 6 — Things We're Probably Missing (Compliance-specific)

### 6.1 Final Declaration Statement wording (must be byte-exact)
**Issue:** Current text (`templates/settings/hmrc.html:459`) is paraphrased from the legal declaration wording. HMRC checklist says: *"this must match the statements shown in the ITSA End to End Service Guide."*
**Source of truth:** https://developer.service.hmrc.gov.uk/guides/income-tax-mtd-end-to-end-service-guide → "Final declaration" → "Customer-facing statements".
**Fix:** Replace paragraph with the verbatim Individual statement (one for `final-declaration`, one for `confirm-amendment` — they differ).

### 6.2 Tax calculation disclaimer wording
**Issue:** Already verbatim. ✅ Just confirm the date placeholder is filled with the calculation `metadata.calculationTimestamp` value at render time.
**Status:** Probably fine — verify in screenshot 1.

### 6.3 Software notice / branding
**Issue:** Footer (`templates/settings/hmrc.html:580-596`) says *"TVS Wages is MTD-compatible software"*. The phrase "MTD-compatible" should not be claimed before HMRC has actually approved production access. Until then, weaker phrasing is safer (e.g. *"…is integrated with HMRC's MTD APIs (sandbox testing in progress)"*).

### 6.4 Sandbox `Gov-Test-Scenario: STATEFUL` leaking to production
**Issue:** `hmrc_client.py:88-93` always sets `Gov-Test-Scenario: STATEFUL` when `environment == 'sandbox'`. Confirm that toggling `HMRC_ENVIRONMENT=production` reliably suppresses both this header **and** the sandbox blueprint (`app/__init__.py:212-217` correctly gates the blueprint, ✅). Nothing further needed.

### 6.5 Dormant Property Business code paths
**Issue:** Property + Foreign-property API methods exist on `HMRCClient` and Property tab in HMRC settings UI. We will be answering "No" to UK and Foreign property in the form. HMRC reviewers may probe these and conclude we're misrepresenting scope. **Recommendation:** hide the Property tab with a feature flag or remove it before submitting the form. Same for `templates/settings/hmrc.html:170-237`.

### 6.6 Validation-error UX (G19)
Current `showNotification(..., validationErrors)` displays errors but they are toast-only. Consider rendering field-level errors next to the offending input to be unambiguous in the screenshot.

### 6.7 Audit log for HMRC submissions
Not asked explicitly but commonly probed: every successful `_store_submission` (`api_hmrc.py:855-904`) writes an `hmrc_submissions` row with `submission_data` (JSON) and `hmrc_receipt_id`. ✅ Sufficient.

---

## Section 7 — Action Plan (priority order)

Effort guide: `XS=<1h, S=2-4h, M=1d, L=2-3d`.

| # | Action | Effort | Blocker for form? |
|---|---|---|---|
| **A1** | Hide / feature-flag UK & Foreign Property UI (`templates/settings/hmrc.html:170-237`) so the screenshots match the "No property" answer. | XS | Yes |
| **A2** | Tighten G16 non-mandated-income disclaimer text in HMRC page footer. | XS | Yes |
| **A3** | Implement Cumulative Period Summary endpoints on `HMRCClient` and route in `api_hmrc.py`. Switch `submit_period` to PUT cumulative. (Self-Employment Business API v5+: `PUT /individuals/business/self-employment/{nino}/{businessId}/cumulative/{taxYear}` and `GET .../cumulative/{taxYear}`). | M | **Yes** |
| **A4** | Implement Periods of Account endpoints (Business Details API v2.0): Retrieve, Create, Update. Add minimal admin UI. | M | **Yes** |
| **A5** | Implement Late Accounting Date Rule (Business Details API v2.0): Retrieve, Disapply, Withdraw. | S | **Yes** |
| **A6** | Implement Annual Submission UI (allowances + adjustments — typically zero for cash-basis sole trader, but must demonstrate the call). | S | Yes (so we can answer Yes truthfully on EOY3) |
| **A7** | Add List BSAS and Submit BSAS adjustments endpoints + sandbox test. | S | Yes (EOY4) |
| **A8** | Add Retrieve/Amend/Delete brought-forward loss endpoints to satisfy "all endpoints" requirement. | S | Yes (EOY5) |
| **A9** | UI affordance to drive `intent-to-amend` calculation and `confirm-amendment` final declaration. Backend already supports both. | S | Yes (EOY6, EOY10) |
| **A10** | Replace Individual Final Declaration Statement text with the verbatim wording from the MTD IT End-to-End Service Guide. Add separate text for the amendment statement. | XS | **Yes** |
| **A11** | Soften footer "MTD-compatible" claim until production access is granted. | XS | Soft |
| **A12** | Capture all screenshots listed in Section 5 from a clean sandbox run. | M (1 day) | **Yes** |
| **A13** | Preserve sandbox API request/response logs (one per endpoint family) ready to attach if HMRC asks. | S | Yes |
| **A14** | Improve validation-error UX so field-level 422 errors render inline (G19 screenshot). | S | Soft |

**Critical-path total:** ~3-4 dev days for A3+A4+A5+A6+A7+A8+A9 + 1 day for screenshots + 0.5 day for A1/A2/A10/A11 housekeeping = **~5 days work** before the form can be returned honestly.

---

## Section 8 — Submission Readiness Checklist

Final pre-submission checks. Tick each ONLY when the evidence is in hand.

- [ ] Every Yes answer in Sections 2-4 has either a code citation or a screenshot already captured.
- [ ] Sandbox test run logs preserved for: Business Details, Obligations (I&E + Final Declaration), Cumulative Period Summary, Annual Submission, BSAS (trigger/list/retrieve/submit), Losses (create/list/retrieve/amend/delete), Calculations (trigger `intent-to-finalise` + `intent-to-amend` + `in-year`, list, retrieve), Final Declaration (`final-declaration` + `confirm-amendment`), Periods of Account, Late Accounting Date Rule.
- [ ] Final Declaration Statement in the UI matches the MTD IT End-to-End Service Guide wording **byte-for-byte** (Individual statement; amendment statement).
- [ ] Tax calculation disclaimer wording matches checklist example. (Currently ✅, just verify the dynamic date renders.)
- [ ] All 9 production APIs subscribed in HMRC Developer Hub: Business Details, Obligations, Self-Employment Business, Individual Calculations, Property Business *(N/A — we do not subscribe)*, BSAS, Individual Losses, Test Fraud Prevention Headers, plus Hello-World for connectivity tests.
- [ ] Fraud prevention headers tested in sandbox via the **Test Fraud Prevention Headers** API (`/test/fraud-prevention-headers/...`) and a green response captured.
- [ ] Property Business UI hidden / feature-flagged (A1).
- [ ] Non-mandated income disclaimer text updated (A2).
- [ ] Production app id pasted into form Table 0, R3.
- [ ] `Completed by` and `Date of completion` filled in Table 0.
- [ ] Form's "Yes/No" answers reduced to the chosen single value (form says "Please delete Yes/No as appropriate").

---

## Appendix — Cited code paths (for the reviewer)

- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_fraud_headers.py:230-279` — fraud header builder
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_client.py:38-181` — request layer with auth + headers + 422 parsing
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_lock.py:35-69` — digital-records lock
- `@/Users/danielhanson/CascadeProjects/Wages-App/migrations/007_hmrc_submission_lock.sql:1-27` — lock schema
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/services/hmrc_mapper.py:194-254` — server-side period payload builder (no manual keying)
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_hmrc.py:855-904` — submission storage + lock activation
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_hmrc.py:1924-2020` — HMRC export endpoint
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/routes/api_expenses.py:155-211` — lock enforcement on expense edit/delete
- `@/Users/danielhanson/CascadeProjects/Wages-App/templates/settings/hmrc.html:442-470` — disclaimer + declaration + checkbox + disabled submit
- `@/Users/danielhanson/CascadeProjects/Wages-App/app/__init__.py:212-217` — sandbox blueprint gated on `HMRC_ENVIRONMENT`
