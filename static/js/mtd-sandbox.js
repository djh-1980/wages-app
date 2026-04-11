/**
 * HMRC Sandbox Testing Dashboard
 * 
 * WARNING: SANDBOX TESTING ONLY
 * Remove this file before production deployment.
 */

let loadingModal;
let credentialsModal;

document.addEventListener('DOMContentLoaded', function() {
    loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    credentialsModal = new bootstrap.Modal(document.getElementById('credentialsModal'));
    
    loadActiveUser();
    loadTestUserHistory();
});

/**
 * Get CSRF token from meta tag
 */
function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.content : '';
}

/**
 * Load the active test user
 */
async function loadActiveUser() {
    try {
        const response = await fetch('/api/hmrc/sandbox/active-test-user');
        const result = await response.json();
        
        if (result.success && result.data) {
            displayActiveUser(result.data);
        } else {
            showNoUserAlert();
        }
    } catch (error) {
        console.error('Error loading active user:', error);
        showNotification('Error loading test user', 'error');
    }
}

/**
 * Display active test user details
 */
function displayActiveUser(user) {
    document.getElementById('noUserAlert').style.display = 'none';
    document.getElementById('activeUserCard').style.display = 'block';
    
    document.getElementById('userId').value = user.userId || '';
    document.getElementById('nino').value = user.nino || '';
    document.getElementById('saUtr').value = user.saUtr || '';
    document.getElementById('businessId').value = user.businessId || 'Not fetched yet';
    document.getElementById('tradingName').value = user.tradingName || 'N/A';
    document.getElementById('accountingType').value = user.accountingType || 'N/A';
    document.getElementById('createdAt').textContent = formatDateTime(user.createdAt);
    
    // Enable fetch business button if no business exists
    const createBusinessBtn = document.getElementById('createBusinessBtn');
    if (!user.businessId) {
        createBusinessBtn.disabled = false;
        createBusinessBtn.classList.remove('btn-success');
        createBusinessBtn.classList.add('btn-warning');
        createBusinessBtn.innerHTML = '<i class="bi bi-download"></i> Fetch Business ID (Required)';
    } else {
        createBusinessBtn.disabled = true;
        createBusinessBtn.classList.remove('btn-warning');
        createBusinessBtn.classList.add('btn-success');
        createBusinessBtn.innerHTML = '<i class="bi bi-check-circle"></i> Business ID Retrieved';
    }
}

/**
 * Show no user alert
 */
function showNoUserAlert() {
    document.getElementById('noUserAlert').style.display = 'block';
    document.getElementById('activeUserCard').style.display = 'none';
    document.getElementById('createBusinessBtn').disabled = true;
}

/**
 * Create a new test user
 */
async function createTestUser() {
    if (!confirm('This will create a new test user and deactivate the current one. Continue?')) {
        return;
    }
    
    try {
        document.getElementById('loadingMessage').textContent = 'Creating test user...';
        loadingModal.show();
        
        const response = await fetch('/api/hmrc/sandbox/create-test-user', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        const result = await response.json();
        loadingModal.hide();
        
        // Log full response for debugging
        console.log('Create test user response:', {
            status: response.status,
            ok: response.ok,
            result: result
        });
        
        if (result.success) {
            // Show credentials modal
            document.getElementById('modalUserId').value = result.data.userId;
            document.getElementById('modalPassword').value = result.data.password;
            document.getElementById('modalNino').value = result.data.nino;
            document.getElementById('modalSaUtr').value = result.data.saUtr;
            
            credentialsModal.show();
            
            // Reload active user and history
            loadActiveUser();
            loadTestUserHistory();
            
            showNotification('Test user created successfully!', 'success');
        } else {
            console.error('Create test user failed:', result);
            showNotification(result.error || 'Failed to create test user', 'error');
        }
    } catch (error) {
        loadingModal.hide();
        console.error('Error creating test user:', error);
        showNotification('Error creating test user', 'error');
    }
}

/**
 * Fetch the auto-provisioned test business for the active user
 */
async function createTestBusiness() {
    const nino = document.getElementById('nino').value;
    
    if (!nino) {
        showNotification('No active test user found', 'error');
        return;
    }
    
    if (!confirm('This will fetch the auto-provisioned business ID for the current test user. Make sure you have authenticated via OAuth first. Continue?')) {
        return;
    }
    
    try {
        document.getElementById('loadingMessage').textContent = 'Fetching business ID...';
        loadingModal.show();
        
        const response = await fetch('/api/hmrc/sandbox/create-test-business', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ nino: nino })
        });
        
        const result = await response.json();
        loadingModal.hide();
        
        // Log full response for debugging
        console.log('Create test business response:', {
            status: response.status,
            ok: response.ok,
            result: result
        });
        
        if (result.success) {
            showNotification('Business ID retrieved successfully!', 'success');
            loadActiveUser();
            loadTestUserHistory();
        } else {
            console.error('Fetch business failed:', result);
            if (result.error.includes('Not authenticated')) {
                showNotification('Please authenticate via OAuth first. Go to HMRC MTD page and connect.', 'error');
            } else {
                showNotification(result.error || 'Failed to retrieve business ID', 'error');
            }
        }
    } catch (error) {
        loadingModal.hide();
        console.error('Error fetching business:', error);
        showNotification('Error fetching business ID', 'error');
    }
}

/**
 * Load test user history
 */
async function loadTestUserHistory() {
    try {
        const response = await fetch('/api/hmrc/sandbox/test-users');
        const result = await response.json();
        
        if (result.success) {
            displayTestUserHistory(result.data);
        }
    } catch (error) {
        console.error('Error loading test user history:', error);
    }
}

/**
 * Display test user history table
 */
function displayTestUserHistory(users) {
    const tbody = document.getElementById('historyTableBody');
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No test users found</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.user_id || 'N/A'}</td>
            <td><code>${user.nino || 'N/A'}</code></td>
            <td><code>${user.business_id || 'N/A'}</code></td>
            <td>${user.trading_name || 'N/A'}</td>
            <td>
                ${user.is_active ? 
                    '<span class="badge bg-success">Active</span>' : 
                    '<span class="badge bg-secondary">Inactive</span>'}
            </td>
            <td>${formatDateTime(user.created_at)}</td>
            <td>
                <button class="btn btn-sm btn-danger" onclick="deleteTestUser(${user.id})">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

/**
 * Delete a test user
 */
async function deleteTestUser(userId) {
    if (!confirm('Are you sure you want to delete this test user record?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/hmrc/sandbox/test-users/${userId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Test user deleted successfully', 'success');
            loadActiveUser();
            loadTestUserHistory();
        } else {
            showNotification(result.error || 'Failed to delete test user', 'error');
        }
    } catch (error) {
        console.error('Error deleting test user:', error);
        showNotification('Error deleting test user', 'error');
    }
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    const text = element.value;
    
    if (!text || text === 'Not created yet' || text === 'N/A') {
        showNotification('Nothing to copy', 'warning');
        return;
    }
    
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showNotification('Failed to copy', 'error');
    });
}

/**
 * Format datetime string
 */
function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    return date.toLocaleString('en-GB', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    // Create Bootstrap alert notification
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${getAlertClass(type)} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.style.minWidth = '300px';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 150);
    }, 5000);
}

/**
 * Get Bootstrap alert class for notification type
 */
function getAlertClass(type) {
    const typeMap = {
        'success': 'success',
        'error': 'danger',
        'warning': 'warning',
        'info': 'info'
    };
    return typeMap[type] || 'info';
}

/**
 * Generate test expenses for MTD sandbox testing
 */
async function generateTestExpenses() {
    if (!confirm('This will generate 12 test expenses (3 per quarter) for tax year 2024/2025.\n\nAll expenses will be prefixed with "TEST -" for easy identification.\n\nContinue?')) {
        return;
    }
    
    try {
        document.getElementById('loadingMessage').textContent = 'Generating test expenses...';
        loadingModal.show();
        
        const response = await fetch('/api/hmrc/sandbox/generate-test-expenses', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        const result = await response.json();
        loadingModal.hide();
        
        if (result.success) {
            showNotification(`Successfully generated ${result.count} test expenses!`, 'success');
        } else {
            showNotification(result.error || 'Failed to generate test expenses', 'error');
        }
    } catch (error) {
        loadingModal.hide();
        console.error('Error generating test expenses:', error);
        showNotification('Error generating test expenses', 'error');
    }
}

/**
 * Delete all test expenses
 */
async function deleteTestExpenses() {
    if (!confirm('This will permanently delete ALL test expenses (those with description starting with "TEST -").\n\nThis action cannot be undone.\n\nContinue?')) {
        return;
    }
    
    try {
        document.getElementById('loadingMessage').textContent = 'Deleting test expenses...';
        loadingModal.show();
        
        const response = await fetch('/api/hmrc/sandbox/delete-test-expenses', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        const result = await response.json();
        loadingModal.hide();
        
        if (result.success) {
            showNotification(`Successfully deleted ${result.count} test expenses!`, 'success');
        } else {
            showNotification(result.error || 'Failed to delete test expenses', 'error');
        }
    } catch (error) {
        loadingModal.hide();
        console.error('Error deleting test expenses:', error);
        showNotification('Error deleting test expenses', 'error');
    }
}
