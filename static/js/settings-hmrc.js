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
    
    // Property event listeners
    document.getElementById('fetchPropertyObligationsBtn').addEventListener('click', fetchPropertyObligations);
    document.getElementById('submitPropertyTestBtn').addEventListener('click', submitPropertyTest);
    
    // BSAS event listeners
    document.getElementById('triggerBsasBtn').addEventListener('click', triggerBsas);
    document.getElementById('fetchBsasSummaryBtn').addEventListener('click', fetchBsasSummary);
    
    // Losses event listeners
    document.getElementById('listLossesBtn').addEventListener('click', listLosses);
    document.getElementById('createLossBtn').addEventListener('click', createLoss);
    
    // Export data event listener
    document.getElementById('exportDataBtn').addEventListener('click', exportMyData);
    
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

    // Phase 2.1: open the cumulative submission panel rather than the
    // legacy per-period flow on /expenses. The legacy expenses.js modal
    // is still in place for migration safety but is no longer reachable
    // from this button.
    if (window.HMRCCumulative && typeof window.HMRCCumulative.open === 'function') {
        window.HMRCCumulative.open(periodId, taxYear, endDate);
        return;
    }

    // Defensive fallback: if the cumulative module failed to load, fall
    // back to the legacy expenses.js modal so submission is never blocked.
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
            
            // Set the calculation date in the HMRC disclaimer
            const calcDateElement = document.getElementById('calculationDate');
            if (calcDateElement) {
                const calcDate = data.calculation.calculationTimestamp || data.calculation.timestamp || new Date().toISOString();
                const formattedDate = new Date(calcDate).toLocaleDateString('en-GB', { 
                    day: 'numeric', 
                    month: 'long', 
                    year: 'numeric' 
                });
                calcDateElement.textContent = formattedDate;
            }
            
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

// ============================================================================
// PROPERTY BUSINESS FUNCTIONS
// ============================================================================

async function fetchPropertyObligations() {
    const nino = hmrcConfig.nino || document.getElementById('ninoInput').value;
    
    if (!nino) {
        showNotification('Please enter your NINO first', 'warning');
        return;
    }
    
    const btn = document.getElementById('fetchPropertyObligationsBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Fetching...';
    btn.disabled = true;
    
    try {
        const response = await fetch(`/api/hmrc/property/obligations?nino=${nino}`);
        const data = await response.json();
        
        console.log('Property obligations response:', data);
        
        if (data.success) {
            displayPropertyObligations(data.data);
            showNotification('Property obligations fetched successfully', 'success');
        } else {
            showNotification('Failed to fetch property obligations: ' + (data.error || 'Unknown error'), 'danger');
            document.getElementById('propertyObligationsList').innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i> ${data.error || 'Failed to fetch obligations'}
                </div>
            `;
        }
    } catch (error) {
        console.error('Error fetching property obligations:', error);
        showNotification('Failed to fetch property obligations', 'danger');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function displayPropertyObligations(data) {
    const container = document.getElementById('propertyObligationsList');
    const obligations = data.obligations || [];
    
    console.log('displayPropertyObligations - data:', data);
    console.log('displayPropertyObligations - obligations:', obligations);
    
    if (obligations.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-inbox fa-3x mb-3"></i>
                <p>No property obligations found</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    obligations.forEach(obligation => {
        const details = obligation.obligationDetails || [];
        console.log('Processing obligation:', obligation);
        console.log('Obligation details:', details);
        
        details.forEach(detail => {
            console.log('Detail item:', detail);
            console.log('From date:', detail.inboundCorrespondenceFromDate);
            console.log('To date:', detail.inboundCorrespondenceToDate);
            console.log('Due date:', detail.inboundCorrespondenceDueDate);
            
            const statusClass = detail.status === 'Open' ? 'warning' : 'success';
            html += `
                <div class="card obligation-card ${detail.status.toLowerCase()} mb-3">
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-8">
                                <h6>${detail.periodKey || 'Property Period'}</h6>
                                <p class="mb-1">
                                    <i class="fas fa-calendar"></i> 
                                    ${formatDate(detail.inboundCorrespondenceFromDate)} - ${formatDate(detail.inboundCorrespondenceToDate)}
                                </p>
                                <p class="mb-0">
                                    <i class="fas fa-clock"></i> 
                                    Due: ${formatDate(detail.inboundCorrespondenceDueDate)}
                                </p>
                            </div>
                            <div class="col-md-4 text-right">
                                <span class="badge badge-${statusClass} badge-lg">
                                    ${detail.status}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
    });
    
    container.innerHTML = html;
}

async function submitPropertyTest() {
    const nino = hmrcConfig.nino || document.getElementById('ninoInput').value;
    const taxYear = document.getElementById('propertyTaxYear').value;
    const fromDate = document.getElementById('propertyFromDate').value;
    const toDate = document.getElementById('propertyToDate').value;
    
    if (!nino) {
        showNotification('Please enter your NINO first', 'warning');
        return;
    }
    
    if (!taxYear || !fromDate || !toDate) {
        showNotification('Please fill in all fields', 'warning');
        return;
    }
    
    const btn = document.getElementById('submitPropertyTestBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/hmrc/property/submit', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                ...getCSRFHeaders()
            },
            body: JSON.stringify({
                nino: nino,
                tax_year: taxYear,
                from_date: fromDate,
                to_date: toDate
            })
        });
        const data = await response.json();
        
        const resultDiv = document.getElementById('propertyTestResult');
        resultDiv.style.display = 'block';
        
        if (data.success) {
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <h6><i class="fas fa-check-circle"></i> Test Submission Successful</h6>
                    <p class="mb-0">Property period submitted successfully to HMRC sandbox.</p>
                    ${data.data && data.data.id ? `<p class="mb-0 mt-2"><strong>Period ID:</strong> <code>${data.data.id}</code></p>` : ''}
                </div>
            `;
            showNotification('Property test submission successful!', 'success');
        } else {
            resultDiv.innerHTML = `
                <div class="alert alert-danger">
                    <h6><i class="fas fa-exclamation-circle"></i> Submission Failed</h6>
                    <p class="mb-0">${data.error || 'Unknown error'}</p>
                </div>
            `;
            showNotification('Property test submission failed: ' + (data.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error submitting property test:', error);
        showNotification('Failed to submit property test', 'danger');
        document.getElementById('propertyTestResult').innerHTML = `
            <div class="alert alert-danger">
                <h6><i class="fas fa-exclamation-circle"></i> Error</h6>
                <p class="mb-0">Failed to submit: ${error.message}</p>
            </div>
        `;
        document.getElementById('propertyTestResult').style.display = 'block';
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// ============================================================================
// BSAS (BUSINESS SOURCE ADJUSTABLE SUMMARY) FUNCTIONS
// ============================================================================

let currentBsasId = null;
let currentBsasTaxYear = null;
let currentBsasBusinessType = null;

async function triggerBsas() {
    const nino = hmrcConfig.nino || document.getElementById('ninoInput').value;
    const taxYear = document.getElementById('bsasTaxYear').value;
    const businessType = document.getElementById('bsasBusinessType').value;
    let businessId = document.getElementById('bsasBusinessId').value.trim();
    
    if (!nino) {
        showNotification('Please enter your NINO first', 'warning');
        return;
    }
    
    if (!taxYear) {
        showNotification('Please enter a tax year', 'warning');
        return;
    }
    
    // Use saved business ID if not provided
    if (!businessId) {
        businessId = hmrcConfig.businessId || 'XAIS12345678901';
    }
    
    const btn = document.getElementById('triggerBsasBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Triggering...';
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/hmrc/bsas/trigger', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                ...getCSRFHeaders()
            },
            body: JSON.stringify({
                nino: nino,
                business_id: businessId,
                tax_year: taxYear,
                type_of_business: businessType
            })
        });
        const data = await response.json();
        
        console.log('BSAS trigger response:', data);
        
        if (data.success && data.data) {
            // Extract calculationId (or bsasId for backwards compatibility) from response
            const bsasId = data.data.calculationId || data.data.bsasId || data.data.id;
            
            if (bsasId) {
                currentBsasId = bsasId;
                currentBsasTaxYear = taxYear;  // Store tax year for later use
                currentBsasBusinessType = businessType;  // Store business type for later use
                document.getElementById('bsasIdValue').textContent = bsasId;
                document.getElementById('bsasIdDisplay').style.display = 'block';
                showNotification('BSAS triggered successfully!', 'success');
            } else {
                showNotification('BSAS triggered but no ID returned', 'warning');
                console.log('Full response data:', data.data);
            }
        } else {
            showNotification('Failed to trigger BSAS: ' + (data.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error triggering BSAS:', error);
        showNotification('Failed to trigger BSAS', 'danger');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function fetchBsasSummary() {
    const nino = hmrcConfig.nino || document.getElementById('ninoInput').value;
    
    if (!nino) {
        showNotification('Please enter your NINO first', 'warning');
        return;
    }
    
    if (!currentBsasId) {
        showNotification('No BSAS ID available. Please trigger BSAS first.', 'warning');
        return;
    }
    
    if (!currentBsasBusinessType) {
        showNotification('No business type available. Please trigger BSAS first.', 'warning');
        return;
    }
    
    const btn = document.getElementById('fetchBsasSummaryBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Fetching...';
    btn.disabled = true;
    
    try {
        const response = await fetch(`/api/hmrc/bsas/${currentBsasId}?nino=${nino}&type_of_business=${currentBsasBusinessType}`);
        const data = await response.json();
        
        console.log('BSAS summary response:', data);
        
        if (data.success && data.data) {
            displayBsasSummary(data.data);
            showNotification('BSAS summary fetched successfully', 'success');
        } else {
            showNotification('Failed to fetch BSAS summary: ' + (data.error || 'Unknown error'), 'danger');
            document.getElementById('bsasSummaryDisplay').innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle"></i> ${data.error || 'Failed to fetch summary'}
                </div>
            `;
        }
    } catch (error) {
        console.error('Error fetching BSAS summary:', error);
        showNotification('Failed to fetch BSAS summary', 'danger');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function displayBsasSummary(data) {
    const container = document.getElementById('bsasSummaryDisplay');
    
    console.log('Displaying BSAS summary:', data);
    
    // Build summary display
    let html = '<div class="card"><div class="card-body">';
    
    // Metadata
    if (data.metadata) {
        html += '<h6>Summary Information</h6>';
        html += '<table class="table table-sm table-bordered">';
        if (data.metadata.typeOfBusiness) {
            html += `<tr><th>Business Type:</th><td>${data.metadata.typeOfBusiness}</td></tr>`;
        }
        if (data.metadata.businessId) {
            html += `<tr><th>Business ID:</th><td><code>${data.metadata.businessId}</code></td></tr>`;
        }
        if (data.metadata.taxYear) {
            html += `<tr><th>Tax Year:</th><td>${data.metadata.taxYear}</td></tr>`;
        }
        if (data.metadata.requestedDateTime) {
            html += `<tr><th>Generated:</th><td>${new Date(data.metadata.requestedDateTime).toLocaleString()}</td></tr>`;
        }
        html += '</table>';
    }
    
    // Income and Expenses Summary
    if (data.inputs) {
        html += '<hr><h6>Income & Expenses Summary</h6>';
        html += '<div class="row">';
        
        // Income
        if (data.inputs.incomeSourceType === 'self-employment' && data.inputs.businessIncome) {
            html += '<div class="col-md-6">';
            html += '<h6 class="text-success">Income</h6>';
            html += '<table class="table table-sm">';
            const income = data.inputs.businessIncome;
            if (income.turnover !== undefined) html += `<tr><td>Turnover:</td><td class="text-right">£${income.turnover.toFixed(2)}</td></tr>`;
            if (income.other !== undefined) html += `<tr><td>Other Income:</td><td class="text-right">£${income.other.toFixed(2)}</td></tr>`;
            html += '</table>';
            html += '</div>';
        }
        
        // Expenses
        if (data.inputs.incomeSourceType === 'self-employment' && data.inputs.businessExpenses) {
            html += '<div class="col-md-6">';
            html += '<h6 class="text-danger">Expenses</h6>';
            html += '<table class="table table-sm">';
            const expenses = data.inputs.businessExpenses;
            if (expenses.costOfGoodsBought !== undefined) html += `<tr><td>Cost of Goods:</td><td class="text-right">£${expenses.costOfGoodsBought.toFixed(2)}</td></tr>`;
            if (expenses.cisPaymentsToSubcontractors !== undefined) html += `<tr><td>Subcontractors:</td><td class="text-right">£${expenses.cisPaymentsToSubcontractors.toFixed(2)}</td></tr>`;
            if (expenses.staffCosts !== undefined) html += `<tr><td>Staff Costs:</td><td class="text-right">£${expenses.staffCosts.toFixed(2)}</td></tr>`;
            if (expenses.travelCosts !== undefined) html += `<tr><td>Travel:</td><td class="text-right">£${expenses.travelCosts.toFixed(2)}</td></tr>`;
            if (expenses.premisesRunningCosts !== undefined) html += `<tr><td>Premises:</td><td class="text-right">£${expenses.premisesRunningCosts.toFixed(2)}</td></tr>`;
            if (expenses.other !== undefined) html += `<tr><td>Other:</td><td class="text-right">£${expenses.other.toFixed(2)}</td></tr>`;
            html += '</table>';
            html += '</div>';
        }
        
        html += '</div>';
    }
    
    // Full JSON for debugging
    html += '<hr><details><summary>Full Response (JSON)</summary>';
    html += `<pre class="bg-light p-3" style="max-height: 400px; overflow-y: auto;">${JSON.stringify(data, null, 2)}</pre>`;
    html += '</details>';
    
    html += '</div></div>';
    
    container.innerHTML = html;
}

// ============================================================================
// LOSSES (INDIVIDUAL LOSSES) FUNCTIONS
// ============================================================================

async function listLosses() {
    const nino = hmrcConfig.nino || document.getElementById('ninoInput').value;
    
    if (!nino) {
        showNotification('Please enter your NINO first', 'warning');
        return;
    }
    
    const btn = document.getElementById('listLossesBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
    btn.disabled = true;
    
    try {
        const response = await fetch(`/api/hmrc/losses/list?nino=${nino}`);
        const data = await response.json();
        
        console.log('Losses list response:', data);
        
        if (data.success && data.data) {
            displayLossesList(data.data);
            showNotification('Losses fetched successfully', 'success');
        } else {
            showNotification('Failed to fetch losses: ' + (data.error || 'Unknown error'), 'danger');
            document.getElementById('lossesListDisplay').innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i> ${data.error || 'Failed to fetch losses'}
                </div>
            `;
        }
    } catch (error) {
        console.error('Error fetching losses:', error);
        showNotification('Failed to fetch losses', 'danger');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function displayLossesList(data) {
    const container = document.getElementById('lossesListDisplay');
    const losses = data.losses || [];
    
    console.log('Displaying losses:', losses);
    
    if (losses.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-inbox fa-3x mb-3"></i>
                <p>No brought forward losses found</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="table-responsive"><table class="table table-striped table-hover">';
    html += '<thead><tr>';
    html += '<th>Loss ID</th>';
    html += '<th>Tax Year From</th>';
    html += '<th>Type of Loss</th>';
    html += '<th>Business ID</th>';
    html += '<th>Loss Amount</th>';
    html += '<th>Last Modified</th>';
    html += '</tr></thead><tbody>';
    
    losses.forEach(loss => {
        html += '<tr>';
        html += `<td><code>${loss.lossId || 'N/A'}</code></td>`;
        html += `<td>${loss.taxYearBroughtForwardFrom || 'N/A'}</td>`;
        html += `<td><span class="badge badge-info">${loss.typeOfLoss || 'N/A'}</span></td>`;
        html += `<td><code>${loss.businessId || 'N/A'}</code></td>`;
        html += `<td class="text-right"><strong>£${(loss.lossAmount || 0).toFixed(2)}</strong></td>`;
        html += `<td>${loss.lastModified ? new Date(loss.lastModified).toLocaleDateString() : 'N/A'}</td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    
    container.innerHTML = html;
}

async function createLoss() {
    const nino = hmrcConfig.nino || document.getElementById('ninoInput').value;
    const taxYear = document.getElementById('lossTaxYear').value;
    const lossType = document.getElementById('lossType').value;
    const lossAmount = document.getElementById('lossAmount').value;
    let businessId = document.getElementById('lossBusinessId').value.trim();
    
    if (!nino) {
        showNotification('Please enter your NINO first', 'warning');
        return;
    }
    
    if (!taxYear) {
        showNotification('Please enter a tax year', 'warning');
        return;
    }
    
    if (!lossAmount || parseFloat(lossAmount) <= 0) {
        showNotification('Please enter a valid loss amount', 'warning');
        return;
    }
    
    // Use saved business ID if not provided
    if (!businessId) {
        businessId = hmrcConfig.businessId || 'XBIS12345678901';
    }
    
    const btn = document.getElementById('createLossBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/hmrc/losses/create', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                ...getCSRFHeaders()
            },
            body: JSON.stringify({
                nino: nino,
                tax_year: taxYear,
                type_of_loss: lossType,
                business_id: businessId,
                loss_amount: parseFloat(lossAmount)
            })
        });
        const data = await response.json();
        
        console.log('Create loss response:', data);
        
        const resultDiv = document.getElementById('createLossResult');
        resultDiv.style.display = 'block';
        
        if (data.success && data.data) {
            const lossId = data.data.lossId || data.data.id;
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <h6><i class="fas fa-check-circle"></i> Loss Created Successfully</h6>
                    <p class="mb-0">Loss has been recorded in HMRC sandbox.</p>
                    ${lossId ? `<p class="mb-0 mt-2"><strong>Loss ID:</strong> <code>${lossId}</code></p>` : ''}
                </div>
            `;
            showNotification('Loss created successfully!', 'success');
            
            // Refresh the losses list
            setTimeout(() => listLosses(), 1000);
        } else {
            resultDiv.innerHTML = `
                <div class="alert alert-danger">
                    <h6><i class="fas fa-exclamation-circle"></i> Creation Failed</h6>
                    <p class="mb-0">${data.error || 'Unknown error'}</p>
                </div>
            `;
            showNotification('Failed to create loss: ' + (data.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error creating loss:', error);
        showNotification('Failed to create loss', 'danger');
        document.getElementById('createLossResult').innerHTML = `
            <div class="alert alert-danger">
                <h6><i class="fas fa-exclamation-circle"></i> Error</h6>
                <p class="mb-0">Failed to create: ${error.message}</p>
            </div>
        `;
        document.getElementById('createLossResult').style.display = 'block';
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// ============================================================================
// DATA EXPORT FUNCTION
// ============================================================================

async function exportMyData() {
    const btn = document.getElementById('exportDataBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Exporting...';
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/hmrc/export');
        
        if (!response.ok) {
            throw new Error('Export failed');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `hmrc-mtd-data-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showNotification('Data exported successfully', 'success');
    } catch (error) {
        console.error('Error exporting data:', error);
        showNotification('Failed to export data', 'danger');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}
