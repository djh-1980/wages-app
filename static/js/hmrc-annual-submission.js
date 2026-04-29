/* HMRC Annual Submission panel controller.
 *
 * Talks to:
 *   GET    /api/hmrc/annual-submission/<tax_year>?nino=&business_id=
 *   PUT    /api/hmrc/annual-submission/<tax_year>
 *   POST   /api/hmrc/annual-submission/<tax_year>/draft
 *   DELETE /api/hmrc/annual-submission/<tax_year>/draft
 *
 * Public API on window.HMRCAnnualSubmission:
 *   load(taxYear)
 *   saveDraft(taxYear)
 *   discardDraft(taxYear)
 *   submit(taxYear)
 *
 * Form serialisation: every input that participates in the submission
 * carries `data-section` (allowances | adjustments | nonFinancials)
 * and `data-field` (HMRC field name). collectFormData() walks them and
 * builds the nested {adjustments, allowances, nonFinancials} payload.
 */

(function () {
    'use strict';

    function $(id) { return document.getElementById(id); }

    function elements() {
        return {
            card: $('annCard'),
            form: $('annForm'),
            yearSelect: $('annTaxYearSelect'),
            lastSubmitted: $('annLastSubmittedTimestamp'),
            draftBadge: $('annDraftBadge'),
            draftAge: $('annDraftAge'),
            saveBtn: $('annSaveDraftBtn'),
            discardBtn: $('annDiscardDraftBtn'),
            submitBtn: $('annSubmitBtn'),
            result: $('annResult'),
        };
    }

    // ----- helpers --------------------------------------------------------

    function getHeaders() {
        if (typeof getJSONHeaders === 'function') return getJSONHeaders();
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        };
    }

    function readNinoBusinessId() {
        const ninoEl = $('ninoInput');
        const bizEl = $('businessIdInput');
        return {
            nino: ninoEl ? ninoEl.value.trim().toUpperCase() : '',
            business_id: bizEl ? bizEl.value.trim() : '',
        };
    }

    function showResult(kind, message) {
        const el = $('annResult');
        if (!el) return;
        const map = {
            success: 'alert alert-success',
            info: 'alert alert-info',
            warning: 'alert alert-warning',
            danger: 'alert alert-danger',
        };
        el.className = `${map[kind] || map.info} mt-3 mb-3`;
        el.textContent = message;
        el.classList.remove('d-none');
    }

    function clearResult() {
        const el = $('annResult');
        if (!el) return;
        el.className = 'd-none mt-3 mb-3';
        el.textContent = '';
    }

    function timeAgo(iso) {
        if (!iso) return '\u2014';
        const then = Date.parse(iso);
        if (Number.isNaN(then)) return iso;
        const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
        if (seconds < 60) return 'just now';
        const mins = Math.floor(seconds / 60);
        if (mins < 60) return `${mins} minute${mins === 1 ? '' : 's'} ago`;
        const hours = Math.floor(mins / 60);
        if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
        const days = Math.floor(hours / 24);
        return `${days} day${days === 1 ? '' : 's'} ago`;
    }

    // ----- form <-> object ------------------------------------------------

    function formInputs() {
        const form = $('annForm');
        if (!form) return [];
        return Array.from(
            form.querySelectorAll('[data-section][data-field]'),
        );
    }

    function resetForm() {
        formInputs().forEach((el) => {
            if (el.type === 'checkbox') {
                el.checked = false;
            } else if (el.tagName === 'SELECT') {
                el.value = '';
            } else {
                el.value = '0';
            }
        });
    }

    function applyAnnualData(annualData) {
        if (!annualData || typeof annualData !== 'object') return;
        formInputs().forEach((el) => {
            const section = el.dataset.section;
            const field = el.dataset.field;
            const sectionData = annualData[section];
            if (!sectionData || typeof sectionData !== 'object') return;
            if (!Object.prototype.hasOwnProperty.call(sectionData, field)) return;
            const val = sectionData[field];
            if (el.type === 'checkbox') {
                el.checked = !!val;
            } else if (el.tagName === 'SELECT') {
                el.value = val == null ? '' : String(val);
            } else {
                el.value = (val === null || val === undefined) ? '0' : String(val);
            }
        });
    }

    function collectFormData() {
        const out = { allowances: {}, adjustments: {}, nonFinancials: {} };
        let invalid = null;

        formInputs().forEach((el) => {
            const section = el.dataset.section;
            const field = el.dataset.field;
            if (!out[section]) out[section] = {};

            if (el.type === 'checkbox') {
                if (el.checked) out[section][field] = true;
                return;
            }
            if (el.tagName === 'SELECT') {
                if (el.value !== '') out[section][field] = el.value;
                return;
            }

            // Numeric input.
            const raw = (el.value || '').trim();
            if (raw === '') return;
            const num = Number(raw);
            if (!Number.isFinite(num)) {
                if (!invalid) invalid = `${field} must be a number`;
                return;
            }
            if (num < 0) {
                if (!invalid) invalid = `${field} cannot be negative`;
                return;
            }
            // Round to 2dp to match HMRC's currency precision.
            out[section][field] = Math.round(num * 100) / 100;
        });

        if (invalid) {
            return { ok: false, error: invalid };
        }

        // Drop empty sections so HMRC doesn't reject a payload with
        // {nonFinancials: {}}; keep allowances and adjustments since
        // submitting zeroes is the canonical cash-basis case.
        if (Object.keys(out.nonFinancials).length === 0) {
            delete out.nonFinancials;
        }
        return { ok: true, data: out };
    }

    // ----- rendering ------------------------------------------------------

    function renderState(payload) {
        const els = elements();
        if (!els.card) return;

        const draft = payload && payload.draft;
        const last = payload && payload.last_submitted;
        const hmrcData = payload && payload.hmrc_data;

        // Last-submitted timestamp.
        if (last && last.submitted_at) {
            els.lastSubmitted.textContent = timeAgo(last.submitted_at);
            els.lastSubmitted.title = last.submitted_at;
        } else {
            els.lastSubmitted.textContent = '\u2014';
            els.lastSubmitted.title = '';
        }

        // Draft badge + Discard button visibility.
        if (draft && draft.updated_at) {
            els.draftAge.textContent = timeAgo(draft.updated_at);
            els.draftBadge.classList.remove('d-none');
            els.discardBtn.classList.remove('d-none');
        } else {
            els.draftBadge.classList.add('d-none');
            els.discardBtn.classList.add('d-none');
        }

        // Populate the form. Priority: draft -> hmrc_data -> last_submitted.
        resetForm();
        if (draft && draft.annual_data) {
            applyAnnualData(draft.annual_data);
        } else if (hmrcData) {
            applyAnnualData(hmrcData);
        } else if (last && last.annual_data) {
            applyAnnualData(last.annual_data);
        }
    }

    function setBusy(isBusy) {
        const els = elements();
        [els.saveBtn, els.discardBtn, els.submitBtn].forEach((btn) => {
            if (!btn) return;
            if (isBusy) {
                btn.dataset.annPrevDisabled = btn.disabled ? 'true' : 'false';
                btn.disabled = true;
            } else {
                btn.disabled = btn.dataset.annPrevDisabled === 'true';
            }
        });
    }

    // ----- HTTP -----------------------------------------------------------

    async function fetchJson(method, url, body) {
        const opts = {
            method,
            headers: getHeaders(),
            credentials: 'same-origin',
        };
        if (body !== undefined) opts.body = JSON.stringify(body);
        const res = await fetch(url, opts);
        let data = null;
        try { data = await res.json(); } catch (_) { data = null; }
        return { status: res.status, data };
    }

    function handleErrorStatus(status, data) {
        if (status === 400) {
            showResult('danger', (data && data.error) || 'Invalid request.');
        } else if (status === 401) {
            showResult('danger', 'Login required. Please refresh the page.');
        } else if (status === 404) {
            showResult('warning', (data && data.error) || 'Not found.');
        } else if (status === 409) {
            showResult('warning', (data && data.error) || 'Conflict.');
        } else if (status === 422) {
            const errs = (data && data.validation_errors) || [];
            const detail = errs.map((e) => `${e.field}: ${e.message}`).join('; ');
            showResult('danger',
                detail || (data && data.error) || 'HMRC rejected the submission.');
        } else if (status >= 500) {
            showResult('danger',
                (data && data.error) || `HMRC server error (${status}).`);
        } else {
            showResult('danger', (data && data.error) || `Request failed (${status}).`);
        }
    }

    // ----- public API -----------------------------------------------------

    async function load(taxYear) {
        clearResult();
        const els = elements();
        if (!els.card) return;
        const ty = taxYear || (els.yearSelect && els.yearSelect.value);
        if (!ty) return;

        const ids = readNinoBusinessId();
        if (!ids.nino || !ids.business_id) {
            showResult('warning',
                'Set the NINO and Business ID in Configuration above first.');
            return;
        }

        const url = `/api/hmrc/annual-submission/${encodeURIComponent(ty)}`
            + `?nino=${encodeURIComponent(ids.nino)}`
            + `&business_id=${encodeURIComponent(ids.business_id)}`;

        try {
            const { status, data } = await fetchJson('GET', url);
            if (status === 200 && data && data.success && data.data) {
                renderState(data.data);
                if (data.data.stale) {
                    showResult('info',
                        'Showing cached data \u2014 not connected to HMRC.');
                }
                return;
            }

            // Surface error and any draft the route returned alongside.
            renderState({
                draft: data && data.draft,
                last_submitted: data && data.last_submitted,
                hmrc_data: null,
            });
            handleErrorStatus(status, data);
        } catch (err) {
            showResult('danger', `Network error: ${err.message || err}`);
        }
    }

    async function saveDraft(taxYear) {
        clearResult();
        const els = elements();
        const ty = taxYear || (els.yearSelect && els.yearSelect.value);
        if (!ty) return;

        const ids = readNinoBusinessId();
        if (!ids.business_id) {
            showResult('warning',
                'Set the Business ID in Configuration above first.');
            return;
        }

        const collected = collectFormData();
        if (!collected.ok) {
            showResult('warning', collected.error);
            return;
        }

        setBusy(true);
        try {
            const url = `/api/hmrc/annual-submission/${encodeURIComponent(ty)}/draft`;
            const { status, data } = await fetchJson(
                'POST', url,
                { business_id: ids.business_id, annual_data: collected.data },
            );
            if (status === 200 && data && data.success) {
                showResult('success', 'Draft saved locally.');
                await load(ty);
            } else {
                handleErrorStatus(status, data);
            }
        } catch (err) {
            showResult('danger', `Network error: ${err.message || err}`);
        } finally {
            setBusy(false);
        }
    }

    async function discardDraft(taxYear) {
        clearResult();
        const els = elements();
        const ty = taxYear || (els.yearSelect && els.yearSelect.value);
        if (!ty) return;

        if (!window.confirm(`Discard the local draft for ${ty}?`)) return;

        const ids = readNinoBusinessId();
        if (!ids.business_id) {
            showResult('warning',
                'Set the Business ID in Configuration above first.');
            return;
        }

        setBusy(true);
        try {
            const url = `/api/hmrc/annual-submission/${encodeURIComponent(ty)}/draft`;
            const { status, data } = await fetchJson(
                'DELETE', url, { business_id: ids.business_id },
            );
            if (status === 200 && data && data.success) {
                showResult('info', 'Draft discarded.');
                await load(ty);
            } else {
                handleErrorStatus(status, data);
            }
        } catch (err) {
            showResult('danger', `Network error: ${err.message || err}`);
        } finally {
            setBusy(false);
        }
    }

    async function submit(taxYear) {
        clearResult();
        const els = elements();
        const ty = taxYear || (els.yearSelect && els.yearSelect.value);
        if (!ty) return;

        const ids = readNinoBusinessId();
        if (!ids.nino || !ids.business_id) {
            showResult('warning',
                'Set the NINO and Business ID in Configuration above first.');
            return;
        }

        const collected = collectFormData();
        if (!collected.ok) {
            showResult('warning', collected.error);
            return;
        }

        if (!window.confirm(
            `Submit the annual submission for ${ty} to HMRC? This is a tax `
            + 'declaration and cannot be undone without contacting HMRC.'
        )) {
            return;
        }

        setBusy(true);
        try {
            const url = `/api/hmrc/annual-submission/${encodeURIComponent(ty)}`;
            const { status, data } = await fetchJson(
                'PUT', url,
                {
                    nino: ids.nino,
                    business_id: ids.business_id,
                    annual_data: collected.data,
                },
            );
            if (status === 200 && data && data.success) {
                showResult('success',
                    `Annual submission accepted by HMRC for ${ty}.`);
                await load(ty);
            } else {
                handleErrorStatus(status, data);
            }
        } catch (err) {
            showResult('danger', `Network error: ${err.message || err}`);
        } finally {
            setBusy(false);
        }
    }

    // ----- bootstrapping --------------------------------------------------

    function bind() {
        const els = elements();
        if (!els.card) return;

        if (els.yearSelect) {
            els.yearSelect.addEventListener('change', () => load());
        }
        if (els.saveBtn) els.saveBtn.addEventListener('click', () => saveDraft());
        if (els.discardBtn) els.discardBtn.addEventListener('click', () => discardDraft());
        if (els.submitBtn) els.submitBtn.addEventListener('click', () => submit());

        load();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bind);
    } else {
        bind();
    }

    window.HMRCAnnualSubmission = {
        load: load,
        saveDraft: saveDraft,
        discardDraft: discardDraft,
        submit: submit,
    };
})();
