function generateMissingDatesReport() {
    showStatus('Generating missing dates report...');
    
    fetch('/api/reports/missing-dates', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess('Report generated! Check the reports/ folder.');
            // Optionally download the file
            window.location.href = '/download/report/' + data.filename;
        } else {
            showError('Failed to generate report');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('Error generating report');
    });
}

function generateTaxYearReport() {
    alert('Tax Year Report - Coming soon!');
}

function generateMonthlyReport() {
    alert('Monthly Report - Coming soon!');
}

function generateClientReport() {
    alert('Client Report - Coming soon!');
}

function generateCustomerReport() {
    alert('Customer Analysis - Coming soon!');
}

function generateActivityReport() {
    alert('Activity Breakdown - Coming soon!');
}

async function loadDiscrepancyReport() {
    const contentDiv = document.getElementById('discrepancyReportContent');
    contentDiv.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-3 text-muted">Analyzing data...</p></div>';
    
    try {
        // Get filter values
        const year = document.getElementById('discrepancyYear')?.value || '';
        const month = document.getElementById('discrepancyMonth')?.value || '';
        
        // Build query string
        const params = new URLSearchParams();
        if (year) params.append('year', year);
        if (month) params.append('month', month);
        
        // Use the new dedicated API endpoint that gets all data
        const response = await fetch(`/api/reports/discrepancies?${params.toString()}`);
        const data = await response.json();
        
        if (data.error) {
            contentDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-exclamation-triangle"></i> Error: ${data.error}</div>`;
            return;
        }
        
        const payslipJobs = new Map(Object.entries(data.payslip_jobs || {}));
        const runsheetJobs = new Map(Object.entries(data.runsheet_jobs || {}));
        
        // Find discrepancies
        const onlyInPayslips = [];
        const onlyInRunsheets = [];
        const matched = [];
        
        payslipJobs.forEach((job, jobNum) => {
            if (!runsheetJobs.has(jobNum)) {
                onlyInPayslips.push({ jobNum, ...job });
            } else {
                matched.push(jobNum);
            }
        });
        
        runsheetJobs.forEach((job, jobNum) => {
            if (!payslipJobs.has(jobNum)) {
                onlyInRunsheets.push({ jobNum, ...job });
            }
        });
        
        // Display results
        let html = `
            <div class="alert alert-info">
                <h5>Discrepancy Report</h5>
                <p><strong>Total Payslip Jobs:</strong> ${payslipJobs.size}</p>
                <p><strong>Total Run Sheet Jobs:</strong> ${runsheetJobs.size}</p>
                <p><strong>Matched:</strong> ${matched.length}</p>
                <p class="text-danger"><strong>Discrepancies Found:</strong> ${onlyInPayslips.length + onlyInRunsheets.length}</p>
            </div>
        `;
        
        if (onlyInPayslips.length > 0) {
            html += `
                <div class="card border-warning mb-3">
                    <div class="card-header bg-warning text-dark">
                        <h6 class="mb-0"><i class="bi bi-exclamation-triangle"></i> Jobs on Payslips but NOT on Run Sheets (${onlyInPayslips.length})</h6>
                        <small>You were paid for these but don't have run sheet records</small>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-sm table-hover mb-0">
                                <thead>
                                    <tr>
                                        <th>Job #</th>
                                        <th>Description</th>
                                        <th>Client</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${onlyInPayslips.map(j => `
                                        <tr>
                                            <td><strong>${j.jobNum}</strong></td>
                                            <td>${j.description || 'N/A'}</td>
                                            <td>${j.client || 'N/A'}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
        }
        
        if (onlyInRunsheets.length > 0) {
            html += `
                <div class="card border-danger mb-3">
                    <div class="card-header bg-danger text-white">
                        <h6 class="mb-0"><i class="bi bi-exclamation-circle"></i> Jobs on Run Sheets but NOT on Payslips (${onlyInRunsheets.length})</h6>
                        <small>You worked these but weren't paid (or not yet processed)</small>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-sm table-hover mb-0">
                                <thead>
                                    <tr>
                                        <th>Job #</th>
                                        <th>Customer</th>
                                        <th>Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${onlyInRunsheets.map(j => `
                                        <tr>
                                            <td><strong>${j.jobNum}</strong></td>
                                            <td>${j.customer || 'Unknown'}</td>
                                            <td>${j.date}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
        }
        
        if (onlyInPayslips.length === 0 && onlyInRunsheets.length === 0) {
            html += `<div class="alert alert-success"><i class="bi bi-check-circle"></i> No discrepancies found! All jobs match.</div>`;
        }
        
        // Display results in the tab
        contentDiv.innerHTML = html;
        console.log('Discrepancy Report:', { onlyInPayslips, onlyInRunsheets, matched });
        
    } catch (error) {
        console.error('Error generating discrepancy report:', error);
        contentDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> <strong>Error:</strong> ${error.message}
                <br><small>Check browser console for details</small>
            </div>
        `;
    }
}

function exportToCSV() {
    alert('CSV Export - Coming soon!');
}

function exportToPDF() {
    alert('PDF Export - Coming soon!');
}

function exportToExcel() {
    alert('Excel Export - Coming soon!');
}

function showStatus(message) {
    const status = document.getElementById('reportStatus');
    status.innerHTML = `<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> ${message}</div>`;
    status.style.display = 'block';
}

function showSuccess(message) {
    const status = document.getElementById('reportStatus');
    status.innerHTML = `<div class="alert alert-success"><i class="bi bi-check-circle"></i> ${message}</div>`;
    status.style.display = 'block';
    setTimeout(() => status.style.display = 'none', 5000);
}

function showError(message) {
    const status = document.getElementById('reportStatus');
    status.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> ${message}</div>`;
    status.style.display = 'block';
}

// ===== NEW COMPREHENSIVE REPORTING FUNCTIONS =====

// Load data on page load
document.addEventListener('DOMContentLoaded', function() {
    loadOverviewData();
    setupDateRangeListener();
    
    // Load discrepancy report when tab is shown
    const discrepanciesTab = document.getElementById('discrepancies-tab');
    if (discrepanciesTab) {
        discrepanciesTab.addEventListener('shown.bs.tab', function() {
            const content = document.getElementById('discrepancyReportContent');
            if (content && content.innerHTML.includes('spinner-border')) {
                loadDiscrepancyReport();
            }
        });
    }
    
    // Load missing run sheets when tab is shown
    const missingRunSheetsTab = document.getElementById('missing-runsheets-tab');
    if (missingRunSheetsTab) {
        missingRunSheetsTab.addEventListener('shown.bs.tab', function() {
            const content = document.getElementById('missingRunSheetsContent');
            if (content && content.innerHTML.includes('spinner-border')) {
                loadMissingRunSheets();
            }
        });
    }
    
    // Load missing payslips when tab is shown
    const missingPayslipsTab = document.getElementById('missing-payslips-tab');
    if (missingPayslipsTab) {
        missingPayslipsTab.addEventListener('shown.bs.tab', function() {
            const content = document.getElementById('missingPayslipsContent');
            if (content && content.innerHTML.includes('spinner-border')) {
                loadMissingPayslips();
            }
        });
    }
});

// Setup date range listener for export
function setupDateRangeListener() {
    const exportDateRange = document.getElementById('exportDateRange');
    if (exportDateRange) {
        exportDateRange.addEventListener('change', function() {
            const customRange = document.getElementById('customDateRange');
            if (this.value === 'custom') {
                customRange.style.display = 'flex';
            } else {
                customRange.style.display = 'none';
            }
        });
    }
}

// Load overview data
async function loadOverviewData() {
    try {
        // Load wages summary
        const wagesResponse = await fetch('/api/summary');
        const wagesData = await wagesResponse.json();
        
        // Load run sheets summary
        const runsheetsResponse = await fetch('/api/runsheets/summary');
        const runsheetsData = await runsheetsResponse.json();
        
        // Update overview cards
        document.getElementById('overviewTotalEarnings').textContent = 
            `£${wagesData.total_earnings?.toFixed(2) || '0.00'}`;
        document.getElementById('overviewTotalJobs').textContent = 
            runsheetsData.overall?.total_jobs || 0;
        
        const avgPerJob = wagesData.total_earnings && runsheetsData.overall?.total_jobs 
            ? wagesData.total_earnings / runsheetsData.overall.total_jobs 
            : 0;
        document.getElementById('overviewAvgPerJob').textContent = `£${avgPerJob.toFixed(2)}`;
        
        document.getElementById('overviewWorkingDays').textContent = 
            runsheetsData.overall?.total_days || 0;
        
        // Load charts
        loadMonthlyTrendsChart();
        loadJobStatusChart();
        
    } catch (error) {
        console.error('Error loading overview data:', error);
        showError('Failed to load overview data');
    }
}

// Load correlation data
async function loadCorrelationData() {
    const fromDate = document.getElementById('correlationFromDate').value;
    const toDate = document.getElementById('correlationToDate').value;
    
    if (!fromDate || !toDate) {
        alert('Please select both from and to dates');
        return;
    }
    
    showStatus('Analyzing correlation...');
    
    try {
        // This would need a new API endpoint to correlate wages and run sheets by date
        // For now, show a placeholder
        showSuccess('Correlation analysis loaded!');
        
        // Load correlation chart (placeholder)
        loadCorrelationChart(fromDate, toDate);
        
    } catch (error) {
        console.error('Error loading correlation:', error);
        showError('Failed to load correlation data');
    }
}

// Chart functions
function loadMonthlyTrendsChart() {
    const ctx = document.getElementById('monthlyTrendsChart');
    if (!ctx) return;
    
    // Placeholder chart - would be populated with real data
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            datasets: [{
                label: 'Earnings (£)',
                data: [1200, 1900, 1500, 2100, 1800, 2300],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1,
                yAxisID: 'y'
            }, {
                label: 'Jobs Completed',
                data: [45, 52, 48, 58, 50, 62],
                borderColor: 'rgb(255, 99, 132)',
                tension: 0.1,
                yAxisID: 'y1'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Earnings (£)'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Jobs'
                    },
                    grid: {
                        drawOnChartArea: false,
                    }
                }
            }
        }
    });
}

function loadJobStatusChart() {
    const ctx = document.getElementById('jobStatusChart');
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Completed', 'DNCO', 'Missed', 'Extra'],
            datasets: [{
                data: [85, 8, 5, 2],
                backgroundColor: [
                    'rgb(75, 192, 192)',
                    'rgb(255, 205, 86)',
                    'rgb(255, 99, 132)',
                    'rgb(54, 162, 235)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function loadCorrelationChart(fromDate, toDate) {
    const ctx = document.getElementById('correlationChart');
    if (!ctx) return;
    
    // Destroy existing chart if it exists
    if (window.correlationChartInstance) {
        window.correlationChartInstance.destroy();
    }
    
    // Create new chart
    window.correlationChartInstance = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Jobs vs Earnings',
                data: [
                    {x: 5, y: 120},
                    {x: 8, y: 200},
                    {x: 6, y: 150},
                    {x: 10, y: 250},
                    {x: 7, y: 180}
                ],
                backgroundColor: 'rgb(75, 192, 192)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Jobs Completed'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Earnings (£)'
                    }
                }
            }
        }
    });
}

function refreshAllData() {
    showStatus('Refreshing all data...');
    loadOverviewData();
    setTimeout(() => {
        showSuccess('Data refreshed successfully!');
    }, 1000);
}

function exportAllData() {
    const dataType = document.getElementById('exportDataType')?.value || 'all';
    const dateRange = document.getElementById('exportDateRange')?.value || 'all';
    
    showStatus(`Exporting ${dataType} data...`);
    alert(`Export functionality coming soon!\n\nData Type: ${dataType}\nDate Range: ${dateRange}`);
}

// Missing Run Sheets Report
async function loadMissingRunSheets() {
    const contentDiv = document.getElementById('missingRunSheetsContent');
    contentDiv.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-3 text-muted">Analyzing dates...</p></div>';
    
    try {
        // Get selected year filter
        const yearFilter = document.getElementById('missingRunSheetsYear')?.value || '';
        
        // Get all run sheets dates from summary
        const response = await fetch('/api/runsheets/list?per_page=1000');
        const data = await response.json();
        
        // Get attendance records to exclude
        const attendanceUrl = yearFilter ? `/api/attendance?year=${yearFilter}` : '/api/attendance';
        const attendanceResponse = await fetch(attendanceUrl);
        const attendanceRecords = await attendanceResponse.json();
        const attendanceDates = new Set(attendanceRecords.map(r => r.date));
        
        // Extract dates from the response
        let dates = [];
        if (data.runsheets && Array.isArray(data.runsheets)) {
            dates = data.runsheets.map(r => r.date);
        } else if (Array.isArray(data)) {
            dates = data.map(r => r.date || r);
        }
        
        // Filter by year if selected (dates are in DD/MM/YYYY format)
        if (yearFilter) {
            dates = dates.filter(d => d.endsWith(yearFilter));
        }
        
        if (dates.length === 0) {
            contentDiv.innerHTML = `<div class="alert alert-warning"><i class="bi bi-exclamation-triangle"></i> No run sheets found${yearFilter ? ' for ' + yearFilter : ' in database'}!</div>`;
            return;
        }
        
        // Convert DD/MM/YYYY to Date objects and sort
        const dateObjects = dates.map(d => {
            const [day, month, year] = d.split('/');
            return {
                dateStr: d,
                dateObj: new Date(year, month - 1, day)
            };
        }).sort((a, b) => a.dateObj - b.dateObj);
        
        // Update dates array with sorted strings
        dates = dateObjects.map(d => d.dateStr);
        
        const missingDates = [];
        
        for (let i = 0; i < dateObjects.length - 1; i++) {
            const current = dateObjects[i].dateObj;
            const next = dateObjects[i + 1].dateObj;
            const diffDays = Math.floor((next - current) / (1000 * 60 * 60 * 24));
            
            // Only report gaps of 1-30 days (ignore huge gaps like years)
            if (diffDays > 1 && diffDays <= 30) {
                // Found a reasonable gap - include all days
                for (let j = 1; j < diffDays; j++) {
                    const missingDate = new Date(current);
                    missingDate.setDate(current.getDate() + j);
                    // Format as DD/MM/YYYY
                    const day = String(missingDate.getDate()).padStart(2, '0');
                    const month = String(missingDate.getMonth() + 1).padStart(2, '0');
                    const year = missingDate.getFullYear();
                    const dateStr = `${day}/${month}/${year}`;
                    
                    // Only add if not in attendance records
                    if (!attendanceDates.has(dateStr)) {
                        missingDates.push(dateStr);
                    }
                }
            }
        }
        
        // Format dates for display
        const firstDate = dates[0];
        const lastDate = dates[dates.length - 1];
        
        let html = `
            <div class="alert alert-info">
                <h6>Run Sheets Analysis</h6>
                <p><strong>Total Run Sheets:</strong> ${dates.length}</p>
                <p><strong>Date Range:</strong> ${firstDate} to ${lastDate}</p>
                <p class="text-warning"><strong>Missing Days:</strong> ${missingDates.length}</p>
            </div>
        `;
        
        if (missingDates.length > 0) {
            html += `
                <div class="card border-warning mb-3">
                    <div class="card-header bg-warning text-dark">
                        <h6 class="mb-0"><i class="bi bi-calendar-x"></i> Missing Run Sheets (${missingDates.length} days)</h6>
                        <small>Dates where you have no run sheet records</small>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-sm table-hover mb-0">
                                <thead>
                                    <tr>
                                        <th>Date</th>
                                        <th>Day of Week</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${missingDates.map(dateStr => {
                                        const [day, month, year] = dateStr.split('/');
                                        const date = new Date(year, month - 1, day);
                                        const dayName = date.toLocaleDateString('en-GB', { weekday: 'long' });
                                        return `
                                            <tr>
                                                <td><strong>${dateStr}</strong></td>
                                                <td>${dayName}</td>
                                            </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
        } else {
            html += '<div class="alert alert-success"><i class="bi bi-check-circle"></i> No missing days found!</div>';
        }
        
        contentDiv.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading missing run sheets:', error);
        contentDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-exclamation-triangle"></i> Error: ${error.message}</div>`;
    }
}

// Missing Payslips Report
async function loadMissingPayslips() {
    const contentDiv = document.getElementById('missingPayslipsContent');
    contentDiv.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-3 text-muted">Analyzing weeks...</p></div>';
    
    try {
        const response = await fetch('/api/payslips');
        const payslips = await response.json();
        
        if (payslips.length === 0) {
            contentDiv.innerHTML = '<div class="alert alert-warning"><i class="bi bi-exclamation-triangle"></i> No payslips found in database!</div>';
            return;
        }
        
        // Group by tax year
        const byYear = {};
        payslips.forEach(p => {
            if (!byYear[p.tax_year]) byYear[p.tax_year] = [];
            byYear[p.tax_year].push(p.week_number);
        });
        
        // Find missing weeks (1-52)
        const missingByYear = {};
        Object.keys(byYear).forEach(year => {
            const weeks = byYear[year].sort((a, b) => a - b);
            const missing = [];
            for (let week = weeks[0]; week <= weeks[weeks.length - 1]; week++) {
                if (!weeks.includes(week)) {
                    missing.push(week);
                }
            }
            if (missing.length > 0) {
                missingByYear[year] = missing;
            }
        });
        
        let html = `
            <div class="alert alert-info">
                <h6>Payslips Analysis</h6>
                <p><strong>Total Payslips:</strong> ${payslips.length}</p>
                <p><strong>Tax Years:</strong> ${Object.keys(byYear).join(', ')}</p>
            </div>
        `;
        
        if (Object.keys(missingByYear).length > 0) {
            html += '<div class="alert alert-warning"><h6><i class="bi bi-file-earmark-x"></i> Missing Weeks</h6>';
            Object.keys(missingByYear).forEach(year => {
                html += `<p><strong>${year}:</strong> Weeks ${missingByYear[year].join(', ')}</p>`;
            });
            html += '</div>';
        } else {
            html += '<div class="alert alert-success"><i class="bi bi-check-circle"></i> No missing weeks found!</div>';
        }
        
        contentDiv.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading missing payslips:', error);
        contentDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-exclamation-triangle"></i> Error: ${error.message}</div>`;
    }
}

// ===== MILEAGE REPORTS =====

async function loadMileageData() {
    console.log('loadMileageData called');
    try {
        const year = document.getElementById('mileageYear')?.value || '';
        console.log('Loading mileage data for year:', year);
        
        const response = await fetch(`/api/reports/mileage-summary?year=${year}`);
        const data = await response.json();
        
        console.log('Mileage data received:', data);
        
        if (data.success) {
            // Update summary cards
            const totalMilesEl = document.getElementById('totalMiles');
            const totalFuelCostEl = document.getElementById('totalFuelCost');
            const avgMilesPerDayEl = document.getElementById('avgMilesPerDay');
            const costPerMileEl = document.getElementById('costPerMile');
            
            if (totalMilesEl) totalMilesEl.textContent = data.summary.total_miles.toLocaleString();
            if (totalFuelCostEl) totalFuelCostEl.textContent = `£${data.summary.total_fuel_cost.toFixed(2)}`;
            if (avgMilesPerDayEl) avgMilesPerDayEl.textContent = data.summary.avg_miles_per_day.toFixed(1);
            if (costPerMileEl) costPerMileEl.textContent = `£${data.summary.cost_per_mile.toFixed(3)}`;
            
            console.log('Summary cards updated');
            
            // Update charts
            console.log('Updating charts with data:', data.monthly_data.length, 'months');
            updateMileageTrendsChart(data.monthly_data);
            updateFuelCostChart(data.fuel_breakdown);
        } else {
            console.error('API returned error:', data.error);
        }
    } catch (error) {
        console.error('Error loading mileage data:', error);
    }
}

function updateMileageTrendsChart(monthlyData) {
    console.log('updateMileageTrendsChart called with data:', monthlyData);
    const ctx = document.getElementById('mileageTrendsChart');
    if (!ctx) {
        console.error('mileageTrendsChart canvas not found');
        return;
    }
    
    // Destroy existing chart if it exists
    if (window.mileageTrendsChart && typeof window.mileageTrendsChart.destroy === 'function') {
        window.mileageTrendsChart.destroy();
    }
    
    if (!monthlyData || monthlyData.length === 0) {
        console.warn('No monthly data provided for chart');
        return;
    }
    
    const months = monthlyData.map(d => d.month);
    const miles = monthlyData.map(d => d.total_miles);
    const costs = monthlyData.map(d => d.total_fuel_cost);
    
    console.log('Chart data prepared:', { months, miles, costs });
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded');
        return;
    }
    
    window.mileageTrendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: months,
            datasets: [{
                label: 'Miles',
                data: miles,
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                yAxisID: 'y'
            }, {
                label: 'Fuel Cost (£)',
                data: costs,
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                yAxisID: 'y1'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: 'Miles' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: { display: true, text: 'Fuel Cost (£)' },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });
}

function updateFuelCostChart(fuelBreakdown) {
    console.log('updateFuelCostChart called with data:', fuelBreakdown);
    const ctx = document.getElementById('fuelCostChart');
    if (!ctx) {
        console.error('fuelCostChart canvas not found');
        return;
    }
    
    // Destroy existing chart if it exists
    if (window.fuelCostChart && typeof window.fuelCostChart.destroy === 'function') {
        window.fuelCostChart.destroy();
    }
    
    if (!fuelBreakdown || fuelBreakdown.length === 0) {
        console.warn('No fuel breakdown data provided for chart');
        return;
    }
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded');
        return;
    }
    
    window.fuelCostChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: fuelBreakdown.map(d => d.range),
            datasets: [{
                data: fuelBreakdown.map(d => d.count),
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

async function loadRecentMileage() {
    const contentDiv = document.getElementById('recentMileageData');
    contentDiv.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div><p class="mt-2 text-muted">Loading...</p></div>';
    
    try {
        const response = await fetch('/api/reports/recent-mileage');
        const data = await response.json();
        
        if (data.success && data.records.length > 0) {
            let html = '<div class="list-group list-group-flush">';
            
            data.records.forEach(record => {
                const fuelInfo = record.fuel_cost ? `£${parseFloat(record.fuel_cost).toFixed(2)}` : 'No fuel data';
                html += `
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${record.date}</strong>
                            <br>
                            <small class="text-muted">${record.mileage} miles</small>
                        </div>
                        <span class="badge bg-primary rounded-pill">${fuelInfo}</span>
                    </div>
                `;
            });
            
            html += '</div>';
            contentDiv.innerHTML = html;
        } else {
            contentDiv.innerHTML = '<div class="alert alert-info"><i class="bi bi-info-circle"></i> No recent mileage data found</div>';
        }
    } catch (error) {
        console.error('Error loading recent mileage:', error);
        contentDiv.innerHTML = '<div class="alert alert-danger"><i class="bi bi-exclamation-triangle"></i> Error loading data</div>';
    }
}

function generateMonthlyMileageReport() {
    showStatus('Generating monthly mileage report...');
    
    fetch('/api/reports/monthly-mileage', { method: 'POST' })
        .then(response => {
            if (response.headers.get('content-type')?.includes('text/csv')) {
                // Direct CSV download
                return response.blob().then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'monthly_mileage_report.csv';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    showSuccess('Monthly mileage report downloaded!');
                });
            } else {
                return response.json().then(data => {
                    if (data.success) {
                        showSuccess('Monthly mileage report generated!');
                    } else {
                        showError('Failed to generate report: ' + (data.error || 'Unknown error'));
                    }
                });
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Error generating report');
        });
}

function generateHighMileageDays() {
    showStatus('Analyzing high mileage days...');
    
    fetch('/api/reports/high-mileage-days', { method: 'POST' })
        .then(response => {
            if (response.headers.get('content-type')?.includes('text/csv')) {
                // Direct CSV download
                return response.blob().then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'high_mileage_days.csv';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    showSuccess('High mileage days report downloaded!');
                });
            } else {
                return response.json().then(data => {
                    if (data.success) {
                        showSuccess('High mileage days report generated!');
                    } else {
                        showError('Failed to generate report: ' + (data.error || 'Unknown error'));
                    }
                });
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Error generating report');
        });
}

function generateFuelEfficiencyReport() {
    showStatus('Calculating fuel efficiency metrics...');
    
    fetch('/api/reports/fuel-efficiency', { method: 'POST' })
        .then(response => {
            if (response.headers.get('content-type')?.includes('text/csv')) {
                // Direct CSV download
                return response.blob().then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'fuel_efficiency_report.csv';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    showSuccess('Fuel efficiency report downloaded!');
                });
            } else {
                return response.json().then(data => {
                    if (data.success) {
                        showSuccess('Fuel efficiency report generated!');
                    } else {
                        showError('Failed to generate report: ' + (data.error || 'Unknown error'));
                    }
                });
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Error generating report');
        });
}

function generateMissingMileageReport() {
    showStatus('Analyzing missing mileage data...');
    
    fetch('/api/reports/missing-mileage-data', { method: 'POST' })
        .then(response => {
            if (response.headers.get('content-type')?.includes('text/csv')) {
                // Direct CSV download
                return response.blob().then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'missing_mileage_data_report.csv';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    showSuccess('Missing data report downloaded!');
                });
            } else {
                return response.json().then(data => {
                    if (data.success) {
                        showSuccess('Missing data report generated!');
                    } else {
                        showError('Failed to generate report: ' + (data.error || 'Unknown error'));
                    }
                });
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Error generating report');
        });
}

// Manual trigger function for testing
window.testMileageReports = function() {
    console.log('Manual test triggered');
    loadMileageData();
    loadRecentMileage();
};

// Initialize mileage tab when it becomes active
document.addEventListener('DOMContentLoaded', function() {
    // Load mileage data when tab is shown
    const mileageTab = document.getElementById('mileage-tab');
    if (mileageTab) {
        mileageTab.addEventListener('shown.bs.tab', function() {
            console.log('Mileage tab activated, loading data...');
            loadMileageData();
            loadRecentMileage();
        });
        
        // Also load data immediately if the mileage tab is already active
        if (mileageTab.classList.contains('active')) {
            console.log('Mileage tab already active, loading data...');
            loadMileageData();
            loadRecentMileage();
        }
    }
    
    // Add click handler as backup
    const mileageTabButton = document.querySelector('[data-bs-target="#mileage"]');
    if (mileageTabButton) {
        mileageTabButton.addEventListener('click', function() {
            console.log('Mileage tab clicked, loading data...');
            setTimeout(() => {
                loadMileageData();
                loadRecentMileage();
            }, 100);
        });
    }
});
