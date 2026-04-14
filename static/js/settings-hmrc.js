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
    
    // Load submission history when tab is shown
    document.querySelector('a[data-bs-target="#submissions"]').addEventListener('shown.bs.tab', function() {
        loadSubmissionHistory();
    });
    
    // Setup final declaration step flow
    setupFinalDeclarationFlow();
});

function setupEventListeners() {
    document.getElementById('connectBtn').addEventListener('click', connectToHMRC);
    document.getElementById('disconnectBtn').addEventListener('click', disconnectFromHMRC);
    document.getElementById('testConnectionBtn').addEventListener('click', testConnection);
    document.getElementById('refreshObligationsBtn').addEventListener('click', refreshObligations);
    document.getElementById('saveConfigBtn').addEventListener('click', saveConfiguration);
    document.getElementById('modalSaveBtn').addEventListener('click', saveModalConfig);
    
    // Final declaration event listeners
    // Final declaration step-by-step flow
    document.getElementById('triggerCalcBtn').addEventListener('click', triggerTaxCalculation);
    document.getElementById('viewCalcBtn').addEventListener('click', viewCalculationDetails);
    document.getElementById('proceedToStep3Btn').addEventListener('click', proceedToStep3);
    document.getElementById('declarationCheckbox').addEventListener('change', function() {
        document.getElementById('submitDeclBtn').disabled = !this.checked;
    });
    document.getElementById('submitDeclBtn').addEventListener('click', submitFinalDeclaration);
}

async function loadConnectionStatus() {
    try {
        const response = await fetch('/api/hmrc/auth/status');
        const responseData = await response.json();
        const data = responseData.success ? responseData.data : responseData;
        
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
        const response = await fetch('/api/hmrc/auth/start', {
            credentials: 'same-origin',
            headers: getCSRFHeaders()
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Auth start response:', data);
        
        if (data.success && data.auth_url) {
            // Redirect to HMRC authorization page
            window.location.href = data.auth_url;
        } else {
            showNotification('Failed to start authorization: ' + (data.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error starting authorization:', error);
        showNotification('Failed to connect to HMRC: ' + error.message, 'danger');
    }
}

async function disconnectFromHMRC() {
    if (!confirm('Are you sure you want to disconnect from HMRC? You will need to re-authorize to submit data.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/hmrc/auth/disconnect', {
            method: 'POST',
            credentials: 'same-origin',
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
        const responseData = await response.json();
        const data = responseData.success ? responseData.data : responseData;
        
        if (data.success || responseData.success) {
            showNotification('Connection test successful!', 'success');
        } else {
            const validationErrors = data.validation_errors || responseData.validation_errors;
            showNotification('Connection test failed: ' + (data.error || 'Unknown error'), 'warning', validationErrors);
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
        // Include date range for current tax year (April 6 2024 to April 5 2025)
        const fromDate = '2024-04-06';
        const toDate = '2025-04-05';
        const response = await fetch(`/api/hmrc/obligations?nino=${hmrcConfig.nino}&from_date=${fromDate}&to_date=${toDate}`);
        const responseData = await response.json();
        const data = responseData.success ? responseData.data : responseData;
        
        if (data.success || responseData.success) {
            showNotification('Obligations refreshed successfully', 'success');
            loadObligations();
        } else {
            const validationErrors = data.validation_errors || responseData.validation_errors;
            showNotification('Failed to refresh obligations: ' + (data.error || 'Unknown error'), 'danger', validationErrors);
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
        const responseData = await response.json();
        
        const obligationsList = document.getElementById('obligationsList');
        
        // API returns: {success: true, data: {obligations: [...], count: N}}
        if (responseData.success && responseData.data && responseData.data.obligations && responseData.data.obligations.length > 0) {
            obligationsList.innerHTML = responseData.data.obligations.map(obligation => `
                <div class="card obligation-card ${obligation.status.toLowerCase()}" 
                     data-period-id="${obligation.period_id}"
                     data-start-date="${obligation.start_date}"
                     data-end-date="${obligation.end_date}"
                     data-tax-year="${obligation.tax_year || ''}">
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
        const responseData = await response.json();
        const data = responseData.success ? responseData.data : responseData;
        
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
    // Load from localStorage
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
    // Find the obligation data for this period
    const obligationsList = document.getElementById('obligationsList');
    const obligationCard = obligationsList.querySelector(`[data-period-id="${periodId}"]`);
    
    if (!obligationCard) {
        showNotification('Could not find obligation details', 'error');
        return;
    }
    
    // Get dates from data attributes (already in YYYY-MM-DD format)
    const startDate = obligationCard.dataset.startDate;
    const endDate = obligationCard.dataset.endDate;
    let taxYear = obligationCard.dataset.taxYear;
    
    // If tax year not stored, derive from start date
    if (!taxYear) {
        const startDateObj = new Date(startDate);
        const taxYearStart = startDateObj.getMonth() >= 3 ? startDateObj.getFullYear() : startDateObj.getFullYear() - 1;
        taxYear = `${taxYearStart}/${taxYearStart + 1}`;
    }
    
    console.log('Submitting period:', {
        period_id: periodId,
        from_date: startDate,
        to_date: endDate,
        tax_year: taxYear
    });
    
    // Navigate to expenses page with all required parameters
    const params = new URLSearchParams({
        from_date: startDate,
        to_date: endDate,
        tax_year: taxYear,
        period_id: periodId,
        mode: 'mtd_submission'
    });
    
    window.location.href = `/expenses?${params.toString()}`;
}

function parseDateString(dateStr) {
    // Parse "06 Apr 2024" format to YYYY-MM-DD
    const months = {
        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
        'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
        'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
    };
    const parts = dateStr.trim().split(/\s+/);
    if (parts.length === 3) {
        const day = parts[0].padStart(2, '0');
        const month = months[parts[1]];
        const year = parts[2];
        return `${year}-${month}-${day}`;
    }
    return dateStr;
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

function showNotification(message, type = 'info', validationErrors = null) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px; max-width: 500px;';
    
    let content = message;
    
    // If validation errors are provided, format them as a list
    if (validationErrors && Array.isArray(validationErrors) && validationErrors.length > 0) {
        content += '<hr class="my-2"><strong>Validation Errors:</strong><ul class="mb-0 mt-1">';
        validationErrors.forEach(err => {
            const field = err.field || 'unknown';
            const msg = err.message || 'Validation error';
            content += `<li><strong>${field}:</strong> ${msg}</li>`;
        });
        content += '</ul>';
    }
    
    notification.innerHTML = `
        ${content}
        <button type="button" class="close" data-dismiss="alert">
            <span>&times;</span>
        </button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-dismiss after 10 seconds for validation errors, 5 seconds for others
    const dismissTime = validationErrors ? 10000 : 5000;
    setTimeout(() => {
        notification.remove();
    }, dismissTime);
}

function getCSRFHeaders() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]');
    return {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken ? csrfToken.content : ''
    };
}

// ============================================================================
// SUBMISSION HISTORY FUNCTIONS
// ============================================================================

async function loadSubmissionHistory() {
    const container = document.getElementById('submissionsList');
    
    try {
        const response = await fetch('/api/hmrc/submissions');
        const data = await response.json();
        
        if (data.success && data.submissions && data.submissions.length > 0) {
            let html = '<div class="table-responsive"><table class="table table-hover">';
            html += '<thead><tr>';
            html += '<th>Period</th>';
            html += '<th>Tax Year</th>';
            html += '<th>Submitted Date</th>';
            html += '<th>Status</th>';
            html += '<th>HMRC Period ID</th>';
            html += '</tr></thead><tbody>';
            
            data.submissions.forEach(sub => {
                const statusBadge = sub.status === 'submitted' 
                    ? '<span class="badge bg-success">Submitted</span>'
                    : '<span class="badge bg-secondary">' + sub.status + '</span>';
                    
                html += '<tr>';
                html += '<td><strong>' + sub.period_id + '</strong></td>';
                html += '<td>' + sub.tax_year + '</td>';
                html += '<td>' + formatDateTime(sub.submitted_at) + '</td>';
                html += '<td>' + statusBadge + '</td>';
                html += '<td><code>' + (sub.hmrc_period_id || 'N/A') + '</code></td>';
                html += '</tr>';
            });
            
            html += '</tbody></table></div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="text-center text-muted py-5"><i class="fas fa-inbox fa-3x mb-3"></i><p>No submissions yet</p></div>';
        }
    } catch (error) {
        console.error('Error loading submission history:', error);
        container.innerHTML = '<div class="alert alert-danger">Failed to load submission history</div>';
    }
}

function formatDateTime(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ============================================================================
// FINAL DECLARATION STEP-BY-STEP FLOW
// ============================================================================

let currentCalculationId = null;

function setupFinalDeclarationFlow() {
    // Reset flow on tax year change
    document.getElementById('finalDeclTaxYear').addEventListener('change', resetFinalDeclFlow);
}

function resetFinalDeclFlow() {
    currentCalculationId = null;
    document.getElementById('step1').style.display = 'block';
    document.getElementById('step2').style.display = 'none';
    document.getElementById('step3').style.display = 'none';
    document.getElementById('stepSuccess').style.display = 'none';
    document.getElementById('step1Loading').style.display = 'none';
    document.getElementById('calcDetails').style.display = 'none';
    document.getElementById('declarationCheckbox').checked = false;
    document.getElementById('submitDeclBtn').disabled = true;
}

async function triggerTaxCalculation() {
    const taxYear = document.getElementById('finalDeclTaxYear').value;
    const nino = hmrcConfig.nino || document.getElementById('ninoInput').value;
    
    if (!nino) {
        showNotification('Please enter your NINO first', 'warning');
        return;
    }
    
    const btn = document.getElementById('triggerCalcBtn');
    const loading = document.getElementById('step1Loading');
    
    btn.disabled = true;
    loading.style.display = 'block';
    
    try {
        const response = await fetch('/api/hmrc/final-declaration/calculate', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                ...getCSRFHeaders()
            },
            body: JSON.stringify({
                tax_year: taxYear,
                nino: nino,
                calculation_type: 'intent-to-finalise'
            })
        });
        const data = await response.json();
        
        if (data.success && data.calculation_id) {
            currentCalculationId = data.calculation_id;
            document.getElementById('calcIdDisplay').textContent = currentCalculationId;
            
            // Move to Step 2
            document.getElementById('step1').style.display = 'none';
            document.getElementById('step2').style.display = 'block';
            
            showNotification('Tax calculation triggered successfully!', 'success');
        } else {
            showNotification('Failed to trigger calculation: ' + (data.error || 'Unknown error'), 'danger');
            btn.disabled = false;
        }
    } catch (error) {
        console.error('Error triggering calculation:', error);
        showNotification('Failed to trigger calculation', 'danger');
        btn.disabled = false;
    } finally {
        loading.style.display = 'none';
    }
}

async function viewCalculationDetails() {
    if (!currentCalculationId) {
        showNotification('No calculation ID available', 'danger');
        return;
    }
    
    const nino = hmrcConfig.nino || document.getElementById('ninoInput').value;
    if (!nino) {
        showNotification('Please enter your NINO first', 'warning');
        return;
    }
    
    const btn = document.getElementById('viewCalcBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
    
    try {
        const response = await fetch(`/api/hmrc/calculations/${currentCalculationId}?nino=${nino}`);
        const data = await response.json();
        
        if (data.success && data.calculation) {
            displayCalculationSummary(data.calculation);
            document.getElementById('calcDetails').style.display = 'block';
        } else {
            showNotification('Failed to load calculation: ' + (data.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error loading calculation:', error);
        showNotification('Failed to load calculation details', 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-eye"></i> View Calculation Details';
    }
}

function displayCalculationSummary(calculation) {
    const container = document.getElementById('calcSummary');
    let html = '<table class="table table-sm">';
    
    // Display key figures from calculation
    if (calculation.totalIncomeTaxAndNicsDue !== undefined) {
        html += '<tr><th>Total Tax & NICs Due:</th><td><strong>£' + calculation.totalIncomeTaxAndNicsDue.toFixed(2) + '</strong></td></tr>';
    }
    if (calculation.totalIncomeReceived !== undefined) {
        html += '<tr><th>Total Income:</th><td>£' + calculation.totalIncomeReceived.toFixed(2) + '</td></tr>';
    }
    if (calculation.totalAllowancesAndDeductions !== undefined) {
        html += '<tr><th>Allowances & Deductions:</th><td>£' + calculation.totalAllowancesAndDeductions.toFixed(2) + '</td></tr>';
    }
    if (calculation.taxableIncome !== undefined) {
        html += '<tr><th>Taxable Income:</th><td>£' + calculation.taxableIncome.toFixed(2) + '</td></tr>';
    }
    
    html += '</table>';
    container.innerHTML = html;
}

function proceedToStep3() {
    document.getElementById('step2').style.display = 'none';
    document.getElementById('step3').style.display = 'block';
}

async function submitFinalDeclaration() {
    const taxYear = document.getElementById('finalDeclTaxYear').value;
    const nino = hmrcConfig.nino || document.getElementById('ninoInput').value;
    const btn = document.getElementById('submitDeclBtn');
    const originalText = btn.innerHTML;
    
    if (!currentCalculationId) {
        showNotification('No calculation ID available', 'danger');
        return;
    }
    
    if (!nino) {
        showNotification('Please enter your NINO first', 'warning');
        return;
    }
    
    if (!document.getElementById('declarationCheckbox').checked) {
        showNotification('Please confirm the declaration', 'warning');
        return;
    }
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
    
    try {
        const response = await fetch('/api/hmrc/final-declaration/submit', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                ...getCSRFHeaders()
            },
            body: JSON.stringify({
                tax_year: taxYear,
                calculation_id: currentCalculationId,
                nino: nino,
                confirmed: true
            })
        });
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('step3').style.display = 'none';
            document.getElementById('stepSuccess').style.display = 'block';
            document.getElementById('successMessage').innerHTML = '<strong>Receipt ID:</strong> ' + (data.receipt_id || 'N/A');
            showNotification('Final declaration submitted successfully!', 'success');
        } else {
            showNotification('Failed to submit final declaration: ' + data.error, 'danger');
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    } catch (error) {
        console.error('Error submitting final declaration:', error);
        showNotification('Failed to submit final declaration', 'danger');
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// ============================================================================
// FINAL DECLARATION FUNCTIONS
// ============================================================================

async function loadFinalDeclarationStatus() {
    const taxYear = document.getElementById('finalDeclTaxYear').value;
    
    try {
        const response = await fetch(`/api/hmrc/final-declaration/status?tax_year=${taxYear}`);
        const data = await response.json();
        
        if (data.success) {
            updateFinalDeclarationUI(data.data);
        } else {
            showNotification('Failed to load final declaration status: ' + data.error, 'danger');
        }
    } catch (error) {
        console.error('Error loading final declaration status:', error);
        showNotification('Failed to load final declaration status', 'danger');
    }
}

function updateFinalDeclarationUI(status) {
    const quarters = ['Q1', 'Q2', 'Q3', 'Q4'];
    
    // Update quarterly checklist
    quarters.forEach(quarter => {
        const statusBadge = document.getElementById(`${quarter.toLowerCase()}Status`);
        const listItem = statusBadge.closest('.list-group-item');
        const icon = listItem.querySelector('i');
        
        if (status.quarters_submitted.includes(quarter)) {
            statusBadge.className = 'badge badge-success';
            statusBadge.textContent = 'Submitted';
            icon.className = 'fas fa-check-circle text-success';
        } else {
            statusBadge.className = 'badge badge-secondary';
            statusBadge.textContent = 'Not Submitted';
            icon.className = 'fas fa-circle text-muted';
        }
    });
    
    // Enable/disable calculate button
    const calculateBtn = document.getElementById('calculateTaxBtn');
    if (status.all_submitted && status.declaration_status === 'not_started') {
        calculateBtn.disabled = false;
        calculateBtn.nextElementSibling.textContent = 'Ready to calculate';
    } else if (status.declaration_status === 'calculated' || status.declaration_status === 'submitted') {
        calculateBtn.disabled = true;
        calculateBtn.nextElementSibling.textContent = 'Already calculated';
    } else {
        calculateBtn.disabled = true;
        calculateBtn.nextElementSibling.textContent = 'All 4 quarters must be submitted first';
    }
    
    // Show tax calculation if available
    const taxCalcSection = document.getElementById('taxCalculationSection');
    const submitBtn = document.getElementById('submitFinalDeclBtn');
    
    if (status.declaration && status.declaration.calculation_id) {
        taxCalcSection.style.display = 'block';
        document.getElementById('estimatedTax').textContent = '£' + (status.declaration.estimated_tax || 0).toFixed(2);
        document.getElementById('calculationId').textContent = status.declaration.calculation_id;
        
        if (status.declaration_status === 'calculated') {
            submitBtn.disabled = false;
            submitBtn.nextElementSibling.textContent = 'Ready to submit';
        } else {
            submitBtn.disabled = true;
            submitBtn.nextElementSibling.textContent = 'Already submitted';
        }
    } else {
        taxCalcSection.style.display = 'none';
        submitBtn.disabled = true;
        submitBtn.nextElementSibling.textContent = 'Tax must be calculated first';
    }
    
    // Show declaration status if submitted
    const declStatusSection = document.getElementById('declarationStatusSection');
    if (status.declaration_status === 'submitted' && status.declaration) {
        declStatusSection.style.display = 'block';
        document.getElementById('receiptId').textContent = status.declaration.hmrc_receipt_id || 'N/A';
        document.getElementById('submittedAt').textContent = formatDate(status.declaration.submitted_at);
    } else {
        declStatusSection.style.display = 'none';
    }
}

async function calculateTaxLiability() {
    const taxYear = document.getElementById('finalDeclTaxYear').value;
    const nino = hmrcConfig.nino || document.getElementById('ninoInput').value;
    const calculateBtn = document.getElementById('calculateTaxBtn');
    const originalText = calculateBtn.innerHTML;
    
    calculateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Calculating...';
    calculateBtn.disabled = true;
    
    try {
        const response = await fetch('/api/hmrc/final-declaration/calculate', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                ...getCSRFHeaders()
            },
            body: JSON.stringify({
                tax_year: taxYear,
                nino: nino,
                calculation_type: 'intent-to-finalise'
            })
        });
        const data = await response.json();
        
        if (data.success) {
            showNotification('Tax calculation completed successfully!', 'success');
            loadFinalDeclarationStatus();
        } else {
            showNotification('Failed to calculate tax: ' + data.error, 'danger');
            calculateBtn.innerHTML = originalText;
            calculateBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error calculating tax:', error);
        showNotification('Failed to calculate tax liability', 'danger');
        calculateBtn.innerHTML = originalText;
        calculateBtn.disabled = false;
    }
}

function showFinalDeclConfirmation() {
    // Reset checkbox
    document.getElementById('confirmCheckbox').checked = false;
    document.getElementById('confirmSubmitBtn').disabled = true;
    
    // Show modal
    $('#finalDeclConfirmModal').modal('show');
}

async function submitFinalDeclaration() {
    const taxYear = document.getElementById('finalDeclTaxYear').value;
    const calculationId = document.getElementById('calculationId').textContent;
    const confirmBtn = document.getElementById('confirmSubmitBtn');
    const originalText = confirmBtn.innerHTML;
    
    confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
    confirmBtn.disabled = true;
    
    try {
        const response = await fetch('/api/hmrc/final-declaration/submit', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                ...getCSRFHeaders()
            },
            body: JSON.stringify({
                tax_year: taxYear,
                calculation_id: calculationId,
                confirmed: true
            })
        });
        const data = await response.json();
        
        if (data.success) {
            $('#finalDeclConfirmModal').modal('hide');
            showNotification('Final declaration submitted successfully!', 'success');
            loadFinalDeclarationStatus();
        } else {
            showNotification('Failed to submit final declaration: ' + data.error, 'danger');
            confirmBtn.innerHTML = originalText;
            confirmBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error submitting final declaration:', error);
        showNotification('Failed to submit final declaration', 'danger');
        confirmBtn.innerHTML = originalText;
        confirmBtn.disabled = false;
    }
}
