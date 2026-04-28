/**
 * HMRC cumulative period submission panel controller.
 *
 * Drives #cumulativePanel on /settings/hmrc. The panel replaces the
 * legacy per-period submission flow that lived in expenses.js: the user
 * picks an open obligation, sees the cumulative figures from 6 April of
 * the tax year up to that obligation's end date, reviews a per-quarter
 * contribution breakdown, ticks a confirmation checkbox, and submits.
 *
 * Talks to:
 *   POST /api/hmrc/period/cumulative/<tax_year>
 *   GET  /api/hmrc/period/cumulative/<tax_year>     (for re-display)
 */

(function () {
    'use strict';

    // Maps the calculator's HMRC field names to a friendlier display label.
    const EXPENSE_LABELS = {
        costOfGoodsBought: 'Cost of goods bought',
        cisPaymentsToSubcontractors: 'CIS payments to subcontractors',
        staffCosts: 'Staff costs',
        travelCosts: 'Travel & vehicle costs',
        premisesRunningCosts: 'Premises running costs',
        maintenanceCosts: 'Maintenance costs',
        adminCosts: 'Admin costs',
        advertisingCosts: 'Advertising',
        interest: 'Interest',
        financialCharges: 'Financial charges',
        badDebt: 'Bad debt',
        professionalFees: 'Professional fees',
        depreciation: 'Depreciation',
        other: 'Other',
    };

    const state = {
        taxYear: null,
        periodId: null,
        endDate: null,
    };

    function $(id) {
        return document.getElementById(id);
    }

    function formatGBP(amount) {
        const n = Number(amount || 0);
        return n.toLocaleString('en-GB', {
            style: 'currency',
            currency: 'GBP',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function formatDate(iso) {
        if (!iso) return '—';
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return iso;
        return d.toLocaleDateString('en-GB', {
            day: '2-digit', month: 'short', year: 'numeric',
        });
    }

    /** Convert legacy 'YYYY/YYYY' to HMRC 'YYYY-YY'. */
    function normaliseTaxYear(taxYear) {
        if (!taxYear) return taxYear;
        if (taxYear.indexOf('/') !== -1) {
            const parts = taxYear.split('/');
            return parts[0] + '-' + parts[1].slice(-2);
        }
        if (taxYear.indexOf('-') !== -1) {
            const parts = taxYear.split('-');
            if (parts[1] && parts[1].length === 4) {
                return parts[0] + '-' + parts[1].slice(-2);
            }
        }
        return taxYear;
    }

    function showPanel() {
        const panel = $('cumulativePanel');
        if (!panel) return;
        panel.classList.remove('d-none', 'cumulative-panel-locked');
        $('cumulativeContent').classList.add('d-none');
        $('cumulativeLoading').classList.remove('d-none');
        $('cumulativeResult').classList.add('d-none');
        $('cumulativeResult').innerHTML = '';
        $('cumulativeConfirmCheckbox').checked = false;
        $('cumulativeSubmitBtn').disabled = true;
        // Scroll into view so the user actually sees it.
        panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function hidePanel() {
        const panel = $('cumulativePanel');
        if (panel) panel.classList.add('d-none');
    }

    function lockPanel() {
        const panel = $('cumulativePanel');
        if (panel) panel.classList.add('cumulative-panel-locked');
        $('cumulativeSubmitBtn').disabled = true;
    }

    function renderExpenses(periodExpenses) {
        const tbody = $('cumulativeExpenseBody');
        if (!tbody) return;
        const entries = Object.entries(periodExpenses || {});
        if (entries.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" class="text-muted text-center">No expenses recorded</td></tr>';
            return;
        }
        tbody.innerHTML = entries
            .sort((a, b) => Number(b[1]) - Number(a[1]))
            .map(([key, value]) => {
                const label = EXPENSE_LABELS[key] || key;
                return '<tr>'
                    + '<td>' + escapeHtml(label) + '</td>'
                    + '<td class="text-end">' + formatGBP(value) + '</td>'
                    + '</tr>';
            })
            .join('');
    }

    function renderBreakdown(breakdown) {
        const tbody = $('cumulativeBreakdownBody');
        if (!tbody) return;
        if (!breakdown || breakdown.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-muted text-center">No data</td></tr>';
            return;
        }
        tbody.innerHTML = breakdown.map(entry => {
            const partial = entry.is_partial
                ? ' <span class="badge text-bg-warning">partial</span>'
                : '';
            const rowClass = entry.is_partial ? 'partial-quarter' : '';
            return '<tr class="' + rowClass + '">'
                + '<td><strong>' + escapeHtml(entry.period_id) + '</strong>' + partial + '</td>'
                + '<td>' + formatDate(entry.start_date) + ' &ndash; ' + formatDate(entry.end_date) + '</td>'
                + '<td class="text-end">' + formatGBP(entry.turnover) + '</td>'
                + '<td class="text-end">' + formatGBP(entry.expenses_total) + '</td>'
                + '</tr>';
        }).join('');
    }

    function escapeHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    /**
     * Build a preview by calling our own server-side calculator. The
     * preview-only call doesn't touch HMRC; the existing /period/preview
     * endpoint isn't aware of the cumulative shape, so we POST with a
     * sentinel ?dry_run=1 if available, otherwise we just show the
     * inputs and let the user confirm-and-submit (server-side calculator
     * recomputes anyway on submission).
     *
     * For now we drive the preview by calling the cumulative submission
     * endpoint with ?preview=1 - if not implemented server-side we fall
     * back to showing the obligation window only.
     */
    async function loadPreview(taxYear, periodId, endDate) {
        const url = '/api/hmrc/period/cumulative/' + encodeURIComponent(taxYear)
            + '?preview=1';
        const body = periodId ? { period_id: periodId } : { period_end_date: endDate };
        // Note: this preview endpoint is not part of Phase 2.1 commit 3.
        // We fail silently and show the empty panel, which the user can
        // still submit (server recomputes on submission).
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: getJSONHeaders ? getJSONHeaders() : {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                body: JSON.stringify(body),
            });
            if (!res.ok) return null;
            const json = await res.json();
            if (!json.success) return null;
            return json;
        } catch (e) {
            return null;
        }
    }

    /**
     * Public entry point - called from settings-hmrc.js when the user
     * clicks "Submit" on an open obligation.
     */
    async function openCumulativePanel(periodId, taxYear, endDate) {
        state.periodId = periodId;
        state.taxYear = normaliseTaxYear(taxYear);
        state.endDate = endDate;

        $('cumulativePanelPeriod').textContent = periodId || ('to ' + formatDate(endDate));
        $('cumulativeStartDate').textContent = '06 Apr ' + state.taxYear.split('-')[0];
        $('cumulativeEndDate').textContent = formatDate(endDate);

        showPanel();

        // Try to fetch a server-computed preview. If unavailable, show an
        // empty content block - the server will compute the real figures
        // when the user clicks Submit.
        const preview = await loadPreview(state.taxYear, state.periodId, state.endDate);
        $('cumulativeLoading').classList.add('d-none');
        $('cumulativeContent').classList.remove('d-none');

        if (preview && preview.data) {
            const sub = preview.data.submission_data || preview.data;
            $('cumulativeTurnover').textContent = formatGBP(
                ((sub.periodIncome || {}).turnover) || 0
            );
            $('cumulativeOther').textContent = formatGBP(
                ((sub.periodIncome || {}).other) || 0
            );
            renderExpenses(sub.periodExpenses);
            renderBreakdown(preview.breakdown || []);
        } else {
            $('cumulativeTurnover').textContent = '—';
            $('cumulativeOther').textContent = '—';
            renderExpenses({});
            renderBreakdown([]);
        }
    }

    function buildResultHTML(kind, body) {
        return '<div class="alert alert-' + kind + ' mb-0">' + body + '</div>';
    }

    function showResult(kind, html) {
        const el = $('cumulativeResult');
        el.innerHTML = buildResultHTML(kind, html);
        el.classList.remove('d-none');
    }

    async function submit() {
        const submitBtn = $('cumulativeSubmitBtn');
        if (submitBtn.disabled) return;

        const nino = (typeof localStorage !== 'undefined' && localStorage.getItem('hmrc_nino')) || '';
        const businessId = (typeof localStorage !== 'undefined' && localStorage.getItem('hmrc_business_id')) || '';

        if (!nino || !businessId) {
            showResult('warning',
                'Please configure your NINO and Business ID in HMRC settings first.');
            return;
        }

        const url = '/api/hmrc/period/cumulative/' + encodeURIComponent(state.taxYear);
        const body = {
            nino: nino,
            business_id: businessId,
        };
        if (state.periodId) {
            body.period_id = state.periodId;
        } else if (state.endDate) {
            body.period_end_date = state.endDate;
        }

        submitBtn.disabled = true;
        const original = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting…';

        try {
            const headers = (typeof getJSONHeaders === 'function')
                ? getJSONHeaders()
                : { 'Content-Type': 'application/json', 'Accept': 'application/json' };
            const res = await fetch(url, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(body),
            });
            const json = await res.json().catch(() => ({}));

            if (res.ok && json.success) {
                const receipt = (json.data && json.data.id) ? json.data.id : 'pending';
                showResult('success',
                    '<h6 class="mb-2"><i class="fas fa-check-circle"></i> Submission accepted by HMRC</h6>'
                    + '<p class="mb-1">Receipt ID: <span class="receipt-id">' + escapeHtml(receipt) + '</span></p>'
                    + '<p class="mb-0">Your records for this period are now locked.</p>');
                lockPanel();
                if (typeof loadObligations === 'function') {
                    loadObligations();
                }
                if (typeof loadSubmissions === 'function') {
                    loadSubmissions();
                }
                return;
            }

            if (res.status === 409) {
                const existingId = json.existing_submission_id;
                const existingReceipt = json.hmrc_receipt_id || '—';
                showResult('warning',
                    '<h6 class="mb-2"><i class="fas fa-info-circle"></i> Already submitted</h6>'
                    + '<p class="mb-1">' + escapeHtml(json.error || 'A submission for this period already exists.') + '</p>'
                    + '<p class="mb-0 small">Existing submission #' + escapeHtml(existingId)
                    + ', receipt <span class="receipt-id">' + escapeHtml(existingReceipt) + '</span></p>');
                lockPanel();
                return;
            }

            if (res.status === 422 && Array.isArray(json.validation_errors) && json.validation_errors.length > 0) {
                let html = '<h6 class="mb-2"><i class="fas fa-exclamation-circle"></i> HMRC rejected the submission</h6>'
                    + '<p class="mb-2">' + escapeHtml(json.error || 'Validation failed') + '</p>'
                    + '<ul class="mb-0">';
                json.validation_errors.forEach(err => {
                    html += '<li><strong>' + escapeHtml(err.field || 'unknown') + ':</strong> '
                        + escapeHtml(err.message || '') + '</li>';
                });
                html += '</ul>';
                showResult('danger', html);
                submitBtn.disabled = false;
                submitBtn.innerHTML = original;
                return;
            }

            if (res.status >= 500) {
                showResult('danger',
                    '<h6 class="mb-2"><i class="fas fa-exclamation-triangle"></i> HMRC service error</h6>'
                    + '<p class="mb-0">HMRC could not process the submission right now. Please try again in a few minutes.</p>');
                submitBtn.disabled = false;
                submitBtn.innerHTML = original;
                return;
            }

            showResult('danger',
                '<h6 class="mb-2"><i class="fas fa-times-circle"></i> Submission failed</h6>'
                + '<p class="mb-0">' + escapeHtml(json.error || ('HTTP ' + res.status)) + '</p>');
            submitBtn.disabled = false;
            submitBtn.innerHTML = original;

        } catch (err) {
            showResult('danger',
                '<h6 class="mb-2"><i class="fas fa-times-circle"></i> Network error</h6>'
                + '<p class="mb-0">' + escapeHtml(err.message || 'Could not reach the server.') + '</p>');
            submitBtn.disabled = false;
            submitBtn.innerHTML = original;
        }
    }

    function init() {
        const checkbox = $('cumulativeConfirmCheckbox');
        const submitBtn = $('cumulativeSubmitBtn');
        const closeBtn = $('cumulativePanelClose');
        const cancelBtn = $('cumulativePanelCancel');

        if (checkbox && submitBtn) {
            checkbox.addEventListener('change', function () {
                submitBtn.disabled = !checkbox.checked;
            });
        }
        if (submitBtn) {
            submitBtn.addEventListener('click', submit);
        }
        if (closeBtn) closeBtn.addEventListener('click', hidePanel);
        if (cancelBtn) cancelBtn.addEventListener('click', hidePanel);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Public API used by settings-hmrc.js.
    window.HMRCCumulative = {
        open: openCumulativePanel,
        close: hidePanel,
    };
})();
