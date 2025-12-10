// Runsheet Analytics Module - Overview, Customers, and Activities tabs
console.log('🟢 runsheet-analytics.js loaded successfully');

// Global chart variables
let rsDailyTrendChart = null;
let rsStatusChart = null;
let rsActivityChart = null;
let rsActivityEarningsChart = null;

// Global data storage
let analyticsData = null;
let customersData = [];
let activitiesData = [];
let currentYearFilter = '';
let availableYears = [];

// Customer sorting and pagination
let customerSortColumn = 'job_count';
let customerSortOrder = 'desc';
let customerCurrentPage = 1;
const customerPerPage = 20;

// Load analytics when tabs are shown
document.addEventListener('DOMContentLoaded', function() {
    const overviewTab = document.getElementById('overview-tab');
    const customersTab = document.getElementById('customers-tab');
    const activitiesTab = document.getElementById('activities-tab');
    
    if (overviewTab) {
        overviewTab.addEventListener('shown.bs.tab', () => {
            if (!analyticsData) loadRunsheetAnalytics();
        });
    }
    
    if (customersTab) {
        customersTab.addEventListener('shown.bs.tab', () => {
            if (!analyticsData) loadRunsheetAnalytics();
        });
    }
    
    if (activitiesTab) {
        activitiesTab.addEventListener('shown.bs.tab', () => {
            if (!analyticsData) loadRunsheetAnalytics();
        });
    }
    
    // Customer search
    const customerSearch = document.getElementById('customerSearch');
    if (customerSearch) {
        customerSearch.addEventListener('input', function() {
            customerCurrentPage = 1;
            renderCustomersTable();
        });
    }
});

// Main function to load all runsheet analytics
async function loadRunsheetAnalytics(year = '') {
    console.log('Loading runsheet analytics...', year ? `Year: ${year}` : 'All Years');
    
    try {
        const url = year ? `/api/runsheets/analytics?year=${year}` : '/api/runsheets/analytics';
        const response = await fetch(url);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load analytics');
        }
        
        console.log('Runsheet analytics loaded:', data);
        analyticsData = data;
        
        // Wait for customer mappings to load
        await window.customerMapping.loadMappings();
        
        // Apply customer mapping to aggregate customer data
        customersData = aggregateCustomerData(data.customer_breakdown);
        activitiesData = data.activity_breakdown;
        
        // Populate year filters if not already done
        if (availableYears.length === 0) {
            await populateYearFilters();
        }
        
        // Render all sections
        renderOverviewTab(data);
        renderCustomersTab(data);
        renderActivitiesTab(data);
        
    } catch (error) {
        console.error('Error loading runsheet analytics:', error);
    }
}

// Aggregate customer data using customer mapping
function aggregateCustomerData(customerBreakdown) {
    const aggregated = {};
    
    customerBreakdown.forEach(customer => {
        const mappedName = window.customerMapping.getMappedCustomer(customer.customer);
        
        if (!aggregated[mappedName]) {
            aggregated[mappedName] = {
                customer: mappedName,
                job_count: 0,
                total_earnings: 0,
                avg_pay: 0,
                days_worked: 0,
                completed_count: 0,
                extra_count: 0,
                dnco_count: 0,
                missed_count: 0,
                original_customers: []
            };
        }
        
        // Aggregate the data
        aggregated[mappedName].job_count += customer.job_count;
        aggregated[mappedName].total_earnings += customer.total_earnings;
        aggregated[mappedName].days_worked += customer.days_worked;
        aggregated[mappedName].completed_count += customer.completed_count;
        aggregated[mappedName].extra_count += customer.extra_count;
        aggregated[mappedName].dnco_count += customer.dnco_count;
        aggregated[mappedName].missed_count += customer.missed_count;
        aggregated[mappedName].original_customers.push(customer.customer);
    });
    
    // Calculate average pay for each aggregated customer
    Object.values(aggregated).forEach(customer => {
        customer.avg_pay = customer.job_count > 0 ? customer.total_earnings / customer.job_count : 0;
    });
    
    // Convert to array and sort by job count
    return Object.values(aggregated).sort((a, b) => b.job_count - a.job_count);
}

// Populate year filter dropdowns
async function populateYearFilters() {
    try {
        // Extract unique years from the loaded analytics data
        const years = new Set();
        
        // Get years from customer breakdown data
        if (analyticsData && analyticsData.customer_breakdown) {
            // We need to query the database for available years
            // For now, let's use a simple approach: hardcode recent years
            const currentYear = new Date().getFullYear();
            for (let year = currentYear; year >= 2021; year--) {
                years.add(year.toString());
            }
        }
        
        availableYears = Array.from(years).sort().reverse();
        
        // Populate all year filter dropdowns
        const filters = ['overviewYearFilter', 'customersYearFilter', 'activitiesYearFilter'];
        filters.forEach(filterId => {
            const select = document.getElementById(filterId);
            if (select) {
                select.innerHTML = '<option value="">All Years</option>';
                availableYears.forEach(year => {
                    select.innerHTML += `<option value="${year}">${year}</option>`;
                });
            }
        });
    } catch (error) {
        console.error('Error populating year filters:', error);
    }
}

// Filter functions for each tab
window.filterOverviewByYear = function() {
    const year = document.getElementById('overviewYearFilter').value;
    currentYearFilter = year;
    loadRunsheetAnalytics(year);
};

window.filterCustomersByYear = function() {
    const year = document.getElementById('customersYearFilter').value;
    currentYearFilter = year;
    loadRunsheetAnalytics(year);
};

window.filterActivitiesByYear = function() {
    const year = document.getElementById('activitiesYearFilter').value;
    currentYearFilter = year;
    loadRunsheetAnalytics(year);
};

// OVERVIEW TAB
function renderOverviewTab(data) {
    renderStatusBreakdownCards(data.status_breakdown);
    renderDailyTrendChart(data.daily_trend);
    renderStatusChart(data.status_breakdown);
    // Use mapped customer data instead of raw data
    renderTopCustomersTable(customersData.slice(0, 10));
}

function renderStatusBreakdownCards(statusBreakdown) {
    const statusConfig = {
        'completed': { label: 'Completed', icon: 'check-circle', color: 'success' },
        'extra': { label: 'Extra Jobs', icon: 'plus-circle', color: 'info' },
        'DNCO': { label: 'DNCO', icon: 'exclamation-triangle', color: 'warning' },
        'missed': { label: 'Missed', icon: 'x-circle', color: 'danger' },
        'pending': { label: 'Pending', icon: 'clock', color: 'secondary' }
    };
    
    let html = '';
    statusBreakdown.forEach(status => {
        const config = statusConfig[status.status] || { label: status.status, icon: 'circle', color: 'secondary' };
        
        // For DNCO, show estimated loss instead of total_pay
        let payDisplay = formatCurrency(status.total_pay);
        if (status.status === 'DNCO' && status.estimated_loss) {
            payDisplay = `Est. Loss: ${formatCurrency(status.estimated_loss)}`;
        }
        
        html += `
            <div class="col-md-3">
                <div class="card stat-card border-${config.color}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <p class="text-muted mb-1 small">${config.label}</p>
                                <h3 class="mb-0">${status.count}</h3>
                                <small class="text-${config.color}">
                                    <i class="bi bi-${config.icon}"></i> ${payDisplay}
                                </small>
                            </div>
                            <div class="stat-icon bg-${config.color} text-white">
                                <i class="bi bi-${config.icon}"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    document.getElementById('statusBreakdownCards').innerHTML = html;
}

function renderDailyTrendChart(dailyTrend) {
    const ctx = document.getElementById('dailyTrendChart').getContext('2d');
    
    if (rsDailyTrendChart) {
        rsDailyTrendChart.destroy();
    }
    
    const sortedData = dailyTrend.reverse(); // Oldest to newest
    
    rsDailyTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: sortedData.map(d => d.date),
            datasets: [{
                label: 'Total Jobs',
                data: sortedData.map(d => d.job_count),
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                yAxisID: 'y'
            }, {
                label: 'Daily Earnings',
                data: sortedData.map(d => d.daily_earnings),
                borderColor: '#43e97b',
                backgroundColor: 'rgba(67, 233, 123, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                yAxisID: 'y1'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: { display: true, position: 'top' },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            if (context.datasetIndex === 1) {
                                return `Earnings: ${formatCurrency(context.parsed.y)}`;
                            }
                            return `Jobs: ${context.parsed.y}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: 'Job Count' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: { display: true, text: 'Earnings (£)' },
                    grid: { drawOnChartArea: false },
                    ticks: {
                        callback: (value) => formatCurrency(value)
                    }
                }
            }
        }
    });
}

function renderStatusChart(statusBreakdown) {
    const ctx = document.getElementById('statusChart').getContext('2d');
    
    if (rsStatusChart) {
        rsStatusChart.destroy();
    }
    
    const colors = {
        'completed': '#10b981',
        'extra': '#3b82f6',
        'DNCO': '#f59e0b',
        'missed': '#ef4444',
        'pending': '#6b7280'
    };
    
    rsStatusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: statusBreakdown.map(s => s.status.charAt(0).toUpperCase() + s.status.slice(1)),
            datasets: [{
                data: statusBreakdown.map(s => s.count),
                backgroundColor: statusBreakdown.map(s => colors[s.status] || '#6b7280')
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
                            const status = statusBreakdown[context.dataIndex];
                            return [
                                `${status.status}: ${status.count} jobs`,
                                `Earnings: ${formatCurrency(status.total_pay)}`
                            ];
                        }
                    }
                }
            }
        }
    });
}

function renderTopCustomersTable(topCustomers) {
    let html = '';
    topCustomers.forEach(customer => {
        const hasMultipleSources = customer.original_customers && customer.original_customers.length > 1;
        const tooltip = hasMultipleSources ? 
            `title="Includes: ${customer.original_customers.join(', ')}"` : '';
        
        html += `
            <tr>
                <td ${tooltip}>
                    ${truncate(customer.customer, 40)}
                    ${hasMultipleSources ? `<small class="text-muted d-block">(${customer.original_customers.length} sources)</small>` : ''}
                </td>
                <td class="text-center"><span class="badge bg-primary">${customer.job_count}</span></td>
                <td class="text-end"><strong class="text-success">${formatCurrency(customer.total_earnings)}</strong></td>
                <td class="text-center"><span class="badge bg-success">${customer.completed_count}</span></td>
                <td class="text-center"><span class="badge bg-info">${customer.extra_count}</span></td>
            </tr>
        `;
    });
    
    document.getElementById('rsTopCustomersTable').innerHTML = html || '<tr><td colspan="5" class="text-center">No data available</td></tr>';
}

// CUSTOMERS TAB
function renderCustomersTab(data) {
    renderCustomersTable();
}

function renderCustomersTable() {
    const searchTerm = document.getElementById('customerSearch')?.value.toLowerCase() || '';
    
    // Filter customers
    let filtered = customersData.filter(c => 
        c.customer.toLowerCase().includes(searchTerm)
    );
    
    // Sort customers
    filtered.sort((a, b) => {
        let aVal = a[customerSortColumn];
        let bVal = b[customerSortColumn];
        
        if (typeof aVal === 'string') {
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }
        
        if (customerSortOrder === 'asc') {
            return aVal > bVal ? 1 : -1;
        } else {
            return aVal < bVal ? 1 : -1;
        }
    });
    
    // Paginate
    const start = (customerCurrentPage - 1) * customerPerPage;
    const end = start + customerPerPage;
    const paginated = filtered.slice(start, end);
    
    // Render table
    let html = '';
    paginated.forEach(customer => {
        const hasMultipleSources = customer.original_customers && customer.original_customers.length > 1;
        const tooltip = hasMultipleSources ? 
            `title="Includes: ${customer.original_customers.join(', ')}"` : '';
        
        html += `
            <tr>
                <td ${tooltip}>
                    ${truncate(customer.customer, 50)}
                    ${hasMultipleSources ? `<small class="text-muted d-block">(${customer.original_customers.length} sources)</small>` : ''}
                </td>
                <td class="text-center"><strong>${customer.job_count}</strong></td>
                <td class="text-end"><strong class="text-success">${formatCurrency(customer.total_earnings)}</strong></td>
                <td class="text-end">${formatCurrency(customer.avg_pay)}</td>
                <td class="text-center">${customer.days_worked}</td>
                <td class="text-center"><span class="badge bg-success">${customer.completed_count}</span></td>
                <td class="text-center"><span class="badge bg-info">${customer.extra_count}</span></td>
                <td class="text-center"><span class="badge bg-warning">${customer.dnco_count}</span></td>
                <td class="text-center"><span class="badge bg-danger">${customer.missed_count}</span></td>
            </tr>
        `;
    });
    
    document.getElementById('customersTableBody').innerHTML = html || '<tr><td colspan="9" class="text-center">No customers found</td></tr>';
    
    // Render pagination
    renderCustomerPagination(filtered.length);
}

function renderCustomerPagination(totalItems) {
    const totalPages = Math.ceil(totalItems / customerPerPage);
    let html = '';
    
    for (let i = 1; i <= totalPages; i++) {
        html += `
            <li class="page-item ${i === customerCurrentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="goToCustomerPage(${i}); return false;">${i}</a>
            </li>
        `;
    }
    
    document.getElementById('customerPagination').innerHTML = html;
}

window.goToCustomerPage = function(page) {
    customerCurrentPage = page;
    renderCustomersTable();
};

window.sortCustomers = function(column) {
    if (customerSortColumn === column) {
        customerSortOrder = customerSortOrder === 'asc' ? 'desc' : 'asc';
    } else {
        customerSortColumn = column;
        customerSortOrder = 'desc';
    }
    renderCustomersTable();
};

// ACTIVITIES TAB
function renderActivitiesTab(data) {
    renderActivityCharts(data.activity_breakdown);
    renderActivitiesTable(data.activity_breakdown);
}

function renderActivityCharts(activities) {
    // Activity Distribution Chart
    const ctx1 = document.getElementById('activityChart').getContext('2d');
    
    if (rsActivityChart) {
        rsActivityChart.destroy();
    }
    
    rsActivityChart = new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: activities.map(a => truncate(a.activity, 20)),
            datasets: [{
                label: 'Job Count',
                data: activities.map(a => a.job_count),
                backgroundColor: '#667eea'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: { display: false }
            }
        }
    });
    
    // Activity Earnings Chart
    const ctx2 = document.getElementById('activityEarningsChart').getContext('2d');
    
    if (rsActivityEarningsChart) {
        rsActivityEarningsChart.destroy();
    }
    
    rsActivityEarningsChart = new Chart(ctx2, {
        type: 'doughnut',
        data: {
            labels: activities.map(a => a.activity),
            datasets: [{
                data: activities.map(a => a.total_earnings),
                backgroundColor: [
                    '#667eea', '#764ba2', '#43e97b', '#fa709a',
                    '#fee140', '#30cfd0', '#a8edea', '#fed6e3'
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
                                `Jobs: ${activity.job_count}`
                            ];
                        }
                    }
                }
            }
        }
    });
}

function renderActivitiesTable(activities) {
    let html = '';
    activities.forEach(activity => {
        html += `
            <tr>
                <td><strong>${activity.activity || 'Unknown'}</strong></td>
                <td class="text-center"><span class="badge bg-primary">${activity.job_count}</span></td>
                <td class="text-end"><strong class="text-success">${formatCurrency(activity.total_earnings)}</strong></td>
                <td class="text-end">${formatCurrency(activity.avg_pay)}</td>
                <td class="text-center">${activity.unique_customers}</td>
                <td class="text-center"><span class="badge bg-success">${activity.completed_count}</span></td>
                <td class="text-center"><span class="badge bg-info">${activity.extra_count}</span></td>
            </tr>
        `;
    });
    
    document.getElementById('activitiesTableBody').innerHTML = html || '<tr><td colspan="7" class="text-center">No activities found</td></tr>';
}

// Helper function
function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}
