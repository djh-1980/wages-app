// Run Sheets Tab JavaScript

let activityChart = null;
let currentRSPage = 1;
let currentRSSortColumn = 'date';
let currentRSSortOrder = 'desc';
let currentFilters = {
    year: '',
    month: '',
    week: '',
    day: ''
};

// Note: This file is now used on the dedicated runsheets page
// Data loading is triggered from the page template

// Populate year filter
function populateYearFilter() {
    const currentYear = new Date().getFullYear();
    const yearSelect = document.getElementById('filterYear');
    
    // Add years from 2021 to current year
    for (let year = currentYear; year >= 2021; year--) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearSelect.appendChild(option);
    }
}

// Populate week filter based on selected year
function populateWeekFilter() {
    const year = document.getElementById('filterYear').value;
    const weekSelect = document.getElementById('filterWeek');
    
    // Clear existing options except "All Weeks"
    weekSelect.innerHTML = '<option value="">All Weeks</option>';
    
    if (year) {
        // Add weeks 1-52
        for (let week = 1; week <= 52; week++) {
            const option = document.createElement('option');
            option.value = week;
            option.textContent = `Week ${week}`;
            weekSelect.appendChild(option);
        }
    }
}

// Apply filters
function applyRunSheetFilters() {
    const yearSelect = document.getElementById('filterYear');
    const monthSelect = document.getElementById('filterMonth');
    const weekSelect = document.getElementById('filterWeek');
    const daySelect = document.getElementById('filterDay');
    
    currentFilters.year = yearSelect.value;
    currentFilters.month = monthSelect.value;
    currentFilters.week = weekSelect.value;
    currentFilters.day = daySelect.value;
    
    // Update week filter options when year changes
    const yearChanged = yearSelect.value !== currentFilters.year;
    if (yearChanged && yearSelect.value) {
        populateWeekFilter();
        // Reset week selection when year changes
        weekSelect.value = '';
        currentFilters.week = '';
    }
    
    // Reload list with filters
    loadRunSheetsList(1);
}

// Sort run sheets by column
function sortRunSheets(column) {
    if (currentRSSortColumn === column) {
        // Toggle sort order
        currentRSSortOrder = currentRSSortOrder === 'asc' ? 'desc' : 'asc';
    } else {
        // New column, default to descending for date, ascending for others
        currentRSSortColumn = column;
        currentRSSortOrder = column === 'date' ? 'desc' : 'asc';
    }
    
    // Reload with new sort
    loadRunSheetsList(1);
}

// Load Run Sheets summary
async function loadRunSheetsSummary() {
    try {
        const response = await fetch('/api/runsheets/summary');
        const data = await response.json();
        
        // Update summary cards
        document.getElementById('rsTotalDays').textContent = data.overall.total_days || 0;
        document.getElementById('rsTotalJobs').textContent = data.overall.total_jobs || 0;
        document.getElementById('rsUniqueCustomers').textContent = data.overall.unique_customers || 0;
        document.getElementById('rsAvgJobsPerDay').textContent = (data.avg_jobs_per_day || 0).toFixed(1);
        
        // Update top customers table with mappings
        const tableBody = document.getElementById('rsTopCustomersTable');
        if (data.top_customers && data.top_customers.length > 0) {
            // Wait for customer mappings to load
            await window.customerMapping.loadMappings();
            
            // Group by mapped customer names and aggregate
            const mappedStats = window.customerMapping.getAggregatedStats(
                data.top_customers.map(c => ({ customer: c.customer, job_count: c.job_count })),
                'customer',
                ['job_count']
            );
            
            // Convert to array and sort by job count
            const sortedCustomers = Object.values(mappedStats)
                .sort((a, b) => b.job_count - a.job_count)
                .slice(0, 10); // Top 10
            
            const totalJobs = data.overall.total_jobs;
            tableBody.innerHTML = sortedCustomers.map(customer => {
                const originalCustomers = customer.original_customers;
                const tooltipText = originalCustomers.length > 1 ? 
                    `Includes: ${originalCustomers.join(', ')}` : 
                    `Original: ${originalCustomers[0]}`;
                    
                return `
                    <tr title="${tooltipText}">
                        <td>
                            ${customer.customer}
                            ${originalCustomers.length > 1 ? `<small class="text-muted d-block">(${originalCustomers.length} sources)</small>` : ''}
                        </td>
                        <td class="text-end">${customer.job_count}</td>
                        <td class="text-end">${((customer.job_count / totalJobs) * 100).toFixed(1)}%</td>
                    </tr>
                `;
            }).join('');
        } else {
            tableBody.innerHTML = '<tr><td colspan="3" class="text-center">No data available</td></tr>';
        }
        
        // Create activity chart - DISABLED: Now handled by runsheet-analytics.js
        // if (data.activities && data.activities.length > 0) {
        //     createActivityChart(data.activities);
        // }
        
    } catch (error) {
        console.error('Error loading run sheets summary:', error);
    }
}

// Create activity breakdown chart
function createActivityChart(activities) {
    const ctx = document.getElementById('activityChart');
    
    if (activityChart) {
        activityChart.destroy();
    }
    
    const colors = [
        '#667eea', '#764ba2', '#f093fb', '#4facfe',
        '#43e97b', '#fa709a', '#fee140', '#30cfd0'
    ];
    
    activityChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: activities.map(a => a.activity),
            datasets: [{
                data: activities.map(a => a.count),
                backgroundColor: colors.slice(0, activities.length),
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Load Run Sheets list
async function loadRunSheetsList(page = 1) {
    currentRSPage = page;
    
    // Build query string with filters
    let queryParams = `page=${page}&per_page=20&sort=${currentRSSortColumn}&order=${currentRSSortOrder}`;
    
    if (currentFilters.year) queryParams += `&year=${currentFilters.year}`;
    if (currentFilters.month) queryParams += `&month=${currentFilters.month}`;
    if (currentFilters.week) queryParams += `&week=${currentFilters.week}`;
    if (currentFilters.day) queryParams += `&day=${currentFilters.day}`;
    
    try {
        // Load both run sheets list and completion status
        const [listResponse, statusResponse] = await Promise.all([
            fetch(`/api/runsheets/list?${queryParams}`),
            fetch('/api/runsheets/completion-status')
        ]);
        
        const data = await listResponse.json();
        const statusData = await statusResponse.json();
        
        const tbody = document.getElementById('runsheetsList');
        const mobileCards = document.getElementById('runsheetsCardsList');
        
        if (data.runsheets && data.runsheets.length > 0) {
            // Desktop table content
            tbody.innerHTML = data.runsheets.map(rs => {
                const activities = rs.activities ? rs.activities.split(',').slice(0, 3).join(', ') : 'N/A';
                
                // Get completion status for this date
                const status = statusData[rs.date];
                let statusBadge = '';
                
                if (status) {
                    switch (status.status) {
                        case 'completed':
                            statusBadge = '<span class="badge bg-success px-3 py-2" title="All jobs completed with mileage"><i class="bi bi-check-circle me-1"></i>Complete</span>';
                            break;
                        case 'in_progress':
                            statusBadge = '<span class="badge bg-warning px-3 py-2" title="Some jobs completed or in progress"><i class="bi bi-clock me-1"></i>In Progress</span>';
                            break;
                        case 'not_started':
                            statusBadge = '<span class="badge bg-danger px-3 py-2" title="No jobs completed yet"><i class="bi bi-circle me-1"></i>Not Started</span>';
                            break;
                    }
                }
                
                // Format daily pay
                let payDisplay = '';
                if (rs.daily_pay && rs.daily_pay > 0) {
                    payDisplay = `<strong class="text-success">${CurrencyFormatter.format(rs.daily_pay)}</strong>`;
                    if (rs.jobs_with_pay && rs.jobs_with_pay < rs.job_count) {
                        payDisplay += `<br><small class="text-muted">${rs.jobs_with_pay}/${rs.job_count} jobs</small>`;
                    }
                } else {
                    payDisplay = '<span class="text-muted">No pay data</span>';
                }

                // Format mileage and fuel cost
                let mileageDisplay = '';
                if (rs.mileage !== null && rs.mileage !== undefined) {
                    mileageDisplay = `<strong class="text-primary">${rs.mileage} miles</strong>`;
                    if (rs.fuel_cost !== null && rs.fuel_cost !== undefined) {
                        mileageDisplay += `<br><small class="text-muted">${CurrencyFormatter.format(rs.fuel_cost)} fuel</small>`;
                    }
                } else {
                    mileageDisplay = '<span class="text-muted">Not recorded</span>';
                }

                return `
                    <tr>
                        <td><strong>${rs.date}</strong></td>
                        <td class="text-center">
                            <span class="badge bg-primary">${rs.job_count} jobs</span>
                        </td>
                        <td><small>${activities}</small></td>
                        <td class="text-end">${payDisplay}</td>
                        <td class="text-end">${mileageDisplay}</td>
                        <td class="text-center">
                            ${statusBadge || '<span class="badge bg-secondary">Unknown</span>'}
                        </td>
                        <td class="text-end">
                            <button class="btn btn-sm btn-outline-primary" onclick="viewRunSheetJobs('${rs.date}')">
                                <i class="bi bi-eye"></i> View
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
            
            // Mobile cards content
            if (mobileCards) {
                mobileCards.innerHTML = data.runsheets.map(rs => {
                const activities = rs.activities ? rs.activities.split(',').slice(0, 2).join(', ') : 'N/A';
                
                // Get completion status for this date
                const status = statusData[rs.date];
                let statusBadge = '';
                
                if (status) {
                    switch (status.status) {
                        case 'completed':
                            statusBadge = '<span class="badge bg-success" title="All jobs completed with mileage"><i class="bi bi-check-circle me-1"></i>Complete</span>';
                            break;
                        case 'in_progress':
                            statusBadge = '<span class="badge bg-warning" title="Some jobs completed or in progress"><i class="bi bi-clock me-1"></i>In Progress</span>';
                            break;
                        case 'not_started':
                            statusBadge = '<span class="badge bg-danger" title="No jobs completed yet"><i class="bi bi-circle me-1"></i>Not Started</span>';
                            break;
                    }
                }
                
                // Format daily pay for mobile
                let payDisplay = '';
                if (rs.daily_pay && rs.daily_pay > 0) {
                    payDisplay = `<div class="text-success fw-bold mb-1">${CurrencyFormatter.format(rs.daily_pay)}</div>`;
                }

                // Format mileage for mobile
                let mileageDisplayMobile = '';
                if (rs.mileage !== null && rs.mileage !== undefined) {
                    mileageDisplayMobile = `<div class="text-primary fw-bold mb-1">${rs.mileage} miles`;
                    if (rs.fuel_cost !== null && rs.fuel_cost !== undefined) {
                        mileageDisplayMobile += ` • ${CurrencyFormatter.format(rs.fuel_cost)} fuel`;
                    }
                    mileageDisplayMobile += `</div>`;
                }
                
                return `
                    <div class="card mb-3 shadow-sm" style="border-radius: 12px;">
                        <div class="card-body p-3">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <div>
                                    <h6 class="mb-1 fw-bold" style="font-size: 1.1rem;">${rs.date}</h6>
                                    <span class="badge bg-primary">${rs.job_count} jobs</span>
                                </div>
                                <div>
                                    ${statusBadge || '<span class="badge bg-secondary">Unknown</span>'}
                                </div>
                            </div>
                            ${payDisplay}
                            ${mileageDisplayMobile}
                            <p class="mb-3 small text-muted" style="font-size: 0.85rem;">${activities}</p>
                            <div class="d-grid">
                                <button class="btn btn-primary py-2" onclick="viewRunSheetJobs('${rs.date}')" style="font-size: 1rem;">
                                    <i class="bi bi-eye me-2"></i>View Jobs
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                }).join('');
            }
            
            // Update pagination
            updateRSPagination(data.page, data.total_pages);
        } else {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center">No run sheets found</td></tr>';
            if (mobileCards) {
                mobileCards.innerHTML = '<div class="text-center p-4"><p class="text-muted">No run sheets found</p></div>';
            }
        }
        
    } catch (error) {
        console.error('Error loading run sheets list:', error);
        document.getElementById('runsheetsList').innerHTML = 
            '<tr><td colspan="7" class="text-center text-danger">Error loading data</td></tr>';
        const mobileCardsError = document.getElementById('runsheetsCardsList');
        if (mobileCardsError) {
            mobileCardsError.innerHTML = '<div class="text-center p-4"><p class="text-danger">Error loading data</p></div>';
        }
    }
}

// Update pagination
function updateRSPagination(currentPage, totalPages) {
    const pagination = document.getElementById('rsPagination');
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous button
    html += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadRunSheetsList(${currentPage - 1}); return false;">
                <i class="bi bi-chevron-left"></i>
            </a>
        </li>
    `;
    
    // Page numbers
    const maxPages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxPages / 2));
    let endPage = Math.min(totalPages, startPage + maxPages - 1);
    
    if (endPage - startPage < maxPages - 1) {
        startPage = Math.max(1, endPage - maxPages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        html += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="loadRunSheetsList(${i}); return false;">${i}</a>
            </li>
        `;
    }
    
    // Next button
    html += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadRunSheetsList(${currentPage + 1}); return false;">
                <i class="bi bi-chevron-right"></i>
            </a>
        </li>
    `;
    
    pagination.innerHTML = html;
}

// View jobs for a specific date
async function viewRunSheetJobs(date) {
    try {
        const response = await fetch(`/api/runsheets/jobs?date=${encodeURIComponent(date)}`);
        const data = await response.json();
        
        // Store jobs globally for edit function
        window.currentRunsheetJobs = data.jobs;
        
        if (data.jobs && data.jobs.length > 0) {
            // Debug: log first job to see what data we have
            console.log('First job data:', data.jobs[0]);
            
            // Debug: find job 4290172
            const job4290172 = data.jobs.find(j => j.job_number === '4290172');
            if (job4290172) {
                console.log('Job 4290172 data:', job4290172);
                console.log('Job 4290172 price_agreed:', job4290172.price_agreed);
            }
            
            // Create modal content
            let modalHTML = `
                <div class="modal fade" id="runsheetJobsModal" tabindex="-1">
                    <div class="modal-dialog modal-xl">
                        <div class="modal-content">
                            <div class="modal-header bg-gradient-primary text-white">
                                <h5 class="modal-title">
                                    <i class="bi bi-calendar-check"></i> Run Sheet - ${date}
                                </h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <div class="d-flex justify-content-between align-items-start mb-2">
                                        <p class="mb-0"><strong>${data.jobs.length} jobs</strong> on this day</p>
                                        <p class="mb-0 text-success fw-bold">
                                            Total Pay: ${(() => {
                                                const totalPay = data.jobs.reduce((sum, job) => sum + (job.pay_amount || 0), 0);
                                                return totalPay > 0 ? CurrencyFormatter.format(totalPay) : 'No pay data';
                                            })()}
                                        </p>
                                    </div>
                                    <div class="d-flex flex-wrap gap-1">
                                        <span class="badge bg-success" id="completedCount">0 Completed</span>
                                        <span class="badge bg-danger" id="missedCount">0 Missed</span>
                                        <span class="badge bg-warning" id="dncoCount">0 DNCO</span>
                                        <span class="badge bg-info" id="extraCount">0 Extra</span>
                                    </div>
                                </div>
                                
                                <!-- Desktop Table View -->
                                <div class="table-responsive d-none d-md-block">
                                    <table class="table table-sm table-hover">
                                        <thead>
                                            <tr>
                                                <th>Job #</th>
                                                <th>Customer</th>
                                                <th>Activity</th>
                                                <th>Address</th>
                                                <th>Status</th>
                                                <th class="text-end">Pay</th>
                                                <th class="text-end">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${data.jobs.map(job => {
                                                const status = job.status || 'pending';
                                                const statusBadge = getStatusBadge(status);
                                                const mappedCustomer = window.customerMapping ? 
                                                    window.customerMapping.getMappedCustomer(job.customer) : 
                                                    job.customer;
                                                
                                                return `
                                                <tr id="job-row-${job.id}" data-status="${status}" title="Original: ${job.customer}">
                                                    <td><strong>${job.job_number}</strong></td>
                                                    <td>${mappedCustomer || 'N/A'}</td>
                                                    <td><span class="badge bg-info">${job.activity || 'N/A'}</span></td>
                                                    <td><small>${job.job_address || 'N/A'}, ${job.postcode || ''}</small></td>
                                                    <td>
                                                        <span class="status-badge ${status === 'extra' ? 'cursor-pointer' : ''}" id="status-${job.id}" ${status === 'extra' ? `onclick="editExtraJob(${job.id}, '${date}')" title="Click to edit"` : ''}>${statusBadge}</span>
                                                        ${job.price_agreed && job.price_agreed > 0 ? `<div class="mt-1"><span class="badge bg-warning text-dark"><i class="bi bi-currency-pound"></i> £${job.price_agreed.toFixed(2)}</span></div>` : ''}
                                                    </td>
                                                    <td class="text-end">
                                                        ${job.pay_amount ? `<strong class="${job.price_agreed && job.pay_amount < job.price_agreed ? 'text-danger' : 'text-success'}">${CurrencyFormatter.format(job.pay_amount)}${job.price_agreed && job.pay_amount < job.price_agreed ? ' <i class="bi bi-exclamation-triangle-fill"></i>' : ''}</strong>` : '<span class="text-muted">No pay data</span>'}
                                                    </td>
                                                    <td class="text-end">
                                                        <div class="btn-group btn-group-sm" role="group">
                                                            <button class="btn btn-outline-success" onclick="updateJobStatus(${job.id}, 'completed')" title="Completed">
                                                                <i class="bi bi-check-circle"></i>
                                                            </button>
                                                            <button class="btn btn-outline-danger" onclick="updateJobStatus(${job.id}, 'missed')" title="Missed">
                                                                <i class="bi bi-x-circle"></i>
                                                            </button>
                                                            <button class="btn btn-outline-warning" onclick="updateJobStatus(${job.id}, 'DNCO')" title="DNCO">
                                                                <i class="bi bi-exclamation-circle"></i>
                                                            </button>
                                                            <button class="btn btn-outline-info" onclick="updateJobStatus(${job.id}, 'extra')" title="Extra">
                                                                <i class="bi bi-plus-circle"></i>
                                                            </button>
                                                            <button class="btn btn-outline-secondary" onclick="deleteJob(${job.id}, '${date}')" title="Delete Job">
                                                                <i class="bi bi-trash"></i>
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            `}).join('')}
                                        </tbody>
                                    </table>
                                </div>
                                
                                <!-- Mobile Card View -->
                                <div class="d-md-none">
                                    ${data.jobs.map(job => {
                                        const status = job.status || 'pending';
                                        const statusBadge = getStatusBadge(status);
                                        return `
                                        <div class="card mb-3 job-card shadow-sm" id="job-row-${job.id}" data-status="${status}" data-job-id="${job.id}" style="border-radius: 12px;">
                                            <div class="card-body p-3">
                                                <div class="d-flex justify-content-between align-items-start mb-3">
                                                    <div class="flex-grow-1">
                                                        <h6 class="mb-1 fw-bold" style="font-size: 1.1rem;">#${job.job_number}</h6>
                                                        <p class="mb-1 text-muted" style="font-size: 0.9rem; line-height: 1.3;" title="Original: ${job.customer}">
                                                            ${window.customerMapping ? window.customerMapping.getMappedCustomer(job.customer) : job.customer || 'N/A'}
                                                        </p>
                                                    </div>
                                                    <div class="status-badge-container ms-2 ${status === 'extra' ? 'cursor-pointer' : ''}" id="status-${job.id}" ${status === 'extra' ? `onclick="editExtraJob(${job.id}, '${date}')" title="Tap to edit"` : ''}>${statusBadge}</div>
                                                </div>
                                                <div class="mb-3 d-flex justify-content-between align-items-center">
                                                    <div>
                                                        <span class="badge bg-info px-3 py-2" style="font-size: 0.8rem;">${job.activity || 'N/A'}</span>
                                                        ${job.price_agreed && job.price_agreed > 0 ? `
                                                            <span class="badge bg-warning text-dark px-2 py-1 ms-2" style="font-size: 0.75rem;">
                                                                Agreed: £${job.price_agreed.toFixed(2)}
                                                            </span>
                                                        ` : ''}
                                                    </div>
                                                    ${job.pay_amount ? `<strong class="text-success">£${job.pay_amount.toFixed(2)}</strong>` : '<span class="text-muted small">No pay data</span>'}
                                                </div>
                                                <p class="mb-3 small text-muted" style="font-size: 0.85rem; line-height: 1.4;">${job.job_address || 'N/A'}${job.postcode ? ', ' + job.postcode : ''}</p>
                                                <div class="d-grid gap-3">
                                                    <button class="btn btn-success py-3" onclick="updateJobStatus(${job.id}, 'completed')" style="font-size: 1rem; font-weight: 500;">
                                                        <i class="bi bi-check-circle me-2"></i>Completed
                                                    </button>
                                                    <div class="row g-2">
                                                        <div class="col-6">
                                                            <button class="btn btn-danger w-100 py-2" onclick="updateJobStatus(${job.id}, 'missed')" style="font-size: 0.9rem;">
                                                                <i class="bi bi-x-circle me-1"></i>Missed
                                                            </button>
                                                        </div>
                                                        <div class="col-6">
                                                            <button class="btn btn-warning w-100 py-2" onclick="updateJobStatus(${job.id}, 'DNCO')" style="font-size: 0.9rem;">
                                                                <i class="bi bi-exclamation-circle me-1"></i>DNCO
                                                            </button>
                                                        </div>
                                                    </div>
                                                    <div class="row g-2">
                                                        <div class="col-6">
                                                            <button class="btn btn-info w-100 py-2" onclick="updateJobStatus(${job.id}, 'extra')" style="font-size: 0.9rem;">
                                                                <i class="bi bi-plus-circle me-1"></i>Extra
                                                            </button>
                                                        </div>
                                                        <div class="col-6">
                                                            <button class="btn btn-secondary w-100 py-2" onclick="deleteJob(${job.id}, '${date}')" style="font-size: 0.9rem;">
                                                                <i class="bi bi-trash me-1"></i>Delete
                                                            </button>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        `}).join('')}
                                </div>
                                
                                <!-- Add Job Form (hidden by default) -->
                                <div id="addJobForm-${date}" class="alert alert-success border-success mb-3 mt-3 shadow-sm" style="display: none; border-left: 4px solid #198754; border-radius: 12px;">
                                    <div class="d-flex justify-content-between align-items-center mb-3">
                                        <h6 class="mb-0 fw-bold">
                                            <i class="bi bi-plus-circle-fill text-success me-2"></i>Add Extra Job
                                        </h6>
                                        <button type="button" class="btn-close" onclick="hideAddJobForm('${date}')"></button>
                                    </div>
                                    <div class="row g-3 mt-1">
                                        <div class="col-md-3 col-12">
                                            <label class="form-label mb-2 fw-semibold" style="font-size: 0.9rem;">Job Number *</label>
                                            <input type="text" class="form-control py-3" id="newJobNumber-${date}" placeholder="e.g. 12345" required style="font-size: 1rem;">
                                        </div>
                                        <div class="col-md-3 col-12">
                                            <label class="form-label mb-2 fw-semibold" style="font-size: 0.9rem;">Customer *</label>
                                            <select class="form-select py-3" id="newCustomer-${date}" required style="font-size: 1rem;">
                                                <option value="">Select customer...</option>
                                            </select>
                                        </div>
                                        <div class="col-md-2 col-12">
                                            <label class="form-label mb-2 fw-semibold" style="font-size: 0.9rem;">Activity</label>
                                            <select class="form-select py-3" id="newActivity-${date}" style="font-size: 1rem;">
                                                <option value="">Select activity...</option>
                                            </select>
                                        </div>
                                        <div class="col-md-2 col-12">
                                            <label class="form-label mb-2 fw-semibold" style="font-size: 0.9rem;">Address</label>
                                            <input type="text" class="form-control py-3" id="newAddress-${date}" placeholder="Job address" style="font-size: 1rem;">
                                        </div>
                                        <div class="col-md-2 col-12">
                                            <label class="form-label mb-2 fw-semibold" style="font-size: 0.9rem;">Postcode</label>
                                            <input type="text" class="form-control py-3" id="newPostcode-${date}" placeholder="e.g. M1 1AA" style="font-size: 1rem; text-transform: uppercase;">
                                        </div>
                                    </div>
                                    <div class="row g-3 mt-1">
                                        <div class="col-md-3 col-12">
                                            <label class="form-label mb-2 fw-semibold" style="font-size: 0.9rem;">
                                                <i class="bi bi-currency-pound me-1"></i>Agreed Price
                                            </label>
                                            <input type="number" class="form-control py-3" id="newAgreedPrice-${date}" placeholder="0.00" step="0.01" min="0" style="font-size: 1rem;">
                                        </div>
                                    </div>
                                    <div class="mt-4 d-grid gap-2 d-md-flex">
                                        <button class="btn btn-success py-3 px-4" onclick="addExtraJob('${date}')" style="font-size: 1rem; font-weight: 500;">
                                            <i class="bi bi-check-circle me-2"></i>Add Job
                                        </button>
                                        <button class="btn btn-outline-secondary py-3 px-4" onclick="hideAddJobForm('${date}')" style="font-size: 1rem;">
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                                
                                <!-- Mileage and Fuel Cost -->
                                <div class="row mt-4 g-3">
                                    <div class="col-md-6 col-12">
                                        <label for="mileage-${date}" class="form-label fw-semibold mb-2" style="font-size: 1rem;">
                                            <i class="bi bi-speedometer2 me-2"></i>Mileage (miles)
                                        </label>
                                        <input type="number" class="form-control py-3" id="mileage-${date}" 
                                               placeholder="Enter total mileage" step="0.1" min="0" style="font-size: 1rem;">
                                    </div>
                                    <div class="col-md-6 col-12">
                                        <label for="fuelCost-${date}" class="form-label fw-semibold mb-2" style="font-size: 1rem;">
                                            <i class="bi bi-fuel-pump me-2"></i>Fuel Cost (£)
                                        </label>
                                        <input type="number" class="form-control py-3" id="fuelCost-${date}" 
                                               placeholder="Enter fuel cost" step="0.01" min="0" style="font-size: 1rem;">
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-success" onclick="showAddJobForm('${date}')">
                                    <i class="bi bi-plus-circle"></i> Add Extra Job
                                </button>
                                <div class="ms-auto">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                                    <button type="button" class="btn btn-primary ms-2" onclick="saveAllJobStatuses('${date}')">
                                        <i class="bi bi-save"></i> Save All Changes
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Remove existing modal if any
            const existingModal = document.getElementById('runsheetJobsModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Add modal to body
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('runsheetJobsModal'));
            modal.show();
            
            // Update counts
            updateStatusCounts();
            
            // Load existing mileage and fuel cost
            loadDailyData(date);
            
            // Add formatting to fuel cost field when user finishes entering value
            const fuelCostInput = document.getElementById(`fuelCost-${date}`);
            if (fuelCostInput) {
                fuelCostInput.addEventListener('blur', function() {
                    const value = this.value.trim();
                    if (value !== '' && !isNaN(value)) {
                        this.value = parseFloat(value).toFixed(2);
                    }
                });
            }
            
            // Clean up modal after it's hidden
            document.getElementById('runsheetJobsModal').addEventListener('hidden.bs.modal', function () {
                this.remove();
            });
        }
        
    } catch (error) {
        console.error('Error loading run sheet jobs:', error);
        alert('Error loading jobs for this date');
    }
}

// Get status badge HTML
function getStatusBadge(status) {
    const badges = {
        'completed': '<span class="badge bg-success">Completed</span>',
        'missed': '<span class="badge bg-danger">Missed</span>',
        'dnco': '<span class="badge bg-warning">DNCO</span>',
        'DNCO': '<span class="badge bg-warning">DNCO</span>',
        'extra': '<span class="badge bg-info">Extra</span>',
        'pending': '<span class="badge bg-secondary">Pending</span>'
    };
    return badges[status] || badges['pending'];
}

// Update job status
async function updateJobStatus(jobId, status) {
    console.log('=== updateJobStatus called ===');
    console.log('Job ID:', jobId);
    console.log('New Status:', status);
    
    // Find ALL elements with this job ID (both desktop table row and mobile card)
    const allRows = document.querySelectorAll(`[id="job-row-${jobId}"]`);
    const allStatusBadges = document.querySelectorAll(`[id="status-${jobId}"]`);
    
    console.log('Found rows:', allRows.length);
    console.log('Found badges:', allStatusBadges.length);
    
    if (allRows.length > 0 && allStatusBadges.length > 0) {
        const newBadgeHTML = getStatusBadge(status);
        console.log('New badge HTML:', newBadgeHTML);
        
        // Update ALL instances (desktop and mobile)
        allRows.forEach(row => {
            row.dataset.status = status;
            console.log('Updated row:', row);
        });
        
        allStatusBadges.forEach(badge => {
            console.log('Current badge HTML:', badge.innerHTML);
            badge.innerHTML = newBadgeHTML;
            console.log('Updated badge HTML:', badge.innerHTML);
        });
        
        updateStatusCounts();
        console.log('✓ Status updated in UI');
        
        // Save to database immediately
        try {
            const response = await fetch('/api/runsheets/update-job-status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    job_id: jobId,
                    status: status
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log('✓ Status saved to database');
            } else {
                console.error('Error saving status:', result.error);
                alert('Error saving status: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error saving status:', error);
            alert('Error saving status');
        }
    } else {
        console.error('❌ Could not find row or badge for job', jobId);
        alert('Could not find job element. Job ID: ' + jobId);
    }
}

// Update status counts
function updateStatusCounts() {
    const rows = document.querySelectorAll('[id^="job-row-"]');
    let counts = { completed: 0, missed: 0, dnco: 0, extra: 0 };
    
    // Track unique job IDs to avoid double counting (desktop + mobile views)
    const seenJobIds = new Set();
    
    rows.forEach(row => {
        // Extract job ID from the row ID (format: "job-row-12345")
        const jobId = row.id.replace('job-row-', '');
        
        // Only count each job once
        if (!seenJobIds.has(jobId)) {
            seenJobIds.add(jobId);
            const status = row.dataset.status;
            // Normalize DNCO to lowercase for counting
            const normalizedStatus = status === 'DNCO' ? 'dnco' : status;
            if (counts.hasOwnProperty(normalizedStatus)) {
                counts[normalizedStatus]++;
            }
        }
    });
    
    document.getElementById('completedCount').textContent = `${counts.completed} Completed`;
    document.getElementById('missedCount').textContent = `${counts.missed} Missed`;
    document.getElementById('dncoCount').textContent = `${counts.dnco} DNCO`;
    document.getElementById('extraCount').textContent = `${counts.extra} Extra`;
}

// Show add job form
async function showAddJobForm(date) {
    document.getElementById(`addJobForm-${date}`).style.display = 'block';
    
    // Load autocomplete data
    try {
        console.log('Loading autocomplete data...');
        const response = await fetch('/api/runsheets/autocomplete-data');
        const data = await response.json();
        
        console.log('Autocomplete data received:', data);
        
        if (data.customers && data.activities) {
            // Populate customers select with mapped names
            const customersSelect = document.getElementById(`newCustomer-${date}`);
            console.log('Found customers select:', customersSelect);
            
            if (customersSelect) {
                // Wait for mappings to load
                await window.customerMapping.loadMappings();
                
                // Priority customers to show at the top
                const priorityCustomers = ['PayPoint', 'Lexmark', 'Fujitsu', 'Star Trains'];
                
                // Sort customers: priority ones first, then alphabetically
                const sortedCustomers = data.customers.sort((a, b) => {
                    const aPriority = priorityCustomers.findIndex(p => a.toLowerCase().includes(p.toLowerCase()));
                    const bPriority = priorityCustomers.findIndex(p => b.toLowerCase().includes(p.toLowerCase()));
                    
                    // If both are priority, sort by priority order
                    if (aPriority !== -1 && bPriority !== -1) {
                        return aPriority - bPriority;
                    }
                    // If only a is priority, it comes first
                    if (aPriority !== -1) return -1;
                    // If only b is priority, it comes first
                    if (bPriority !== -1) return 1;
                    // Otherwise alphabetical
                    return a.localeCompare(b);
                });
                
                // Create options with mapped names but original values
                const customerOptions = sortedCustomers.map(customer => {
                    const mappedName = window.customerMapping.getMappedCustomer(customer);
                    const displayName = mappedName !== customer ? `${mappedName} (${customer})` : customer;
                    return `<option value="${customer}" title="Original: ${customer}">${displayName}</option>`;
                }).join('');
                
                customersSelect.innerHTML = '<option value="">Select customer...</option>' + customerOptions;
                console.log('Populated customers:', data.customers.length, 'options with mappings');
            }
            
            // Populate activities select
            const activitiesSelect = document.getElementById(`newActivity-${date}`);
            console.log('Found activities select:', activitiesSelect);
            
            if (activitiesSelect) {
                // Sort activities: Tech Exchange first, then alphabetically
                const sortedActivities = data.activities.sort((a, b) => {
                    const aIsTechExchange = a.toLowerCase().includes('tech exchange');
                    const bIsTechExchange = b.toLowerCase().includes('tech exchange');
                    
                    if (aIsTechExchange && !bIsTechExchange) return -1;
                    if (!aIsTechExchange && bIsTechExchange) return 1;
                    return a.localeCompare(b);
                });
                
                activitiesSelect.innerHTML = '<option value="">Select activity...</option>' + 
                    sortedActivities.map(activity => 
                        `<option value="${activity}">${activity}</option>`
                    ).join('');
                console.log('Populated activities:', data.activities.length, 'options');
            }
        }
    } catch (error) {
        console.error('Error loading autocomplete data:', error);
    }
}

// Hide add job form
function hideAddJobForm(date) {
    const form = document.getElementById(`addJobForm-${date}`);
    form.style.display = 'none';
    
    // Clear editing flag
    delete form.dataset.editingJobId;
    
    // Reset form title
    const formTitle = form.querySelector('h6');
    if (formTitle) {
        formTitle.innerHTML = '<i class="bi bi-plus-circle-fill text-success me-2"></i>Add Extra Job';
    }
    
    // Clear form fields
    document.getElementById(`newJobNumber-${date}`).value = '';
    document.getElementById(`newCustomer-${date}`).value = '';
    document.getElementById(`newActivity-${date}`).value = '';
    document.getElementById(`newAddress-${date}`).value = '';
    document.getElementById(`newPostcode-${date}`).value = '';
    document.getElementById(`newAgreedPrice-${date}`).value = '';
}

// Add or edit extra job
async function addExtraJob(date) {
    const jobNumber = document.getElementById(`newJobNumber-${date}`).value.trim();
    const customer = document.getElementById(`newCustomer-${date}`).value.trim();
    const activity = document.getElementById(`newActivity-${date}`).value.trim();
    const address = document.getElementById(`newAddress-${date}`).value.trim();
    const postcode = document.getElementById(`newPostcode-${date}`).value.trim();
    const agreedPrice = document.getElementById(`newAgreedPrice-${date}`).value.trim();
    
    if (!jobNumber || !customer) {
        alert('Job Number and Customer are required');
        return;
    }
    
    // Check if we're editing an existing job
    const form = document.getElementById(`addJobForm-${date}`);
    const editingJobId = form.dataset.editingJobId;
    
    try {
        let response;
        
        if (editingJobId) {
            // Update existing job
            response = await fetch(`/api/runsheets/edit-job/${editingJobId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    job_number: jobNumber,
                    customer: customer,
                    activity: activity,
                    job_address: address,
                    postcode: postcode,
                    agreed_price: agreedPrice ? parseFloat(agreedPrice) : null
                })
            });
        } else {
            // Add new job
            response = await fetch('/api/runsheets/add-job', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    date: date,
                    job_number: jobNumber,
                    customer: customer,
                    activity: activity,
                    job_address: address,
                    postcode: postcode,
                    status: 'extra',
                    agreed_price: agreedPrice ? parseFloat(agreedPrice) : null,
                    send_email_confirmation: agreedPrice ? true : false
                })
            });
        }
        
        const result = await response.json();
        
        if (result.success) {
            alert(editingJobId ? 'Extra job updated successfully!' : 'Extra job added successfully!');
            // Clear the editing flag
            delete form.dataset.editingJobId;
            // Close and reopen modal to refresh
            bootstrap.Modal.getInstance(document.getElementById('runsheetJobsModal')).hide();
            // Reload the run sheet
            setTimeout(() => viewRunSheetJobs(date), 300);
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error saving job');
    }
}

// Edit extra job - opens add form with data pre-filled
function editExtraJob(jobId, date) {
    // Find the job in the current data
    const jobs = window.currentRunsheetJobs || [];
    const job = jobs.find(j => j.id === jobId);
    
    if (!job) {
        alert('Job data not found');
        return;
    }
    
    // Only allow editing extra jobs
    if (job.status !== 'extra') {
        alert('Only extra jobs can be edited this way');
        return;
    }
    
    // Show the add job form
    showAddJobForm(date);
    
    // Pre-fill the form with existing data
    setTimeout(() => {
        document.getElementById(`newJobNumber-${date}`).value = job.job_number || '';
        
        // Set customer (either select from dropdown or add as custom)
        const customerSelect = document.getElementById(`newCustomer-${date}`);
        if (customerSelect) {
            // Try to find matching option
            let found = false;
            for (let option of customerSelect.options) {
                if (option.value === job.customer) {
                    customerSelect.value = job.customer;
                    found = true;
                    break;
                }
            }
            // If not found, add it as an option and select it
            if (!found && job.customer) {
                const newOption = new Option(job.customer, job.customer, true, true);
                customerSelect.add(newOption);
            }
        }
        
        // Set activity
        const activitySelect = document.getElementById(`newActivity-${date}`);
        if (activitySelect) {
            let found = false;
            for (let option of activitySelect.options) {
                if (option.value === job.activity) {
                    activitySelect.value = job.activity;
                    found = true;
                    break;
                }
            }
            if (!found && job.activity) {
                const newOption = new Option(job.activity, job.activity, true, true);
                activitySelect.add(newOption);
            }
        }
        
        document.getElementById(`newAddress-${date}`).value = job.job_address || '';
        document.getElementById(`newPostcode-${date}`).value = job.postcode || '';
        document.getElementById(`newAgreedPrice-${date}`).value = job.price_agreed || '';
        
        // Store the job ID so we know we're editing
        document.getElementById(`addJobForm-${date}`).dataset.editingJobId = jobId;
        
        // Change the form title
        const formTitle = document.querySelector(`#addJobForm-${date} h6`);
        if (formTitle) {
            formTitle.innerHTML = '<i class="bi bi-pencil-fill text-success me-2"></i>Edit Extra Job';
        }
    }, 100);
}

// Load existing mileage and fuel cost data
async function loadDailyData(date) {
    try {
        const response = await fetch(`/api/runsheets/daily-data?date=${encodeURIComponent(date)}`);
        const data = await response.json();
        
        if (data.mileage !== null && data.mileage !== undefined) {
            document.getElementById(`mileage-${date}`).value = data.mileage;
        }
        if (data.fuel_cost !== null && data.fuel_cost !== undefined) {
            // Format cost to 2 decimal places (0 becomes 0.00, 5.5 becomes 5.50)
            document.getElementById(`fuelCost-${date}`).value = parseFloat(data.fuel_cost).toFixed(2);
        }
    } catch (error) {
        console.error('Error loading daily data:', error);
    }
}

// Save all job statuses
async function saveAllJobStatuses(date) {
    const rows = document.querySelectorAll('[id^="job-row-"]');
    const updates = [];
    const seenJobIds = new Set();
    
    rows.forEach(row => {
        const jobId = row.id.replace('job-row-', '');
        const status = row.dataset.status;
        
        // Only add each job once (avoid counting desktop + mobile views)
        if (status !== 'pending' && !seenJobIds.has(jobId)) {
            seenJobIds.add(jobId);
            updates.push({ job_id: jobId, status: status });
        }
    });
    
    // Get mileage and fuel cost
    const mileageValue = document.getElementById(`mileage-${date}`).value.trim();
    const fuelCostValue = document.getElementById(`fuelCost-${date}`).value.trim();
    
    const mileage = mileageValue === '' ? null : parseFloat(mileageValue);
    const fuelCost = fuelCostValue === '' ? null : parseFloat(fuelCostValue);
    
    if (updates.length === 0 && mileage === null && fuelCost === null) {
        alert('No changes to save');
        return;
    }
    
    try {
        const response = await fetch('/api/runsheets/update-statuses', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                date: date,
                updates: updates,
                mileage: mileage,
                fuel_cost: fuelCost
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            let message = '';
            if (updates.length > 0) {
                message += `Updated ${updates.length} job statuses. `;
            }
            if (mileage !== null || fuelCost !== null) {
                message += 'Saved mileage and fuel cost.';
            }
            alert(message || 'Changes saved successfully!');
            // Refresh the run sheets list to update status badges
            loadRunSheetsList(currentRSPage);
            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('runsheetJobsModal')).hide();
        } else {
            alert('Error saving changes: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error saving changes:', error);
        alert('Error saving changes');
    }
}

// Delete a job
async function deleteJob(jobId, date) {
    if (!confirm('⚠️ Are you sure you want to delete this job?\n\nThis will permanently remove it from the database.\n\nNote: If this job is in a runsheet PDF, it may reappear if you re-import that PDF.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/runsheets/delete-job/${jobId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Remove the job row from both desktop and mobile views
            const jobRows = document.querySelectorAll(`[id="job-row-${jobId}"]`);
            jobRows.forEach(row => row.remove());
            
            // Update status counts
            updateStatusCounts();
            
            // Refresh the run sheets list to update job counts and status
            loadRunSheetsList(currentRSPage);
            
            alert('Job deleted successfully');
        } else {
            alert('Error deleting job: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error deleting job:', error);
        alert('Error deleting job');
    }
}
