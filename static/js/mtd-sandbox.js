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
    loadAuthStatus();
});

/**
 * Get CSRF token from meta tag
 */
function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.content : '';
}

/**
 * Load HMRC authentication status
 */
async function loadAuthStatus() {
    try {
        const response = await fetch('/api/hmrc/auth/status');
        const responseData = await response.json();
        const data = responseData.success ? responseData.data : responseData;
        
        const statusDiv = document.getElementById('oauthStatus');
        if (!statusDiv) return;
        
        if (data.authenticated) {
            const expiryDate = new Date(data.expires_at);
            const now = new Date();
            const hoursRemaining = Math.round((expiryDate - now) / (1000 * 60 * 60));
            
            statusDiv.innerHTML = `
                <span class="badge bg-success" title="Expires: ${expiryDate.toLocaleString()}">
                    <i class="bi bi-check-circle-fill"></i> Connected (${hoursRemaining}h)
                </span>
            `;
        } else {
            statusDiv.innerHTML = `
                <span class="badge bg-secondary">
                    <i class="bi bi-x-circle"></i> Not Connected
                </span>
            `;
        }
    } catch (error) {
        console.error('Error loading auth status:', error);
    }
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
 * Display active test user in the card
 */
function displayActiveUser(user) {
    const bodyDiv = document.getElementById('activeUserBody');
    const ninoDiv = document.getElementById('activeNino');
    const businessDiv = document.getElementById('activeBusinessId');
    
    // Update status tiles
    if (ninoDiv) ninoDiv.innerHTML = `<strong>${user.nino || '—'}</strong>`;
    if (businessDiv) businessDiv.innerHTML = `<strong>${user.businessId || '—'}</strong>`;
    
    // Update card body
    bodyDiv.innerHTML = `
        <div class="row">
            <div class="col-md-6 mb-3">
                <label class="form-label fw-bold">User ID</label>
                <input type="text" class="form-control" value="${user.userId || ''}" readonly>
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label fw-bold">NINO</label>
                <input type="text" class="form-control" value="${user.nino || ''}" readonly>
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label fw-bold">SA UTR</label>
                <input type="text" class="form-control" value="${user.saUtr || ''}" readonly>
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label fw-bold">Business ID</label>
                <input type="text" class="form-control" value="${user.businessId || 'Not fetched'}" readonly>
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label fw-bold">Trading Name</label>
                <input type="text" class="form-control" value="${user.tradingName || '—'}" readonly>
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label fw-bold">Created</label>
                <input type="text" class="form-control" value="${new Date(user.createdAt).toLocaleString()}" readonly>
            </div>
        </div>
        <button type="button" class="btn btn-success" onclick="fetchBusinessId('${user.nino}')" ${user.businessId ? 'disabled' : ''}>
            <i class="bi bi-download"></i> Fetch Business ID
        </button>
    `;
}

/**
 * Show "no user" alert
 */
function showNoUserAlert() {
    const bodyDiv = document.getElementById('activeUserBody');
    const ninoDiv = document.getElementById('activeNino');
    const businessDiv = document.getElementById('activeBusinessId');
    
    if (ninoDiv) ninoDiv.innerHTML = '<span class="text-muted">—</span>';
    if (businessDiv) businessDiv.innerHTML = '<span class="text-muted">—</span>';
    
    bodyDiv.innerHTML = `
        <div class="alert alert-info">
            <i class="bi bi-info-circle"></i> No active test user — create one below
        </div>
    `;
}

/**
 * Create a new test user
 */
async function createTestUser() {
    try {
        loadingModal.show();
        document.getElementById('loadingMessage').textContent = 'Creating test user...';
        
        const response = await fetch('/api/hmrc/sandbox/create-test-user', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        const result = await response.json();
        loadingModal.hide();
        
        if (result.success) {
            showCredentialsModal(result.data);
            loadActiveUser();
            loadTestUserHistory();
            showNotification('Test user created successfully', 'success');
        } else {
            showNotification(result.error || 'Failed to create test user', 'error');
        }
    } catch (error) {
        loadingModal.hide();
        console.error('Error creating test user:', error);
        showNotification('Error creating test user', 'error');
    }
}

/**
 * Fetch business ID for active user
 */
async function fetchBusinessId(nino) {
    try {
        loadingModal.show();
        document.getElementById('loadingMessage').textContent = 'Fetching business ID...';
        
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
        
        if (result.success) {
            loadActiveUser();
            showNotification('Business ID fetched successfully', 'success');
        } else {
            showNotification(result.error || 'Failed to fetch business ID', 'error');
        }
    } catch (error) {
        loadingModal.hide();
        console.error('Error fetching business ID:', error);
        showNotification('Error fetching business ID', 'error');
    }
}

/**
 * Show credentials modal
 */
function showCredentialsModal(data) {
    const bodyDiv = document.getElementById('credentialsBody');
    bodyDiv.innerHTML = `
        <div class="alert alert-success">
            <i class="bi bi-check-circle-fill"></i> Test user created successfully!
        </div>
        <div class="mb-3">
            <label class="form-label fw-bold">User ID</label>
            <input type="text" class="form-control" value="${data.userId}" readonly>
        </div>
        <div class="mb-3">
            <label class="form-label fw-bold">Password</label>
            <input type="text" class="form-control" value="${data.password}" readonly>
        </div>
        <div class="mb-3">
            <label class="form-label fw-bold">NINO</label>
            <input type="text" class="form-control" value="${data.nino}" readonly>
        </div>
        <div class="alert alert-info">
            <strong>Next Steps:</strong>
            <ol class="mb-0 mt-2">
                <li>Click "Connect to HMRC" above</li>
                <li>Use the User ID and Password to authenticate</li>
                <li>Return here and click "Fetch Business ID"</li>
            </ol>
        </div>
    `;
    credentialsModal.show();
}

/**
 * Load test user history
 */
async function loadTestUserHistory() {
    try {
        const response = await fetch('/api/hmrc/sandbox/test-users');
        const result = await response.json();
        
        const tbody = document.getElementById('testUserHistoryBody');
        if (!tbody) return;
        
        if (result.success && result.data && result.data.length > 0) {
            tbody.innerHTML = result.data.map(user => `
                <tr>
                    <td>${user.nino}</td>
                    <td>${user.business_id || '—'}</td>
                    <td>${new Date(user.created_at).toLocaleString()}</td>
                    <td>
                        ${user.is_active ? 
                            '<span class="badge bg-success">Active</span>' : 
                            '<span class="badge bg-secondary">Inactive</span>'}
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No test users found</td></tr>';
        }
    } catch (error) {
        console.error('Error loading test user history:', error);
    }
}

/**
 * Validate fraud prevention headers
 */
async function validateFraudHeaders() {
    const resultDiv = document.getElementById('fraudHeadersResult');
    const alertDiv = document.getElementById('fraudHeadersAlert');
    const detailsPre = document.getElementById('fraudHeadersDetails');
    
    try {
        resultDiv.classList.remove('d-none');
        alertDiv.className = 'alert alert-info';
        alertDiv.innerHTML = '<i class="bi bi-hourglass-split"></i> Validating fraud prevention headers...';
        detailsPre.textContent = '';
        
        const response = await fetch('/api/hmrc/fraud-headers/validate');
        const result = await response.json();
        
        if (result.success) {
            alertDiv.className = 'alert alert-success';
            alertDiv.innerHTML = `
                <h6><i class="bi bi-check-circle-fill"></i> Validation Successful</h6>
                <p class="mb-0">All fraud prevention headers validated successfully.</p>
                <p class="mb-0 mt-2"><strong>Headers sent:</strong> ${result.sent_headers ? result.sent_headers.length : 0}</p>
            `;
        } else {
            alertDiv.className = 'alert alert-danger';
            alertDiv.innerHTML = `
                <h6><i class="bi bi-exclamation-circle-fill"></i> Validation Failed</h6>
                <p class="mb-0">${result.error || 'Unknown error occurred'}</p>
            `;
        }
        
        detailsPre.textContent = JSON.stringify(result, null, 2);
        
    } catch (error) {
        console.error('Error validating fraud headers:', error);
        resultDiv.classList.remove('d-none');
        alertDiv.className = 'alert alert-danger';
        alertDiv.innerHTML = `
            <h6><i class="bi bi-exclamation-circle-fill"></i> Error</h6>
            <p class="mb-0">Failed to validate fraud headers: ${error.message}</p>
        `;
    }
}

/**
 * Run sandbox tests (placeholder)
 */
function runSandboxTests() {
    showNotification('Sandbox test runner not yet implemented', 'info');
}

/**
 * Generate test expenses
 */
async function generateTestExpenses() {
    if (!confirm('Generate 12 sample expenses for testing?')) return;
    
    try {
        loadingModal.show();
        document.getElementById('loadingMessage').textContent = 'Generating test expenses...';
        
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
            showNotification('Test expenses generated successfully', 'success');
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
 * Delete test expenses
 */
async function deleteTestExpenses() {
    if (!confirm('Delete all test expenses? This cannot be undone.')) return;
    
    try {
        loadingModal.show();
        document.getElementById('loadingMessage').textContent = 'Deleting test expenses...';
        
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
            showNotification('Test expenses deleted successfully', 'success');
        } else {
            showNotification(result.error || 'Failed to delete test expenses', 'error');
        }
    } catch (error) {
        loadingModal.hide();
        console.error('Error deleting test expenses:', error);
        showNotification('Error deleting test expenses', 'error');
    }
}

/**
 * Clear all HMRC submissions
 */
async function clearAllSubmissions() {
    if (!confirm('Clear all HMRC submission records? This cannot be undone.')) return;
    
    try {
        loadingModal.show();
        document.getElementById('loadingMessage').textContent = 'Clearing submissions...';
        
        const response = await fetch('/api/hmrc/sandbox/clear-submissions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        const result = await response.json();
        loadingModal.hide();
        
        if (result.success) {
            showNotification('Submissions cleared successfully', 'success');
        } else {
            showNotification(result.error || 'Failed to clear submissions', 'error');
        }
    } catch (error) {
        loadingModal.hide();
        console.error('Error clearing submissions:', error);
        showNotification('Error clearing submissions', 'error');
    }
}

/**
 * Show notification (reuses base.js if available)
 */
function showNotification(message, type) {
    if (typeof window.showNotification === 'function') {
        window.showNotification(message, type);
    } else {
        alert(message);
    }
}
