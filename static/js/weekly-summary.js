/**
 * Weekly Summary Report Module
 * Handles the weekly performance report tab in the Reports page
 */

let currentWeekStart = null;

// Initialize weekly summary when page loads
function initWeeklySummary() {
    const weeklyTab = document.getElementById('weekly-summary-tab');
    const weeklyPane = document.getElementById('weekly-summary');
    
    console.log('Initializing weekly summary...');
    console.log('weeklyTab:', weeklyTab);
    console.log('weeklyPane:', weeklyPane);
    
    if (weeklyTab) {
        // Load when tab is shown
        weeklyTab.addEventListener('shown.bs.tab', () => {
            console.log('Tab shown event fired');
            if (!currentWeekStart) {
                window.currentWeek();
            }
        });
        
        // Load if it's the active tab on page load
        if (weeklyTab.classList.contains('active')) {
            console.log('Tab is active on load, loading data...');
            window.currentWeek();
        }
    }
    
    // Also check if the pane is active
    if (weeklyPane && weeklyPane.classList.contains('show', 'active')) {
        console.log('Pane is active on load, loading data...');
        window.currentWeek();
    }
}

// Try both DOMContentLoaded and load events
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWeeklySummary);
} else {
    // DOM already loaded
    initWeeklySummary();
}

window.addEventListener('load', initWeeklySummary);

// Navigation functions - exposed globally for onclick handlers
window.currentWeek = function() {
    currentWeekStart = null;
    loadWeeklySummary();
}

window.previousWeek = function() {
    if (!currentWeekStart) return;
    const date = new Date(currentWeekStart);
    date.setDate(date.getDate() - 7);
    currentWeekStart = date.toISOString().split('T')[0];
    loadWeeklySummary();
}

window.nextWeek = function() {
    if (!currentWeekStart) {
        window.currentWeek();
        return;
    }
    const date = new Date(currentWeekStart);
    date.setDate(date.getDate() + 7);
    currentWeekStart = date.toISOString().split('T')[0];
    loadWeeklySummary();
}

// Load weekly summary data from API
async function loadWeeklySummary() {
    try {
        const url = currentWeekStart 
            ? `/api/weekly-summary?week_start=${currentWeekStart}`
            : '/api/weekly-summary';
        
        console.log('Loading weekly summary from:', url);
        
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('Weekly summary data received:', data);
        
        if (data.error) {
            console.error('API returned error:', data.error);
            showError('Error loading weekly summary: ' + data.error);
            return;
        }
        
        // Store the week start for navigation
        if (!currentWeekStart) {
            // Convert DD/MM/YYYY to YYYY-MM-DD
            const parts = data.week_start.split('/');
            currentWeekStart = `${parts[2]}-${parts[1]}-${parts[0]}`;
        }
        
        displayWeeklySummary(data);
    } catch (error) {
        console.error('Error loading weekly summary:', error);
        console.error('Error stack:', error.stack);
        showError('Failed to load weekly summary: ' + error.message);
    }
}

// Display weekly summary data in the UI
function displayWeeklySummary(data) {
    // Fallback currency formatter if CurrencyFormatter is not available
    const formatCurrency = (value) => {
        if (typeof CurrencyFormatter !== 'undefined') {
            return CurrencyFormatter.format(value);
        }
        // Fallback formatting
        return '£' + (value || 0).toFixed(2);
    };
    
    // Update week label with week number
    const weekLabel = document.getElementById('weekLabel');
    console.log('weekLabel element:', weekLabel);
    console.log('Setting week label to:', `Week ${data.week_number} - ${data.week_label}`);
    if (weekLabel) {
        weekLabel.textContent = `Week ${data.week_number} - ${data.week_label}`;
    } else {
        console.error('weekLabel element not found!');
    }
    
    // Summary Cards
    const summaryCards = document.getElementById('weeklySummaryCards');
    const discrepancyClass = data.summary.discrepancies > 0 ? 'text-danger' : 'text-success';
    summaryCards.innerHTML = `
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body">
                    <h6 class="text-muted mb-2">Total Jobs</h6>
                    <h3 class="mb-0">${data.summary.total_jobs}</h3>
                    <small class="text-muted">${data.summary.working_days} working days</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body">
                    <h6 class="text-muted mb-2">Total Earnings</h6>
                    <h3 class="mb-0">${formatCurrency(data.summary.total_earnings)}</h3>
                    <small class="text-success">${formatCurrency(data.metrics.avg_earnings_per_day)}/day</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body">
                    <h6 class="text-muted mb-2">Completion Rate</h6>
                    <h3 class="mb-0">${data.summary.completion_rate}%</h3>
                    <small class="text-success">Jobs completed</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body">
                    <h6 class="text-muted mb-2">Discrepancies</h6>
                    <h3 class="mb-0 ${discrepancyClass}">${data.summary.discrepancies}</h3>
                    <small class="text-muted">Missing from runsheets</small>
                </div>
            </div>
        </div>
    `;
    
    // Status Breakdown - Simple table
    const statusBreakdown = document.getElementById('weeklyStatusBreakdown');
    let statusHTML = '<div class="table-responsive"><table class="table"><tbody>';
    
    const statusConfig = {
        'completed': { label: 'Completed', class: 'success' },
        'extra': { label: 'Extra', class: 'info' },
        'DNCO': { label: 'DNCO', class: 'warning' },
        'dnco': { label: 'DNCO', class: 'warning' },
        'missed': { label: 'Missed', class: 'danger' },
        'pending': { label: 'Pending', class: 'secondary' }
    };
    
    for (const [status, info] of Object.entries(data.status_breakdown)) {
        const config = statusConfig[status] || { label: status, class: 'secondary' };
        
        // Show estimated loss for DNCO jobs
        let earningsDisplay = formatCurrency(info.earnings);
        if ((status === 'DNCO' || status === 'dnco') && info.estimated_loss) {
            earningsDisplay = `${formatCurrency(info.earnings)}<br><small class="text-danger">Est. loss: ${formatCurrency(info.estimated_loss)}</small>`;
        }
        
        statusHTML += `
            <tr>
                <td><strong>${config.label}</strong></td>
                <td><span class="badge bg-${config.class}">${info.count} jobs</span></td>
                <td class="text-end"><strong>${earningsDisplay}</strong></td>
            </tr>
        `;
    }
    statusHTML += '</tbody></table></div>';
    statusBreakdown.innerHTML = statusHTML;
    
    // Daily Breakdown
    const dailyBreakdown = document.getElementById('weeklyDailyBreakdown');
    dailyBreakdown.innerHTML = data.daily_breakdown.map(day => {
        const mileageData = data.mileage_data.find(m => m.date === day.date) || {};
        return `
            <tr>
                <td><strong>${day.day_name}</strong></td>
                <td>${day.date}</td>
                <td><strong>${day.jobs}</strong></td>
                <td><span class="badge bg-success">${day.completed}</span></td>
                <td><span class="badge bg-info">${day.extra}</span></td>
                <td><span class="badge bg-warning">${day.dnco}</span></td>
                <td><span class="badge bg-secondary">${day.pending}</span></td>
                <td><strong>${formatCurrency(day.earnings)}</strong></td>
                <td>${mileageData.mileage || 0} mi</td>
                <td>${formatCurrency(mileageData.fuel_cost || 0)}</td>
            </tr>
        `;
    }).join('');
    
    // Performance Metrics
    const metrics = document.getElementById('weeklyMetrics');
    metrics.innerHTML = `
        <div class="col-md-3">
            <div class="text-center p-3 bg-light rounded">
                <h4 class="text-primary">${data.metrics.avg_jobs_per_day}</h4>
                <small class="text-muted">Avg Jobs/Day</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="text-center p-3 bg-light rounded">
                <h4 class="text-primary">${formatCurrency(data.metrics.avg_earnings_per_day)}</h4>
                <small class="text-muted">Avg Earnings/Day</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="text-center p-3 bg-light rounded">
                <h4 class="text-primary">${formatCurrency(data.metrics.avg_earnings_per_job)}</h4>
                <small class="text-muted">Avg Earnings/Job</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="text-center p-3 bg-light rounded">
                <h4 class="text-primary">${formatCurrency(data.metrics.earnings_per_mile)}</h4>
                <small class="text-muted">Earnings/Mile</small>
            </div>
        </div>
    `;
    
    // Mileage Summary (inside performance metrics card)
    const mileageSummary = document.getElementById('weeklyMileageSummary');
    mileageSummary.innerHTML = `
        <div class="col-md-4">
            <div class="text-center p-3 bg-light rounded">
                <h5 class="text-primary">${data.summary.total_mileage} mi</h5>
                <small class="text-muted">Total Mileage</small>
            </div>
        </div>
        <div class="col-md-4">
            <div class="text-center p-3 bg-light rounded">
                <h5 class="text-primary">${formatCurrency(data.summary.total_fuel_cost)}</h5>
                <small class="text-muted">Total Fuel Cost</small>
            </div>
        </div>
        <div class="col-md-4">
            <div class="text-center p-3 bg-light rounded">
                <h5 class="text-primary">${formatCurrency(data.metrics.cost_per_mile)}</h5>
                <small class="text-muted">Cost per Mile</small>
            </div>
        </div>
    `;
    
    // Top Customers
    const topCustomers = document.getElementById('weeklyTopCustomers');
    topCustomers.innerHTML = data.top_customers.map((customer, index) => `
        <tr>
            <td>${customer.customer}</td>
            <td><span class="badge bg-primary">${customer.jobs}</span></td>
            <td><strong>${formatCurrency(customer.earnings)}</strong></td>
        </tr>
    `).join('');
    
    // Job Types
    const jobTypes = document.getElementById('weeklyJobTypes');
    jobTypes.innerHTML = data.job_types.map(type => `
        <tr>
            <td>${type.type}</td>
            <td class="text-end"><span class="badge bg-info">${type.count}</span></td>
        </tr>
    `).join('');
}
