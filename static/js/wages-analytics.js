/**
 * Wages page - Analytics tab "Tax Year Overview" section.
 *
 * Fetches /api/wages/analytics and renders:
 *   - 4 KPI cards (gross YTD, expenses YTD, net profit YTD, avg weekly)
 *   - 5 Chart.js charts (weekly trend, YoY cumulative, monthly I/E,
 *     top expense categories, jobs per day of week)
 *
 * Chart colour palette matches the rest of the app (Bootstrap primary /
 * success / danger / info / warning). Charts are destroyed and rebuilt
 * on every tax-year change so switching years never stacks canvases.
 */

(function () {
    'use strict';

    const charts = {
        weekly: null,
        yoy: null,
        monthly: null,
        topExpenses: null,
        jobsDow: null,
    };

    let loaded = false;
    let loadingPromise = null;

    // ---- helpers -----------------------------------------------------------
    function currency(value) {
        const n = Number(value || 0);
        return n.toLocaleString('en-GB', {
            style: 'currency',
            currency: 'GBP',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function toggleLoading(spinnerId, canvasId, showSpinner) {
        const spinner = document.getElementById(spinnerId);
        const canvas = document.getElementById(canvasId);
        if (spinner) spinner.classList.toggle('d-none', !showSpinner);
        if (canvas) canvas.classList.toggle('d-none', showSpinner);
    }

    function destroyChart(key) {
        if (charts[key]) {
            charts[key].destroy();
            charts[key] = null;
        }
    }

    // ---- KPI cards ---------------------------------------------------------
    function renderKpis(kpis, taxYearLabel) {
        document.getElementById('kpiGrossYtd').textContent = currency(kpis.gross_income_ytd);
        document.getElementById('kpiExpensesYtd').textContent = currency(kpis.allowable_expenses_ytd);

        const netEl = document.getElementById('kpiNetProfitYtd');
        netEl.textContent = currency(kpis.net_profit_ytd);
        netEl.classList.toggle('text-danger', kpis.net_profit_ytd < 0);
        netEl.classList.toggle('text-success', kpis.net_profit_ytd >= 0);

        document.getElementById('kpiAvgWeekly').textContent = currency(kpis.avg_weekly_earnings);
        const weeksEl = document.getElementById('kpiWeeksCompleted');
        if (weeksEl) {
            const w = kpis.weeks_completed || 0;
            weeksEl.textContent = `${w} week${w === 1 ? '' : 's'} in ${taxYearLabel}`;
        }
    }

    // ---- Chart 1: weekly earnings trend -----------------------------------
    function renderWeeklyEarnings(rows) {
        destroyChart('weekly');
        const ctx = document.getElementById('weeklyEarningsChart');
        if (!ctx) return;

        const labels = rows.map(r => `W${r.week_number}`);
        const data = rows.map(r => r.gross);

        charts.weekly = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Gross Earnings',
                    data,
                    backgroundColor: 'rgba(25, 135, 84, 0.75)',
                    borderColor: 'rgba(25, 135, 84, 1)',
                    borderWidth: 1,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => currency(ctx.parsed.y),
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: (v) => '£' + v },
                    },
                },
            },
        });
        toggleLoading('loadingWeeklyEarnings', 'weeklyEarningsChart', false);
    }

    // ---- Chart 2: YoY cumulative ------------------------------------------
    function renderYearComparison(yoy, currentKey) {
        destroyChart('yoy');
        const ctx = document.getElementById('yoyCumulativeChart');
        if (!ctx) return;

        const palette = ['#0d6efd', '#6c757d', '#198754', '#dc3545'];
        // Use weeks 1..52 as the shared x-axis.
        const labels = Array.from({ length: 52 }, (_, i) => `W${i + 1}`);

        const datasets = Object.entries(yoy).map(([year, series], i) => {
            const byWeek = new Map(series.map(p => [p.week, p.cumulative]));
            let lastVal = null;
            const data = labels.map((_, idx) => {
                const w = idx + 1;
                if (byWeek.has(w)) {
                    lastVal = byWeek.get(w);
                    return lastVal;
                }
                // No data for this week yet - don't invent points for the
                // current (incomplete) year so the line stops at the latest
                // real data point.
                return year === currentKey ? null : lastVal;
            });
            const colour = palette[i % palette.length];
            const isCurrent = year === currentKey;
            return {
                label: year + (isCurrent ? ' (current)' : ''),
                data,
                borderColor: colour,
                backgroundColor: colour + '20',
                borderWidth: isCurrent ? 3 : 2,
                tension: 0.25,
                fill: false,
                spanGaps: false,
                pointRadius: 0,
                pointHoverRadius: 4,
            };
        });

        charts.yoy = new Chart(ctx, {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (c) => `${c.dataset.label}: ${currency(c.parsed.y)}`,
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: (v) => '£' + (v / 1000).toFixed(0) + 'k' },
                    },
                },
            },
        });
        toggleLoading('loadingYearComparison', 'yoyCumulativeChart', false);
    }

    // ---- Chart 3: monthly income vs expenses ------------------------------
    function renderMonthlyIncomeExpenses(months) {
        destroyChart('monthly');
        const ctx = document.getElementById('monthlyIncomeExpensesChart');
        if (!ctx) return;

        const labels = months.map(m => m.label);
        const income = months.map(m => m.income);
        const expenses = months.map(m => m.expenses);

        charts.monthly = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Income',
                        data: income,
                        backgroundColor: 'rgba(25, 135, 84, 0.8)',
                        stack: 'money',
                    },
                    {
                        label: 'Expenses',
                        data: expenses,
                        backgroundColor: 'rgba(220, 53, 69, 0.8)',
                        stack: 'money',
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (c) => `${c.dataset.label}: ${currency(c.parsed.y)}`,
                        },
                    },
                },
                scales: {
                    x: { stacked: true },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        ticks: { callback: (v) => '£' + v },
                    },
                },
            },
        });
        toggleLoading('loadingMonthlyIE', 'monthlyIncomeExpensesChart', false);
    }

    // ---- Chart 4: top expense categories ----------------------------------
    function renderTopExpenses(categories) {
        destroyChart('topExpenses');
        const ctx = document.getElementById('topExpensesChart');
        if (!ctx) return;

        if (!categories || categories.length === 0) {
            toggleLoading('loadingTopExpenses', 'topExpensesChart', false);
            const parent = ctx.parentElement;
            if (parent) {
                parent.insertAdjacentHTML('beforeend',
                    '<div class="text-center text-muted py-4" id="topExpensesEmpty">No expenses recorded for this tax year yet.</div>');
            }
            return;
        }
        const emptyMsg = document.getElementById('topExpensesEmpty');
        if (emptyMsg) emptyMsg.remove();

        charts.topExpenses = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: categories.map(c => c.category_name),
                datasets: [{
                    label: 'Spend',
                    data: categories.map(c => c.total),
                    backgroundColor: 'rgba(220, 53, 69, 0.75)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 1,
                }],
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (c) => currency(c.parsed.x),
                        },
                    },
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: { callback: (v) => '£' + v },
                    },
                },
            },
        });
        toggleLoading('loadingTopExpenses', 'topExpensesChart', false);
    }

    // ---- Chart 5: jobs per day of week ------------------------------------
    function renderJobsPerDow(rows) {
        destroyChart('jobsDow');
        const ctx = document.getElementById('jobsPerDowChart');
        if (!ctx) return;

        charts.jobsDow = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: rows.map(r => r.day),
                datasets: [{
                    label: 'Avg jobs',
                    data: rows.map(r => r.avg_jobs),
                    backgroundColor: 'rgba(13, 110, 253, 0.75)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 1,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (c) => {
                                const row = rows[c.dataIndex];
                                return `${row.avg_jobs.toFixed(2)} avg (${row.total_jobs} jobs over ${row.days_worked} days)`;
                            },
                        },
                    },
                },
                scales: {
                    y: { beginAtZero: true },
                },
            },
        });
        toggleLoading('loadingJobsDow', 'jobsPerDowChart', false);
    }

    // ---- Tax year dropdown -------------------------------------------------
    function populateTaxYearSelect(available, selectedKey) {
        const select = document.getElementById('analyticsTaxYearFilter');
        if (!select) return;
        // Only repopulate once; subsequent renders just re-select.
        if (!select.dataset.populated) {
            select.innerHTML = '';
            available.forEach(y => {
                const opt = document.createElement('option');
                opt.value = y.key;
                opt.textContent = y.label;
                select.appendChild(opt);
            });
            select.dataset.populated = '1';
            select.addEventListener('change', () => {
                loadAnalytics(select.value);
            });
        }
        select.value = selectedKey;
    }

    function showAllLoading() {
        toggleLoading('loadingWeeklyEarnings', 'weeklyEarningsChart', true);
        toggleLoading('loadingYearComparison', 'yoyCumulativeChart', true);
        toggleLoading('loadingMonthlyIE', 'monthlyIncomeExpensesChart', true);
        toggleLoading('loadingTopExpenses', 'topExpensesChart', true);
        toggleLoading('loadingJobsDow', 'jobsPerDowChart', true);
    }

    // ---- Main fetch+render -------------------------------------------------
    async function loadAnalytics(taxYear) {
        showAllLoading();
        const url = taxYear
            ? `/api/wages/analytics?tax_year=${encodeURIComponent(taxYear)}`
            : '/api/wages/analytics';
        try {
            const res = await fetch(url);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const body = await res.json();
            if (!body.success) throw new Error(body.error || 'Unknown error');
            const d = body.data;

            populateTaxYearSelect(d.available_tax_years, d.tax_year.key);
            renderKpis(d.kpis, d.tax_year.label);
            renderWeeklyEarnings(d.weekly_earnings);
            renderYearComparison(d.year_comparison, d.tax_year.key);
            renderMonthlyIncomeExpenses(d.monthly_income_expenses);
            renderTopExpenses(d.top_expense_categories);
            renderJobsPerDow(d.jobs_per_dow);
            loaded = true;
        } catch (err) {
            console.error('Failed to load wages analytics:', err);
            ['loadingWeeklyEarnings', 'loadingYearComparison', 'loadingMonthlyIE',
             'loadingTopExpenses', 'loadingJobsDow'].forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.innerHTML = `<div class="text-danger"><i class="bi bi-exclamation-triangle"></i> Failed to load: ${err.message}</div>`;
                }
            });
        }
    }

    // Lazy-load the first time the Analytics tab is shown; already-loaded
    // charts stay mounted to avoid re-fetching on every tab click.
    document.addEventListener('DOMContentLoaded', function () {
        const tab = document.getElementById('analytics-tab');
        if (!tab) return;
        tab.addEventListener('shown.bs.tab', function () {
            if (loaded || loadingPromise) return;
            loadingPromise = loadAnalytics().finally(() => { loadingPromise = null; });
        });
    });
})();
