/* HMRC Periods of Account panel controller.
 *
 * Talks to:
 *   POST   /api/hmrc/period-of-account/<tax_year>
 *   GET    /api/hmrc/period-of-account/<tax_year>
 *   PUT    /api/hmrc/period-of-account/<tax_year>
 *   DELETE /api/hmrc/period-of-account/<tax_year>
 *
 * Public API exposed on window.HMRCPeriodsOfAccount:
 *   load(taxYear)
 *   create(taxYear, options)
 *   update(taxYear, dates)
 *   delete(taxYear)
 *
 * Distinct status handling: 200 / 400 / 404 / 409 / 422 / 5xx.
 * No inline styles - all visual state goes via CSS classes from
 * static/css/hmrc-periods-of-account.css and Bootstrap utilities.
 */

(function () {
    'use strict';

    // ----- DOM references -------------------------------------------------

    function $(id) { return document.getElementById(id); }

    function elements() {
        return {
            card: $('periodOfAccountCard'),
            yearSelect: $('poaTaxYearSelect'),
            summaryEmpty: $('poaSummaryEmpty'),
            summaryContent: $('poaSummaryContent'),
            summaryDates: $('poaSummaryDates'),
            summaryPeriodId: $('poaSummaryPeriodId'),
            typeBadge: $('poaTypeBadge'),
            customToggle: $('poaCustomToggle'),
            customDates: $('poaCustomDates'),
            startDate: $('poaStartDate'),
            endDate: $('poaEndDate'),
            createBtn: $('poaCreateBtn'),
            createLabel: $('poaCreateBtnLabel'),
            updateBtn: $('poaUpdateBtn'),
            deleteBtn: $('poaDeleteBtn'),
            result: $('poaResult'),
        };
    }

    // ----- helpers --------------------------------------------------------

    function fmtDate(iso) {
        // Render an ISO YYYY-MM-DD as 'DD MMMM YYYY'.
        if (!iso || typeof iso !== 'string') return '\u2014';
        const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
        if (!m) return iso;
        const months = ['January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'];
        return `${m[3]} ${months[parseInt(m[2], 10) - 1]} ${m[1]}`;
    }

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
        const el = $('poaResult');
        if (!el) return;
        const map = {
            success: 'alert alert-success',
            info: 'alert alert-info',
            warning: 'alert alert-warning',
            danger: 'alert alert-danger',
        };
        el.className = `${map[kind] || map.info} mb-3`;
        el.textContent = message;
        el.classList.remove('d-none');
    }

    function clearResult() {
        const el = $('poaResult');
        if (!el) return;
        el.className = 'd-none mb-3';
        el.textContent = '';
    }

    function setBusy(isBusy) {
        const els = elements();
        [els.createBtn, els.updateBtn, els.deleteBtn].forEach(btn => {
            if (!btn) return;
            btn.disabled = isBusy ? true : btn.dataset.poaDisabled === 'true';
        });
    }

    function rememberDisabledState() {
        // Persist the "natural" disabled state the load() function sets so
        // setBusy(false) restores it correctly afterwards.
        const els = elements();
        [els.createBtn, els.updateBtn, els.deleteBtn].forEach(btn => {
            if (btn) btn.dataset.poaDisabled = btn.disabled ? 'true' : 'false';
        });
    }

    // ----- rendering ------------------------------------------------------

    function renderEmpty() {
        const els = elements();
        if (!els.summaryEmpty) return;
        els.summaryEmpty.classList.remove('d-none');
        els.summaryContent.classList.add('d-none');
        if (els.createBtn) els.createBtn.disabled = false;
        if (els.updateBtn) els.updateBtn.disabled = true;
        if (els.deleteBtn) els.deleteBtn.disabled = true;
        if (els.createLabel) {
            els.createLabel.textContent = els.customToggle && els.customToggle.checked
                ? 'Create Custom Period'
                : 'Set Standard Period';
        }
        rememberDisabledState();
    }

    function renderRecord(record) {
        const els = elements();
        if (!els.summaryEmpty) return;
        els.summaryEmpty.classList.add('d-none');
        els.summaryContent.classList.remove('d-none');

        els.summaryDates.textContent =
            `${fmtDate(record.period_start_date)} \u2013 ${fmtDate(record.period_end_date)}`;
        els.summaryPeriodId.textContent = record.period_id || '\u2014';

        const isStandard = (record.period_type || 'standard') === 'standard';
        els.typeBadge.textContent = isStandard ? 'Standard' : 'Custom';
        els.typeBadge.classList.toggle('poa-type-non-standard', !isStandard);

        if (els.createBtn) els.createBtn.disabled = true;
        if (els.updateBtn) els.updateBtn.disabled = false;
        if (els.deleteBtn) els.deleteBtn.disabled = false;
        if (els.createLabel) els.createLabel.textContent = 'Period Already Set';
        rememberDisabledState();
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
            showResult('warning', (data && data.error) || 'Conflict with existing record.');
        } else if (status === 422) {
            const errs = (data && data.validation_errors) || [];
            const detail = errs.map(e => `${e.field}: ${e.message}`).join('; ');
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

        try {
            const { status, data } = await fetchJson(
                'GET', `/api/hmrc/period-of-account/${encodeURIComponent(ty)}`,
            );
            if (status === 200 && data && data.success && data.data) {
                renderRecord(data.data);
                return;
            }
            if (status === 404) {
                renderEmpty();
                return;
            }
            renderEmpty();
            handleErrorStatus(status, data);
        } catch (err) {
            renderEmpty();
            showResult('danger', `Network error: ${err.message || err}`);
        }
    }

    async function create(taxYear, options) {
        clearResult();
        setBusy(true);
        const els = elements();
        const ty = taxYear || (els.yearSelect && els.yearSelect.value);
        if (!ty) {
            setBusy(false);
            return;
        }

        const ids = readNinoBusinessId();
        if (!ids.nino || !ids.business_id) {
            showResult('warning',
                'Set the NINO and Business ID in Configuration above first.');
            setBusy(false);
            return;
        }

        const useCustom = !!(options && options.custom)
            || (els.customToggle && els.customToggle.checked);
        const body = Object.assign({}, ids);
        if (useCustom) {
            body.period_type = 'non-standard';
            body.start_date = (options && options.start_date)
                || (els.startDate && els.startDate.value);
            body.end_date = (options && options.end_date)
                || (els.endDate && els.endDate.value);
            if (!body.start_date || !body.end_date) {
                showResult('warning', 'Please supply both a start and end date.');
                setBusy(false);
                return;
            }
            if (body.start_date >= body.end_date) {
                showResult('warning', 'Start date must be before end date.');
                setBusy(false);
                return;
            }
        } else {
            body.period_type = 'standard';
        }

        try {
            const { status, data } = await fetchJson(
                'POST', `/api/hmrc/period-of-account/${encodeURIComponent(ty)}`, body,
            );
            if (status === 200 && data && data.success) {
                showResult('success',
                    `Period of account registered with HMRC for ${ty}.`);
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

    async function update(taxYear, dates) {
        clearResult();
        setBusy(true);
        const els = elements();
        const ty = taxYear || (els.yearSelect && els.yearSelect.value);
        if (!ty) {
            setBusy(false);
            return;
        }

        const ids = readNinoBusinessId();
        if (!ids.nino || !ids.business_id) {
            showResult('warning',
                'Set the NINO and Business ID in Configuration above first.');
            setBusy(false);
            return;
        }

        const body = Object.assign({}, ids);
        const startVal = (dates && dates.start_date)
            || (els.startDate && els.startDate.value);
        const endVal = (dates && dates.end_date)
            || (els.endDate && els.endDate.value);
        if (startVal) body.start_date = startVal;
        if (endVal) body.end_date = endVal;

        if (body.start_date && body.end_date && body.start_date >= body.end_date) {
            showResult('warning', 'Start date must be before end date.');
            setBusy(false);
            return;
        }

        try {
            const { status, data } = await fetchJson(
                'PUT', `/api/hmrc/period-of-account/${encodeURIComponent(ty)}`, body,
            );
            if (status === 200 && data && data.success) {
                showResult('success', `Period of account updated for ${ty}.`);
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

    async function deletePeriod(taxYear) {
        clearResult();
        const els = elements();
        const ty = taxYear || (els.yearSelect && els.yearSelect.value);
        if (!ty) return;

        if (!window.confirm(
            `Delete the period of account for ${ty}? This will be sent to ` +
            'HMRC and cannot be undone.'
        )) {
            return;
        }

        const ids = readNinoBusinessId();
        if (!ids.nino || !ids.business_id) {
            showResult('warning',
                'Set the NINO and Business ID in Configuration above first.');
            return;
        }

        setBusy(true);
        try {
            const { status, data } = await fetchJson(
                'DELETE', `/api/hmrc/period-of-account/${encodeURIComponent(ty)}`, ids,
            );
            if (status === 200 && data && data.success) {
                showResult('success', `Period of account deleted for ${ty}.`);
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
        if (els.customToggle) {
            els.customToggle.addEventListener('change', () => {
                const on = els.customToggle.checked;
                els.customDates.classList.toggle('d-none', !on);
                if (els.createLabel && els.createBtn && !els.createBtn.disabled) {
                    els.createLabel.textContent = on
                        ? 'Create Custom Period'
                        : 'Set Standard Period';
                }
            });
        }
        if (els.createBtn) els.createBtn.addEventListener('click', () => create());
        if (els.updateBtn) els.updateBtn.addEventListener('click', () => update());
        if (els.deleteBtn) els.deleteBtn.addEventListener('click', () => deletePeriod());

        // Initial render.
        load();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bind);
    } else {
        bind();
    }

    window.HMRCPeriodsOfAccount = {
        load: load,
        create: create,
        update: update,
        delete: deletePeriod,
    };
})();
