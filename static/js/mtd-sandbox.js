/**
 * HMRC Sandbox Testing Dashboard
 * WARNING: SANDBOX TESTING ONLY
 */

let loadingModal;
let credentialsModal;
let activeUserNino = null;

function initSandboxPage() {
    const loadingEl = document.getElementById('loadingModal');
    const credentialsEl = document.getElementById('credentialsModal');
    if (loadingEl) loadingModal = new bootstrap.Modal(loadingEl);
    if (credentialsEl) credentialsModal = new bootstrap.Modal(credentialsEl);
    
    loadOAuthStatus();
    loadActiveUser();
    loadTestUserHistory();
}

function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.content : '';
}

/**
 * Load OAuth status for connection status bar
 */
async function loadOAuthStatus() {
    try {
        const response = await fetch('/api/hmrc/auth/status', { credentials: 'include' });
        const responseData = await response.json();
        const data = responseData.success ? responseData.data : responseData;
        
        console.log('Auth status response:', data);
        
        const badge = document.getElementById('oauthStatusBadge');
        if (!badge) return;
        
        if (data.connected) {
            const expiryDate = new Date(data.expires_at);
            const now = new Date();
            const hoursRemaining = Math.round((expiryDate - now) / (1000 * 60 * 60));
            
            badge.className = 'badge bg-success';
            badge.textContent = `Connected · expires in ${hoursRemaining}h`;
        } else {
            badge.className = 'badge bg-secondary';
            badge.textContent = 'Not connected';
        }
    } catch (error) {
        console.error('Error loading OAuth status:', error);
    }
}

/**
 * Load active test user
 */
async function loadActiveUser() {
    try {
        const response = await fetch('/api/hmrc/sandbox/active-test-user');
        const result = await response.json();
        
        const bodyDiv = document.getElementById('activeUserBody');
        const statusNino = document.getElementById('statusNino');
        const statusBusinessId = document.getElementById('statusBusinessId');
        const fetchBtn = document.getElementById('fetchBusinessBtn');
        
        if (result.success && result.data) {
            const user = result.data;
            activeUserNino = user.nino;
            
            // Update status bar
            if (statusNino) statusNino.textContent = user.nino || '—';
            if (statusBusinessId) statusBusinessId.textContent = user.businessId || '—';
            
            // Update card body with simple table
            bodyDiv.innerHTML = `
                <table class="table table-sm mb-0">
                    <tr><td class="fw-bold">User ID</td><td>${user.userId || '—'}</td></tr>
                    <tr><td class="fw-bold">NINO</td><td>${user.nino || '—'}</td></tr>
                    <tr><td class="fw-bold">SA UTR</td><td>${user.saUtr || '—'}</td></tr>
                    <tr><td class="fw-bold">Business ID</td><td>${user.businessId || 'Not fetched'}</td></tr>
                    <tr><td class="fw-bold">Trading Name</td><td>${user.tradingName || '—'}</td></tr>
                    <tr><td class="fw-bold">Created</td><td>${new Date(user.createdAt).toLocaleString()}</td></tr>
                </table>
            `;
            
            // Enable/disable fetch button
            if (fetchBtn) {
                fetchBtn.disabled = !!user.businessId;
            }
        } else {
            activeUserNino = null;
            if (statusNino) statusNino.textContent = '—';
            if (statusBusinessId) statusBusinessId.textContent = '—';
            bodyDiv.innerHTML = '<p class="text-muted">No active test user — click Create below.</p>';
            if (fetchBtn) fetchBtn.disabled = true;
        }
    } catch (error) {
        console.error('Error loading active user:', error);
    }
}

/**
 * Load test user history
 */
async function loadTestUserHistory() {
    try {
        const response = await fetch('/api/hmrc/sandbox/test-users');
        const result = await response.json();
        
        const tbody = document.getElementById('historyTableBody');
        if (!tbody) return;
        
        if (result.success && result.data && result.data.length > 0) {
            tbody.innerHTML = result.data.map(user => `
                <tr>
                    <td>${user.nino}</td>
                    <td>${user.business_id || '—'}</td>
                    <td>
                        ${user.is_active ? 
                            '<span class="badge bg-success">Active</span>' : 
                            '<span class="badge bg-secondary">Inactive</span>'}
                    </td>
                    <td>${new Date(user.created_at).toLocaleString()}</td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No test users found</td></tr>';
        }
    } catch (error) {
        console.error('Error loading test user history:', error);
        const tbody = document.getElementById('historyTableBody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Error loading history</td></tr>';
        }
    }
}

/**
 * Create new test user
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
async function fetchBusinessId() {
    if (!activeUserNino) {
        showNotification('No active test user', 'error');
        return;
    }
    
    try {
        loadingModal.show();
        document.getElementById('loadingMessage').textContent = 'Fetching business ID...';
        
        const response = await fetch('/api/hmrc/sandbox/create-test-business', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ nino: activeUserNino })
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
        <table class="table table-sm">
            <tr><td class="fw-bold">User ID</td><td>${data.userId}</td></tr>
            <tr><td class="fw-bold">Password</td><td>${data.password}</td></tr>
            <tr><td class="fw-bold">NINO</td><td>${data.nino}</td></tr>
        </table>
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
 * Validate fraud prevention headers
 */
async function validateFraudHeaders() {
    const resultDiv = document.getElementById('fraudResultBody');
    
    try {
        resultDiv.innerHTML = '<p class="text-muted"><i class="bi bi-hourglass-split"></i> Validating...</p>';
        
        const response = await fetch('/api/hmrc/fraud-headers/validate');
        const result = await response.json();
        
        if (result.success) {
            resultDiv.innerHTML = `
                <div class="alert alert-success alert-sm mb-2">
                    <i class="bi bi-check-circle-fill"></i> Valid (${result.sent_headers ? result.sent_headers.length : 0} headers)
                </div>
                <pre class="small mb-0" style="max-height: 300px; overflow-y: auto;">${JSON.stringify(result, null, 2)}</pre>
            `;
        } else {
            resultDiv.innerHTML = `
                <div class="alert alert-danger alert-sm mb-2">
                    <i class="bi bi-exclamation-circle-fill"></i> Failed
                </div>
                <pre class="small mb-0" style="max-height: 300px; overflow-y: auto;">${JSON.stringify(result, null, 2)}</pre>
            `;
        }
    } catch (error) {
        console.error('Error validating fraud headers:', error);
        resultDiv.innerHTML = `<p class="text-danger">Error: ${error.message}</p>`;
    }
}

/**
 * Run sandbox tests
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
 * Show notification
 */
function showNotification(message, type) {
    alert(message);
}
