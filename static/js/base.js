// Global Search Function
async function performGlobalSearch() {
    const searchInput = document.getElementById('globalSearchInput');
    const resultsDiv = document.getElementById('globalSearchResults');
    const jobNumber = searchInput.value.trim();
    
    if (!jobNumber) {
        resultsDiv.innerHTML = '<div class="alert alert-warning">Please enter a job number</div>';
        return;
    }
    
    resultsDiv.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Searching...</p></div>';
    
    try {
        const response = await fetch(`/api/search/job/${encodeURIComponent(jobNumber)}`);
        const data = await response.json();
        
        if (!data.found) {
            resultsDiv.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle"></i> No results found for job number: <strong>${jobNumber}</strong>
                </div>
            `;
            return;
        }
        
        let html = `<div class="alert alert-success"><i class="bi bi-check-circle"></i> Found job number: <strong>${jobNumber}</strong></div>`;
        
        // Show run sheet results
        if (data.runsheets && data.runsheets.length > 0) {
            html += `
                <h6 class="mt-3"><i class="bi bi-calendar-check text-primary"></i> Run Sheets (${data.runsheets.length})</h6>
                <div class="list-group mb-3">
            `;
            data.runsheets.forEach(rs => {
                html += `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="mb-1">${rs.customer || 'Unknown Customer'}</h6>
                                <p class="mb-1"><strong>Date:</strong> ${rs.date}</p>
                                <p class="mb-1"><strong>Address:</strong> ${rs.address || 'N/A'}</p>
                                <p class="mb-0"><strong>Status:</strong> <span class="badge bg-${rs.status === 'completed' ? 'success' : 'warning'}">${rs.status || 'pending'}</span></p>
                            </div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }
        
        // Show payslip results
        if (data.payslips && data.payslips.length > 0) {
            html += `
                <h6 class="mt-3"><i class="bi bi-wallet2 text-success"></i> Payslips (${data.payslips.length})</h6>
                <div class="list-group">
            `;
            data.payslips.forEach(ps => {
                const amountNum = parseFloat(ps.amount);
                const amount = (!isNaN(amountNum) && amountNum !== null) ? amountNum.toFixed(2) : '0.00';
                html += `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="mb-1">Week ${ps.week_number}, ${ps.tax_year}</h6>
                                <p class="mb-1"><strong>Description:</strong> ${ps.description || 'N/A'}</p>
                                <p class="mb-1"><strong>Client:</strong> ${ps.client || 'N/A'}</p>
                                <p class="mb-0"><strong>Amount:</strong> <span class="text-success">£${amount}</span></p>
                            </div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }
        
        resultsDiv.innerHTML = html;
        
    } catch (error) {
        console.error('Search error:', error);
        resultsDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-exclamation-triangle"></i> Error: ${error.message}</div>`;
    }
}

// Notification System
async function checkNotifications() {
    try {
        const response = await fetch('/api/notifications/runsheets');
        if (!response.ok) {
            // Silently fail if endpoint doesn't exist
            return;
        }
        const data = await response.json();
        
        const badge = document.getElementById('notification-badge');
        const count = document.getElementById('notification-count');
        
        if (badge && count) {
            if (data.has_new && data.count > 0) {
                count.textContent = data.count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    } catch (error) {
        // Silently fail - notifications are not critical
    }
}

// Initialize base functionality
document.addEventListener('DOMContentLoaded', function() {
    // Allow Enter key to search
    const searchInput = document.getElementById('globalSearchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performGlobalSearch();
            }
        });
    }
    
    // Mark notifications as read when viewing run sheets page
    if (window.location.pathname === '/runsheets' || window.location.pathname === '/') {
        fetch('/api/notifications/runsheets/mark-read', {
            method: 'POST'
        }).catch(err => console.error('Error marking notifications as read:', err));
    }
    
    // Check notifications on page load
    checkNotifications();
    
    // Check every 5 minutes
    setInterval(checkNotifications, 5 * 60 * 1000);
});
