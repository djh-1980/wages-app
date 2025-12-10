// Comprehensive Earnings Analytics Module
console.log('🟢 earnings-analytics.js loaded successfully');

// Global chart variables
let monthlyTrendsChart = null;
let earningsPerJobChart = null;
let customerBreakdownChart = null;
let activityBreakdownChart = null;
let jobStatusChart = null;

// Load analytics when tab is shown
document.addEventListener('DOMContentLoaded', function() {
    const analyticsTab = document.getElementById('analytics-tab');
    if (analyticsTab) {
        analyticsTab.addEventListener('shown.bs.tab', function() {
            loadEarningsAnalytics();
        });
    }
});

// Main function to load all analytics
async function loadEarningsAnalytics() {
    console.log('Loading comprehensive earnings analytics...');
    
    // Show loading spinner
    document.getElementById('analyticsLoadingSpinner').style.display = 'block';
    document.getElementById('analyticsContent').style.display = 'none';
    
    try {
        const response = await fetch('/api/earnings-analytics');
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load analytics');
        }
        
        console.log('Analytics data loaded:', data);
        
        // Render all sections
        renderForecast(data.forecast, data.year_comparison);
        renderYearComparison(data.year_comparison);
        renderMonthlyTrends(data.monthly_trends);
        renderPerformanceMetrics(data.performance_metrics);
        renderCustomerBreakdown(data.customer_breakdown);
        renderActivityBreakdown(data.activity_breakdown);
        renderBestWorstWeeks(data.best_weeks, data.worst_weeks);
        renderJobStatusBreakdown(data.job_status_breakdown);
        renderCompletionStats(data.completion_stats);
        
        // Hide loading, show content
        document.getElementById('analyticsLoadingSpinner').style.display = 'none';
        document.getElementById('analyticsContent').style.display = 'block';
        
    } catch (error) {
        console.error('Error loading earnings analytics:', error);
        document.getElementById('analyticsLoadingSpinner').innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> Error loading analytics: ${error.message}
            </div>
        `;
    }
}

// Render Forecast Section
function renderForecast(forecast, yearComparison) {
    const currentYear = yearComparison[0]; // Most recent year
    const progressPercent = (forecast.weeks_worked / 52 * 100).toFixed(1);
    
    document.getElementById('forecastCards').innerHTML = `
        <div class="col-md-3">
            <div class="text-center p-3 bg-light rounded">
                <h6 class="text-muted mb-1">Weeks Worked</h6>
                <h3 class="text-primary mb-0">${forecast.weeks_worked}</h3>
                <small class="text-muted">${forecast.weeks_remaining} remaining</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="text-center p-3 bg-light rounded">
                <h6 class="text-muted mb-1">Total Earned</h6>
                <h3 class="text-success mb-0">${formatCurrency(forecast.total_earned)}</h3>
                <small class="text-muted">Year to date</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="text-center p-3 bg-light rounded">
                <h6 class="text-muted mb-1">Average Weekly</h6>
                <h3 class="text-info mb-0">${formatCurrency(forecast.avg_weekly)}</h3>
                <small class="text-muted">Current pace</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="text-center p-3 bg-light rounded">
                <h6 class="text-muted mb-1">Projected Year End</h6>
                <h3 class="text-warning mb-0">${formatCurrency(forecast.projected_year_end)}</h3>
                <small class="text-muted">At current pace</small>
            </div>
        </div>
    `;
    
    document.getElementById('yearProgressBar').style.width = progressPercent + '%';
    document.getElementById('yearProgressText').textContent = `${progressPercent}% Complete (Week ${forecast.weeks_worked} of 52)`;
}

// Render Year Comparison Cards
function renderYearComparison(yearComparison) {
    let html = '<div class="row g-3">';
    
    yearComparison.forEach((year, index) => {
        const isCurrentYear = index === 0;
        const cardClass = isCurrentYear ? 'border-primary' : '';
        const badge = isCurrentYear ? '<span class="badge bg-primary ms-2">Current</span>' : '';
        
        html += `
            <div class="col-md-6 col-lg-3">
                <div class="card ${cardClass} h-100">
                    <div class="card-body">
                        <h5 class="card-title">
                            ${year.tax_year}${badge}
                        </h5>
                        <hr>
                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-muted">Weeks:</span>
                            <strong>${year.weeks_worked}</strong>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-muted">Total:</span>
                            <strong class="text-success">${formatCurrency(year.total_earnings)}</strong>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-muted">Avg/Week:</span>
                            <strong>${formatCurrency(year.avg_weekly)}</strong>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-muted">Best:</span>
                            <strong class="text-primary">${formatCurrency(year.best_week)}</strong>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span class="text-muted">Worst:</span>
                            <strong class="text-danger">${formatCurrency(year.worst_week)}</strong>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    document.getElementById('yearComparisonCards').innerHTML = html;
}

// Render Monthly Trends Chart
function renderMonthlyTrends(monthlyTrends) {
    const ctx = document.getElementById('monthlyTrendsChart').getContext('2d');
    
    if (monthlyTrendsChart) {
        monthlyTrendsChart.destroy();
    }
    
    // Group by year
    const yearData = {};
    monthlyTrends.forEach(row => {
        if (!yearData[row.tax_year]) {
            yearData[row.tax_year] = [];
        }
        yearData[row.tax_year].push(row);
    });
    
    const datasets = [];
    const colors = ['#667eea', '#764ba2', '#43e97b', '#fa709a'];
    let colorIndex = 0;
    
    Object.keys(yearData).sort().reverse().forEach(year => {
        datasets.push({
            label: year,
            data: yearData[year].map(d => ({x: d.month_num, y: d.total_earnings})),
            borderColor: colors[colorIndex % colors.length],
            backgroundColor: colors[colorIndex % colors.length] + '40',
            borderWidth: 2,
            tension: 0.4,
            fill: true
        });
        colorIndex++;
    });
    
    monthlyTrendsChart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'top' },
                tooltip: {
                    callbacks: {
                        label: (context) => `${context.dataset.label}: ${formatCurrency(context.parsed.y)}`
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: { display: true, text: 'Month' },
                    min: 1,
                    max: 12,
                    ticks: { stepSize: 1 }
                },
                y: {
                    title: { display: true, text: 'Total Earnings (£)' },
                    ticks: {
                        callback: (value) => formatCurrency(value)
                    }
                }
            }
        }
    });
}

// Render Performance Metrics (Earnings per Job)
function renderPerformanceMetrics(metrics) {
    const ctx = document.getElementById('earningsPerJobChart').getContext('2d');
    
    if (earningsPerJobChart) {
        earningsPerJobChart.destroy();
    }
    
    const labels = metrics.map(m => `W${m.week_number}`).reverse();
    const data = metrics.map(m => m.earnings_per_job || 0).reverse();
    
    earningsPerJobChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Earnings per Job',
                data: data,
                borderColor: '#fbbf24',
                backgroundColor: 'rgba(251, 191, 36, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => `${formatCurrency(context.parsed.y)} per job`
                    }
                }
            },
            scales: {
                y: {
                    ticks: {
                        callback: (value) => formatCurrency(value)
                    }
                }
            }
        }
    });
}

// Render Customer Breakdown Chart
function renderCustomerBreakdown(customers) {
    const ctx = document.getElementById('customerBreakdownChart').getContext('2d');
    
    if (customerBreakdownChart) {
        customerBreakdownChart.destroy();
    }
    
    const top10 = customers.slice(0, 10);
    
    customerBreakdownChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: top10.map(c => truncate(c.client, 20)),
            datasets: [{
                label: 'Total Earnings',
                data: top10.map(c => c.total_earnings),
                backgroundColor: '#667eea',
                borderColor: '#667eea',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const customer = top10[context.dataIndex];
                            return [
                                `Earnings: ${formatCurrency(customer.total_earnings)}`,
                                `Jobs: ${customer.job_count}`,
                                `Avg: ${formatCurrency(customer.avg_per_job)}`,
                                `Share: ${customer.percentage}%`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        callback: (value) => formatCurrency(value)
                    }
                }
            }
        }
    });
}

// Render Activity Breakdown Chart
function renderActivityBreakdown(activities) {
    const ctx = document.getElementById('activityBreakdownChart').getContext('2d');
    
    if (activityBreakdownChart) {
        activityBreakdownChart.destroy();
    }
    
    activityBreakdownChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: activities.map(a => a.activity || 'Unknown'),
            datasets: [{
                data: activities.map(a => a.total_earnings),
                backgroundColor: [
                    '#667eea', '#764ba2', '#43e97b', '#fa709a',
                    '#fee140', '#30cfd0', '#a8edea', '#fed6e3',
                    '#c471ed', '#f64f59'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right' },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const activity = activities[context.dataIndex];
                            return [
                                `${activity.activity}`,
                                `Earnings: ${formatCurrency(activity.total_earnings)}`,
                                `Jobs: ${activity.job_count}`,
                                `Avg: ${formatCurrency(activity.avg_per_job)}`
                            ];
                        }
                    }
                }
            }
        }
    });
}

// Render Best/Worst Weeks
function renderBestWorstWeeks(bestWeeks, worstWeeks) {
    // Best weeks
    let bestHtml = '<div class="list-group">';
    bestWeeks.forEach((week, index) => {
        bestHtml += `
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <span class="badge bg-warning text-dark me-2">#${index + 1}</span>
                    <strong>Week ${week.week_number}, ${week.tax_year}</strong>
                    <br>
                    <small class="text-muted">${week.pay_date} • ${week.job_count} jobs</small>
                </div>
                <h5 class="mb-0 text-success">${formatCurrency(week.net_payment)}</h5>
            </div>
        `;
    });
    bestHtml += '</div>';
    document.getElementById('bestWeeksList').innerHTML = bestHtml;
    
    // Worst weeks
    let worstHtml = '<div class="list-group">';
    worstWeeks.forEach((week, index) => {
        worstHtml += `
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <span class="badge bg-secondary me-2">#${index + 1}</span>
                    <strong>Week ${week.week_number}, ${week.tax_year}</strong>
                    <br>
                    <small class="text-muted">${week.pay_date} • ${week.job_count} jobs</small>
                </div>
                <h5 class="mb-0 text-danger">${formatCurrency(week.net_payment)}</h5>
            </div>
        `;
    });
    worstHtml += '</div>';
    document.getElementById('worstWeeksList').innerHTML = worstHtml;
}

// Render Job Status Breakdown
function renderJobStatusBreakdown(jobStatus) {
    const ctx = document.getElementById('jobStatusChart').getContext('2d');
    
    if (jobStatusChart) {
        jobStatusChart.destroy();
    }
    
    jobStatusChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: jobStatus.map(s => s.status.charAt(0).toUpperCase() + s.status.slice(1)),
            datasets: [{
                data: jobStatus.map(s => s.total_earnings),
                backgroundColor: ['#667eea', '#43e97b']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const status = jobStatus[context.dataIndex];
                            const total = jobStatus.reduce((sum, s) => sum + s.total_earnings, 0);
                            const percentage = ((status.total_earnings / total) * 100).toFixed(1);
                            return [
                                `${status.status}: ${formatCurrency(status.total_earnings)}`,
                                `${status.count} jobs (${percentage}%)`
                            ];
                        }
                    }
                }
            }
        }
    });
}

// Render Completion Statistics
function renderCompletionStats(stats) {
    document.getElementById('completionStats').innerHTML = `
        <div class="row">
            <div class="col-md-4">
                <h2 class="text-success">${stats.completion_rate}%</h2>
                <p class="text-muted mb-0">Completion Rate</p>
            </div>
            <div class="col-md-4">
                <h2 class="text-primary">${stats.total_jobs.toLocaleString()}</h2>
                <p class="text-muted mb-0">Total Jobs</p>
            </div>
            <div class="col-md-4">
                <h2 class="text-info">${formatCurrency(stats.total_earnings)}</h2>
                <p class="text-muted mb-0">Total Earnings</p>
            </div>
        </div>
    `;
}

// Helper function to truncate text
function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}
