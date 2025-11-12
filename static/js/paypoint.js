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
        
        console.log('Paypoint system initialized successfully');
    } catch (error) {
        console.error('Error initializing Paypoint system:', error);
        showError('Failed to initialize Paypoint system');
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
    document.getElementById('deployedDevices').textContent = summary.deployed_devices || 0;
    document.getElementById('returnedDevices').textContent = summary.returned_devices || 0;
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
 * Update devices table
 */
function updateDevicesTable() {
    const tbody = document.getElementById('devicesTableBody');
    
    if (devices.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted">
                    <i class="bi bi-device-hdd fs-1 d-block mb-2"></i>
                    No devices found. Add your first device to get started.
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = devices.map(device => `
        <tr>
            <td><strong>${device.paypoint_type}</strong></td>
            <td><code>${device.serial_ptid}</code></td>
            <td><span class="badge bg-secondary">${device.trace_stock}</span></td>
            <td>
                <span class="badge ${getStatusBadgeClass(device.status)}">
                    ${device.status.toUpperCase()}
                </span>
            </td>
            <td>${device.current_job_number || '-'}</td>
            <td>${device.deployment_date ? formatDate(device.deployment_date) : '-'}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    ${device.status === 'available' ? 
                        `<button class="btn btn-outline-success" onclick="quickDeploy(${device.id})" title="Deploy">
                            <i class="bi bi-arrow-up-circle"></i>
                        </button>` : ''
                    }
                    ${device.status === 'deployed' ? 
                        `<button class="btn btn-outline-warning" onclick="quickReturn(${device.id})" title="Return">
                            <i class="bi bi-arrow-down-circle"></i>
                        </button>` : ''
                    }
                    <button class="btn btn-outline-info" onclick="viewDeviceHistory(${device.id})" title="View History">
                        <i class="bi bi-clock-history"></i>
                    </button>
                </div>
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
        const response = await fetch('/api/paypoint/returns');
        const data = await response.json();
        
        if (data.success) {
            currentReturns = data.returns;
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
    
    if (currentReturns.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted">
                    No returns recorded yet.
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = currentReturns.map(returnItem => `
        <tr>
            <td>${formatDate(returnItem.return_date)}</td>
            <td><strong>${returnItem.job_number}</strong></td>
            <td>${returnItem.paypoint_type}</td>
            <td><code>${returnItem.return_serial_ptid}</code></td>
            <td><span class="badge bg-info">${returnItem.return_trace}</span></td>
            <td>${returnItem.customer || '-'}</td>
            <td>${returnItem.return_reason || '-'}</td>
        </tr>
    `).join('');
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
    
    tbody.innerHTML = currentAuditHistory.map(audit => `
        <tr>
            <td>${formatDate(audit.date)}</td>
            <td>
                <span class="badge ${audit.type === 'deployment' ? 'bg-success' : 'bg-warning'}">
                    ${audit.type.toUpperCase()}
                </span>
            </td>
            <td><strong>${audit.job_number}</strong></td>
            <td>${audit.paypoint_type}</td>
            <td><code>${audit.serial_ptid}</code></td>
            <td><span class="badge bg-secondary">${audit.trace_stock}</span></td>
            <td>${audit.customer || '-'}</td>
            <td>
                <span class="badge ${getStatusBadgeClass(audit.status)}">
                    ${audit.status.toUpperCase()}
                </span>
            </td>
        </tr>
    `).join('');
}

/**
 * Show modals - Make sure these are in global scope
 */
window.showAddDeviceModal = function() {
    const modal = new bootstrap.Modal(document.getElementById('addDeviceModal'));
    modal.show();
}

window.showDeployModal = function() {
    const modal = new bootstrap.Modal(document.getElementById('deployModal'));
    modal.show();
}

window.showReturnModal = function() {
    const modal = new bootstrap.Modal(document.getElementById('returnModal'));
    modal.show();
}

/**
 * Add new device
 */
window.addDevice = async function() {
    try {
        const formData = {
            paypoint_type: document.getElementById('paypointType').value,
            serial_ptid: document.getElementById('serialPtid').value,
            trace_stock: document.getElementById('traceStock').value,
            notes: document.getElementById('deviceNotes').value
        };
        
        if (!formData.paypoint_type || !formData.serial_ptid || !formData.trace_stock) {
            showError('Paypoint type, serial/TID, and trace/stock are required');
            return;
        }
        
        const response = await fetch('/api/paypoint/devices', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('Device added successfully');
            bootstrap.Modal.getInstance(document.getElementById('addDeviceModal')).hide();
            document.getElementById('addDeviceForm').reset();
            await refreshData();
        } else {
            showError(data.error || 'Failed to add device');
        }
    } catch (error) {
        console.error('Error adding device:', error);
        showError('Failed to add device');
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
                installation_notes: installationNotes
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess(data.message);
            bootstrap.Modal.getInstance(document.getElementById('deployModal')).hide();
            document.getElementById('deployForm').reset();
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
 * Quick actions
 */
window.quickDeploy = function(deviceId) {
    document.getElementById('deployDeviceSelect').value = deviceId;
    showDeployModal();
}

window.quickReturn = function(deviceId) {
    document.getElementById('returnDeploymentSelect').value = deviceId;
    showReturnModal();
}

window.returnFromDeployment = function(deploymentId) {
    document.getElementById('returnDeploymentSelect').value = deploymentId;
    showReturnModal();
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
    document.querySelectorAll('#paypointTabs button[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const target = event.target.getAttribute('data-bs-target');
            
            // Refresh data when switching to certain tabs
            if (target === '#deployments') {
                loadDeployments();
            } else if (target === '#returns') {
                loadReturns();
            } else if (target === '#audit') {
                loadAuditHistory();
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

