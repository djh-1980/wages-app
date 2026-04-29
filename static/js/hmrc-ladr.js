/* HMRC Late Accounting Date Rule panel controller.
 *
 * Talks to:
 *   GET    /api/hmrc/late-accounting-date-rule/<tax_year>?nino=&business_id=
 *   POST   /api/hmrc/late-accounting-date-rule/<tax_year>/disapply
 *   DELETE /api/hmrc/late-accounting-date-rule/<tax_year>/disapply
 *
 * Public API exposed on window.HMRCLateAccountingDateRule:
 *   load(taxYear)
 *   disapply(taxYear)
 *   withdraw(taxYear)
 *
 * Distinct status handling: 200 / 400 / 404 / 409 / 422 / 5xx.
 * Confirms before any mutation.
 */

(function () {
    'use strict';

    function $(id) { return document.getElementById(id); }

    function elements() {
        return {
            card: $('ladrCard'),
            yearSelect: $('ladrTaxYearSelect'),
            statusBadge: $('ladrStatusBadge'),
            lastSynced: $('ladrLastSynced'),
            staleBadge: $('ladrStaleBadge'),
            refreshBtn: $('ladrRefreshBtn'),
            disapplyBtn: $('ladrDisapplyBtn'),
            withdrawBtn: $('ladrWithdrawBtn'),
            result: $('ladrResult'),
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
        const el = $('ladrResult');
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
        const el = $('ladrResult');
        if (!el) return;
        el.className = 'd-none mb-3';
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

    // ----- rendering ------------------------------------------------------

    function renderStatus(status, lastSyncedIso, opts) {
        const els = elements();
        if (!els.card) return;
        const safeStatus = status || 'Unknown';

        // Badge text + variant class.
        els.statusBadge.textContent = safeStatus;
        els.statusBadge.classList.remove(
            'ladr-status-applied',
            'ladr-status-disapplied',
            'ladr-status-unknown',
        );
        if (safeStatus === 'Applied') {
            els.statusBadge.classList.add('ladr-status-applied');
        } else if (safeStatus === 'Disapplied') {
            els.statusBadge.classList.add('ladr-status-disapplied');
        } else {
            els.statusBadge.classList.add('ladr-status-unknown');
        }

        // Last synced / stale flag.
        els.lastSynced.textContent = lastSyncedIso ? timeAgo(lastSyncedIso) : '\u2014';
        els.lastSynced.title = lastSyncedIso || '';
        const stale = !!(opts && opts.stale);
        els.staleBadge.classList.toggle('d-none', !stale);

        // Action button visibility + enabled state.
        const connected = !(opts && opts.disconnected);
        els.disapplyBtn.classList.toggle('d-none', safeStatus !== 'Applied');
        els.withdrawBtn.classList.toggle('d-none', safeStatus !== 'Disapplied');
        els.disapplyBtn.disabled = !connected || safeStatus !== 'Applied';
        els.withdrawBtn.disabled = !connected || safeStatus !== 'Disapplied';
    }

    function setBusy(isBusy) {
        const els = elements();
        [els.refreshBtn, els.disapplyBtn, els.withdrawBtn].forEach(btn => {
            if (!btn) return;
            if (isBusy) {
                btn.dataset.ladrPrevDisabled = btn.disabled ? 'true' : 'false';
                btn.disabled = true;
            } else {
                btn.disabled = btn.dataset.ladrPrevDisabled === 'true';
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
            showResult('warning', (data && data.error) || 'Conflict with existing state.');
        } else if (status === 422) {
            const errs = (data && data.validation_errors) || [];
            const detail = errs.map(e => `${e.field}: ${e.message}`).join('; ');
            showResult('danger',
                detail || (data && data.error) || 'HMRC rejected the request.');
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
            renderStatus('Unknown', null, { disconnected: true });
            showResult('warning',
                'Set the NINO and Business ID in Configuration above first.');
            return;
        }

        const url = `/api/hmrc/late-accounting-date-rule/${encodeURIComponent(ty)}`
            + `?nino=${encodeURIComponent(ids.nino)}`
            + `&business_id=${encodeURIComponent(ids.business_id)}`;

        try {
            const { status, data } = await fetchJson('GET', url);
            if (status === 200 && data && data.success && data.data) {
                renderStatus(
                    data.data.status,
                    data.data.last_synced_at,
                    { stale: !!data.data.stale, disconnected: !!data.data.stale },
                );
                return;
            }

            if (status === 404) {
                renderStatus('Unknown', null, { disconnected: true });
                handleErrorStatus(status, data);
                return;
            }

            // Soft fallback: route may include cached state alongside error.
            if (data && data.cached) {
                renderStatus(
                    data.cached.status,
                    data.cached.last_synced_at,
                    { stale: true, disconnected: true },
                );
            } else {
                renderStatus('Unknown', null, { disconnected: true });
            }
            handleErrorStatus(status, data);
        } catch (err) {
            renderStatus('Unknown', null, { disconnected: true });
            showResult('danger', `Network error: ${err.message || err}`);
        }
    }

    async function disapply(taxYear) {
        clearResult();
        const els = elements();
        const ty = taxYear || (els.yearSelect && els.yearSelect.value);
        if (!ty) return;

        if (!window.confirm(
            `Disapply the Late Accounting Date Rule for ${ty}? This is a tax `
            + 'decision that will be sent to HMRC.'
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
            const url = `/api/hmrc/late-accounting-date-rule/${encodeURIComponent(ty)}/disapply`;
            const { status, data } = await fetchJson('POST', url, ids);
            if (status === 200 && data && data.success) {
                showResult('success',
                    `Late Accounting Date Rule disapplied for ${ty}.`);
                renderStatus(
                    data.data.status,
                    data.data.last_synced_at,
                    { stale: false },
                );
            } else {
                handleErrorStatus(status, data);
            }
        } catch (err) {
            showResult('danger', `Network error: ${err.message || err}`);
        } finally {
            setBusy(false);
        }
    }

    async function withdraw(taxYear) {
        clearResult();
        const els = elements();
        const ty = taxYear || (els.yearSelect && els.yearSelect.value);
        if (!ty) return;

        if (!window.confirm(
            `Withdraw the disapplication of the Late Accounting Date Rule `
            + `for ${ty}? The rule will be re-applied.`
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
            const url = `/api/hmrc/late-accounting-date-rule/${encodeURIComponent(ty)}/disapply`;
            const { status, data } = await fetchJson('DELETE', url, ids);
            if (status === 200 && data && data.success) {
                showResult('success',
                    `Disapplication withdrawn for ${ty}; rule re-applied.`);
                renderStatus(
                    data.data.status,
                    data.data.last_synced_at,
                    { stale: false },
                );
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
        if (els.refreshBtn) {
            els.refreshBtn.addEventListener('click', () => load());
        }
        if (els.disapplyBtn) {
            els.disapplyBtn.addEventListener('click', () => disapply());
        }
        if (els.withdrawBtn) {
            els.withdrawBtn.addEventListener('click', () => withdraw());
        }

        load();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bind);
    } else {
        bind();
    }

    window.HMRCLateAccountingDateRule = {
        load: load,
        disapply: disapply,
        withdraw: withdraw,
    };
})();
