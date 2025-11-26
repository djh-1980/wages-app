/**
 * Weekly Summary Report Module
 * Handles the weekly performance report tab in the Reports page
 */

let currentWeekStart = null;

// Initialize weekly summary when page loads
function initWeeklySummary() {
    const weeklyTab = document.getElementById('weekly-summary-tab');
    const weeklyPane = document.getElementById('weekly-summary');
    
    if (weeklyTab) {
        // Load when tab is shown
        weeklyTab.addEventListener('shown.bs.tab', () => {
            if (!currentWeekStart) {
                window.currentWeek();
            }
        });
        
        // Load if it's the active tab on page load
        if (weeklyTab.classList.contains('active')) {
            window.currentWeek();
        }
    }
    
    // Also check if the pane is active
    if (weeklyPane && weeklyPane.classList.contains('show', 'active')) {
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
async function loadWeeklySummary(weekStart = null) {
    // Update currentWeekStart if a new week is provided
    if (weekStart) {
        currentWeekStart = weekStart;
        console.log('Updated currentWeekStart to:', currentWeekStart);
    }
    try {
        const url = currentWeekStart 
            ? `/api/weekly-summary?week_start=${currentWeekStart}`
            : '/api/weekly-summary';
        
        console.log('Loading weekly summary from:', url);
        
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('Weekly summary data received:', data);
        
        // Handle redirect to latest available week
        if (data.redirect && data.latest_week_start) {
            console.log('Redirecting to latest week:', data.latest_week_start);
            console.log('Current week start:', currentWeekStart);
            console.log('Message:', data.message || 'Redirecting to latest available week');
            
            // Convert DD/MM/YYYY to YYYY-MM-DD for comparison
            const [day, month, year] = data.latest_week_start.split('/');
            const isoDate = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
            console.log('Target ISO date:', isoDate);
            
            // Prevent infinite loops by checking if we're already trying this week
            if (currentWeekStart === isoDate) {
                console.error('Infinite redirect detected - already on target week, stopping');
                showError('Unable to load weekly summary - the latest available week also has no data');
                return;
            }
            
            // Set a flag to prevent multiple redirects
            if (window.weeklyRedirectCount && window.weeklyRedirectCount > 3) {
                console.error('Too many redirects, stopping');
                showError('Unable to load weekly summary - multiple redirect attempts failed');
                return;
            }
            
            window.weeklyRedirectCount = (window.weeklyRedirectCount || 0) + 1;
            console.log('Redirect attempt:', window.weeklyRedirectCount);
            
            loadWeeklySummary(isoDate);
            return;
        }
        
        if (data.error) {
            console.error('API returned error:', data.error);
            showError('Error loading weekly summary: ' + data.error);
            return;
        }
        
        // Reset redirect counter on successful load
        window.weeklyRedirectCount = 0;
        
        // Always update currentWeekStart to match the actual data being displayed
        // Convert DD/MM/YYYY to YYYY-MM-DD
        const parts = data.week_start.split('/');
        currentWeekStart = `${parts[2]}-${parts[1]}-${parts[0]}`;
        console.log('Updated currentWeekStart to match displayed data:', currentWeekStart);
        
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
    if (weekLabel) {
        weekLabel.textContent = `Week ${data.week_number} - ${data.week_label}`;
    }
    
    // Check for verbal confirmation for this week
    let verbalConfirmation = null;
    if (data.week_number && typeof checkVerbalMatch === 'function') {
        // Fetch verbal confirmation asynchronously
        fetch(`/api/verbal-pay/confirmations/week/${data.week_number}/year/2025`)
            .then(response => response.json())
            .then(result => {
                if (result.success && result.confirmation) {
                    verbalConfirmation = result.confirmation;
                    // Update the earnings card with verbal info
                    updateEarningsCardWithVerbal(verbalConfirmation, data.summary.total_earnings);
                }
            })
            .catch(error => console.error('Error fetching verbal confirmation:', error));
    }
    
    // Check for missing mileage data and show alert
    const missingMileageDates = data.summary.missing_mileage_dates || [];
    const hasMissingMileage = missingMileageDates.length > 0;
    
    // Add alert banner if there's missing mileage
    let alertHTML = '';
    if (hasMissingMileage) {
        const datesList = missingMileageDates.map(date => {
            const dayName = new Date(date.split('/').reverse().join('-')).toLocaleDateString('en-GB', { weekday: 'short' });
            return `<strong>${dayName} ${date}</strong>`;
        }).join(', ');
        
        alertHTML = `
            <div class="alert alert-warning alert-dismissible fade show mb-3" role="alert">
                <i class="bi bi-exclamation-triangle-fill"></i>
                <strong>Missing Mileage Data!</strong> 
                Please add mileage for: ${datesList}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
    }
    
    // Insert alert before summary cards
    const summaryCards = document.getElementById('weeklySummaryCards');
    const parentContainer = summaryCards.parentElement;
    
    // Remove any existing alerts
    const existingAlerts = parentContainer.querySelectorAll('.alert-warning');
    existingAlerts.forEach(alert => alert.remove());
    
    // Add new alert if needed
    if (alertHTML) {
        summaryCards.insertAdjacentHTML('beforebegin', alertHTML);
    }
    
    const discrepancyClass = data.summary.discrepancies > 0 ? 'text-danger' : 'text-success';
    
    // Check for earnings discrepancy
    const earningsDiscrepancy = data.summary.earnings_discrepancy || 0;
    const hasEarningsDiscrepancy = Math.abs(earningsDiscrepancy) > 0.01;
    const earningsDiscrepancyClass = hasEarningsDiscrepancy ? 'text-danger' : 'text-success';
    const earningsDiscrepancyText = hasEarningsDiscrepancy 
        ? `<small class="text-danger">Payslip diff: ${formatCurrency(earningsDiscrepancy)}</small>`
        : `<small class="text-success">Matches payslip ✓</small>`;
    
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
                    ${earningsDiscrepancyText}
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body">
                    <h6 class="text-muted mb-2">Completion Rate</h6>
                    <h3 class="mb-0">${data.summary.completion_rate}%</h3>
                    <small class="text-muted">Successfully completed</small>
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
        'PDA Licence': { label: 'PDA Licence', class: 'secondary' },
        'SASER Auto Billing': { label: 'SASER Auto Billing', class: 'secondary' },
        'missed': { label: 'Missed', class: 'danger' },
        'pending': { label: 'Pending', class: 'secondary' }
    };
    
    // Merge DNCO and dnco entries
    const mergedBreakdown = {...data.status_breakdown};
    if (mergedBreakdown['DNCO'] && mergedBreakdown['dnco']) {
        // Merge dnco into DNCO
        mergedBreakdown['DNCO'] = {
            count: mergedBreakdown['DNCO'].count + mergedBreakdown['dnco'].count,
            earnings: mergedBreakdown['DNCO'].earnings + mergedBreakdown['dnco'].earnings,
            estimated_loss: (mergedBreakdown['DNCO'].estimated_loss || 0) + (mergedBreakdown['dnco'].estimated_loss || 0)
        };
        delete mergedBreakdown['dnco'];
    } else if (mergedBreakdown['dnco']) {
        // Only dnco exists, rename it to DNCO
        mergedBreakdown['DNCO'] = mergedBreakdown['dnco'];
        delete mergedBreakdown['dnco'];
    }
    
    // Define the order we want to display statuses
    const statusOrder = ['completed', 'extra', 'DNCO', 'PDA Licence', 'SASER Auto Billing', 'missed', 'pending'];
    
    // First, display statuses in the specified order
    for (const status of statusOrder) {
        if (mergedBreakdown[status]) {
            const info = mergedBreakdown[status];
            const config = statusConfig[status] || { label: status, class: 'secondary' };
            
            // Show estimated loss for DNCO jobs
            let earningsDisplay = formatCurrency(info.earnings);
            if (status === 'DNCO' && info.estimated_loss) {
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
    }
    
    // Then add any remaining statuses not in the order list
    for (const [status, info] of Object.entries(mergedBreakdown)) {
        if (!statusOrder.includes(status)) {
            const config = statusConfig[status] || { label: status, class: 'secondary' };
            statusHTML += `
                <tr>
                    <td><strong>${config.label}</strong></td>
                    <td><span class="badge bg-${config.class}">${info.count} jobs</span></td>
                    <td class="text-end"><strong>${formatCurrency(info.earnings)}</strong></td>
                </tr>
            `;
        }
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

// Update earnings card with verbal confirmation info
function updateEarningsCardWithVerbal(verbalConfirmation, totalEarnings) {
    const formatCurrency = (value) => {
        if (typeof CurrencyFormatter !== 'undefined') {
            return CurrencyFormatter.format(value);
        }
        return '£' + (value || 0).toFixed(2);
    };
    
    const summaryCards = document.getElementById('weeklySummaryCards');
    const earningsCard = summaryCards.querySelector('.col-md-3:nth-child(2) .card-body');
    
    if (earningsCard) {
        const verbalAmount = verbalConfirmation.verbal_amount;
        const matched = Math.abs(verbalAmount - totalEarnings) < 0.01;
        const difference = totalEarnings - verbalAmount;
        
        let verbalHTML = '';
        if (matched) {
            verbalHTML = `<small class="text-success"><i class="bi bi-check-circle-fill"></i> Matches verbal (${formatCurrency(verbalAmount)})</small>`;
        } else {
            const diffText = difference > 0 ? `+${formatCurrency(difference)}` : formatCurrency(difference);
            verbalHTML = `<small class="text-warning"><i class="bi bi-exclamation-triangle-fill"></i> Verbal: ${formatCurrency(verbalAmount)} (${diffText})</small>`;
        }
        
        // Find and update the earnings discrepancy text
        const existingSmall = earningsCard.querySelector('small');
        if (existingSmall) {
            existingSmall.outerHTML = verbalHTML;
        } else {
            earningsCard.innerHTML += `<br>${verbalHTML}`;
        }
    }
}

// Export weekly summary as PDF
window.exportWeeklySummaryPDF = function() {
    if (!currentWeekStart) {
        alert('Please load a week first');
        return;
    }
    
    // Show loading state
    const btn = event.target.closest('button');
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Generating PDF...';
    
    // Make POST request to export endpoint
    fetch('/api/weekly-summary/export-pdf', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            week_start: currentWeekStart
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to generate PDF');
        }
        return response.blob();
    })
    .then(blob => {
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `weekly_summary_${currentWeekStart.replace(/\//g, '-')}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        // Reset button
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    })
    .catch(error => {
        console.error('Error generating PDF:', error);
        alert('Failed to generate PDF. Please try again.');
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    });
}
