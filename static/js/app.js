// Main application JavaScript

// Global variables
let weeklyChart = null;
let clientsChart = null;
let jobTypesChart = null;

// Global state
let currentReportData = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Set current date (if element exists)
    const currentDateEl = document.getElementById('currentDate');
    if (currentDateEl) {
        currentDateEl.textContent = new Date().toLocaleDateString('en-GB', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    }
    
    // Load initial data
    loadSummary();
    loadTaxYears(); // This will also load the weekly trend with default year
    loadCustomFilterOptions();
    
    // Setup event listeners
    setupEventListeners();
    
    // TEST: Load payslips immediately to see if function works
    console.log('🧪 Testing payslips load on page load...');
    setTimeout(() => {
        if (typeof window.loadPayslips === 'function') {
            console.log('✓ loadPayslips function exists');
            window.loadPayslips();
        } else {
            console.error('❌ loadPayslips function not found!');
        }
    }, 2000);
});

function setupEventListeners() {
    // Tab change events - use Bootstrap's shown.bs.tab event (with null checks)
    const payslipsTab = document.getElementById('payslips-tab');
    if (payslipsTab) {
        payslipsTab.addEventListener('shown.bs.tab', function() {
            loadPayslips();
        });
    }
    
    const clientsTab = document.getElementById('clients-tab');
    if (clientsTab) {
        clientsTab.addEventListener('shown.bs.tab', loadClients);
    }
    
    const jobsTab = document.getElementById('jobs-tab');
    if (jobsTab) {
        jobsTab.addEventListener('shown.bs.tab', loadJobTypes);
    }
    
    const settingsTab = document.getElementById('settings-tab');
    if (settingsTab) {
        settingsTab.addEventListener('shown.bs.tab', loadSettings);
    }
    
    // Tax year filter
    const taxYearFilter = document.getElementById('taxYearFilter');
    if (taxYearFilter) {
        taxYearFilter.addEventListener('change', function() {
            loadPayslips(this.value);
        });
    }
    
    // Search input with debounce (if exists)
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(this.value);
            }, 500);
        });
    }
}

// Load summary statistics
async function loadSummary() {
    try {
        const response = await fetch('/api/summary');
        const data = await response.json();
        
        // Update summary cards
        document.getElementById('totalEarnings').textContent = formatCurrency(data.overall.total_earnings);
        document.getElementById('avgWeekly').textContent = formatCurrency(data.overall.avg_weekly);
        document.getElementById('totalJobs').textContent = data.overall.total_jobs.toLocaleString();
        document.getElementById('bestWeek').textContent = formatCurrency(data.best_week.net_payment);
        document.getElementById('bestWeekInfo').textContent = `Week ${data.best_week.week_number}, ${data.best_week.tax_year}`;
        
        // Update current tax year info
        document.getElementById('currentTaxYear').textContent = data.current_year.tax_year;
        document.getElementById('currentYearWeeks').textContent = data.current_year.weeks;
        document.getElementById('currentYearTotal').textContent = formatCurrency(data.current_year.total);
        document.getElementById('currentYearAvg').textContent = formatCurrency(data.current_year.avg);
        document.getElementById('last4WeeksAvg').textContent = formatCurrency(data.last_4_weeks_avg);
        
        // Load top clients for dashboard
        loadTopClients();
        
    } catch (error) {
        console.error('Error loading summary:', error);
        showError('Failed to load summary data');
    }
}

// Update weekly trend when year filter changes
function updateWeeklyTrend() {
    const selectedYear = document.getElementById('trendYearFilter').value;
    loadWeeklyTrend(selectedYear);
}

// Load weekly trend chart
async function loadWeeklyTrend(taxYear = '') {
    try {
        const url = taxYear 
            ? `/api/weekly_trend?tax_year=${taxYear}` 
            : '/api/weekly_trend?limit=26';
        const response = await fetch(url);
        const data = await response.json();
        
        const ctx = document.getElementById('weeklyChart').getContext('2d');
        
        if (weeklyChart) {
            weeklyChart.destroy();
        }
        
        weeklyChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => `${d.tax_year} W${d.week_number}`),
                datasets: [{
                    label: 'Net Payment',
                    data: data.map(d => d.net_payment),
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return 'Earnings: £' + context.parsed.y.toFixed(2);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '£' + value.toFixed(0);
                            }
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Error loading weekly trend:', error);
    }
}

// Load top clients for dashboard
async function loadTopClients() {
    try {
        const response = await fetch('/api/clients?limit=5');
        const data = await response.json();
        
        const html = data.map((client, index) => `
            <div class="card border-0 bg-light mb-2">
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <small class="text-muted">#${index + 1}</small>
                            <div class="fw-bold">${truncate(client.client, 30)}</div>
                            <small class="text-muted">${client.job_count} jobs</small>
                        </div>
                        <div class="text-end">
                            <div class="fw-bold text-success">${formatCurrency(client.total_amount)}</div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        document.getElementById('topClientsList').innerHTML = html;
        
    } catch (error) {
        console.error('Error loading top clients:', error);
    }
}

// Global sort order for payslips
let payslipSortOrder = 'desc'; // 'desc' = newest first, 'asc' = oldest first

// Toggle payslip sort order
window.togglePayslipSort = function() {
    payslipSortOrder = payslipSortOrder === 'desc' ? 'asc' : 'desc';
    
    const btn = document.getElementById('sortOrderBtn');
    if (payslipSortOrder === 'desc') {
        btn.innerHTML = '<i class="bi bi-sort-down"></i> Newest First';
    } else {
        btn.innerHTML = '<i class="bi bi-sort-up"></i> Oldest First';
    }
    
    // Reload payslips with current filter
    const taxYearFilter = document.getElementById('taxYearFilter');
    loadPayslips(taxYearFilter ? taxYearFilter.value : '');
}

// Load all payslips
window.loadPayslips = async function(taxYear = '') {
    console.log('=== loadPayslips called ===');
    console.log('Tax year filter:', taxYear);
    console.log('Sort order:', payslipSortOrder);
    
    const tbody = document.getElementById('payslipsTableBody');
    
    if (!tbody) {
        console.error('❌ payslipsTableBody element not found!');
        alert('Error: Table body element not found. Check console.');
        return;
    }
    
    console.log('✓ Table body element found');
    
    // Show loading state
    tbody.innerHTML = '<tr><td colspan="6" class="text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></td></tr>';
    console.log('✓ Loading spinner displayed');
    
    try {
        const url = taxYear ? `/api/payslips?tax_year=${taxYear}` : '/api/payslips';
        console.log('📡 Fetching payslips from:', url);
        
        // Add timeout to prevent hanging
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
        
        const response = await fetch(url, { signal: controller.signal });
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        let data = await response.json();
        console.log('Received payslips:', data.length);
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No payslips found</td></tr>';
            return;
        }
        
        // Sort data based on current sort order
        data.sort((a, b) => {
            const yearCompare = a.tax_year.localeCompare(b.tax_year);
            if (yearCompare !== 0) {
                return payslipSortOrder === 'desc' ? -yearCompare : yearCompare;
            }
            return payslipSortOrder === 'desc' ? b.week_number - a.week_number : a.week_number - b.week_number;
        });
        
        tbody.innerHTML = data.map(p => `
            <tr>
                <td><span class="badge bg-primary">${p.tax_year}</span></td>
                <td>Week ${p.week_number}</td>
                <td>${p.pay_date || 'N/A'}</td>
                <td class="text-end"><strong class="text-success">${formatCurrency(p.net_payment)}</strong></td>
                <td class="text-center"><span class="badge bg-info">${p.job_count || 0} jobs</span></td>
                <td class="text-center">
                    <button class="btn btn-sm btn-outline-primary" onclick="viewPayslip(${p.id})">
                        <i class="bi bi-eye"></i> View
                    </button>
                </td>
            </tr>
        `).join('');
        
    } catch (error) {
        console.error('Error loading payslips:', error);
        
        let errorMessage = error.message;
        if (error.name === 'AbortError') {
            errorMessage = 'Request timed out. Server may be slow or not responding.';
        }
        
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">
            <i class="bi bi-exclamation-triangle"></i> Error loading payslips: ${errorMessage}
            <br><small>Check browser console for details</small>
            <br><button class="btn btn-sm btn-primary mt-2" onclick="loadPayslips()">Retry</button>
        </td></tr>`;
    }
}

// Load clients data
async function loadClients() {
    try {
        const response = await fetch('/api/clients?limit=20');
        const data = await response.json();
        
        // Update table
        const tbody = document.getElementById('clientsTable');
        tbody.innerHTML = data.map((c, index) => `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <span class="badge bg-secondary me-2">${index + 1}</span>
                        ${truncate(c.client, 40)}
                    </div>
                </td>
                <td class="hide-mobile"><span class="badge bg-info">${c.job_count}</span></td>
                <td><strong class="text-success">${formatCurrency(c.total_amount)}</strong></td>
                <td class="hide-mobile">${formatCurrency(c.avg_amount)}</td>
            </tr>
        `).join('');
        
        // Update chart
        const ctx = document.getElementById('clientsChart').getContext('2d');
        
        if (clientsChart) {
            clientsChart.destroy();
        }
        
        const top10 = data.slice(0, 10);
        
        clientsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: top10.map(c => truncate(c.client, 20)),
                datasets: [{
                    label: 'Total Earnings',
                    data: top10.map(c => c.total_amount),
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: '#667eea',
                    borderWidth: 2,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return 'Total: £' + context.parsed.y.toFixed(2);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '£' + value.toFixed(0);
                            }
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Error loading clients:', error);
    }
}

// Load job types data
async function loadJobTypes() {
    try {
        const response = await fetch('/api/job_types?limit=20');
        const data = await response.json();
        
        // Update table
        const tbody = document.getElementById('jobTypesTable');
        tbody.innerHTML = data.map((j, index) => `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <span class="badge bg-secondary me-2">${index + 1}</span>
                        ${truncate(j.job_type, 40)}
                    </div>
                </td>
                <td class="hide-mobile"><span class="badge bg-info">${j.job_count}</span></td>
                <td><strong class="text-success">${formatCurrency(j.total_amount)}</strong></td>
                <td class="hide-mobile">${formatCurrency(j.avg_amount)}</td>
            </tr>
        `).join('');
        
        // Update chart
        const ctx = document.getElementById('jobTypesChart').getContext('2d');
        
        if (jobTypesChart) {
            jobTypesChart.destroy();
        }
        
        const top10 = data.slice(0, 10);
        
        jobTypesChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: top10.map(j => truncate(j.job_type, 25)),
                datasets: [{
                    data: top10.map(j => j.job_count),
                    backgroundColor: [
                        '#667eea', '#764ba2', '#f093fb', '#4facfe',
                        '#43e97b', '#fa709a', '#fee140', '#30cfd0',
                        '#a8edea', '#fed6e3'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            boxWidth: 15,
                            padding: 10
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Error loading job types:', error);
    }
}

// Load tax years for filter
async function loadTaxYears() {
    try {
        const response = await fetch('/api/tax_years');
        const years = await response.json();
        
        // Populate payslips filter (if exists)
        const select = document.getElementById('taxYearFilter');
        if (select) {
            select.innerHTML = ''; // Clear existing options
            
            // Add "All Years" option
            const allOption = document.createElement('option');
            allOption.value = '';
            allOption.textContent = 'All Years';
            select.appendChild(allOption);
            
            // Add year options
            years.forEach(year => {
                const option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                select.appendChild(option);
            });
        }
        
        // Populate dashboard trend filter (if exists)
        const trendFilter = document.getElementById('trendYearFilter');
        if (trendFilter) {
            trendFilter.innerHTML = ''; // Clear existing options
            
            years.forEach((year, index) => {
                const option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                if (index === 0) {
                    option.selected = true; // Select most recent year by default
                }
                trendFilter.appendChild(option);
            });
            
            // Load trend for the default (most recent) year
            if (years.length > 0) {
                loadWeeklyTrend(years[0]);
            }
        }
        
        // Populate report filters (if exist)
        const reportTaxYear = document.getElementById('reportTaxYear');
        const reportMonthlyYear = document.getElementById('reportMonthlyYear');
        
        if (reportTaxYear && reportMonthlyYear) {
            years.forEach(year => {
                const option1 = document.createElement('option');
                option1.value = year;
                option1.textContent = year;
                reportTaxYear.appendChild(option1);
                
                const option2 = document.createElement('option');
                option2.value = year;
                option2.textContent = year;
                reportMonthlyYear.appendChild(option2);
            });
        }
        
        // Populate upload year filter (add future years + existing years)
        const uploadYearFilter = document.getElementById('uploadTaxYear');
        if (uploadYearFilter) {
            uploadYearFilter.innerHTML = ''; // Clear existing
            
            // Add future years
            const currentYear = new Date().getFullYear();
            for (let y = currentYear + 2; y >= currentYear; y--) {
                const option = document.createElement('option');
                option.value = y;
                option.textContent = y;
                if (y === currentYear) option.selected = true;
                uploadYearFilter.appendChild(option);
            }
            
            // Add existing years from database
            years.forEach(year => {
                if (year < currentYear) {
                    const option = document.createElement('option');
                    option.value = year;
                    option.textContent = year;
                    uploadYearFilter.appendChild(option);
                }
            });
            
            // Add older years for historical uploads
            for (let y = currentYear - 1; y >= 2015; y--) {
                if (!years.includes(y.toString())) {
                    const option = document.createElement('option');
                    option.value = y;
                    option.textContent = y;
                    uploadYearFilter.appendChild(option);
                }
            }
        }
        
    } catch (error) {
        console.error('Error loading tax years:', error);
    }
}

// View payslip detail
async function viewPayslip(payslipId) {
    const modalEl = document.getElementById('payslipModal');
    if (!modalEl) {
        alert('Payslip modal not found');
        return;
    }
    
    const modal = new bootstrap.Modal(modalEl, {
        backdrop: true,
        keyboard: true,
        focus: true
    });
    const modalBody = document.getElementById('payslipModalBody');
    
    modalBody.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
    
    modal.show();
    
    try {
        const response = await fetch(`/api/payslip/${payslipId}`);
        const data = await response.json();
        
        const p = data.payslip;
        
        let html = `
            <div class="row mb-3">
                <div class="col-md-6">
                    <h6 class="text-muted">Tax Year ${p.tax_year}, Week ${p.week_number}</h6>
                    <p class="mb-1"><strong>Pay Date:</strong> ${p.pay_date || 'N/A'}</p>
                    <p class="mb-1"><strong>Period End:</strong> ${p.period_end || 'N/A'}</p>
                    <p class="mb-1"><strong>Verification:</strong> ${p.verification_number || 'N/A'}</p>
                </div>
                <div class="col-md-6 text-end">
                    <div class="card bg-light border-0">
                        <div class="card-body">
                            <p class="mb-1 text-muted">Net Payment</p>
                            <h3 class="text-success mb-0">${formatCurrency(p.net_payment)}</h3>
                        </div>
                    </div>
                </div>
            </div>
            
            <hr>
            
            <h6 class="mb-3">Financial Summary</h6>
            <div class="row mb-3">
                <div class="col-6">
                    <small class="text-muted">Gross Payment:</small>
                    <div><strong>${formatCurrency(p.gross_subcontractor_payment)}</strong></div>
                </div>
                <div class="col-6">
                    <small class="text-muted">YTD:</small>
                    <div><strong>${formatCurrency(p.gross_subcontractor_payment_ytd)}</strong></div>
                </div>
            </div>
            
            <hr>
            
            <h6 class="mb-3">Job Items (${data.jobs.length})</h6>
            <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                <table class="table table-sm table-hover">
                    <thead class="table-light sticky-top">
                        <tr>
                            <th>Job #</th>
                            <th>Client</th>
                            <th>Job Type</th>
                            <th>Location</th>
                            <th>Date/Time</th>
                            <th class="text-end">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        data.jobs.forEach(job => {
            const dateTime = job.date ? `${job.date} ${job.time || ''}`.trim() : 'N/A';
            html += `
                <tr>
                    <td><small class="text-muted">#${job.job_number || 'N/A'}</small></td>
                    <td>${truncate(job.client || 'N/A', 25)}</td>
                    <td><small>${truncate(job.job_type || 'N/A', 20)}</small></td>
                    <td><small>${truncate(job.location || 'N/A', 20)}</small></td>
                    <td><small class="text-muted">${dateTime}</small></td>
                    <td class="text-end"><strong>${formatCurrency(job.amount)}</strong></td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        modalBody.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading payslip detail:', error);
        modalBody.innerHTML = '<div class="alert alert-danger">Failed to load payslip details</div>';
    }
}

// Perform search
async function performSearch(query) {
    const resultsDiv = document.getElementById('searchResults');
    
    if (!query || query.length < 2) {
        resultsDiv.innerHTML = '<p class="text-muted text-center">Enter at least 2 characters to search...</p>';
        return;
    }
    
    resultsDiv.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Searching...</span>
            </div>
        </div>
    `;
    
    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.length === 0) {
            resultsDiv.innerHTML = '<div class="alert alert-info">No results found</div>';
            return;
        }
        
        let html = `
            <div class="alert alert-success">
                <i class="bi bi-check-circle"></i> Found ${data.length} result(s)
            </div>
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Year/Week</th>
                            <th>Job #</th>
                            <th>Client</th>
                            <th>Location</th>
                            <th>Type</th>
                            <th>Amount</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        data.forEach(job => {
            const dateTime = job.date ? `<small class="text-muted">${job.date} ${job.time || ''}</small>` : '';
            html += `
                <tr>
                    <td><span class="badge bg-primary">${job.tax_year} W${job.week_number}</span></td>
                    <td><small class="text-muted">#${job.job_number}</small></td>
                    <td>
                        ${truncate(job.client || 'N/A', 30)}
                        ${dateTime ? '<br>' + dateTime : ''}
                    </td>
                    <td><small>${truncate(job.location || 'N/A', 25)}</small></td>
                    <td><small>${truncate(job.job_type || 'N/A', 25)}</small></td>
                    <td><strong class="text-success">${formatCurrency(job.amount)}</strong></td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        resultsDiv.innerHTML = html;
        
    } catch (error) {
        console.error('Error performing search:', error);
        resultsDiv.innerHTML = '<div class="alert alert-danger">Search failed</div>';
    }
}

// Utility functions
function formatCurrency(value) {
    if (value === null || value === undefined) return '£0.00';
    return '£' + parseFloat(value).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

function showError(message) {
    console.error(message);
    // Could add toast notification here
}

// Report generation functions
async function generateDateRangeReport() {
    const taxYear = document.getElementById('reportTaxYear').value;
    showReportLoading('Date Range Report');
    
    try {
        const url = taxYear ? `/api/payslips?tax_year=${taxYear}` : '/api/payslips';
        const response = await fetch(url);
        const data = await response.json();
        
        let html = `
            <h5 class="mb-4">${taxYear ? `Tax Year ${taxYear}` : 'All Years'} - Earnings Report</h5>
            
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <small class="text-muted">Total Weeks</small>
                            <h4 class="mb-0">${data.length}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <small class="text-muted">Total Earnings</small>
                            <h4 class="mb-0 text-success">${formatCurrency(data.reduce((sum, p) => sum + p.net_payment, 0))}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <small class="text-muted">Average/Week</small>
                            <h4 class="mb-0 text-primary">${formatCurrency(data.reduce((sum, p) => sum + p.net_payment, 0) / data.length)}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <small class="text-muted">Best Week</small>
                            <h4 class="mb-0 text-warning">${formatCurrency(Math.max(...data.map(p => p.net_payment)))}</h4>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Week</th>
                            <th>Pay Date</th>
                            <th>Jobs</th>
                            <th class="text-end">Net Payment</th>
                            <th class="text-end">YTD</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        data.forEach(p => {
            html += `
                <tr>
                    <td><strong>${p.tax_year} Week ${p.week_number}</strong></td>
                    <td>${p.pay_date || 'N/A'}</td>
                    <td><span class="badge bg-info">${p.job_count}</span></td>
                    <td class="text-end"><strong>${formatCurrency(p.net_payment)}</strong></td>
                    <td class="text-end text-muted">${formatCurrency(p.gross_subcontractor_payment_ytd)}</td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        showReport('Date Range Report', html);
        
    } catch (error) {
        console.error('Error generating date range report:', error);
        showReportError('Failed to generate report');
    }
}

async function generateClientReport() {
    const limit = document.getElementById('reportClientLimit').value;
    showReportLoading('Client Analysis Report');
    
    try {
        const url = limit === 'all' ? '/api/clients?limit=1000' : `/api/clients?limit=${limit}`;
        const response = await fetch(url);
        const data = await response.json();
        
        const totalEarnings = data.reduce((sum, c) => sum + c.total_amount, 0);
        const totalJobs = data.reduce((sum, c) => sum + c.job_count, 0);
        
        let html = `
            <h5 class="mb-4">Client Analysis Report - ${limit === 'all' ? 'All Clients' : `Top ${limit}`}</h5>
            
            <div class="row mb-4">
                <div class="col-md-4">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <small class="text-muted">Total Clients</small>
                            <h4 class="mb-0">${data.length}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <small class="text-muted">Total Earnings</small>
                            <h4 class="mb-0 text-success">${formatCurrency(totalEarnings)}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <small class="text-muted">Total Jobs</small>
                            <h4 class="mb-0 text-info">${totalJobs}</h4>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>#</th>
                            <th>Client</th>
                            <th class="text-end">Jobs</th>
                            <th class="text-end">Total</th>
                            <th class="text-end">Average</th>
                            <th class="text-end">% of Total</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        data.forEach((c, index) => {
            const percentage = (c.total_amount / totalEarnings * 100).toFixed(1);
            html += `
                <tr>
                    <td><span class="badge bg-secondary">${index + 1}</span></td>
                    <td><strong>${c.client}</strong></td>
                    <td class="text-end">${c.job_count}</td>
                    <td class="text-end"><strong class="text-success">${formatCurrency(c.total_amount)}</strong></td>
                    <td class="text-end">${formatCurrency(c.avg_amount)}</td>
                    <td class="text-end">
                        <div class="progress" style="height: 20px;">
                            <div class="progress-bar" role="progressbar" style="width: ${percentage}%">
                                ${percentage}%
                            </div>
                        </div>
                    </td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        showReport('Client Analysis Report', html);
        
    } catch (error) {
        console.error('Error generating client report:', error);
        showReportError('Failed to generate report');
    }
}

async function generateJobTypeReport() {
    const limit = document.getElementById('reportJobTypeLimit').value;
    showReportLoading('Job Type Report');
    
    try {
        const url = limit === 'all' ? '/api/job_types?limit=1000' : `/api/job_types?limit=${limit}`;
        const response = await fetch(url);
        const data = await response.json();
        
        const totalEarnings = data.reduce((sum, j) => sum + j.total_amount, 0);
        const totalJobs = data.reduce((sum, j) => sum + j.job_count, 0);
        
        let html = `
            <h5 class="mb-4">Job Type Analysis Report - ${limit === 'all' ? 'All Types' : `Top ${limit}`}</h5>
            
            <div class="row mb-4">
                <div class="col-md-4">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <small class="text-muted">Job Types</small>
                            <h4 class="mb-0">${data.length}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <small class="text-muted">Total Earnings</small>
                            <h4 class="mb-0 text-success">${formatCurrency(totalEarnings)}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <small class="text-muted">Total Jobs</small>
                            <h4 class="mb-0 text-info">${totalJobs}</h4>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>#</th>
                            <th>Job Type</th>
                            <th class="text-end">Count</th>
                            <th class="text-end">Total</th>
                            <th class="text-end">Average</th>
                            <th class="text-end">% of Jobs</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        data.forEach((j, index) => {
            const percentage = (j.job_count / totalJobs * 100).toFixed(1);
            html += `
                <tr>
                    <td><span class="badge bg-secondary">${index + 1}</span></td>
                    <td><strong>${j.job_type}</strong></td>
                    <td class="text-end"><span class="badge bg-info">${j.job_count}</span></td>
                    <td class="text-end"><strong class="text-success">${formatCurrency(j.total_amount)}</strong></td>
                    <td class="text-end">${formatCurrency(j.avg_amount)}</td>
                    <td class="text-end">
                        <div class="progress" style="height: 20px;">
                            <div class="progress-bar bg-info" role="progressbar" style="width: ${percentage}%">
                                ${percentage}%
                            </div>
                        </div>
                    </td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        showReport('Job Type Analysis Report', html);
        
    } catch (error) {
        console.error('Error generating job type report:', error);
        showReportError('Failed to generate report');
    }
}

async function generateMonthlyReport() {
    const taxYear = document.getElementById('reportMonthlyYear').value;
    showReportLoading('Monthly Summary Report');
    
    try {
        const response = await fetch('/api/monthly_breakdown');
        const data = await response.json();
        
        const filteredData = taxYear ? data.filter(d => d.tax_year === taxYear) : data;
        
        let html = `
            <h5 class="mb-4">Monthly Summary - ${taxYear || 'All Years'}</h5>
            
            <div class="alert alert-info">
                <i class="bi bi-info-circle"></i>
                <strong>Note:</strong> Months are approximate (4.33 weeks per month)
            </div>
            
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Tax Year</th>
                            <th>Month</th>
                            <th class="text-end">Weeks</th>
                            <th class="text-end">Total Earnings</th>
                            <th class="text-end">Avg/Week</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        filteredData.forEach(m => {
            const avgPerWeek = m.total / m.weeks;
            html += `
                <tr>
                    <td><strong>${m.tax_year}</strong></td>
                    <td>Month ${m.month}</td>
                    <td class="text-end">${m.weeks}</td>
                    <td class="text-end"><strong class="text-success">${formatCurrency(m.total)}</strong></td>
                    <td class="text-end">${formatCurrency(avgPerWeek)}</td>
                </tr>
            `;
        });
        
        const totalEarnings = filteredData.reduce((sum, m) => sum + m.total, 0);
        const totalWeeks = filteredData.reduce((sum, m) => sum + m.weeks, 0);
        
        html += `
                    <tr class="table-secondary fw-bold">
                        <td colspan="2">TOTAL</td>
                        <td class="text-end">${totalWeeks}</td>
                        <td class="text-end">${formatCurrency(totalEarnings)}</td>
                        <td class="text-end">${formatCurrency(totalEarnings / totalWeeks)}</td>
                    </tr>
                    </tbody>
                </table>
            </div>
        `;
        
        showReport('Monthly Summary Report', html);
        
    } catch (error) {
        console.error('Error generating monthly report:', error);
        showReportError('Failed to generate report');
    }
}

function showReportLoading(title) {
    document.getElementById('reportTitle').textContent = title;
    document.getElementById('reportContent').innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3 text-muted">Generating report...</p>
        </div>
    `;
    document.getElementById('reportOutput').style.display = 'block';
    
    // Scroll to report
    document.getElementById('reportOutput').scrollIntoView({ behavior: 'smooth' });
}

function showReport(title, content) {
    document.getElementById('reportTitle').textContent = title;
    document.getElementById('reportContent').innerHTML = content;
    document.getElementById('reportOutput').style.display = 'block';
}

function showReportError(message) {
    document.getElementById('reportContent').innerHTML = `
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle"></i> ${message}
        </div>
    `;
}

function printReport() {
    const reportContent = document.getElementById('reportContent').innerHTML;
    const reportTitle = document.getElementById('reportTitle').textContent;
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>${reportTitle}</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body { padding: 20px; }
                @media print {
                    .no-print { display: none; }
                }
            </style>
        </head>
        <body>
            <h2>${reportTitle}</h2>
            <p class="text-muted">Generated: ${new Date().toLocaleString()}</p>
            <hr>
            ${reportContent}
            <script>
                window.onload = function() {
                    window.print();
                };
            </script>
        </body>
        </html>
    `);
    printWindow.document.close();
}

// Load custom filter options
async function loadCustomFilterOptions() {
    await refreshCustomFilters();
}

async function refreshCustomFilters() {
    try {
        // Check if custom filter elements exist (they may not on all pages)
        const customTaxYear = document.getElementById('customTaxYear');
        const customClient = document.getElementById('customClient');
        const customJobType = document.getElementById('customJobType');
        
        if (!customTaxYear || !customClient || !customJobType) {
            // Custom filters not on this page, skip
            return;
        }
        
        // Load settings/groups
        const settingsResponse = await fetch('/api/settings/groups');
        const settings = await settingsResponse.json();
        
        // Load tax years
        const yearsResponse = await fetch('/api/tax_years');
        const years = await yearsResponse.json();
        
        customTaxYear.innerHTML = '<option value="">All Years</option>';
        years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            customTaxYear.appendChild(option);
        });
        
        // Load clients and groups
        const clientsResponse = await fetch('/api/all_clients');
        const clients = await clientsResponse.json();
        
        customClient.innerHTML = '<option value="">All Clients</option>';
        
        // Add groups first (if any)
        if (settings.client_groups && Object.keys(settings.client_groups).length > 0) {
            const groupOptGroup = document.createElement('optgroup');
            groupOptGroup.label = '📁 Client Groups';
            
            for (const [groupName, groupClients] of Object.entries(settings.client_groups)) {
                const option = document.createElement('option');
                option.value = groupName;
                option.textContent = `${groupName} (${groupClients.length} clients)`;
                groupOptGroup.appendChild(option);
            }
            customClient.appendChild(groupOptGroup);
        }
        
        // Add individual clients
        const clientOptGroup = document.createElement('optgroup');
        clientOptGroup.label = '👤 Individual Clients';
        clients.forEach(client => {
            const option = document.createElement('option');
            option.value = client;
            option.textContent = truncate(client, 50);
            clientOptGroup.appendChild(option);
        });
        customClient.appendChild(clientOptGroup);
        
        // Load job types and groups
        const jobTypesResponse = await fetch('/api/all_job_types');
        const jobTypes = await jobTypesResponse.json();
        
        customJobType.innerHTML = '<option value="">All Types</option>';
        
        // Add groups first (if any)
        if (settings.job_type_groups && Object.keys(settings.job_type_groups).length > 0) {
            const groupOptGroup = document.createElement('optgroup');
            groupOptGroup.label = '📁 Job Type Groups';
            
            for (const [groupName, groupTypes] of Object.entries(settings.job_type_groups)) {
                const option = document.createElement('option');
                option.value = groupName;
                option.textContent = `${groupName} (${groupTypes.length} types)`;
                groupOptGroup.appendChild(option);
            }
            customJobType.appendChild(groupOptGroup);
        }
        
        // Add individual job types
        const typeOptGroup = document.createElement('optgroup');
        typeOptGroup.label = '🔨 Individual Types';
        jobTypes.forEach(jobType => {
            const option = document.createElement('option');
            option.value = jobType;
            option.textContent = jobType;
            typeOptGroup.appendChild(option);
        });
        customJobType.appendChild(typeOptGroup);
        
    } catch (error) {
        console.error('Error loading custom filter options:', error);
    }
}

// Generate custom filtered report
async function generateCustomReport() {
    showReportLoading('Custom Filtered Report');
    
    try {
        const taxYear = document.getElementById('customTaxYear').value;
        const weekFrom = document.getElementById('customWeekFrom').value;
        const weekTo = document.getElementById('customWeekTo').value;
        const client = document.getElementById('customClient').value;
        const jobType = document.getElementById('customJobType').value;
        const useGroupings = document.getElementById('useGroupings').checked;
        
        // Build query string
        const params = new URLSearchParams();
        if (taxYear) params.append('tax_year', taxYear);
        if (weekFrom) params.append('week_from', weekFrom);
        if (weekTo) params.append('week_to', weekTo);
        if (client) params.append('client', client);
        if (jobType) params.append('job_type', jobType);
        params.append('use_groups', useGroupings);
        
        const response = await fetch(`/api/custom_report?${params.toString()}`);
        const data = await response.json();
        
        currentReportData = data; // Store for CSV export
        
        if (data.length === 0) {
            showReport('Custom Filtered Report', '<div class="alert alert-warning">No jobs found matching the selected criteria.</div>');
            return;
        }
        
        // Build filter description
        let filterDesc = [];
        if (taxYear) filterDesc.push(`Tax Year: ${taxYear}`);
        if (weekFrom || weekTo) filterDesc.push(`Weeks: ${weekFrom || '1'} - ${weekTo || '52'}`);
        if (client) filterDesc.push(`Client: ${truncate(client, 40)}`);
        if (jobType) filterDesc.push(`Job Type: ${jobType}`);
        
        const totalAmount = data.reduce((sum, j) => sum + j.amount, 0);
        const avgAmount = totalAmount / data.length;
        
        let html = `
            <h5 class="mb-3">Custom Filtered Report</h5>
            <div class="alert alert-secondary">
                <strong>Filters:</strong> ${filterDesc.length > 0 ? filterDesc.join(' | ') : 'None (showing all)'}
            </div>
            
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <small class="text-muted">Total Jobs</small>
                            <h4 class="mb-0">${data.length}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <small class="text-muted">Total Earnings</small>
                            <h4 class="mb-0 text-success">${formatCurrency(totalAmount)}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <small class="text-muted">Average/Job</small>
                            <h4 class="mb-0 text-primary">${formatCurrency(avgAmount)}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <small class="text-muted">Highest Job</small>
                            <h4 class="mb-0 text-warning">${formatCurrency(Math.max(...data.map(j => j.amount)))}</h4>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="table-responsive">
                <table class="table table-striped table-hover table-sm">
                    <thead class="table-dark">
                        <tr>
                            <th>Year/Week</th>
                            <th>Job #</th>
                            <th>Date</th>
                            <th>Client</th>
                            <th>Location</th>
                            <th>Job Type</th>
                            <th class="text-end">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        data.forEach(job => {
            const dateTime = job.date ? `${job.date} ${job.time || ''}`.trim() : 'N/A';
            const useGroupings = document.getElementById('useGroupings').checked;
            
            // Use grouped names if available and groupings enabled
            const displayClient = useGroupings && job.client_group 
                ? `<strong>${job.client_group}</strong><br><small class="text-muted">${truncate(job.client, 25)}</small>`
                : truncate(job.client || 'N/A', 30);
            
            const displayJobType = useGroupings && job.job_type_group
                ? `<strong>${job.job_type_group}</strong><br><small class="text-muted">${truncate(job.job_type, 20)}</small>`
                : truncate(job.job_type || 'N/A', 25);
            
            html += `
                <tr>
                    <td><span class="badge bg-primary">${job.tax_year} W${job.week_number}</span></td>
                    <td><small class="text-muted">#${job.job_number}</small></td>
                    <td><small>${dateTime}</small></td>
                    <td>${displayClient}</td>
                    <td><small>${truncate(job.location || 'N/A', 25)}</small></td>
                    <td><small>${displayJobType}</small></td>
                    <td class="text-end"><strong class="text-success">${formatCurrency(job.amount)}</strong></td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                    <tfoot class="table-secondary fw-bold">
                        <tr>
                            <td colspan="6" class="text-end">TOTAL:</td>
                            <td class="text-end">${formatCurrency(totalAmount)}</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        `;
        
        showReport('Custom Filtered Report', html);
        
    } catch (error) {
        console.error('Error generating custom report:', error);
        showReportError('Failed to generate report');
    }
}

function clearCustomFilters() {
    document.getElementById('customTaxYear').value = '';
    document.getElementById('customWeekFrom').value = '';
    document.getElementById('customWeekTo').value = '';
    document.getElementById('customClient').value = '';
    document.getElementById('customJobType').value = '';
}

function downloadReportCSV() {
    if (!currentReportData || currentReportData.length === 0) {
        alert('No report data to export');
        return;
    }
    
    // Convert to CSV
    const headers = Object.keys(currentReportData[0]);
    let csv = headers.join(',') + '\n';
    
    currentReportData.forEach(row => {
        const values = headers.map(header => {
            const value = row[header] || '';
            // Escape quotes and wrap in quotes if contains comma
            return typeof value === 'string' && value.includes(',') 
                ? `"${value.replace(/"/g, '""')}"` 
                : value;
        });
        csv += values.join(',') + '\n';
    });
    
    // Download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

function downloadReportPDF() {
    if (!currentReportData || currentReportData.length === 0) {
        alert('No report data to export');
        return;
    }
    
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF('l', 'mm', 'a4'); // Landscape orientation
    
    // Title
    const reportTitle = document.getElementById('reportTitle').textContent;
    doc.setFontSize(16);
    doc.text(reportTitle, 14, 15);
    
    // Date
    doc.setFontSize(10);
    doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 22);
    
    // Prepare table data
    const headers = [['Year/Week', 'Job #', 'Date', 'Client', 'Location', 'Job Type', 'Amount']];
    const data = currentReportData.map(job => [
        `${job.tax_year} W${job.week_number}`,
        job.job_number || 'N/A',
        job.date || 'N/A',
        truncate(job.client || 'N/A', 25),
        truncate(job.location || 'N/A', 20),
        truncate(job.job_type || 'N/A', 20),
        formatCurrency(job.amount)
    ]);
    
    // Add total row
    const totalAmount = currentReportData.reduce((sum, j) => sum + j.amount, 0);
    data.push(['', '', '', '', '', 'TOTAL:', formatCurrency(totalAmount)]);
    
    // Generate table
    doc.autoTable({
        head: headers,
        body: data,
        startY: 28,
        styles: { fontSize: 8 },
        headStyles: { fillColor: [41, 128, 185] },
        footStyles: { fillColor: [240, 240, 240], textColor: [0, 0, 0], fontStyle: 'bold' },
        columnStyles: {
            6: { halign: 'right' }
        }
    });
    
    // Download
    doc.save(`report_${new Date().toISOString().split('T')[0]}.pdf`);
}

// Global settings storage
let currentSettings = {
    client_groups: {},
    job_type_groups: {}
};

// Settings functions
async function loadSettings() {
    try {
        const response = await fetch('/api/settings/groups');
        const settings = await response.json();
        
        currentSettings = settings;
        
        // Load client groups
        displayClientGroups(settings.client_groups || {});
        
        // Load job type groups
        displayJobTypeGroups(settings.job_type_groups || {});
        
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

function displayClientGroups(groups) {
    const container = document.getElementById('clientGroupsList');
    
    if (Object.keys(groups).length === 0) {
        container.innerHTML = '<p class="text-muted small">No client groups defined yet.</p>';
        return;
    }
    
    let html = '';
    for (const [groupName, clients] of Object.entries(groups)) {
        html += `
            <div class="card mb-2">
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${groupName}</strong>
                            <br><small class="text-muted">${clients.length} clients</small>
                        </div>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteClientGroup('${groupName}')">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

function displayJobTypeGroups(groups) {
    const container = document.getElementById('jobTypeGroupsList');
    
    if (Object.keys(groups).length === 0) {
        container.innerHTML = '<p class="text-muted small">No job type groups defined yet.</p>';
        return;
    }
    
    let html = '';
    for (const [groupName, jobTypes] of Object.entries(groups)) {
        html += `
            <div class="card mb-2">
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${groupName}</strong>
                            <br><small class="text-muted">${jobTypes.length} job types</small>
                        </div>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteJobTypeGroup('${groupName}')">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

// Show client group modal with checkboxes
async function showClientGroupModal() {
    const modal = new bootstrap.Modal(document.getElementById('clientGroupModal'));
    modal.show();
    
    // Clear previous
    document.getElementById('clientGroupName').value = '';
    document.getElementById('clientSearchBox').value = '';
    
    // Load all clients
    try {
        const response = await fetch('/api/all_clients');
        const clients = await response.json();
        
        displayClientCheckboxes(clients);
        
        // Setup search filter
        document.getElementById('clientSearchBox').addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const filtered = clients.filter(c => c.toLowerCase().includes(searchTerm));
            displayClientCheckboxes(filtered);
        });
        
    } catch (error) {
        console.error('Error loading clients:', error);
    }
}

function displayClientCheckboxes(clients) {
    const container = document.getElementById('clientCheckboxList');
    
    let html = '';
    clients.forEach((client, index) => {
        html += `
            <div class="form-check">
                <input class="form-check-input client-checkbox" type="checkbox" value="${client}" 
                       id="client_${index}" onchange="updateClientCount()">
                <label class="form-check-label" for="client_${index}">
                    ${client}
                </label>
            </div>
        `;
    });
    
    container.innerHTML = html;
    updateClientCount();
}

function updateClientCount() {
    const checked = document.querySelectorAll('.client-checkbox:checked').length;
    document.getElementById('clientSelectedCount').textContent = checked;
}

async function saveClientGroup() {
    const groupName = document.getElementById('clientGroupName').value.trim();
    if (!groupName) {
        alert('Please enter a group name');
        return;
    }
    
    const selectedClients = Array.from(document.querySelectorAll('.client-checkbox:checked'))
        .map(cb => cb.value);
    
    if (selectedClients.length === 0) {
        alert('Please select at least one client');
        return;
    }
    
    // Add to current settings
    currentSettings.client_groups[groupName] = selectedClients;
    
    // Save to backend
    try {
        const response = await fetch('/api/settings/groups', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(currentSettings)
        });
        
        if (response.ok) {
            alert(`✅ Group "${groupName}" created with ${selectedClients.length} clients!`);
            
            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('clientGroupModal')).hide();
            
            // Reload settings and custom filters
            loadSettings();
            refreshCustomFilters();
        } else {
            alert('❌ Failed to save group');
        }
        
    } catch (error) {
        console.error('Error saving client group:', error);
        alert('❌ Error saving group');
    }
}

// Show job type group modal with checkboxes
async function showJobTypeGroupModal() {
    const modal = new bootstrap.Modal(document.getElementById('jobTypeGroupModal'));
    modal.show();
    
    // Clear previous
    document.getElementById('jobTypeGroupName').value = '';
    document.getElementById('jobTypeSearchBox').value = '';
    
    // Load all job types
    try {
        const response = await fetch('/api/all_job_types');
        const jobTypes = await response.json();
        
        displayJobTypeCheckboxes(jobTypes);
        
        // Setup search filter
        document.getElementById('jobTypeSearchBox').addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const filtered = jobTypes.filter(jt => jt.toLowerCase().includes(searchTerm));
            displayJobTypeCheckboxes(filtered);
        });
        
    } catch (error) {
        console.error('Error loading job types:', error);
    }
}

function displayJobTypeCheckboxes(jobTypes) {
    const container = document.getElementById('jobTypeCheckboxList');
    
    let html = '';
    jobTypes.forEach((jobType, index) => {
        html += `
            <div class="form-check">
                <input class="form-check-input jobtype-checkbox" type="checkbox" value="${jobType}" 
                       id="jobtype_${index}" onchange="updateJobTypeCount()">
                <label class="form-check-label" for="jobtype_${index}">
                    ${jobType}
                </label>
            </div>
        `;
    });
    
    container.innerHTML = html;
    updateJobTypeCount();
}

function updateJobTypeCount() {
    const checked = document.querySelectorAll('.jobtype-checkbox:checked').length;
    document.getElementById('jobTypeSelectedCount').textContent = checked;
}

async function saveJobTypeGroup() {
    const groupName = document.getElementById('jobTypeGroupName').value.trim();
    if (!groupName) {
        alert('Please enter a group name');
        return;
    }
    
    const selectedJobTypes = Array.from(document.querySelectorAll('.jobtype-checkbox:checked'))
        .map(cb => cb.value);
    
    if (selectedJobTypes.length === 0) {
        alert('Please select at least one job type');
        return;
    }
    
    // Add to current settings
    currentSettings.job_type_groups[groupName] = selectedJobTypes;
    
    // Save to backend
    try {
        const response = await fetch('/api/settings/groups', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(currentSettings)
        });
        
        if (response.ok) {
            alert(`✅ Group "${groupName}" created with ${selectedJobTypes.length} job types!`);
            
            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('jobTypeGroupModal')).hide();
            
            // Reload settings and custom filters
            loadSettings();
            refreshCustomFilters();
        } else {
            alert('❌ Failed to save group');
        }
        
    } catch (error) {
        console.error('Error saving job type group:', error);
        alert('❌ Error saving group');
    }
}

async function deleteClientGroup(groupName) {
    if (confirm(`Delete client group "${groupName}"?`)) {
        delete currentSettings.client_groups[groupName];
        
        try {
            const response = await fetch('/api/settings/groups', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(currentSettings)
            });
            
            if (response.ok) {
                alert('✅ Group deleted.');
                loadSettings();
            }
        } catch (error) {
            console.error('Error deleting group:', error);
        }
    }
}

async function deleteJobTypeGroup(groupName) {
    if (confirm(`Delete job type group "${groupName}"?`)) {
        delete currentSettings.job_type_groups[groupName];
        
        try {
            const response = await fetch('/api/settings/groups', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(currentSettings)
            });
            
            if (response.ok) {
                alert('✅ Group deleted.');
                loadSettings();
            }
        } catch (error) {
            console.error('Error deleting group:', error);
        }
    }
}

// Upload payslips
async function uploadPayslips() {
    const fileInput = document.getElementById('payslipFiles');
    const files = fileInput.files;
    
    if (files.length === 0) {
        alert('Please select at least one PDF file');
        return;
    }
    
    // Get tax year
    const taxYear = document.getElementById('uploadTaxYear').value;
    
    const statusDiv = document.getElementById('uploadStatus');
    const messageDiv = document.getElementById('uploadMessage');
    
    statusDiv.style.display = 'block';
    messageDiv.textContent = `Uploading ${files.length} file(s) to ${taxYear}...`;
    
    const formData = new FormData();
    formData.append('tax_year', taxYear);
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    try {
        const response = await fetch('/api/upload_payslips', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            messageDiv.textContent = `✅ Uploaded ${result.uploaded} file(s) to ${taxYear}. Processing...`;
            
            // Wait then reload
            setTimeout(() => {
                messageDiv.textContent = '✅ Complete! Reloading data...';
                setTimeout(() => {
                    location.reload();
                }, 2000);
            }, 5000);
        } else {
            messageDiv.textContent = `❌ Error: ${result.message}`;
        }
        
    } catch (error) {
        console.error('Error uploading payslips:', error);
        messageDiv.textContent = '❌ Error uploading files';
    }
}

// Process new payslips
async function processPayslips() {
    if (!confirm('This will process all PDF files in the PaySlips folder.\n\nThis may take a few minutes. Continue?')) {
        return;
    }
    
    const statusDiv = document.getElementById('processingStatus');
    const messageDiv = document.getElementById('processingMessage');
    
    statusDiv.style.display = 'block';
    messageDiv.textContent = 'Processing PDFs... This may take a few minutes.';
    
    try {
        const response = await fetch('/api/process_payslips', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            messageDiv.textContent = '✅ Processing started! Check the terminal for progress.';
            
            // Wait a bit then reload data
            setTimeout(() => {
                messageDiv.textContent = '✅ Processing complete! Reloading data...';
                
                // Reload all data
                setTimeout(() => {
                    location.reload();
                }, 3000);
            }, 5000);
        } else {
            messageDiv.textContent = '❌ Failed to start processing.';
        }
        
    } catch (error) {
        console.error('Error processing payslips:', error);
        messageDiv.textContent = '❌ Error: ' + error.message;
    }
}

// Backup database
function backupDatabase() {
    if (confirm('Download a backup of your database?\n\nThis will save all your payslip data.')) {
        window.location.href = '/api/backup_database';
    }
}

// Clear database
async function clearDatabase() {
    if (!confirm('⚠️ WARNING: This will DELETE ALL payslip data from the database!\n\nThis action cannot be undone.\n\nAre you sure you want to continue?')) {
        return;
    }
    
    // Ask about PDF files
    const deletePDFs = confirm('Do you also want to DELETE all PDF files?\n\nClick OK to delete PDFs\nClick Cancel to keep PDFs');
    
    if (!confirm('⚠️ FINAL WARNING!\n\nThis will permanently delete:\n- All payslips from database\n- All job data\n- All reports\n' + (deletePDFs ? '- All PDF files\n' : '') + '\nType YES in the next prompt to confirm.')) {
        return;
    }
    
    const confirmation = prompt('Type YES (in capitals) to confirm deletion:');
    if (confirmation !== 'YES') {
        alert('Deletion cancelled.');
        return;
    }
    
    const statusDiv = document.getElementById('clearStatus');
    const messageDiv = document.getElementById('clearMessage');
    
    statusDiv.style.display = 'block';
    messageDiv.textContent = 'Clearing database' + (deletePDFs ? ' and PDFs' : '') + '...';
    
    try {
        const response = await fetch('/api/clear_database', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ delete_pdfs: deletePDFs })
        });
        
        const result = await response.json();
        
        if (result.success) {
            messageDiv.textContent = '✅ ' + result.message + '! Reloading...';
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            messageDiv.textContent = `❌ Error: ${result.message}`;
        }
        
    } catch (error) {
        console.error('Error clearing database:', error);
        messageDiv.textContent = '❌ Error clearing database';
    }
}

// Check for missing payslips
async function checkMissingPayslips() {
    const resultsDiv = document.getElementById('missingResults');
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-warning" role="status"></div>
            <p class="text-muted small mt-2">Checking...</p>
        </div>
    `;
    
    try {
        const response = await fetch('/api/check_missing');
        const data = await response.json();
        
        let html = '';
        let totalMissing = 0;
        
        data.forEach(year => {
            totalMissing += year.missing_weeks.length;
            
            const statusClass = year.has_missing ? 'danger' : 'success';
            const statusIcon = year.has_missing ? 'exclamation-triangle-fill' : 'check-circle-fill';
            
            html += `
                <div class="alert alert-${statusClass} small mb-2">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <strong><i class="bi bi-${statusIcon}"></i> ${year.tax_year}</strong>
                            <br>
                            <small>Weeks ${year.min_week}-${year.max_week} (${year.total_weeks} payslips)</small>
                        </div>
                        <div class="text-end">
                            ${year.has_missing 
                                ? `<span class="badge bg-danger">${year.missing_weeks.length} missing</span>`
                                : `<span class="badge bg-success">Complete ✓</span>`
                            }
                        </div>
                    </div>
                    ${year.has_missing 
                        ? `<div class="mt-2"><strong>Missing weeks:</strong> ${year.missing_weeks.join(', ')}</div>`
                        : ''
                    }
                </div>
            `;
        });
        
        // Summary at top
        const summaryClass = totalMissing > 0 ? 'warning' : 'success';
        const summaryIcon = totalMissing > 0 ? 'exclamation-triangle' : 'check-circle';
        const summaryText = totalMissing > 0 
            ? `${totalMissing} week(s) missing across all years`
            : 'All weeks present - no gaps detected!';
        
        resultsDiv.innerHTML = `
            <div class="alert alert-${summaryClass} fw-bold">
                <i class="bi bi-${summaryIcon}-fill"></i> ${summaryText}
            </div>
            ${html}
        `;
        
    } catch (error) {
        console.error('Error checking missing payslips:', error);
        resultsDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-x-circle"></i> Error checking payslips
            </div>
        `;
    }
}
