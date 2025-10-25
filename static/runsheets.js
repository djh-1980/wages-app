// Run Sheets Tab JavaScript

let activityChart = null;
let currentRSPage = 1;
let currentRSSortColumn = 'date';
let currentRSSortOrder = 'desc';

// Load Run Sheets data when tab is shown
document.getElementById('runsheets-tab').addEventListener('shown.bs.tab', function () {
    loadRunSheetsSummary();
    loadRunSheetsList(1);
});

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
    
    try {
        const response = await fetch(`/api/runsheets/list?page=${page}&per_page=20&sort=${currentRSSortColumn}&order=${currentRSSortOrder}`);
        const data = await response.json();
        
        const tbody = document.getElementById('runsheetsList');
        
        if (data.runsheets && data.runsheets.length > 0) {
            tbody.innerHTML = data.runsheets.map(rs => {
                const activities = rs.activities ? rs.activities.split(',').slice(0, 3).join(', ') : 'N/A';
                return `
                    <tr>
                        <td><strong>${rs.date}</strong></td>
                        <td class="text-center">
                            <span class="badge bg-primary">${rs.job_count} jobs</span>
                        </td>
                        <td><small>${activities}</small></td>
                        <td class="text-end">
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
                                <p class="mb-3"><strong>${data.jobs.length} jobs</strong> on this day</p>
                                <div class="table-responsive">
                                    <table class="table table-sm table-hover">
                                        <thead>
                                            <tr>
                                                <th>Job #</th>
                                                <th>Customer</th>
                                                <th>Activity</th>
                                                <th>Priority</th>
                                                <th>Address</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${data.jobs.map(job => `
                                                <tr>
                                                    <td><strong>${job.job_number}</strong></td>
                                                    <td>${job.customer || 'N/A'}</td>
                                                    <td><span class="badge bg-info">${job.activity || 'N/A'}</span></td>
                                                    <td><span class="badge bg-warning">${job.priority || 'N/A'}</span></td>
                                                    <td><small>${job.job_address || 'N/A'}, ${job.postcode || ''}</small></td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
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
