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
        
        // Update top customers table
        const tableBody = document.getElementById('rsTopCustomersTable');
        if (data.top_customers && data.top_customers.length > 0) {
            const totalJobs = data.overall.total_jobs;
            tableBody.innerHTML = data.top_customers.map(customer => `
                <tr>
                    <td>${customer.customer}</td>
                    <td class="text-end">${customer.job_count}</td>
                    <td class="text-end">${((customer.job_count / totalJobs) * 100).toFixed(1)}%</td>
                </tr>
            `).join('');
        } else {
            tableBody.innerHTML = '<tr><td colspan="3" class="text-center">No data available</td></tr>';
        }
        
        // Create activity chart
        if (data.activities && data.activities.length > 0) {
            createActivityChart(data.activities);
        }
        
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
        
        if (data.runsheets && data.runsheets.length > 0) {
            tbody.innerHTML = data.runsheets.map(rs => {
                const activities = rs.activities ? rs.activities.split(',').slice(0, 3).join(', ') : 'N/A';
                
                // Get completion status for this date
                const status = statusData[rs.date];
                let statusBadge = '';
                
                if (status) {
                    switch (status.status) {
                        case 'completed':
                            statusBadge = '<span class="badge bg-success me-2" title="All jobs completed with mileage"><i class="bi bi-check-circle"></i> Complete</span>';
                            break;
                        case 'in_progress':
                            statusBadge = '<span class="badge bg-warning me-2" title="Some jobs completed or in progress"><i class="bi bi-clock"></i> In Progress</span>';
                            break;
                        case 'not_started':
                            statusBadge = '<span class="badge bg-danger me-2" title="No jobs completed yet"><i class="bi bi-circle"></i> Not Started</span>';
                            break;
                    }
                }
                
                return `
                    <tr>
                        <td><strong>${rs.date}</strong></td>
                        <td class="text-center">
                            <span class="badge bg-primary">${rs.job_count} jobs</span>
                        </td>
                        <td><small>${activities}</small></td>
                        <td class="text-end">
                            ${statusBadge}
                            <button class="btn btn-sm btn-outline-primary" onclick="viewRunSheetJobs('${rs.date}')">
                                <i class="bi bi-eye"></i> View
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
            
            // Update pagination
            updateRSPagination(data.page, data.total_pages);
        } else {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center">No run sheets found</td></tr>';
        }
        
    } catch (error) {
        console.error('Error loading run sheets list:', error);
        document.getElementById('runsheetsList').innerHTML = 
            '<tr><td colspan="4" class="text-center text-danger">Error loading data</td></tr>';
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
        
        if (data.jobs && data.jobs.length > 0) {
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
                                    <p class="mb-2"><strong>${data.jobs.length} jobs</strong> on this day</p>
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
                                                <th class="text-end">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${data.jobs.map(job => {
                                                const status = job.status || 'pending';
                                                const statusBadge = getStatusBadge(status);
                                                return `
                                                <tr id="job-row-${job.id}" data-status="${status}">
                                                    <td><strong>${job.job_number}</strong></td>
                                                    <td>${job.customer || 'N/A'}</td>
                                                    <td><span class="badge bg-info">${job.activity || 'N/A'}</span></td>
                                                    <td><small>${job.job_address || 'N/A'}, ${job.postcode || ''}</small></td>
                                                    <td><span class="status-badge" id="status-${job.id}">${statusBadge}</span></td>
                                                    <td class="text-end">
                                                        <div class="btn-group btn-group-sm" role="group">
                                                            <button class="btn btn-outline-success" onclick="updateJobStatus(${job.id}, 'completed')" title="Completed">
                                                                <i class="bi bi-check-circle"></i>
                                                            </button>
                                                            <button class="btn btn-outline-danger" onclick="updateJobStatus(${job.id}, 'missed')" title="Missed">
                                                                <i class="bi bi-x-circle"></i>
                                                            </button>
                                                            <button class="btn btn-outline-warning" onclick="updateJobStatus(${job.id}, 'dnco')" title="DNCO">
                                                                <i class="bi bi-exclamation-circle"></i>
                                                            </button>
                                                            <button class="btn btn-outline-info" onclick="updateJobStatus(${job.id}, 'extra')" title="Extra">
                                                                <i class="bi bi-plus-circle"></i>
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
                                        <div class="card mb-3 job-card" id="job-row-${job.id}" data-status="${status}" data-job-id="${job.id}">
                                            <div class="card-body">
                                                <div class="d-flex justify-content-between align-items-start mb-2">
                                                    <div>
                                                        <h6 class="mb-1"><strong>#${job.job_number}</strong></h6>
                                                        <p class="mb-1 text-muted">${job.customer || 'N/A'}</p>
                                                    </div>
                                                    <div class="status-badge-container" id="status-${job.id}">${statusBadge}</div>
                                                </div>
                                                <div class="mb-2">
                                                    <span class="badge bg-info">${job.activity || 'N/A'}</span>
                                                </div>
                                                <p class="mb-3 small text-muted">${job.job_address || 'N/A'}${job.postcode ? ', ' + job.postcode : ''}</p>
                                                <div class="d-grid gap-2">
                                                    <button class="btn btn-success" onclick="updateJobStatus(${job.id}, 'completed')">
                                                        <i class="bi bi-check-circle"></i> Completed
                                                    </button>
                                                    <div class="row g-2">
                                                        <div class="col-4">
                                                            <button class="btn btn-danger w-100" onclick="updateJobStatus(${job.id}, 'missed')">
                                                                <i class="bi bi-x-circle"></i> Missed
                                                            </button>
                                                        </div>
                                                        <div class="col-4">
                                                            <button class="btn btn-warning w-100" onclick="updateJobStatus(${job.id}, 'dnco')">
                                                                <i class="bi bi-exclamation-circle"></i> DNCO
                                                            </button>
                                                        </div>
                                                        <div class="col-4">
                                                            <button class="btn btn-info w-100" onclick="updateJobStatus(${job.id}, 'extra')">
                                                                <i class="bi bi-plus-circle"></i> Extra
                                                            </button>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        `}).join('')}
                                </div>
                                
                                <!-- Add Job Form (hidden by default) -->
                                <div id="addJobForm-${date}" class="alert alert-success border-success mb-3 mt-3" style="display: none; border-left: 4px solid #198754;">
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <h6 class="mb-0">
                                            <i class="bi bi-plus-circle-fill text-success"></i> Add Extra Job
                                        </h6>
                                        <button type="button" class="btn-close" onclick="hideAddJobForm('${date}')"></button>
                                    </div>
                                    <div class="row g-3 mt-1">
                                        <div class="col-md-3">
                                            <label class="form-label small mb-1">Job Number *</label>
                                            <input type="text" class="form-control" id="newJobNumber-${date}" placeholder="e.g. 12345" required>
                                        </div>
                                        <div class="col-md-3">
                                            <label class="form-label small mb-1">Customer *</label>
                                            <input type="text" class="form-control" id="newCustomer-${date}" placeholder="Customer name" required>
                                        </div>
                                        <div class="col-md-3">
                                            <label class="form-label small mb-1">Activity</label>
                                            <input type="text" class="form-control" id="newActivity-${date}" placeholder="e.g. REPAIR">
                                        </div>
                                        <div class="col-md-3">
                                            <label class="form-label small mb-1">Address</label>
                                            <input type="text" class="form-control" id="newAddress-${date}" placeholder="Job address">
                                        </div>
                                    </div>
                                    <div class="mt-3">
                                        <button class="btn btn-success" onclick="addExtraJob('${date}')">
                                            <i class="bi bi-check-circle"></i> Add Job
                                        </button>
                                        <button class="btn btn-outline-secondary ms-2" onclick="hideAddJobForm('${date}')">
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                                
                                <!-- Mileage and Fuel Cost -->
                                <div class="row mt-4">
                                    <div class="col-md-6">
                                        <label for="mileage-${date}" class="form-label">
                                            <i class="bi bi-speedometer2"></i> Mileage (miles)
                                        </label>
                                        <input type="number" class="form-control" id="mileage-${date}" 
                                               placeholder="Enter total mileage for this day" step="0.1" min="0">
                                    </div>
                                    <div class="col-md-6">
                                        <label for="fuelCost-${date}" class="form-label">
                                            <i class="bi bi-fuel-pump"></i> Fuel Cost (£)
                                        </label>
                                        <input type="number" class="form-control" id="fuelCost-${date}" 
                                               placeholder="Enter fuel cost" step="0.01" min="0">
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
            if (counts.hasOwnProperty(status)) {
                counts[status]++;
            }
        }
    });
    
    document.getElementById('completedCount').textContent = `${counts.completed} Completed`;
    document.getElementById('missedCount').textContent = `${counts.missed} Missed`;
    document.getElementById('dncoCount').textContent = `${counts.dnco} DNCO`;
    document.getElementById('extraCount').textContent = `${counts.extra} Extra`;
}

// Show add job form
function showAddJobForm(date) {
    document.getElementById(`addJobForm-${date}`).style.display = 'block';
}

// Hide add job form
function hideAddJobForm(date) {
    document.getElementById(`addJobForm-${date}`).style.display = 'none';
    // Clear form fields
    document.getElementById(`newJobNumber-${date}`).value = '';
    document.getElementById(`newCustomer-${date}`).value = '';
    document.getElementById(`newActivity-${date}`).value = '';
    document.getElementById(`newAddress-${date}`).value = '';
}

// Add extra job
async function addExtraJob(date) {
    const jobNumber = document.getElementById(`newJobNumber-${date}`).value.trim();
    const customer = document.getElementById(`newCustomer-${date}`).value.trim();
    const activity = document.getElementById(`newActivity-${date}`).value.trim();
    const address = document.getElementById(`newAddress-${date}`).value.trim();
    
    if (!jobNumber || !customer) {
        alert('Job Number and Customer are required');
        return;
    }
    
    try {
        const response = await fetch('/api/runsheets/add-job', {
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
                status: 'extra'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Extra job added successfully!');
            // Close and reopen modal to refresh
            bootstrap.Modal.getInstance(document.getElementById('runsheetJobsModal')).hide();
            // Reload the run sheet
            setTimeout(() => viewRunSheetJobs(date), 300);
        } else {
            alert('Error adding job: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error adding job:', error);
        alert('Error adding job');
    }
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
            document.getElementById(`fuelCost-${date}`).value = data.fuel_cost;
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
    const mileage = parseFloat(document.getElementById(`mileage-${date}`).value) || null;
    const fuelCost = parseFloat(document.getElementById(`fuelCost-${date}`).value) || null;
    
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
