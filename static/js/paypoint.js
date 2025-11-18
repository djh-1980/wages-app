/**
 * Paypoint Device Management JavaScript
 * Updated for device-based tracking system
 */

// Global variables
let devices = [];
let currentDeployments = [];
let currentReturns = [];
let currentAuditHistory = [];

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializePaypoint();
    
    // Reset Use Stock modal when it's closed
    const useStockModal = document.getElementById('useStockModal');
    if (useStockModal) {
        useStockModal.addEventListener('hidden.bs.modal', function() {
            resetUseStockModal();
        });
    }
});

/**
 * Initialize Paypoint system
 */
async function initializePaypoint() {
    try {
        // Initialize database tables first
        await initializeTables();
        
        // Load initial data
        await loadSummary();
        await loadDevices();
        await loadDeployments();
        await loadReturns();
        await loadAuditHistory();
        
        // Set up event listeners
        setupEventListeners();
        
        // Set up job number auto-fill
        setupJobNumberAutoFill();
        
        console.log('Paypoint system initialized successfully');
    } catch (error) {
        console.error('Error initializing Paypoint system:', error);
        showError('Failed to initialize Paypoint system');
    }
}

/**
 * Setup job number auto-fill from runsheets
 */
function setupJobNumberAutoFill() {
    // Set up event listener when deploy modal is shown
    const deployModal = document.getElementById('deployModal');
    if (deployModal) {
        deployModal.addEventListener('shown.bs.modal', function() {
            const jobNumberInput = document.getElementById('deployJobNumber');
            if (jobNumberInput && !jobNumberInput.dataset.listenerAttached) {
                // Mark as attached to avoid duplicate listeners
                jobNumberInput.dataset.listenerAttached = 'true';
                
                jobNumberInput.addEventListener('blur', async function() {
                    const jobNumber = this.value.trim();
                    if (jobNumber) {
                        await fetchJobDetails(jobNumber);
                    }
                });
                
                // Also trigger on Enter key
                jobNumberInput.addEventListener('keypress', async function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        const jobNumber = this.value.trim();
                        if (jobNumber) {
                            await fetchJobDetails(jobNumber);
                        }
                    }
                });
            }
        });
    }
}

/**
 * Fetch job details from runsheets and auto-fill form
 */
async function fetchJobDetails(jobNumber) {
    try {
        console.log('Fetching job details for:', jobNumber);
        const response = await fetch(`/api/search/job/${jobNumber}`);
        if (!response.ok) {
            console.log('Job not found in runsheets');
            return;
        }
        
        const data = await response.json();
        console.log('Job search response:', data);
        
        if (data && data.found && data.runsheets && data.runsheets.length > 0) {
            // Get the most recent job entry from runsheets
            const job = data.runsheets[0];
            
            // Auto-fill customer and location
            const customerInput = document.getElementById('deployCustomer');
            const locationInput = document.getElementById('deployLocation');
            
            if (customerInput && job.customer) {
                customerInput.value = job.customer;
                console.log('Customer filled:', job.customer);
            }
            
            if (locationInput && job.address) {
                locationInput.value = job.address;
                console.log('Location filled:', job.address);
            }
            
            // Show success feedback
            const jobNumberInput = document.getElementById('deployJobNumber');
            if (jobNumberInput) {
                jobNumberInput.classList.add('is-valid');
                setTimeout(() => jobNumberInput.classList.remove('is-valid'), 2000);
            }
            
            console.log('Job details auto-filled from runsheet');
        } else {
            console.log('No runsheet data found for job:', jobNumber);
        }
    } catch (error) {
        console.error('Error fetching job details:', error);
        // Don't show error to user - just fail silently if job not found
    }
}

/**
 * Initialize database tables
 */
async function initializeTables() {
    try {
        const response = await fetch('/api/paypoint/initialize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Failed to initialize tables');
        }
    } catch (error) {
        console.error('Error initializing tables:', error);
        // Don't throw here as tables might already exist
    }
}

/**
 * Load summary statistics
 */
async function loadSummary() {
    try {
        const response = await fetch('/api/paypoint/summary');
        const data = await response.json();
        
        if (data.success) {
            updateSummaryCards(data.summary);
        }
    } catch (error) {
        console.error('Error loading summary:', error);
    }
}

/**
 * Update summary cards
 */
function updateSummaryCards(summary) {
    document.getElementById('totalDevices').textContent = summary.total_devices || 0;
    document.getElementById('availableDevices').textContent = summary.available_devices || 0;
    const returnedEl = document.getElementById('returnedDevices');
    if (returnedEl) {
        returnedEl.textContent = summary.returned_devices || 0;
    }
}

/**
 * Load devices
 */
async function loadDevices() {
    try {
        const response = await fetch('/api/paypoint/stock');
        const data = await response.json();
        
        if (data.success) {
            devices = data.items;
            updateDevicesTable();
            updateDeviceSelects();
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('Error loading devices:', error);
        showError('Failed to load devices');
    }
}

/**
 * Update devices table - only show available stock
 */
function updateDevicesTable() {
    const tbody = document.getElementById('devicesTableBody');
    const stockCount = document.getElementById('stockCount');
    
    // Filter to only show available stock (not returned)
    const availableStock = devices.filter(d => d.status === 'available');
    
    // Update count badge
    if (stockCount) {
        stockCount.textContent = `${availableStock.length} item${availableStock.length !== 1 ? 's' : ''}`;
    }
    
    if (availableStock.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted" style="padding: 3rem;">
                    <i class="bi bi-inbox" style="font-size: 3rem; opacity: 0.3;"></i>
                    <p class="mt-2 mb-0">No stock available</p>
                    <small>Click "Add Stock" to add devices to your van</small>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = availableStock.map(device => `
        <tr style="border-bottom: 1px solid #f0f0f0;">
            <td style="font-weight: 500;">${device.paypoint_type}</td>
            <td><code style="background: #f8f9fa; padding: 0.25rem 0.5rem; border-radius: 4px;">${device.serial_ptid}</code></td>
            <td><span class="badge" style="background: linear-gradient(135deg, #17a2b8, #138496); font-size: 0.85rem;">${device.trace_stock}</span></td>
            <td><span class="badge bg-success" style="font-size: 0.85rem;">Available</span></td>
            <td style="color: #6c757d;">${device.notes || '-'}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="editStock(${device.id})" title="Edit">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteStock(${device.id})" title="Delete">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

/**
 * Get status badge class
 */
function getStatusBadgeClass(status) {
    switch(status) {
        case 'available': return 'bg-success';
        case 'deployed': return 'bg-warning';
        case 'returned': return 'bg-info';
        default: return 'bg-secondary';
    }
}

/**
 * Update device select dropdowns
 */
function updateDeviceSelects() {
    // Update available devices for deployment
    const deploySelect = document.getElementById('deployDeviceSelect');
    if (deploySelect) {
        const availableDevices = devices.filter(device => device.status === 'available');
        deploySelect.innerHTML = '<option value="">Select device...</option>' +
            availableDevices.map(device => 
                `<option value="${device.id}">${device.paypoint_type} - ${device.serial_ptid}</option>`
            ).join('');
    }
    
    // Update deployed devices for returns
    const returnSelect = document.getElementById('returnDeploymentSelect');
    if (returnSelect) {
        const deployedDevices = devices.filter(device => device.status === 'deployed');
        returnSelect.innerHTML = '<option value="">Select deployed device...</option>' +
            deployedDevices.map(device => 
                `<option value="${device.id}">${device.paypoint_type} - ${device.serial_ptid} (Job: ${device.current_job_number})</option>`
            ).join('');
    }
}

/**
 * Load deployments
 */
async function loadDeployments() {
    try {
        const response = await fetch('/api/paypoint/deployments');
        const data = await response.json();
        
        if (data.success) {
            currentDeployments = data.deployments;
            updateDeploymentsTable();
        }
    } catch (error) {
        console.error('Error loading deployments:', error);
    }
}

/**
 * Update deployments table
 */
function updateDeploymentsTable() {
    const tbody = document.getElementById('deploymentsTableBody');
    
    // If table doesn't exist on this page, skip
    if (!tbody) {
        return;
    }
    
    if (currentDeployments.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted">
                    No deployments recorded yet.
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = currentDeployments.map(deployment => `
        <tr>
            <td>${formatDate(deployment.deployment_date)}</td>
            <td><strong>${deployment.job_number}</strong></td>
            <td>${deployment.paypoint_type}</td>
            <td><code>${deployment.serial_ptid}</code></td>
            <td><span class="badge bg-secondary">${deployment.trace_stock}</span></td>
            <td>${deployment.customer || '-'}</td>
            <td>
                <span class="badge ${deployment.status === 'deployed' ? 'bg-warning' : 'bg-info'}">
                    ${deployment.status.toUpperCase()}
                </span>
            </td>
            <td>
                ${deployment.status === 'deployed' ? 
                    `<button class="btn btn-sm btn-warning" onclick="returnFromDeployment(${deployment.id})">
                        <i class="bi bi-arrow-down-circle"></i> Return
                    </button>` : '-'
                }
            </td>
        </tr>
    `).join('');
}

/**
 * Load returns
 */
async function loadReturns() {
    try {
        console.log('Loading returns...');
        const response = await fetch('/api/paypoint/returns');
        const data = await response.json();
        console.log('Returns API response:', data);
        
        if (data.success) {
            currentReturns = data.returns;
            console.log('Current returns:', currentReturns);
            updateReturnsTable();
        }
    } catch (error) {
        console.error('Error loading returns:', error);
    }
}

/**
 * Update returns table
 */
function updateReturnsTable() {
    const tbody = document.getElementById('returnsTableBody');
    const returnsCount = document.getElementById('returnsCount');
    
    if (!tbody) {
        console.error('returnsTableBody element not found!');
        return;
    }
    
    // Update count badge
    if (returnsCount) {
        returnsCount.textContent = `${currentReturns.length} return${currentReturns.length !== 1 ? 's' : ''}`;
    }
    
    if (currentReturns.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted" style="padding: 3rem;">
                    <i class="bi bi-archive" style="font-size: 3rem; opacity: 0.3;"></i>
                    <p class="mt-2 mb-0">No returns recorded yet</p>
                    <small>Returns will appear here when you use stock</small>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = currentReturns.map(returnItem => {
        // Show both original and returned TID if different
        let tidDisplay = `<code style="background: #f8f9fa; padding: 0.25rem 0.5rem; border-radius: 4px; color: #d63384;">${returnItem.return_serial_ptid}</code>`;
        if (returnItem.original_tid && returnItem.original_tid !== returnItem.return_serial_ptid) {
            tidDisplay = `
                <div style="font-size: 0.75rem; color: #6c757d; margin-bottom: 2px;">Original: <code style="background: #fff3cd; padding: 0.15rem 0.4rem; border-radius: 3px; color: #856404;">${returnItem.original_tid}</code></div>
                <div style="font-size: 0.75rem; color: #6c757d;">Returned: <code style="background: #d1ecf1; padding: 0.15rem 0.4rem; border-radius: 3px; color: #0c5460;">${returnItem.return_serial_ptid}</code></div>
            `;
        }
        
        // Show both original and returned trace if different
        let traceDisplay = `<span class="badge" style="background: linear-gradient(135deg, #17a2b8, #138496); font-size: 0.85rem;">${returnItem.return_trace}</span>`;
        if (returnItem.original_trace && returnItem.original_trace !== returnItem.return_trace) {
            traceDisplay = `
                <div style="margin-bottom: 3px;"><span class="badge bg-secondary" style="font-size: 0.75rem;">${returnItem.original_trace}</span></div>
                <div><span class="badge" style="background: linear-gradient(135deg, #17a2b8, #138496); font-size: 0.75rem;">${returnItem.return_trace}</span></div>
            `;
        }
        
        return `
            <tr style="border-bottom: 1px solid #f0f0f0;">
                <td>${formatDate(returnItem.return_date)}</td>
                <td><strong style="color: #0d6efd;">${returnItem.job_number}</strong></td>
                <td style="font-weight: 500;">${returnItem.paypoint_type}</td>
                <td>${tidDisplay}</td>
                <td>${traceDisplay}</td>
                <td style="color: #6c757d;">${returnItem.location || '-'}</td>
                <td><span class="badge bg-secondary" style="font-size: 0.85rem;">${returnItem.return_reason || '-'}</span></td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="editReturn(${returnItem.id})" title="Edit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteReturn(${returnItem.id})" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * Load audit history
 */
async function loadAuditHistory() {
    try {
        const response = await fetch('/api/paypoint/audit');
        const data = await response.json();
        
        if (data.success) {
            currentAuditHistory = data.audit_history;
            updateAuditTable();
        }
    } catch (error) {
        console.error('Error loading audit history:', error);
    }
}

/**
 * Update audit table
 */
function updateAuditTable() {
    const tbody = document.getElementById('auditTableBody');
    
    // If table doesn't exist on this page, skip
    if (!tbody) {
        return;
    }
    
    if (currentAuditHistory.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted">
                    No audit history available.
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = currentAuditHistory.map(audit => {
        // For returns, show both original and return TID
        let tidDisplay = `<code>${audit.serial_ptid}</code>`;
        if (audit.type === 'return' && audit.original_tid && audit.original_tid !== audit.serial_ptid) {
            tidDisplay = `
                <div><small class="text-muted">Original:</small> <code>${audit.original_tid}</code></div>
                <div><small class="text-muted">Returned:</small> <code>${audit.serial_ptid}</code></div>
            `;
        }
        
        // For returns, show both original and return trace
        let traceDisplay = `<span class="badge bg-secondary">${audit.trace_stock}</span>`;
        if (audit.type === 'return' && audit.original_trace && audit.original_trace !== audit.trace_stock) {
            traceDisplay = `
                <div><span class="badge bg-secondary">${audit.original_trace}</span> <small class="text-muted">→</small></div>
                <div><span class="badge bg-info">${audit.trace_stock}</span></div>
            `;
        }
        
        return `
            <tr>
                <td>${formatDate(audit.date)}</td>
                <td>
                    <span class="badge ${audit.type === 'deployment' ? 'bg-success' : 'bg-warning'}">
                        ${audit.type.toUpperCase()}
                    </span>
                </td>
                <td><strong>${audit.job_number}</strong></td>
                <td>${audit.paypoint_type}</td>
                <td>${tidDisplay}</td>
                <td>${traceDisplay}</td>
                <td>${audit.customer || '-'}</td>
                <td>
                    <span class="badge ${getStatusBadgeClass(audit.status)}">
                        ${audit.status.toUpperCase()}
                    </span>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * Show modals - Make sure these are in global scope
 */
window.showAddDeviceModal = function() {
    const modal = new bootstrap.Modal(document.getElementById('addDeviceModal'));
    modal.show();
}

// Old deploy/return modals removed - now using unified Use Stock modal

/**
 * Add new stock
 */
window.addStock = async function() {
    try {
        const paypointType = document.getElementById('paypointType').value;
        const serialPtid = document.getElementById('serialPtid').value;
        const traceStock = document.getElementById('traceStock').value;
        const notes = document.getElementById('deviceNotes').value;
        
        if (!paypointType || !serialPtid || !traceStock) {
            showError('Please fill in all required fields');
            return;
        }
        
        const response = await fetch('/api/paypoint/devices', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                paypoint_type: paypointType,
                serial_ptid: serialPtid,
                trace_stock: traceStock,
                notes: notes
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('Stock added successfully');
            bootstrap.Modal.getInstance(document.getElementById('addStockModal')).hide();
            document.getElementById('addStockForm').reset();
            await refreshData();
        } else {
            showError(data.error || 'Failed to add stock');
        }
    } catch (error) {
        console.error('Error adding stock:', error);
        showError('Failed to add stock');
    }
}

/**
 * Use stock (deploy and return in one action)
 */
window.useStock = async function() {
    try {
        const deviceId = document.getElementById('useStockDevice').value;
        const jobNumber = document.getElementById('useStockJobNumber').value;
        const customer = document.getElementById('useStockCustomer').value;
        const location = document.getElementById('useStockLocation').value;
        const returnSerial = document.getElementById('useStockReturnSerial').value;
        const returnTrace = document.getElementById('useStockReturnTrace').value;
        const returnReason = document.getElementById('useStockReturnReason').value;
        const notes = document.getElementById('useStockNotes').value;
        
        if (!deviceId || !jobNumber) {
            showError('Device and job number are required');
            return;
        }
        
        // Deploy and return in one API call
        const response = await fetch(`/api/paypoint/devices/${deviceId}/deploy`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_number: jobNumber,
                customer: customer,
                location: location,
                installation_notes: notes,
                return_immediately: true,
                return_notes: `Return Serial: ${returnSerial || 'N/A'}, Return Trace: ${returnTrace || 'N/A'}, Reason: ${returnReason || 'N/A'}, Notes: ${notes}`
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess(`Stock used for job ${jobNumber}`);
            bootstrap.Modal.getInstance(document.getElementById('useStockModal')).hide();
            document.getElementById('useStockForm').reset();
            await refreshData();
        } else {
            showError(data.error || 'Failed to use stock');
        }
    } catch (error) {
        console.error('Error using stock:', error);
        showError('Failed to use stock');
    }
}

/**
 * Show Add Stock modal
 */
window.showAddStockModal = function() {
    const modal = new bootstrap.Modal(document.getElementById('addStockModal'));
    modal.show();
}

/**
 * Show Use Stock modal
 */
window.showUseStockModal = async function() {
    // Load available devices
    await loadDevices();
    
    // Populate device dropdown
    const select = document.getElementById('useStockDevice');
    if (select && devices) {
        select.innerHTML = '<option value="">Select device...</option>';
        devices.filter(d => d.status === 'available').forEach(device => {
            const option = document.createElement('option');
            option.value = device.id;
            option.textContent = `${device.paypoint_type} - ${device.serial_ptid}`;
            select.appendChild(option);
        });
    }
    
    // Set up job number auto-fill
    const jobNumberInput = document.getElementById('useStockJobNumber');
    if (jobNumberInput && !jobNumberInput.dataset.listenerAttached) {
        jobNumberInput.dataset.listenerAttached = 'true';
        
        jobNumberInput.addEventListener('blur', async function() {
            const jobNumber = this.value.trim();
            if (jobNumber) {
                await fetchJobDetailsForUseStock(jobNumber);
            }
        });
        
        jobNumberInput.addEventListener('keypress', async function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const jobNumber = this.value.trim();
                if (jobNumber) {
                    await fetchJobDetailsForUseStock(jobNumber);
                }
            }
        });
    }
    
    const modal = new bootstrap.Modal(document.getElementById('useStockModal'));
    modal.show();
}

/**
 * Fetch job details for Use Stock form
 */
async function fetchJobDetailsForUseStock(jobNumber) {
    try {
        console.log('Fetching job details for:', jobNumber);
        const response = await fetch(`/api/search/job/${jobNumber}`);
        if (!response.ok) {
            console.log('Job not found in runsheets');
            return;
        }
        
        const data = await response.json();
        console.log('Job search response:', data);
        
        if (data && data.found && data.runsheets && data.runsheets.length > 0) {
            const job = data.runsheets[0];
            
            const customerInput = document.getElementById('useStockCustomer');
            const locationInput = document.getElementById('useStockLocation');
            
            if (customerInput && job.customer) {
                customerInput.value = job.customer;
            }
            
            if (locationInput && job.address) {
                locationInput.value = job.address;
            }
            
            const jobNumberInput = document.getElementById('useStockJobNumber');
            if (jobNumberInput) {
                jobNumberInput.classList.add('is-valid');
                setTimeout(() => jobNumberInput.classList.remove('is-valid'), 2000);
            }
            
            console.log('Job details auto-filled');
        }
    } catch (error) {
        console.error('Error fetching job details:', error);
    }
}

/**
 * Deploy device
 */
window.deployDevice = async function() {
    try {
        const deviceId = document.getElementById('deployDeviceSelect').value;
        const jobNumber = document.getElementById('deployJobNumber').value;
        const customer = document.getElementById('deployCustomer').value;
        const location = document.getElementById('deployLocation').value;
        const installationNotes = document.getElementById('deployNotes').value;
        const returnImmediately = document.getElementById('deployAndReturn').checked;
        const returnNotes = document.getElementById('deployReturnNotes').value;
        
        if (!deviceId || !jobNumber) {
            showError('Device and job number are required');
            return;
        }
        
        const response = await fetch(`/api/paypoint/devices/${deviceId}/deploy`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_number: jobNumber,
                customer: customer,
                location: location,
                installation_notes: installationNotes,
                return_immediately: returnImmediately,
                return_notes: returnNotes
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess(data.message);
            bootstrap.Modal.getInstance(document.getElementById('deployModal')).hide();
            document.getElementById('deployForm').reset();
            document.getElementById('deployAndReturn').checked = false;
            toggleReturnNotes();
            await refreshData();
        } else {
            showError(data.error || 'Failed to deploy device');
        }
    } catch (error) {
        console.error('Error deploying device:', error);
        showError('Failed to deploy device');
    }
}

/**
 * Return device
 */
window.returnDevice = async function() {
    try {
        const deploymentId = document.getElementById('returnDeploymentSelect').value;
        const returnSerialPtid = document.getElementById('returnSerialPtid').value;
        const returnTrace = document.getElementById('returnTrace').value;
        const returnReason = document.getElementById('returnReason').value;
        const returnNotes = document.getElementById('returnNotes').value;
        
        if (!deploymentId || !returnSerialPtid || !returnTrace) {
            showError('Deployed device, return serial/TID, and return trace are required');
            return;
        }
        
        const response = await fetch(`/api/paypoint/deployments/${deploymentId}/return`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                return_serial_ptid: returnSerialPtid,
                return_trace: returnTrace,
                return_reason: returnReason,
                return_notes: returnNotes
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess(data.message);
            bootstrap.Modal.getInstance(document.getElementById('returnModal')).hide();
            document.getElementById('returnForm').reset();
            await refreshData();
        } else {
            showError(data.error || 'Failed to return device');
        }
    } catch (error) {
        console.error('Error returning device:', error);
        showError('Failed to return device');
    }
}

/**
 * Quick actions - updated for new Use Stock workflow
 */
window.quickUseStock = async function(deviceId) {
    await showUseStockModal();
    document.getElementById('useStockDevice').value = deviceId;
}

window.viewDeviceHistory = function(deviceId) {
    // Switch to audit tab and filter by device
    const auditTab = new bootstrap.Tab(document.getElementById('audit-tab'));
    auditTab.show();
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Tab change events
    const tabs = document.querySelectorAll('#paypointTabs button[data-bs-toggle="tab"]');
    console.log('Setting up event listeners for', tabs.length, 'tabs');
    
    tabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const target = event.target.getAttribute('data-bs-target');
            console.log('Tab switched to:', target);
            
            // Refresh data when switching to certain tabs
            if (target === '#returns') {
                console.log('Loading returns from tab switch');
                loadReturns();
            } else if (target === '#devices') {
                loadDevices();
            }
        });
    });
}

/**
 * Refresh all data
 */
async function refreshData() {
    try {
        await Promise.all([
            loadSummary(),
            loadDevices(),
            loadDeployments(),
            loadReturns(),
            loadAuditHistory()
        ]);
    } catch (error) {
        console.error('Error refreshing data:', error);
        showError('Failed to refresh data');
    }
}

/**
 * Show success message
 */
function showSuccess(message) {
    showAlert(message, 'success');
}

/**
 * Show error message
 */
function showError(message) {
    showAlert(message, 'danger');
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    // Remove existing alerts
    const existingAlerts = document.querySelectorAll('.paypoint-alert');
    existingAlerts.forEach(alert => alert.remove());
    
    // Create new alert
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} paypoint-alert`;
    alert.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
            <span>${message}</span>
            <button type="button" class="btn-close ms-auto" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    
    // Add to page
    document.body.appendChild(alert);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    if (!dateString) return '-';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-GB', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return dateString;
    }
}

// Barcode Scanner Functions
let currentScanTargetField = null;
let barcodeStream = null;
let detectedBarcodes = [];
let lastDetectedCode = null;

async function quickScan() {
    // Show modal asking which field to fill
    const modal = new bootstrap.Modal(document.getElementById('barcodeScannerModal'));
    modal.show();
    
    document.getElementById('scannerResult').style.display = 'none';
    document.getElementById('scannerStatus').innerHTML = `
        <div class="alert alert-info">
            <strong>Which field do you want to fill?</strong>
            <div class="mt-3 d-grid gap-2">
                <button class="btn btn-primary" onclick="scanBarcode('serialPtid')">
                    <i class="bi bi-upc-scan me-2"></i>Scan for Serial / TID
                </button>
                <button class="btn btn-primary" onclick="scanBarcode('traceStock')">
                    <i class="bi bi-upc-scan me-2"></i>Scan for Trace / Stock
                </button>
                <button class="btn btn-secondary" data-bs-dismiss="modal">
                    Cancel
                </button>
            </div>
        </div>
    `;
}

async function scanBarcode(targetFieldId) {
    currentScanTargetField = targetFieldId;
    
    // Show the scanner modal
    const modal = new bootstrap.Modal(document.getElementById('barcodeScannerModal'));
    modal.show();
    
    // Reset UI
    document.getElementById('scannerResult').style.display = 'none';
    document.getElementById('scannerStatus').innerHTML = '<p class="text-muted">Initializing camera...</p>';
    
    // Start camera when modal is shown
    document.getElementById('barcodeScannerModal').addEventListener('shown.bs.modal', function () {
        startBarcodeScanner();
    }, { once: true });
    
    // Stop camera when modal is hidden
    document.getElementById('barcodeScannerModal').addEventListener('hidden.bs.modal', function () {
        stopBarcodeScanner();
    }, { once: true });
}

async function startBarcodeScanner() {
    const video = document.getElementById('barcodeVideo');
    
    try {
        // Request camera access (rear camera preferred on mobile)
        const constraints = {
            video: {
                facingMode: { ideal: 'environment' },
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        };
        
        barcodeStream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = barcodeStream;
        video.play();
        
        document.getElementById('scannerStatus').innerHTML = '<p class="text-muted">Position barcode in front of camera</p>';
        
        // Start barcode detection
        detectBarcode(video);
    } catch (error) {
        console.error('Camera access error:', error);
        document.getElementById('scannerStatus').innerHTML = `
            <div class="alert alert-warning">
                <i class="bi bi-exclamation-triangle"></i> 
                <strong>Camera not available</strong>
                <p class="mb-2 mt-2">Camera access requires HTTPS or may be blocked. Please enter barcode manually:</p>
                <div class="input-group">
                    <input type="text" class="form-control" id="manualBarcodeInput" placeholder="Enter barcode manually">
                    <button class="btn btn-primary" onclick="useManualBarcode()">Use This</button>
                </div>
            </div>
        `;
    }
}

function detectBarcode(video) {
    // Use ZXing (industry standard - same as Podfather app)
    if (typeof ZXing !== 'undefined') {
        console.log('Starting ZXing barcode scanner...');
        
        const codeReader = new ZXing.BrowserMultiFormatReader();
        
        codeReader.decodeFromVideoDevice(undefined, video, (result, err) => {
            if (result) {
                const code = result.getText();
                const format = result.getBarcodeFormat();
                
                console.log('Barcode detected:', code, 'Format:', format);
                
                // Require 3 consecutive identical reads for accuracy
                detectedBarcodes.push(code);
                
                if (detectedBarcodes.length >= 3) {
                    // Check if last 3 reads are identical
                    const last3 = detectedBarcodes.slice(-3);
                    if (last3[0] === last3[1] && last3[1] === last3[2]) {
                        codeReader.reset();
                        handleBarcodeDetected(code, format);
                        detectedBarcodes = [];
                    } else {
                        // Show progress
                        document.getElementById('scannerStatus').innerHTML = `
                            <p class="text-warning">
                                <i class="bi bi-hourglass-split"></i> Reading... Hold steady (${detectedBarcodes.length}/3)
                            </p>
                        `;
                    }
                }
            }
            
            if (err && !(err instanceof ZXing.NotFoundException)) {
                console.error('ZXing error:', err);
            }
        });
    } else {
        console.error('ZXing library not loaded');
        document.getElementById('scannerStatus').innerHTML = '<p class="text-danger">Scanner library not loaded. Please refresh the page.</p>';
    }
}

function handleBarcodeDetected(barcode, format) {
    console.log('Barcode confirmed:', barcode, 'Format:', format);
    
    // Stop scanning
    stopBarcodeScanner();
    
    // Show result with options
    document.getElementById('scannedValue').textContent = barcode;
    document.getElementById('scannerResult').style.display = 'block';
    document.getElementById('scannerStatus').innerHTML = `
        <div class="alert alert-success">
            <i class="bi bi-check-circle"></i> Barcode detected: <strong>${barcode}</strong>
            <div class="text-muted small mt-1">Format: ${format || 'Unknown'}</div>
            <div class="mt-3 d-flex gap-2">
                <button class="btn btn-success" onclick="confirmBarcode('${barcode}')">
                    <i class="bi bi-check"></i> Use This
                </button>
                <button class="btn btn-warning" onclick="rescanBarcode()">
                    <i class="bi bi-arrow-clockwise"></i> Scan Again
                </button>
            </div>
        </div>
    `;
}

function confirmBarcode(barcode) {
    // Fill the target field
    if (currentScanTargetField) {
        document.getElementById(currentScanTargetField).value = barcode;
    }
    
    // Close modal
    bootstrap.Modal.getInstance(document.getElementById('barcodeScannerModal')).hide();
}

function rescanBarcode() {
    // Reset and restart scanner
    detectedBarcodes = [];
    document.getElementById('scannerResult').style.display = 'none';
    document.getElementById('scannerStatus').innerHTML = '<p class="text-muted">Position barcode in front of camera</p>';
    startBarcodeScanner();
}

function editBarcode(barcode) {
    document.getElementById('scannerStatus').innerHTML = `
        <div class="alert alert-info">
            <strong>Edit Barcode</strong>
            <div class="input-group mt-2">
                <input type="text" class="form-control" id="editBarcodeInput" value="${barcode}">
                <button class="btn btn-primary" onclick="confirmBarcode(document.getElementById('editBarcodeInput').value)">
                    <i class="bi bi-check"></i> Use This
                </button>
            </div>
        </div>
    `;
}

function stopBarcodeScanner() {
    // Stop ZXing if running
    if (typeof ZXing !== 'undefined' && ZXing.BrowserMultiFormatReader) {
        try {
            const codeReader = new ZXing.BrowserMultiFormatReader();
            codeReader.reset();
        } catch (e) {
            console.log('Error stopping scanner:', e);
        }
    }
    
    if (barcodeStream) {
        barcodeStream.getTracks().forEach(track => track.stop());
        barcodeStream = null;
    }
    
    const video = document.getElementById('barcodeVideo');
    if (video) {
        video.srcObject = null;
    }
}

function useManualBarcode() {
    const manualInput = document.getElementById('manualBarcodeInput');
    const barcode = manualInput.value.trim();
    
    if (!barcode) {
        alert('Please enter a barcode');
        return;
    }
    
    handleBarcodeDetected(barcode);
}

// Edit and Delete Functions
function editStock(id) {
    const device = devices.find(d => d.id === id);
    if (!device) {
        alert('Device not found');
        return;
    }
    
    // Populate the Add Stock modal with existing data
    document.getElementById('paypointType').value = device.paypoint_type;
    document.getElementById('serialPtid').value = device.serial_ptid;
    document.getElementById('traceStock').value = device.trace_stock;
    document.getElementById('deviceNotes').value = device.notes || '';
    
    // Change the modal title and button
    document.querySelector('#addStockModal .modal-title').textContent = 'Edit Stock';
    const addButton = document.querySelector('#addStockModal .btn-primary');
    addButton.textContent = 'Update Stock';
    addButton.onclick = () => updateStock(id);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('addStockModal'));
    modal.show();
}

async function updateStock(id) {
    const paypointType = document.getElementById('paypointType').value;
    const serialPtid = document.getElementById('serialPtid').value;
    const traceStock = document.getElementById('traceStock').value;
    const notes = document.getElementById('deviceNotes').value;
    
    if (!paypointType || !serialPtid || !traceStock) {
        alert('Please fill in all required fields');
        return;
    }
    
    try {
        const response = await fetch(`/api/paypoint/stock/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                paypoint_type: paypointType,
                serial_ptid: serialPtid,
                trace_stock: traceStock,
                notes: notes
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('addStockModal')).hide();
            await loadStock();
            showSuccess('Stock updated successfully');
            
            // Reset modal
            document.querySelector('#addStockModal .modal-title').textContent = 'Add Stock to Van';
            const addButton = document.querySelector('#addStockModal .btn-primary');
            addButton.textContent = 'Add Stock';
            addButton.onclick = addStock;
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        console.error('Error updating stock:', error);
        alert('Error updating stock');
    }
}

async function deleteStock(id) {
    if (!confirm('Are you sure you want to delete this stock item?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/paypoint/stock/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            await loadStock();
            showSuccess('Stock deleted successfully');
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        console.error('Error deleting stock:', error);
        alert('Error deleting stock');
    }
}

function editReturn(id) {
    const returnItem = currentReturns.find(r => r.id === id);
    if (!returnItem) {
        alert('Return not found');
        return;
    }
    
    // Hide the device selector when editing (device already selected)
    const deviceSelect = document.getElementById('useStockDevice');
    if (deviceSelect) {
        const deviceSelectGroup = deviceSelect.closest('.mb-3');
        if (deviceSelectGroup) {
            deviceSelectGroup.style.display = 'none';
        }
    }
    
    // Populate the Use Stock modal with existing data
    document.getElementById('useStockJobNumber').value = returnItem.job_number;
    document.getElementById('useStockCustomer').value = returnItem.customer || '';
    document.getElementById('useStockLocation').value = returnItem.location || '';
    document.getElementById('useStockReturnSerial').value = returnItem.return_serial_ptid;
    document.getElementById('useStockReturnTrace').value = returnItem.return_trace;
    document.getElementById('useStockReturnReason').value = returnItem.return_reason || '';
    document.getElementById('useStockNotes').value = returnItem.notes || '';
    
    // Change the modal title and button
    document.querySelector('#useStockModal .modal-title').textContent = 'Edit Return';
    const useButton = document.querySelector('#useStockModal .btn-success');
    useButton.textContent = 'Update Return';
    useButton.onclick = () => updateReturn(id);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('useStockModal'));
    modal.show();
}

async function updateReturn(id) {
    const jobNumber = document.getElementById('useStockJobNumber').value;
    const customer = document.getElementById('useStockCustomer').value;
    const location = document.getElementById('useStockLocation').value;
    const returnSerial = document.getElementById('useStockReturnSerial').value;
    const returnTrace = document.getElementById('useStockReturnTrace').value;
    const returnReason = document.getElementById('useStockReturnReason').value;
    const notes = document.getElementById('useStockNotes').value;
    
    if (!jobNumber) {
        alert('Please enter a job number');
        return;
    }
    
    try {
        const response = await fetch(`/api/paypoint/returns/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_number: jobNumber,
                customer: customer,
                location: location,
                return_serial_ptid: returnSerial,
                return_trace: returnTrace,
                return_reason: returnReason,
                notes: notes
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('useStockModal')).hide();
            await loadReturns();
            showSuccess('Return updated successfully');
            
            // Reset modal
            resetUseStockModal();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        console.error('Error updating return:', error);
        alert('Error updating return');
    }
}

function resetUseStockModal() {
    // Show device selector again
    const deviceSelect = document.getElementById('useStockDevice');
    if (deviceSelect) {
        const deviceSelectGroup = deviceSelect.closest('.mb-3');
        if (deviceSelectGroup) {
            deviceSelectGroup.style.display = 'block';
        }
    }
    
    // Reset modal title and button
    const modalTitle = document.querySelector('#useStockModal .modal-title');
    if (modalTitle) {
        modalTitle.textContent = 'Use Stock';
    }
    
    const useButton = document.querySelector('#useStockModal .btn-success');
    if (useButton) {
        useButton.textContent = 'Use Stock';
        useButton.onclick = useStock;
    }
}

async function deleteReturn(id) {
    if (!confirm('Are you sure you want to delete this return record?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/paypoint/returns/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            await loadReturns();
            showSuccess('Return deleted successfully');
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        console.error('Error deleting return:', error);
        alert('Error deleting return');
    }
}

