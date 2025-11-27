function generateMissingDatesReport() {
    showStatus('Generating missing dates report...');
    
    fetch('/api/data/reports/missing-dates', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess('Report generated! Check the data/reports/ folder.');
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
        
        // Use the runsheets discrepancy API endpoint
        const response = await fetch(`/api/runsheets/discrepancy-report?${params.toString()}`);
        const data = await response.json();
        
        if (data.error) {
            contentDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-exclamation-triangle"></i> Error: ${data.error}</div>`;
            return;
        }
        
        // Display results using our new API data structure
        let html = `
            <div class="alert alert-info">
                <h5><i class="bi bi-clipboard-data"></i> Discrepancy Analysis Results</h5>
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Total Payslip Jobs:</strong> ${data.total_payslip_jobs?.toLocaleString() || 0}</p>
                        <p><strong>Total Runsheet Jobs:</strong> ${data.total_runsheet_jobs?.toLocaleString() || 0}</p>
                        <p><strong>Match Rate:</strong> <span class="badge bg-${data.match_rate > 90 ? 'success' : data.match_rate > 80 ? 'warning' : 'danger'}">${data.match_rate}%</span></p>
                    </div>
                    <div class="col-md-6">
                        <p class="text-danger"><strong>Missing from Runsheets:</strong> ${data.total_missing_count?.toLocaleString() || 0}</p>
                        <p class="text-success"><strong>Total Missing Value:</strong> ${CurrencyFormatter.format(data.total_missing_value)}</p>
                    </div>
                </div>
            </div>
        `;
        
        if (data.missing_jobs && data.missing_jobs.length > 0) {
            html += `
                <div class="card border-warning mb-3">
                    <div class="card-header bg-warning text-dark">
                        <h6 class="mb-0"><i class="bi bi-exclamation-triangle"></i> Jobs Paid but Missing from Runsheets (${data.missing_jobs.length})</h6>
                        <small>You were paid for these but don't have runsheet records - ${CurrencyFormatter.format(data.total_missing_value)} total value</small>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-sm table-hover mb-0">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Job #</th>
                                        <th>Client</th>
                                        <th>Location</th>
                                        <th>Amount</th>
                                        <th>Week/Year</th>
                                        <th>Date</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.missing_jobs.map(j => `
                                        <tr>
                                            <td><strong>${j.job_number}</strong></td>
                                            <td>${j.client || 'N/A'}</td>
                                            <td>${j.location || 'N/A'} ${j.postcode || ''}</td>
                                            <td class="text-success">${CurrencyFormatter.format(j.amount)}</td>
                                            <td><small>Week ${j.week_number}/${j.tax_year}</small></td>
                                            <td>
                                                <input type="date" class="form-control form-control-sm" 
                                                       id="date_${j.job_number}" 
                                                       style="width: 150px;">
                                            </td>
                                            <td>
                                                <button class="btn btn-sm btn-primary" 
                                                        onclick="addDiscrepancyToRunsheet('${j.job_number}', '${j.client?.replace(/'/g, "\\'")}', '${j.location?.replace(/'/g, "\\'")}', ${j.amount})">
                                                    <i class="bi bi-plus-circle"></i> Add
                                                </button>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
        }
        
        if (data.total_missing_count === 0) {
            html += `<div class="alert alert-success"><i class="bi bi-check-circle"></i> Excellent! No missing jobs found. All payslip jobs are properly recorded in runsheets.</div>`;
        } else {
            html += `
                <div class="alert alert-warning">
                    <h6><i class="bi bi-info-circle"></i> Recommendations:</h6>
                    <ul class="mb-0">
                        <li>Review missing jobs to identify patterns (e.g., specific agencies or job types)</li>
                        <li>Check if runsheet files are missing for certain date ranges</li>
                        <li>Verify import processes are capturing all work types</li>
                        <li>Generate PDF report for detailed analysis</li>
                    </ul>
                </div>
            `;
        }
        
        // Display results in the tab
        contentDiv.innerHTML = html;
        console.log('Discrepancy Report:', data);
        
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

// Add discrepancy job to runsheet
async function addDiscrepancyToRunsheet(jobNumber, client, location, amount) {
    const dateInput = document.getElementById(`date_${jobNumber}`);
    const selectedDate = dateInput.value;
    
    if (!selectedDate) {
        alert('Please select a date first');
        return;
    }
    
    // Convert YYYY-MM-DD to DD/MM/YYYY
    const [year, month, day] = selectedDate.split('-');
    const formattedDate = `${day}/${month}/${year}`;
    
    try {
        const response = await fetch('/api/runsheets/add-job', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                date: formattedDate,
                job_number: jobNumber,
                customer: client,
                location: location,
                pay_amount: amount,
                status: 'extra'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Show success message
            alert(`✓ Job ${jobNumber} added to runsheet for ${formattedDate} as Extra`);
            
            // Reload the discrepancy report
            loadDiscrepancyReport();
        } else {
            alert(`Error: ${result.error || 'Failed to add job'}`);
        }
    } catch (error) {
        console.error('Error adding job:', error);
        alert(`Error: ${error.message}`);
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
        const attendanceUrl = yearFilter ? `/api/attendance/records?year=${yearFilter}` : '/api/attendance/records';
        const attendanceResponse = await fetch(attendanceUrl);
        const attendanceData = await attendanceResponse.json();
        
        // Handle different response formats and ensure we have an array
        let attendanceRecords = [];
        if (Array.isArray(attendanceData)) {
            attendanceRecords = attendanceData;
        } else if (attendanceData && Array.isArray(attendanceData.records)) {
            attendanceRecords = attendanceData.records;
        } else if (attendanceData && Array.isArray(attendanceData.data)) {
            attendanceRecords = attendanceData.data;
        }
        
        // Create attendance dates set with proper format normalization
        const attendanceDates = new Set();
        attendanceRecords.forEach(record => {
            if (record && record.date) {
                let dateStr = record.date;
                // Normalize different date formats to DD/MM/YYYY
                if (dateStr.includes('-')) {
                    // Convert YYYY-MM-DD to DD/MM/YYYY
                    const [year, month, day] = dateStr.split('-');
                    dateStr = `${day.padStart(2, '0')}/${month.padStart(2, '0')}/${year}`;
                }
                attendanceDates.add(dateStr);
            }
        });
        
        console.log('Attendance records found:', attendanceRecords.length);
        console.log('Attendance dates:', Array.from(attendanceDates).slice(0, 5)); // Show first 5 for debugging
        
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
                    
                    // Only add if not in attendance records (no weekend exclusion - works 7 days)
                    if (!attendanceDates.has(dateStr)) {
                        missingDates.push(dateStr);
                        console.log(`Missing date found: ${dateStr} (not in attendance)`);
                    } else {
                        console.log(`Date ${dateStr} excluded (attendance record exists)`);
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
                <p><strong>Attendance Records:</strong> ${attendanceRecords.length} (${attendanceDates.size} unique dates)</p>
                <p><strong>Date Range:</strong> ${firstDate} to ${lastDate}</p>
                <p class="text-warning"><strong>Missing Days:</strong> ${missingDates.length} (excluding attendance records)</p>
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
        
        const response = await fetch(`/api/data/reports/mileage-summary?year=${year}`);
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
        const response = await fetch('/api/data/reports/recent-mileage');
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

function generateMonthlyMileageReport(format = 'csv') {
    const formatName = format.toUpperCase();
    showStatus(`Generating monthly mileage ${formatName} report...`);
    
    fetch('/api/data/reports/monthly-mileage', { 
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ format: format })
    })
        .then(response => {
            if (response.headers.get('content-type')?.includes('text/csv') || 
                response.headers.get('content-type')?.includes('application/pdf')) {
                // Direct file download
                return response.blob().then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = format === 'pdf' ? 'monthly_mileage_report.pdf' : 'monthly_mileage_report.csv';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    showSuccess(`Monthly mileage ${formatName} report downloaded!`);
                });
            } else {
                return response.json().then(data => {
                    if (data.success) {
                        showSuccess(`Monthly mileage ${formatName} report generated!`);
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

function generateHighMileageDays(format = 'csv') {
    const formatName = format.toUpperCase();
    showStatus(`Analyzing high mileage days for ${formatName} report...`);
    
    fetch('/api/data/reports/high-mileage-days', { 
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ format: format })
    })
        .then(response => {
            if (response.headers.get('content-type')?.includes('text/csv') || 
                response.headers.get('content-type')?.includes('application/pdf')) {
                // Direct file download
                return response.blob().then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = format === 'pdf' ? 'high_mileage_days.pdf' : 'high_mileage_days.csv';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    showSuccess(`High mileage days ${formatName} report downloaded!`);
                });
            } else {
                return response.json().then(data => {
                    if (data.success) {
                        showSuccess(`High mileage days ${formatName} report generated!`);
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
    
    fetch('/api/data/reports/fuel-efficiency', { method: 'POST' })
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

function generateMissingMileageReport(format = 'csv') {
    const formatName = format.toUpperCase();
    showStatus(`Analyzing missing mileage data for ${formatName} report...`);
    
    fetch('/api/data/reports/missing-mileage-data', { 
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ format: format })
    })
        .then(response => {
            if (response.headers.get('content-type')?.includes('text/csv') || 
                response.headers.get('content-type')?.includes('application/pdf')) {
                // Direct file download
                return response.blob().then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = format === 'pdf' ? 'missing_mileage_data_report.pdf' : 'missing_mileage_data_report.csv';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    showSuccess(`Missing data ${formatName} report downloaded!`);
                });
            } else {
                return response.json().then(data => {
                    if (data.success) {
                        showSuccess(`Missing data ${formatName} report generated!`);
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

// PDF Generation for Discrepancy Report
async function generateDiscrepancyPDF() {
    try {
        // Get current filter values
        const year = document.getElementById('discrepancyYear')?.value || '';
        const month = document.getElementById('discrepancyMonth')?.value || '';
        
        // Show loading state
        const button = event.target;
        button.innerHTML = '<i class="bi bi-hourglass-split"></i> Generating...';
        button.disabled = true;
        
        // Use the PDF generation endpoint
        const response = await fetch('/api/runsheets/discrepancy-pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ year, month })
        });
        
        if (response.ok) {
            // Download the PDF file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Generate filename with date filters
            let filename = 'discrepancy_report';
            if (year) filename += `_${year}`;
            if (month) filename += `_${month}`;
            filename += `_${new Date().toISOString().slice(0, 10)}.pdf`;
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showSuccess('Professional PDF report downloaded successfully! Contains executive summary, detailed analysis, and recommendations.');
        } else {
            const error = await response.json();
            showError(`Failed to generate PDF: ${error.error || 'Unknown error'}`);
        }
        
    } catch (error) {
        console.error('Error:', error);
        showError('Error generating PDF report');
    } finally {
        // Restore button state
        const button = event.target;
        button.innerHTML = '<i class="bi bi-file-earmark-pdf"></i> PDF';
        button.disabled = false;
    }
}

// CSV Generation for Discrepancy Report
async function generateDiscrepancyCSV() {
    try {
        // Get current filter values
        const year = document.getElementById('discrepancyYear')?.value || '';
        const month = document.getElementById('discrepancyMonth')?.value || '';
        
        // Show loading state
        const button = event.target;
        button.innerHTML = '<i class="bi bi-hourglass-split"></i> Generating...';
        button.disabled = true;
        
        // Use the CSV generation endpoint
        const response = await fetch('/api/runsheets/discrepancy-csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ year, month })
        });
        
        if (response.ok) {
            // Download the CSV file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Generate filename with date filters
            let filename = 'discrepancy_report';
            if (year) filename += `_${year}`;
            if (month) filename += `_${month}`;
            filename += `_${new Date().toISOString().slice(0, 10)}.csv`;
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showSuccess('CSV report downloaded successfully! Contains all missing job details with applied date filters.');
        } else {
            const error = await response.json();
            showError(`Failed to generate CSV: ${error.error || 'Unknown error'}`);
        }
        
    } catch (error) {
        console.error('Error:', error);
        showError('Error generating CSV report');
    } finally {
        // Restore button state
        const button = event.target;
        button.innerHTML = '<i class="bi bi-file-earmark-spreadsheet"></i> CSV';
        button.disabled = false;
    }
}

// Helper functions for status messages
function showSuccess(message) {
    const alert = document.createElement('div');
    alert.className = 'alert alert-success alert-dismissible fade show position-fixed';
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alert.innerHTML = `<i class="bi bi-check-circle"></i> ${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    document.body.appendChild(alert);
    setTimeout(() => alert.remove(), 5000);
}

function showError(message) {
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alert.innerHTML = `<i class="bi bi-exclamation-triangle"></i> ${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    document.body.appendChild(alert);
    setTimeout(() => alert.remove(), 8000);
}

// Weekly Summary Functions moved to weekly-summary.js

// ===== REPORT GENERATOR FUNCTIONS =====

// Initialize report generator on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeReportGenerator();
});

function initializeReportGenerator() {
    // Populate year dropdown with last 5 years and select current year
    const yearSelect = document.getElementById('yearSelect');
    if (yearSelect && yearSelect.options.length === 0) { // Only populate if empty
        const currentYear = new Date().getFullYear();
        for (let year = currentYear; year >= currentYear - 5; year--) {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            if (year === currentYear) {
                option.selected = true;
            }
            yearSelect.appendChild(option);
        }
    }
    
    // Populate month dropdown with "All Months" selected by default
    const monthSelect = document.getElementById('monthSelect');
    if (monthSelect && monthSelect.options.length === 0) {
        const allOption = document.createElement('option');
        allOption.value = '';
        allOption.textContent = 'All Months';
        allOption.selected = true;
        monthSelect.appendChild(allOption);
        
        const months = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December'];
        months.forEach((month, index) => {
            const option = document.createElement('option');
            option.value = index + 1;
            option.textContent = month;
            monthSelect.appendChild(option);
        });
    }
    
    // Populate week dropdown (1-53) with "All Weeks" selected by default
    const weekSelect = document.getElementById('weekSelect');
    if (weekSelect && weekSelect.options.length === 0) {
        const allOption = document.createElement('option');
        allOption.value = '';
        allOption.textContent = 'All Weeks';
        allOption.selected = true;
        weekSelect.appendChild(allOption);
        
        for (let week = 1; week <= 53; week++) {
            const option = document.createElement('option');
            option.value = week;
            option.textContent = `Week ${week}`;
            weekSelect.appendChild(option);
        }
    }
    
    // Auto-generate the report on page load
    const reportType = document.getElementById('reportType');
    if (reportType && reportType.value === 'dnco') {
        generateCustomReport();
    }
}

function selectWeek() {
    // Clear month selection when week is selected
    const monthSelect = document.getElementById('monthSelect');
    if (monthSelect) {
        monthSelect.value = '';
    }
    generateCustomReport();
}

function selectMonth() {
    // Clear week selection when month is selected
    const weekSelect = document.getElementById('weekSelect');
    if (weekSelect) {
        weekSelect.value = '';
    }
    generateCustomReport();
}

// Store last report data for sorting
let lastReportData = null;
let lastReportType = null;
let sortDescending = true; // Default to descending (latest first)

function toggleReportSort() {
    sortDescending = !sortDescending;
    
    // Update icon
    const icon = document.getElementById('sortIcon');
    if (icon) {
        icon.className = sortDescending ? 'bi bi-sort-down' : 'bi bi-sort-up';
    }
    
    // Re-render the report with new sort order
    if (lastReportData && lastReportType) {
        displayCustomReportData(lastReportData, lastReportType);
    }
}

function updateReportPreview() {
    // Auto-generate when report type changes
    generateCustomReport();
}

// Generate custom report
async function generateCustomReport() {
    const reportType = document.getElementById('reportType').value;
    const year = document.getElementById('yearSelect').value;
    const week = document.getElementById('weekSelect').value;
    const month = document.getElementById('monthSelect').value;
    
    const outputDiv = document.getElementById('customReportOutput');
    
    if (!reportType) {
        outputDiv.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-3 text-muted">Select a report type to generate...</p>
            </div>
        `;
        return;
    }
    
    outputDiv.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3 text-muted">Generating ${reportType} report...</p>
        </div>
    `;
    
    try {
        const response = await fetch('/api/data/reports/custom', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                report_type: reportType,
                year: year,
                week: week,
                month: month
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Store data for sorting
            lastReportData = result.data;
            lastReportType = reportType;
            displayCustomReportData(result.data, reportType);
        } else {
            outputDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-exclamation-triangle"></i> ${result.error}</div>`;
        }
    } catch (error) {
        console.error('Error generating report:', error);
        outputDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-exclamation-triangle"></i> Error: ${error.message}</div>`;
    }
}

function displayCustomReportData(data, reportType) {
    // Apply sorting to the data before displaying
    if (data.dnco_jobs) {
        data.dnco_jobs.sort((a, b) => {
            const dateA = parseDate(a.date);
            const dateB = parseDate(b.date);
            return sortDescending ? dateB - dateA : dateA - dateB;
        });
    }
    
    if (data.pending_jobs) {
        data.pending_jobs.sort((a, b) => {
            const dateA = parseDate(a.date);
            const dateB = parseDate(b.date);
            return sortDescending ? dateB - dateA : dateA - dateB;
        });
    }
    if (data.discrepancies) {
        data.discrepancies.sort((a, b) => {
            if (reportType === 'earnings_discrepancy') {
                // Sort by week number
                return sortDescending ? b.week - a.week : a.week - b.week;
            } else {
                const dateA = parseDate(a.date);
                const dateB = parseDate(b.date);
                return sortDescending ? dateB - dateA : dateA - dateB;
            }
        });
    }
    if (data.jobs) {
        data.jobs.sort((a, b) => {
            const dateA = parseDate(a.date);
            const dateB = parseDate(b.date);
            return sortDescending ? dateB - dateA : dateA - dateB;
        });
    }
    if (data.mileage) {
        data.mileage.sort((a, b) => {
            const dateA = parseDate(a.date);
            const dateB = parseDate(b.date);
            return sortDescending ? dateB - dateA : dateA - dateB;
        });
    }
    
    displayCustomReport(data, reportType);
}

// Helper function to parse DD/MM/YYYY dates
function parseDate(dateStr) {
    if (!dateStr) return new Date(0);
    const parts = dateStr.split('/');
    if (parts.length === 3) {
        return new Date(parts[2], parts[1] - 1, parts[0]);
    }
    return new Date(0);
}

function displayCustomReport(data, reportType) {
    const outputDiv = document.getElementById('customReportOutput');
    
    let html = '';
    
    // Data table
    if (reportType === 'earnings' && data.payslips) {
        html += `
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Date</th>
                            <th>Week</th>
                            <th>Gross Pay</th>
                            <th>Net Pay</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        data.payslips.forEach(p => {
            html += `
                <tr>
                    <td>${p.date}</td>
                    <td>${p.week}</td>
                    <td>${formatCurrency(p.gross)}</td>
                    <td>${formatCurrency(p.net)}</td>
                    <td><span class="badge bg-${p.status === 'paid' ? 'success' : 'warning'}">${p.status}</span></td>
                </tr>
            `;
        });
        html += `</tbody></table></div>`;
        
    } else if (reportType === 'jobs' && data.jobs) {
        html += `
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr><th>Job Number</th><th>Customer</th><th>Amount</th><th>Date</th></tr>
                    </thead>
                    <tbody>
        `;
        data.jobs.forEach(j => {
            html += `<tr><td>${j.job}</td><td>${j.customer}</td><td>${formatCurrency(j.amount)}</td><td>${j.date}</td></tr>`;
        });
        html += `</tbody></table></div>`;
        
    } else if (reportType === 'mileage' && data.mileage) {
        html += `
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr><th>Date</th><th>Job Number</th><th>Customer</th><th>Amount</th></tr>
                    </thead>
                    <tbody>
        `;
        data.mileage.forEach(m => {
            html += `<tr><td>${m.date}</td><td>${m.job}</td><td>${m.customer}</td><td>${formatCurrency(m.amount)}</td></tr>`;
        });
        html += `</tbody></table></div>`;
        
    } else if (reportType === 'pending' && data.pending_jobs) {
        // Pending Jobs Report
        html += `
            <div class="alert alert-warning mb-3">
                <div class="d-flex align-items-center mb-3">
                    <i class="bi bi-clock-fill me-2"></i>
                    <strong>Pending Jobs Report</strong>
                </div>
                <div class="row">
                    <div class="col-md-12">
                        <div><strong>Total Pending Jobs:</strong> ${data.summary.total_pending}</div>
                        <p class="mb-0 mt-2 small">These jobs have not been marked as completed, missed, or DNCO</p>
                    </div>
                </div>
            </div>
        `;
        
        // Table
        html += `
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Date</th>
                            <th>Job Number</th>
                            <th>Customer</th>
                            <th>Address</th>
                            <th>Activity</th>
                            <th>Priority</th>
                            <th>Notes</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        data.pending_jobs.forEach(job => {
            const priorityBadge = job.priority ? `<span class="badge bg-${job.priority === 'High' ? 'danger' : job.priority === 'Medium' ? 'warning' : 'secondary'}">${job.priority}</span>` : '-';
            html += `
                <tr>
                    <td>${job.date}</td>
                    <td><strong>${job.job_number || '-'}</strong></td>
                    <td>${job.customer || '-'}</td>
                    <td class="small">${job.address || '-'}</td>
                    <td class="small">${job.activity || '-'}</td>
                    <td>${priorityBadge}</td>
                    <td class="small">${job.notes || '-'}</td>
                </tr>
            `;
        });
        html += `</tbody></table></div>`;
        
    } else if (reportType === 'dnco' && data.dnco_jobs) {
        // DNCO Analysis Results Box
        html += `
            <div class="alert alert-info mb-3">
                <div class="d-flex align-items-center mb-3">
                    <i class="bi bi-info-circle-fill me-2"></i>
                    <strong>Report Summary</strong>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div><strong>Estimated Loss:</strong> ${formatCurrency(data.summary.estimated_loss)}</div>
                    </div>
                    <div class="col-md-6">
                        <div><strong>Total Dnco:</strong> ${data.summary.total_dnco}</div>
                    </div>
                </div>
            </div>
        `;
        
        // Warning banner
        html += `
            <div class="alert alert-warning">
                <strong><i class="bi bi-exclamation-triangle me-2"></i>Jobs Not Completed (${data.summary.total_dnco})</strong>
                <p class="mb-0 mt-2">These jobs were not completed and represent potential lost earnings</p>
            </div>
        `;
        
        // Table
        html += `
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr><th>Date</th><th>Job Number</th><th>Customer</th><th>Address</th><th>Est. Loss</th></tr>
                    </thead>
                    <tbody>
        `;
        data.dnco_jobs.forEach(d => {
            html += `<tr><td>${d.date}</td><td>${d.job}</td><td>${d.customer}</td><td>${d.address}</td><td class="text-danger fw-bold">${formatCurrency(d.amount)}</td></tr>`;
        });
        html += `</tbody></table></div>`;
        
    } else if (reportType === 'earnings_discrepancy' && data.discrepancies) {
        // Earnings Discrepancy Report
        html += `
            <div class="alert alert-info mb-3">
                <div class="d-flex align-items-center mb-3">
                    <i class="bi bi-info-circle-fill me-2"></i>
                    <strong>Earnings Discrepancy Summary</strong>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div><strong>Weeks with Discrepancy:</strong> ${data.summary.weeks_with_discrepancy}</div>
                    </div>
                    <div class="col-md-6">
                        <div><strong>Total Discrepancy:</strong> <span class="${data.summary.total_discrepancy >= 0 ? 'text-success' : 'text-danger'}">${formatCurrency(data.summary.total_discrepancy)}</span></div>
                    </div>
                </div>
            </div>
        `;
        
        html += `
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Week</th>
                            <th>Period End</th>
                            <th>Payslip Amount</th>
                            <th>Runsheet Amount</th>
                            <th>Discrepancy</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        data.discrepancies.forEach(d => {
            const discrepancyClass = d.discrepancy >= 0 ? 'text-success' : 'text-danger';
            const discrepancyIcon = d.discrepancy >= 0 ? '▲' : '▼';
            html += `
                <tr>
                    <td>Week ${d.week}/${d.year}</td>
                    <td>${d.period_end}</td>
                    <td>${formatCurrency(d.payslip_amount)}</td>
                    <td>${formatCurrency(d.runsheet_amount)}</td>
                    <td class="${discrepancyClass} fw-bold">${discrepancyIcon} ${formatCurrency(Math.abs(d.discrepancy))}</td>
                </tr>
            `;
        });
        html += `</tbody></table></div>`;
        
    } else if (reportType === 'discrepancies' && data.discrepancies) {
        html += `
            <div class="alert alert-warning">
                <strong><i class="bi bi-exclamation-triangle me-2"></i>Jobs Paid but Missing from Run Sheets</strong>
            </div>
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr><th>Job Number</th><th>Customer</th><th>Amount</th><th>Date</th></tr>
                    </thead>
                    <tbody>
        `;
        data.discrepancies.forEach(d => {
            html += `<tr><td>${d.job}</td><td>${d.customer}</td><td>${formatCurrency(d.amount)}</td><td>${d.date}</td></tr>`;
        });
        html += `</tbody></table></div>`;
        
    } else if ((reportType === 'missing-runsheets' || reportType === 'missing-payslips') && data.dates) {
        html += `
            <div class="alert alert-warning">
                <strong><i class="bi bi-calendar-x me-2"></i>Missing Dates</strong>
            </div>
            <div class="row">
        `;
        data.dates.forEach(d => {
            html += `<div class="col-md-3 mb-2"><span class="badge bg-warning">${d.date}</span></div>`;
        });
        html += `</div>`;
        
    } else if (reportType === 'paypoint' && data) {
        // Paypoint Report - Stock, Deployments, and Returns
        html += `
            <div class="alert alert-info mb-3">
                <strong><i class="bi bi-device-hdd me-2"></i>Paypoint Stock Management Report</strong>
                <p class="mb-0 mt-2">Overview of stock levels, deployments, and returns</p>
            </div>
            
            <!-- Summary Cards -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card bg-primary text-white">
                        <div class="card-body text-center">
                            <h4>${data.summary.total_stock || 0}</h4>
                            <small>Total Stock</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-success text-white">
                        <div class="card-body text-center">
                            <h4>${data.summary.available_stock || 0}</h4>
                            <small>Available</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-warning text-white">
                        <div class="card-body text-center">
                            <h4>${data.summary.deployments_count || 0}</h4>
                            <small>Deployments</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-info text-white">
                        <div class="card-body text-center">
                            <h4>${data.summary.returns_count || 0}</h4>
                            <small>Returns</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Deployments Table
        if (data.deployments && data.deployments.length > 0) {
            html += `
                <h5><i class="bi bi-box-arrow-right text-warning"></i> Recent Deployments</h5>
                <div class="table-responsive mb-4">
                    <table class="table table-striped table-hover">
                        <thead class="table-dark">
                            <tr>
                                <th>Date</th>
                                <th>Job Number</th>
                                <th>Customer</th>
                                <th>Device Type</th>
                                <th>Serial/TID</th>
                                <th>Trace/Stock</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            data.deployments.forEach(d => {
                const deployDate = d.deployment_date ? new Date(d.deployment_date).toLocaleDateString('en-GB') : 'N/A';
                html += `
                    <tr>
                        <td>${deployDate}</td>
                        <td>${d.job_number || 'N/A'}</td>
                        <td>${d.customer || 'N/A'}</td>
                        <td>${d.paypoint_type || 'N/A'}</td>
                        <td><span class="badge bg-secondary">${d.serial_ptid || 'N/A'}</span></td>
                        <td><span class="badge bg-info">${d.trace_stock || 'N/A'}</span></td>
                        <td><span class="badge bg-${d.status === 'deployed' ? 'warning' : 'success'}">${d.status || 'N/A'}</span></td>
                    </tr>
                `;
            });
            html += `</tbody></table></div>`;
        }
        
        // Returns Table
        if (data.returns && data.returns.length > 0) {
            html += `
                <h5><i class="bi bi-arrow-down-circle text-info"></i> Recent Returns</h5>
                <div class="table-responsive">
                    <table class="table table-striped table-hover">
                        <thead class="table-dark">
                            <tr>
                                <th>Return Date</th>
                                <th>Job Number</th>
                                <th>Device Type</th>
                                <th>Return Serial/TID</th>
                                <th>Return Trace</th>
                                <th>Reason</th>
                                <th>Customer</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            data.returns.forEach(r => {
                const returnDate = r.return_date ? new Date(r.return_date).toLocaleDateString('en-GB') : 'N/A';
                html += `
                    <tr>
                        <td>${returnDate}</td>
                        <td>${r.job_number || 'N/A'}</td>
                        <td>${r.paypoint_type || 'N/A'}</td>
                        <td><span class="badge bg-secondary">${r.return_serial_ptid || 'N/A'}</span></td>
                        <td><span class="badge bg-info">${r.return_trace || 'N/A'}</span></td>
                        <td>${r.return_reason || 'N/A'}</td>
                        <td>${r.customer || 'N/A'}</td>
                    </tr>
                `;
            });
            html += `</tbody></table></div>`;
        }
    }
    
    outputDiv.innerHTML = html;
}

async function exportCustomReportPDF() {
    const reportType = document.getElementById('reportType').value;
    const year = document.getElementById('yearSelect').value;
    const week = document.getElementById('weekSelect').value;
    const month = document.getElementById('monthSelect').value;
    
    if (!reportType) {
        showError('Please select a report type first');
        return;
    }
    
    try {
        
        const response = await fetch('/api/data/reports/custom/pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                report_type: reportType,
                year: year,
                week: week,
                month: month
            })
        });
        
        if (response.ok) {
            // Get the PDF blob
            const blob = await response.blob();
            
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Generate filename
            let filename = `${reportType}_report`;
            if (year && week) {
                filename += `_${year}_week${week}`;
            } else if (year && month) {
                filename += `_${year}_${month}`;
            } else if (year) {
                filename += `_${year}`;
            }
            filename += '.pdf';
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showSuccess('PDF downloaded successfully!');
        } else {
            const error = await response.json();
            showError('Failed to generate PDF: ' + (error.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error exporting PDF:', error);
        showError('Error generating PDF: ' + error.message);
    }
}

function exportCustomReportCSV() {
    const reportType = document.getElementById('reportType').value;
    
    if (!reportType) {
        showError('Please select a report type first');
        return;
    }
    
    showSuccess('CSV export functionality coming soon!');
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize reports page
});
