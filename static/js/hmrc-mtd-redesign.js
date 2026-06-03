/**
 * HMRC MTD Redesigned Page JavaScript
 * User-facing, task-driven interface for Making Tax Digital ITSA
 */

// Tax year configuration
const TAX_YEAR = '2026-27';
const TAX_YEAR_START = new Date('2026-04-06');
const TAX_YEAR_END = new Date('2027-04-05');

// Quarter definitions (standard MTD ITSA periods)
const QUARTERS = [
    {
        quarter: 1,
        label: 'Q1',
        startDate: new Date('2026-04-06'),
        endDate: new Date('2026-07-05'),
        deadline: new Date('2026-08-07'),
        dateRangeDisplay: '6 Apr – 5 Jul',
        deadlineDisplay: '7 Aug'
    },
    {
        quarter: 2,
        label: 'Q2',
        startDate: new Date('2026-07-06'),
        endDate: new Date('2026-10-05'),
        deadline: new Date('2026-11-07'),
        dateRangeDisplay: '6 Jul – 5 Oct',
        deadlineDisplay: '7 Nov'
    },
    {
        quarter: 3,
        label: 'Q3',
        startDate: new Date('2026-10-06'),
        endDate: new Date('2027-01-05'),
        deadline: new Date('2027-02-07'),
        dateRangeDisplay: '6 Oct – 5 Jan',
        deadlineDisplay: '7 Feb'
    },
    {
        quarter: 4,
        label: 'Q4',
        startDate: new Date('2027-01-06'),
        endDate: new Date('2027-04-05'),
        deadline: new Date('2027-05-07'),
        dateRangeDisplay: '6 Jan – 5 Apr',
        deadlineDisplay: '7 May'
    }
];

// State
let connectionStatus = null;
let obligations = null;
let currentQuarter = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializePage();
});

async function initializePage() {
    // Load connection status
    await loadConnectionStatus();
    
    // Determine current quarter
    determineCurrentQuarter();
    
    // Update UI based on current state
    updateQuarterlyCards();
    updateStatusBar();
    updateMetadataStrip();
    
    // Setup event listeners
    setupEventListeners();
    
    // Load obligations if connected
    if (connectionStatus && connectionStatus.connected) {
        await loadObligations();
    }
}

function setupEventListeners() {
    // Quarter action buttons
    document.querySelectorAll('.quarter-action-btn').forEach(btn => {
        btn.addEventListener('click', handleQuarterAction);
    });
    
    // Final declaration button
    const finalDeclBtn = document.getElementById('viewFinalDeclarationBtn');
    if (finalDeclBtn) {
        finalDeclBtn.addEventListener('click', showFinalDeclaration);
    }
}

async function loadConnectionStatus() {
    try {
        const response = await fetch('/api/hmrc/auth/status');
        const data = await response.json();
        
        connectionStatus = data.success ? data.data : data;
        
        // Show sandbox warning if not in production
        if (connectionStatus.environment !== 'production') {
            document.getElementById('sandboxWarning').classList.remove('d-none');
        }
        
    } catch (error) {
        console.error('Error loading connection status:', error);
        connectionStatus = {
            connected: false,
            environment: 'sandbox',
            message: 'Unable to check connection status'
        };
    }
}

async function loadObligations() {
    try {
        const response = await fetch('/api/hmrc/obligations');
        const data = await response.json();
        
        if (data.success) {
            obligations = data.data;
            updateQuarterlyCardsWithObligations();
        }
    } catch (error) {
        console.error('Error loading obligations:', error);
    }
}

function determineCurrentQuarter() {
    const today = new Date();
    
    // Find which quarter we're currently in
    for (let i = 0; i < QUARTERS.length; i++) {
        const q = QUARTERS[i];
        if (today >= q.startDate && today <= q.endDate) {
            currentQuarter = q.quarter;
            return;
        }
    }
    
    // If we're before Q1 or after Q4, determine based on proximity
    if (today < QUARTERS[0].startDate) {
        currentQuarter = null; // Before tax year starts
    } else if (today > QUARTERS[3].endDate) {
        currentQuarter = null; // After tax year ends
    }
}

function updateQuarterlyCards() {
    // Cards are now statically rendered with Bootstrap classes
    // This function only updates them if we have obligations data
    // The initial state shows Q1 as Open, Q2-Q4 as Future with "Opens [date]" labels
}

function updateQuarterlyCardsWithObligations() {
    if (!obligations || !obligations.obligations) return;
    
    // Map obligations to quarters
    obligations.obligations.forEach(obl => {
        // Find matching quarter based on period
        const quarter = findQuarterForObligation(obl);
        if (quarter) {
            const statusBadge = document.getElementById(`q${quarter}Status`);
            const actionBtn = document.querySelector(`#q${quarter}Card .quarter-action-btn`);
            
            if (obl.status === 'F') {
                // Fulfilled/Submitted
                statusBadge.className = 'badge bg-primary';
                statusBadge.textContent = 'Submitted';
                
                actionBtn.className = 'btn btn-outline-primary w-100 quarter-action-btn';
                actionBtn.innerHTML = '<i class="fas fa-eye me-1"></i>View Submission';
                actionBtn.disabled = false;
                actionBtn.dataset.status = 'submitted';
            } else if (obl.status === 'O') {
                // Open
                statusBadge.className = 'badge bg-success';
                statusBadge.textContent = 'Open';
                
                actionBtn.className = 'btn btn-primary w-100 quarter-action-btn';
                actionBtn.innerHTML = '<i class="fas fa-edit me-1"></i>Prepare Update';
                actionBtn.disabled = false;
                actionBtn.dataset.status = 'open';
            }
        }
    });
}

function findQuarterForObligation(obligation) {
    // Parse obligation period and match to quarter
    // HMRC format: "2026-04-06" to "2026-07-05"
    const oblStart = new Date(obligation.start);
    
    for (let i = 0; i < QUARTERS.length; i++) {
        const q = QUARTERS[i];
        if (oblStart.getTime() === q.startDate.getTime()) {
            return q.quarter;
        }
    }
    
    return null;
}

function updateStatusBar() {
    // Update tax year display
    document.getElementById('taxYearDisplay').textContent = TAX_YEAR;
    document.getElementById('taxYearDates').textContent = '6 Apr 2026 – 5 Apr 2027';
    
    // Update current quarter badge - Q1 is currently open
    const quarterBadge = document.getElementById('currentQuarterBadge');
    quarterBadge.innerHTML = '<i class="fas fa-calendar-check me-1"></i>Q1 Open';
    quarterBadge.className = 'badge bg-light text-dark';
    
    // Update credential badge based on real connection status
    const credBadge = document.getElementById('credentialBadge');
    if (connectionStatus && connectionStatus.connected) {
        credBadge.innerHTML = '<i class="fas fa-check-circle me-1"></i>Connected';
        credBadge.className = 'badge bg-success';
    } else {
        credBadge.innerHTML = '<i class="fas fa-times-circle me-1"></i>Not Connected';
        credBadge.className = 'badge bg-danger';
    }
    
    // Update environment badge
    const envBadge = document.getElementById('environmentBadge');
    const env = connectionStatus ? connectionStatus.environment : 'sandbox';
    if (env === 'production') {
        envBadge.textContent = 'Production';
        envBadge.className = 'badge bg-success';
    } else {
        envBadge.textContent = 'Sandbox';
        envBadge.className = 'badge bg-warning text-dark';
    }
}

function updateMetadataStrip() {
    // Environment
    const metaEnv = document.getElementById('metaEnvironment');
    const env = connectionStatus ? connectionStatus.environment : 'sandbox';
    if (env === 'production') {
        metaEnv.innerHTML = '<span class="badge bg-success">Production</span>';
    } else {
        metaEnv.innerHTML = '<span class="badge bg-warning text-dark">Sandbox</span>';
    }
    
    // Authorisation - use real connection status
    const metaAuth = document.getElementById('metaAuth');
    if (connectionStatus && connectionStatus.connected) {
        metaAuth.innerHTML = '<i class="fas fa-check-circle text-success me-1"></i><span>Connected</span>';
    } else {
        metaAuth.innerHTML = '<i class="fas fa-times-circle text-danger me-1"></i><span>Not Connected</span>';
    }
    
    // Fraud prevention headers - always active in this implementation
    const metaFraud = document.getElementById('metaFraud');
    metaFraud.innerHTML = '<i class="fas fa-check-circle text-success me-1"></i><span>Active</span>';
}

function handleQuarterAction(event) {
    const btn = event.currentTarget;
    const quarter = parseInt(btn.dataset.quarter);
    const status = btn.dataset.status;
    
    if (status === 'open') {
        // Open quarterly submission modal
        showQuarterlySubmissionModal(quarter);
    } else if (status === 'submitted') {
        // Show submission details
        showSubmissionDetails(quarter);
    }
}

function showQuarterlySubmissionModal(quarter) {
    const modal = new bootstrap.Modal(document.getElementById('quarterlySubmissionModal'));
    const modalTitle = document.querySelector('#quarterlySubmissionModalLabel');
    const modalContent = document.getElementById('quarterlySubmissionContent');
    
    const q = QUARTERS[quarter - 1];
    modalTitle.innerHTML = `<i class="fas fa-edit me-2"></i>Prepare Q${quarter} Update (${q.dateRangeDisplay})`;
    
    // Load cumulative data for this quarter
    modalContent.innerHTML = `
        <div class="text-center py-5">
            <i class="fas fa-spinner fa-spin fa-3x text-muted mb-3"></i>
            <p class="text-muted">Loading cumulative data for Q${quarter}...</p>
        </div>
    `;
    
    modal.show();
    
    // Load the actual quarterly submission form
    loadQuarterlySubmissionForm(quarter, modalContent);
}

async function loadQuarterlySubmissionForm(quarter, container) {
    try {
        const q = QUARTERS[quarter - 1];
        
        // Fetch cumulative data from API
        const response = await fetch(`/api/hmrc/cumulative-data?start=${q.startDate.toISOString().split('T')[0]}&end=${q.endDate.toISOString().split('T')[0]}`);
        const data = await response.json();
        
        if (data.success) {
            // Render the cumulative submission form
            renderCumulativeForm(container, quarter, data.data);
        } else {
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Failed to load quarterly data: ${data.error || 'Unknown error'}
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading quarterly submission form:', error);
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Error loading quarterly data. Please try again.
            </div>
        `;
    }
}

function renderCumulativeForm(container, quarter, cumulativeData) {
    const q = QUARTERS[quarter - 1];
    
    container.innerHTML = `
        <div class="cumulative-submission-form">
            <div class="alert alert-info mb-4">
                <strong><i class="fas fa-info-circle me-2"></i>Cumulative Submission</strong>
                <p class="mb-0 mt-2">This update includes all income and expenses from 6 April to ${q.endDate.toLocaleDateString('en-GB')}.</p>
            </div>
            
            <div class="row g-3 mb-4">
                <div class="col-12 col-md-6">
                    <div class="summary-card">
                        <div class="summary-label">Cumulative Turnover</div>
                        <div class="summary-value">£${(cumulativeData.turnover || 0).toFixed(2)}</div>
                    </div>
                </div>
                <div class="col-12 col-md-6">
                    <div class="summary-card">
                        <div class="summary-label">Cumulative Expenses</div>
                        <div class="summary-value">£${(cumulativeData.expenses || 0).toFixed(2)}</div>
                    </div>
                </div>
            </div>
            
            <h6 class="mb-3">Expense Breakdown</h6>
            <div class="table-responsive mb-4">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Category</th>
                            <th class="text-end">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${renderExpenseRows(cumulativeData.expense_breakdown || {})}
                    </tbody>
                </table>
            </div>
            
            <div class="form-check mb-4">
                <input type="checkbox" class="form-check-input" id="confirmSubmission">
                <label class="form-check-label" for="confirmSubmission">
                    I confirm these cumulative totals are correct and I want to submit them to HMRC.
                </label>
            </div>
            
            <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-primary" id="submitQuarterBtn" disabled>
                    <i class="fas fa-paper-plane me-1"></i>Submit to HMRC
                </button>
            </div>
        </div>
    `;
    
    // Enable submit button when checkbox is checked
    document.getElementById('confirmSubmission').addEventListener('change', function() {
        document.getElementById('submitQuarterBtn').disabled = !this.checked;
    });
    
    // Handle submit
    document.getElementById('submitQuarterBtn').addEventListener('click', function() {
        submitQuarterlyUpdate(quarter, cumulativeData);
    });
}

function renderExpenseRows(expenseBreakdown) {
    if (!expenseBreakdown || Object.keys(expenseBreakdown).length === 0) {
        return '<tr><td colspan="2" class="text-muted text-center">No expenses</td></tr>';
    }
    
    return Object.entries(expenseBreakdown)
        .map(([category, amount]) => `
            <tr>
                <td>${category}</td>
                <td class="text-end">£${amount.toFixed(2)}</td>
            </tr>
        `)
        .join('');
}

async function submitQuarterlyUpdate(quarter, data) {
    const btn = document.getElementById('submitQuarterBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Submitting...';
    
    try {
        const q = QUARTERS[quarter - 1];
        
        const response = await fetch('/api/hmrc/submit-period', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getCSRFHeaders()
            },
            body: JSON.stringify({
                quarter: quarter,
                start_date: q.startDate.toISOString().split('T')[0],
                end_date: q.endDate.toISOString().split('T')[0],
                data: data
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(`Q${quarter} submitted successfully!`, 'success');
            bootstrap.Modal.getInstance(document.getElementById('quarterlySubmissionModal')).hide();
            
            // Refresh the page to update cards
            await loadObligations();
            updateQuarterlyCards();
        } else {
            showNotification(`Submission failed: ${result.error}`, 'danger');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-paper-plane me-1"></i>Submit to HMRC';
        }
    } catch (error) {
        console.error('Error submitting quarterly update:', error);
        showNotification('Error submitting quarterly update', 'danger');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-paper-plane me-1"></i>Submit to HMRC';
    }
}

function showSubmissionDetails(quarter) {
    // Show details of a submitted quarter
    showNotification(`Viewing submission details for Q${quarter}`, 'info');
    // TODO: Implement submission details view
}

function showFinalDeclaration() {
    const modal = new bootstrap.Modal(document.getElementById('finalDeclarationModal'));
    const modalContent = document.getElementById('finalDeclarationContent');
    
    // Load final declaration content
    modalContent.innerHTML = `
        <div class="alert alert-info">
            <strong><i class="fas fa-info-circle me-2"></i>Final Declaration Requirements</strong>
            <p class="mb-0 mt-2">All four quarterly updates must be submitted before you can complete your final declaration.</p>
        </div>
        
        <h6 class="mb-3">Checklist</h6>
        <ul class="list-group mb-4">
            <li class="list-group-item">
                <i class="fas fa-square text-muted me-2"></i>Q1 Submitted
            </li>
            <li class="list-group-item">
                <i class="fas fa-square text-muted me-2"></i>Q2 Submitted
            </li>
            <li class="list-group-item">
                <i class="fas fa-square text-muted me-2"></i>Q3 Submitted
            </li>
            <li class="list-group-item">
                <i class="fas fa-square text-muted me-2"></i>Q4 Submitted
            </li>
            <li class="list-group-item">
                <i class="fas fa-square text-muted me-2"></i>BSAS Adjustments Reviewed
            </li>
            <li class="list-group-item">
                <i class="fas fa-square text-muted me-2"></i>Losses Declared
            </li>
        </ul>
        
        <p class="text-muted">Once all requirements are met, you'll be able to submit your final declaration.</p>
    `;
    
    modal.show();
}

// Helper function for CSRF headers
function getCSRFHeaders() {
    const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    return token ? { 'X-CSRFToken': token } : {};
}

// Helper function for notifications
function showNotification(message, type = 'info') {
    // Use existing notification system if available
    if (typeof window.showNotification === 'function') {
        window.showNotification(message, type);
    } else {
        // Fallback to console
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}
