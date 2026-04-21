/**
 * Tax Estimator - dashboard widget + compact pill.
 *
 * Fetches a YTD tax-estimate breakdown from /api/tax/estimate and renders
 * it into whatever container(s) happen to be on the current page:
 *
 *   - #taxEstimatorWidget   Full widget (e.g. /wages)
 *   - #taxEstimatorPill     Compact pill (e.g. /runsheets landing)
 *   - #taxEstimatorModal    Detail modal (any page with the widget)
 *
 * Missing containers are skipped, so one script works across all pages.
 *
 * The data refreshes every 60s while the tab is visible and re-fetches
 * immediately when the tab becomes visible again after being hidden.
 */

(function () {
    'use strict';

    const REFRESH_MS = 60 * 1000;
    let refreshTimer = null;
    let lastData = null;

    // -- Utilities --------------------------------------------------------

    function fmtGBP(n) {
        if (n === null || n === undefined || Number.isNaN(n)) return '\u00a30.00';
        return new Intl.NumberFormat('en-GB', {
            style: 'currency', currency: 'GBP', minimumFractionDigits: 2,
        }).format(n);
    }

    function fmtInt(n) {
        if (n === null || n === undefined) return '0';
        return new Intl.NumberFormat('en-GB').format(n);
    }

    function fmtDate(iso) {
        if (!iso) return '-';
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return iso;
        return d.toLocaleDateString('en-GB', {
            day: '2-digit', month: 'short', year: 'numeric',
        });
    }

    function fmtRate(r) {
        return `${Math.round(r * 100)}%`;
    }

    // -- Fetch ------------------------------------------------------------

    async function fetchEstimate() {
        try {
            const res = await fetch('/api/tax/estimate', {
                credentials: 'same-origin',
                headers: {Accept: 'application/json'},
            });
            if (!res.ok) {
                console.warn('Tax estimate request failed:', res.status);
                return null;
            }
            const payload = await res.json();
            if (!payload.success) {
                console.warn('Tax estimate API returned error:', payload.error);
                return null;
            }
            return payload.data;
        } catch (err) {
            console.error('Tax estimate fetch error:', err);
            return null;
        }
    }

    // -- Rendering: full widget ------------------------------------------

    function renderFullWidget(data) {
        const root = document.getElementById('taxEstimatorWidget');
        if (!root) return;

        if (!data) {
            root.innerHTML = `
                <div class="tax-estimator-card tax-estimator-error">
                    <i class="bi bi-exclamation-triangle"></i>
                    Could not load tax estimate. Check your connection and try again.
                </div>`;
            return;
        }

        const warningsHtml = (data.warnings || []).map(w =>
            `<li class="small text-warning"><i class="bi bi-exclamation-circle me-1"></i>${w}</li>`
        ).join('');

        root.innerHTML = `
            <div class="tax-estimator-card" role="button" tabindex="0"
                 data-bs-toggle="modal" data-bs-target="#taxEstimatorModal"
                 aria-label="Open tax estimate breakdown">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <div class="tax-estimator-label">
                            <i class="bi bi-calculator me-1"></i>
                            Estimated tax owed
                        </div>
                        <div class="text-muted small">Tax year ${data.tax_year}</div>
                    </div>
                    <span class="badge bg-primary-subtle text-primary border border-primary-subtle">
                        <i class="bi bi-chevron-right"></i>
                    </span>
                </div>

                <div class="tax-estimator-total">${fmtGBP(data.total_tax_owed)}</div>

                <div class="progress tax-estimator-progress mt-3" role="progressbar"
                     aria-label="Tax year progress"
                     aria-valuemin="0" aria-valuemax="100"
                     aria-valuenow="${data.progress.percent_complete}">
                    <div class="progress-bar" style="width: ${data.progress.percent_complete}%"></div>
                </div>
                <div class="d-flex justify-content-between small text-muted mt-1">
                    <span>${fmtInt(data.progress.days_elapsed)} of ${fmtInt(data.progress.total_days)} days</span>
                    <span>${data.progress.percent_complete}% through year</span>
                </div>

                <hr class="my-3">

                <dl class="row mb-0 small">
                    <dt class="col-6 text-muted fw-normal">YTD income</dt>
                    <dd class="col-6 text-end mb-1">${fmtGBP(data.income.gross)}</dd>

                    <dt class="col-6 text-muted fw-normal">Allowable expenses</dt>
                    <dd class="col-6 text-end mb-1">-${fmtGBP(data.expenses.allowable_total)}</dd>

                    <dt class="col-6 text-muted fw-normal">Personal allowance</dt>
                    <dd class="col-6 text-end mb-1">-${fmtGBP(data.profile_personal_allowance || data.profit.personal_allowance)}</dd>

                    <dt class="col-6 fw-semibold">Taxable profit</dt>
                    <dd class="col-6 text-end mb-0 fw-semibold">${fmtGBP(data.profit.taxable_profit)}</dd>
                </dl>

                ${warningsHtml ? `<ul class="list-unstyled mt-3 mb-0">${warningsHtml}</ul>` : ''}

                <div class="text-muted small mt-3 text-end">
                    <i class="bi bi-clock me-1"></i>
                    Updated ${fmtDate(data.generated_at)} \u00b7 Tap for breakdown
                </div>
            </div>`;
    }

    // -- Rendering: compact pill -----------------------------------------

    function renderCompactPill(data) {
        const root = document.getElementById('taxEstimatorPill');
        if (!root) return;

        if (!data) {
            root.classList.add('d-none');
            return;
        }

        root.classList.remove('d-none');
        root.innerHTML = `
            <a href="/wages#taxEstimatorWidget" class="tax-estimator-pill"
               title="Tax year ${data.tax_year} \u00b7 tap for full breakdown">
                <i class="bi bi-calculator"></i>
                <span class="tax-estimator-pill-label">Tax owed YTD</span>
                <strong>${fmtGBP(data.total_tax_owed)}</strong>
            </a>`;
    }

    // -- Rendering: detail modal -----------------------------------------

    function renderDetailModal(data) {
        const body = document.getElementById('taxEstimatorModalBody');
        if (!body) return;

        if (!data) {
            body.innerHTML = '<p class="text-danger">Could not load tax estimate.</p>';
            return;
        }

        const incomeTaxRows = (data.income_tax.bands || []).map(b => `
            <tr>
                <td>
                    ${fmtGBP(b.lower)} \u2013
                    ${b.upper === null ? 'no ceiling' : fmtGBP(b.upper)}
                </td>
                <td class="text-end">${fmtRate(b.rate)}</td>
                <td class="text-end">${fmtGBP(b.amount_in_band)}</td>
                <td class="text-end">${fmtGBP(b.tax)}</td>
            </tr>`).join('');

        const ni4Rows = (data.class_4_ni.bands || []).map(b => `
            <tr>
                <td>
                    ${fmtGBP(b.lower)} \u2013
                    ${b.upper === null ? 'no ceiling' : fmtGBP(b.upper)}
                </td>
                <td class="text-end">${fmtRate(b.rate)}</td>
                <td class="text-end">${fmtGBP(b.amount_in_band)}</td>
                <td class="text-end">${fmtGBP(b.tax)}</td>
            </tr>`).join('');

        const catRows = (data.expenses.by_category || []).map(c => `
            <tr class="${c.allowable ? '' : 'text-muted'}">
                <td>
                    ${c.category_name}
                    ${c.allowable ? '' : '<span class="badge bg-secondary ms-1">excluded</span>'}
                </td>
                <td>${c.hmrc_box || ''}</td>
                <td class="text-end">${fmtInt(c.count)}</td>
                <td class="text-end">${fmtGBP(c.total)}</td>
            </tr>`).join('');

        const warnings = (data.warnings || []).map(w =>
            `<li class="small text-warning-emphasis"><i class="bi bi-exclamation-circle me-1"></i>${w}</li>`
        ).join('');

        body.innerHTML = `
            <div class="mb-3">
                <h6 class="text-uppercase text-muted small">Year to date</h6>
                <dl class="row mb-0">
                    <dt class="col-sm-5">Tax year</dt>
                    <dd class="col-sm-7">${data.tax_year}
                        <span class="text-muted small">
                            (${fmtDate(data.progress.start_date)} \u2013 ${fmtDate(data.progress.end_date)},
                            ${data.progress.percent_complete}% complete)
                        </span>
                    </dd>

                    <dt class="col-sm-5">Gross income</dt>
                    <dd class="col-sm-7">
                        ${fmtGBP(data.income.gross)}
                        <span class="text-muted small">
                            (${fmtInt(data.income.payslip_count)} payslip${data.income.payslip_count === 1 ? '' : 's'})
                        </span>
                    </dd>

                    <dt class="col-sm-5">Allowable expenses</dt>
                    <dd class="col-sm-7">${fmtGBP(data.expenses.allowable_total)}</dd>

                    ${data.expenses.excluded_total > 0 ? `
                    <dt class="col-sm-5 text-muted">Excluded (depreciation)</dt>
                    <dd class="col-sm-7 text-muted">${fmtGBP(data.expenses.excluded_total)}</dd>` : ''}

                    <dt class="col-sm-5">Profit</dt>
                    <dd class="col-sm-7">${fmtGBP(data.profit.gross_profit)}</dd>

                    <dt class="col-sm-5">Personal allowance</dt>
                    <dd class="col-sm-7">${fmtGBP(data.profit.personal_allowance)}</dd>

                    <dt class="col-sm-5 fw-semibold">Taxable profit</dt>
                    <dd class="col-sm-7 fw-semibold">${fmtGBP(data.profit.taxable_profit)}</dd>
                </dl>
            </div>

            <h6 class="text-uppercase text-muted small mt-4">Income tax</h6>
            <div class="table-responsive">
                <table class="table table-sm mb-2">
                    <thead>
                        <tr><th>Band</th><th class="text-end">Rate</th>
                            <th class="text-end">In band</th><th class="text-end">Tax</th></tr>
                    </thead>
                    <tbody>${incomeTaxRows}</tbody>
                    <tfoot>
                        <tr><th colspan="3" class="text-end">Total income tax</th>
                            <th class="text-end">${fmtGBP(data.income_tax.total)}</th></tr>
                    </tfoot>
                </table>
            </div>

            <h6 class="text-uppercase text-muted small mt-4">Class 4 National Insurance</h6>
            <div class="table-responsive">
                <table class="table table-sm mb-2">
                    <thead>
                        <tr><th>Band</th><th class="text-end">Rate</th>
                            <th class="text-end">In band</th><th class="text-end">NI</th></tr>
                    </thead>
                    <tbody>${ni4Rows}</tbody>
                    <tfoot>
                        <tr><th colspan="3" class="text-end">Total Class 4 NI</th>
                            <th class="text-end">${fmtGBP(data.class_4_ni.total)}</th></tr>
                    </tfoot>
                </table>
            </div>

            <div class="alert alert-primary d-flex justify-content-between align-items-center mt-3">
                <div>
                    <strong>Total estimated tax owed</strong>
                    <div class="text-muted small">Income tax + Class 4 NI (Class 2 NI abolished April 2024)</div>
                </div>
                <span class="h4 mb-0">${fmtGBP(data.total_tax_owed)}</span>
            </div>

            ${catRows ? `
            <h6 class="text-uppercase text-muted small mt-4">Expenses by category</h6>
            <div class="table-responsive">
                <table class="table table-sm mb-2">
                    <thead>
                        <tr><th>Category</th><th>HMRC box</th>
                            <th class="text-end">Count</th><th class="text-end">Total</th></tr>
                    </thead>
                    <tbody>${catRows}</tbody>
                </table>
            </div>` : ''}

            ${warnings ? `<ul class="list-unstyled mt-3">${warnings}</ul>` : ''}

            <div class="alert alert-light border small mt-3 mb-0">
                <i class="bi bi-info-circle me-1"></i>
                ${data.disclaimer}
            </div>`;
    }

    // -- Orchestration ----------------------------------------------------

    async function refresh() {
        const data = await fetchEstimate();
        lastData = data;
        renderFullWidget(data);
        renderCompactPill(data);
        renderDetailModal(data);
    }

    function startRefreshTimer() {
        stopRefreshTimer();
        refreshTimer = setInterval(refresh, REFRESH_MS);
    }

    function stopRefreshTimer() {
        if (refreshTimer) {
            clearInterval(refreshTimer);
            refreshTimer = null;
        }
    }

    function onVisibilityChange() {
        if (document.hidden) {
            stopRefreshTimer();
        } else {
            refresh();
            startRefreshTimer();
        }
    }

    function init() {
        // Only bother fetching if at least one container is on the page.
        const hasAnyContainer =
            document.getElementById('taxEstimatorWidget') ||
            document.getElementById('taxEstimatorPill') ||
            document.getElementById('taxEstimatorModalBody');
        if (!hasAnyContainer) return;

        refresh();
        startRefreshTimer();
        document.addEventListener('visibilitychange', onVisibilityChange);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose for manual debugging / testing.
    window.TaxEstimator = {refresh, get lastData() { return lastData; }};
})();
