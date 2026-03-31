/**
 * HMRC MTD Settings Page JavaScript
 * Handles authentication, connection status, and configuration
 */

let hmrcConfig = {
    nino: '',
    businessId: ''
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadConnectionStatus();
    loadStoredConfig();
    setupEventListeners();
    
    // Check for auth callback parameters
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('auth') === 'success') {
        showNotification('Successfully connected to HMRC!', 'success');
        loadConnectionStatus();
        window.history.replaceState({}, document.title, window.location.pathname);
    } else if (urlParams.get('auth') === 'error') {
        const message = urlParams.get('message') || 'Authentication failed';
        showNotification(message, 'danger');
        window.history.replaceState({}, document.title, window.location.pathname);
    }
});

function setupEventListeners() {
    document.getElementById('connectBtn').addEventListener('click', connectToHMRC);
    document.getElementById('disconnectBtn').addEventListener('click', disconnectFromHMRC);
    document.getElementById('testConnectionBtn').addEventListener('click', testConnection);
    document.getElementById('refreshObligationsBtn').addEventListener('click', refreshObligations);
    document.getElementById('saveConfigBtn').addEventListener('click', saveConfiguration);
    document.getElementById('modalSaveBtn').addEventListener('click', saveModalConfig);
}

async function loadConnectionStatus() {
    try {
        const response = await fetch('/api/hmrc/auth/status');
        const data = await response.json();
        
        updateConnectionUI(data);
    } catch (error) {
        console.error('Error loading connection status:', error);
        showNotification('Failed to load connection status', 'danger');
    }
}

function updateConnectionUI(status) {
    const statusDiv = document.getElementById('connectionStatus');
    const connectBtn = document.getElementById('connectBtn');
    const disconnectBtn = document.getElementById('disconnectBtn');
    const testBtn = document.getElementById('testConnectionBtn');
    const refreshBtn = document.getElementById('refreshObligationsBtn');
    
    if (status.connected) {
        statusDiv.className = 'connection-status connected text-center';
        statusDiv.innerHTML = `
            <div class="status-icon">
                <i class="fas fa-check-circle"></i>
            </div>
            <h3>Connected to HMRC</h3>
            <p class="mb-2">${status.message}</p>
            <small>Expires: ${new Date(status.expires_at).toLocaleString()}</small>
            <span class="environment-badge ${status.environment}">${status.environment.toUpperCase()}</span>
        `;
        
        connectBtn.style.display = 'none';
        disconnectBtn.style.display = 'block';
        testBtn.style.display = 'block';
        refreshBtn.style.display = 'block';
        
        // Load obligations and submissions
        loadObligations();
        loadSubmissions();
    } else {
        statusDiv.className = 'connection-status disconnected text-center';
        statusDiv.innerHTML = `
            <div class="status-icon">
                <i class="fas fa-plug"></i>
            </div>
            <h3>Not Connected</h3>
            <p class="mb-0">${status.message}</p>
            <span class="environment-badge ${status.environment}">${status.environment.toUpperCase()}</span>
        `;
        
        connectBtn.style.display = 'block';
        disconnectBtn.style.display = 'none';
        testBtn.style.display = 'none';
        refreshBtn.style.display = 'none';
    }
}

async function connectToHMRC() {
    try {
        const response = await fetch('/api/hmrc/auth/start');
        const data = await response.json();
        
        if (data.success && data.auth_url) {
            // Redirect to HMRC authorization page
            window.location.href = data.auth_url;
        } else {
            showNotification('Failed to start authorization: ' + (data.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error starting authorization:', error);
        showNotification('Failed to connect to HMRC', 'danger');
    }
}

async function disconnectFromHMRC() {
    if (!confirm('Are you sure you want to disconnect from HMRC? You will need to re-authorize to submit data.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/hmrc/auth/disconnect', {
            method: 'POST',
            headers: getCSRFHeaders()
        });
        const data = await response.json();
        
        if (data.success) {
            showNotification('Successfully disconnected from HMRC', 'success');
            loadConnectionStatus();
        } else {
            showNotification('Failed to disconnect: ' + (data.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error disconnecting:', error);
        showNotification('Failed to disconnect from HMRC', 'danger');
    }
}

async function testConnection() {
    const testBtn = document.getElementById('testConnectionBtn');
    const originalText = testBtn.innerHTML;
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
    testBtn.disabled = true;
    
    try {
        const response = await fetch('/api/hmrc/test-connection');
        const data = await response.json();
        
        if (data.success) {
            showNotification('Connection test successful!', 'success');
        } else {
            showNotification('Connection test failed: ' + (data.error || 'Unknown error'), 'warning');
        }
    } catch (error) {
        console.error('Error testing connection:', error);
        showNotification('Failed to test connection', 'danger');
    } finally {
        testBtn.innerHTML = originalText;
        testBtn.disabled = false;
    }
}

async function refreshObligations() {
    // Check if NINO and Business ID are configured
    if (!hmrcConfig.nino || !hmrcConfig.businessId) {
        $('#configModal').modal('show');
        return;
    }
    
    const refreshBtn = document.getElementById('refreshObligationsBtn');
    const originalText = refreshBtn.innerHTML;
    refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
    refreshBtn.disabled = true;
    
    try {
        const response = await fetch(`/api/hmrc/obligations?nino=${hmrcConfig.nino}`);
        const data = await response.json();
        
        if (data.success) {
            showNotification('Obligations refreshed successfully', 'success');
            loadObligations();
        } else {
            showNotification('Failed to refresh obligations: ' + (data.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error refreshing obligations:', error);
        showNotification('Failed to refresh obligations', 'danger');
    } finally {
        refreshBtn.innerHTML = originalText;
        refreshBtn.disabled = false;
    }
}

async function loadObligations() {
    try {
        const response = await fetch('/api/hmrc/obligations/stored');
        const data = await response.json();
        
        const obligationsList = document.getElementById('obligationsList');
        
        if (data.success && data.obligations.length > 0) {
            obligationsList.innerHTML = data.obligations.map(obligation => `
                <div class="card obligation-card ${obligation.status.toLowerCase()}">
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-8">
                                <h6>${obligation.period_id}</h6>
                                <p class="mb-1">
                                    <i class="fas fa-calendar"></i> 
                                    ${formatDate(obligation.start_date)} - ${formatDate(obligation.end_date)}
                                </p>
                                <p class="mb-0">
                                    <i class="fas fa-clock"></i> 
                                    Due: ${formatDate(obligation.due_date)}
                                </p>
                            </div>
                            <div class="col-md-4 text-right">
                                <span class="badge badge-${obligation.status === 'Open' ? 'warning' : 'success'} badge-lg">
                                    ${obligation.status}
                                </span>
                                ${obligation.status === 'Open' ? `
                                    <button class="btn btn-sm btn-primary mt-2" onclick="submitPeriod('${obligation.period_id}')">
                                        <i class="fas fa-paper-plane"></i> Submit
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            obligationsList.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="fas fa-calendar-times fa-3x mb-3"></i>
                    <p>No obligations found. Click "Refresh Obligations" to load from HMRC.</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading obligations:', error);
    }
}

async function loadSubmissions() {
    try {
        const response = await fetch('/api/hmrc/submissions');
        const data = await response.json();
        
        const submissionsList = document.getElementById('submissionsList');
        
        if (data.success && data.submissions.length > 0) {
            submissionsList.innerHTML = data.submissions.map(submission => `
                <div class="card submission-card ${submission.status}">
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-8">
                                <h6>${submission.period_id} - ${submission.tax_year}</h6>
                                <p class="mb-1">
                                    <i class="fas fa-calendar"></i> 
                                    Submitted: ${formatDate(submission.submission_date)}
                                </p>
                                ${submission.hmrc_receipt_id ? `
                                    <p class="mb-0">
                                        <i class="fas fa-receipt"></i> 
                                        Receipt ID: ${submission.hmrc_receipt_id}
                                    </p>
                                ` : ''}
                                ${submission.error_message ? `
                                    <p class="mb-0 text-danger">
                                        <i class="fas fa-exclamation-circle"></i> 
                                        ${submission.error_message}
                                    </p>
                                ` : ''}
                            </div>
                            <div class="col-md-4 text-right">
                                <span class="badge badge-${submission.status === 'submitted' ? 'success' : 'danger'} badge-lg">
                                    ${submission.status.toUpperCase()}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            submissionsList.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="fas fa-inbox fa-3x mb-3"></i>
                    <p>No submissions yet</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading submissions:', error);
    }
}

function saveConfiguration() {
    const nino = document.getElementById('ninoInput').value.trim();
    const businessId = document.getElementById('businessIdInput').value.trim();
    
    if (!nino || !businessId) {
        showNotification('Please enter both NINO and Business ID', 'warning');
        return;
    }
    
    // Validate NINO format (basic)
    const ninoRegex = /^[A-Z]{2}[0-9]{6}[A-Z]$/;
    if (!ninoRegex.test(nino)) {
        showNotification('Invalid NINO format. Should be like: AA123456A', 'danger');
        return;
    }
    
    hmrcConfig.nino = nino;
    hmrcConfig.businessId = businessId;
    
    // Store in localStorage
    localStorage.setItem('hmrc_nino', nino);
    localStorage.setItem('hmrc_business_id', businessId);
    
    showNotification('Configuration saved successfully', 'success');
}

function loadStoredConfig() {
    const nino = localStorage.getItem('hmrc_nino');
    const businessId = localStorage.getItem('hmrc_business_id');
    
    if (nino) {
        document.getElementById('ninoInput').value = nino;
        hmrcConfig.nino = nino;
    }
    
    if (businessId) {
        document.getElementById('businessIdInput').value = businessId;
        hmrcConfig.businessId = businessId;
    }
}

function saveModalConfig() {
    const nino = document.getElementById('modalNino').value.trim();
    const businessId = document.getElementById('modalBusinessId').value.trim();
    
    if (!nino || !businessId) {
        showNotification('Please enter both NINO and Business ID', 'warning');
        return;
    }
    
    hmrcConfig.nino = nino;
    hmrcConfig.businessId = businessId;
    
    localStorage.setItem('hmrc_nino', nino);
    localStorage.setItem('hmrc_business_id', businessId);
    
    document.getElementById('ninoInput').value = nino;
    document.getElementById('businessIdInput').value = businessId;
    
    $('#configModal').modal('hide');
    
    // Continue with refresh
    refreshObligations();
}

function submitPeriod(periodId) {
    // This will be implemented in the expenses page
    // For now, redirect to expenses page
    window.location.href = `/expenses?submit_period=${periodId}`;
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="close" data-dismiss="alert">
            <span>&times;</span>
        </button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}
