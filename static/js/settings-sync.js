/**
 * Enhanced Sync Controls for Settings Page
 * Handles all auto-sync configuration, health monitoring, and control functions
 */

// Global sync state
let syncConfigModal = null;
let syncStatusInterval = null;

// Initialize sync controls when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modal
    const modalElement = document.getElementById('syncConfigModal');
    if (modalElement) {
        syncConfigModal = new bootstrap.Modal(modalElement);
    }
    
    // Load initial sync status
    loadSyncStatus();
    loadSyncHealth();
    loadSyncConfig();
    
    // Auto-refresh sync status every 30 seconds
    syncStatusInterval = setInterval(() => {
        loadSyncStatus();
        loadSyncHealth();
    }, 30000);
});

/**
 * Load current sync status
 */
async function loadSyncStatus() {
    try {
        const response = await fetch('/api/data/periodic-sync/status');
        const data = await response.json();
        
        if (data.success) {
            // API returns status fields directly in data object
            updateSyncStatusUI(data);
        }
    } catch (error) {
        console.error('Failed to load sync status:', error);
    }
}

/**
 * Update sync status UI elements
 */
function updateSyncStatusUI(status) {
    // Safety check
    if (!status || typeof status.is_running === 'undefined') {
        console.warn('Invalid status data received:', status);
        return;
    }
    
    const toggle = document.getElementById('periodicSyncToggle');
    const badge = document.getElementById('autoSyncBadge');
    const badgeText = document.getElementById('autoSyncBadgeText');
    const label = document.getElementById('periodicSyncLabel');
    const controls = document.getElementById('syncControls');
    const pauseBtn = document.getElementById('pauseSyncBtn');
    const resumeBtn = document.getElementById('resumeSyncBtn');
    const nextSyncTime = document.getElementById('nextSyncTime');
    const nextSyncValue = document.getElementById('nextSyncTimeValue');
    const historyContainer = document.getElementById('syncHistoryContainer');
    
    // Check if elements exist
    if (!toggle || !badge || !label) {
        console.warn('Required UI elements not found');
        return;
    }
    
    // Update toggle
    toggle.checked = status.is_running;
    label.textContent = status.is_running ? 'Enabled' : 'Disabled';
    
    // Update badge based on state
    badge.className = 'badge ms-2';
    if (!status.is_running) {
        badge.classList.add('bg-secondary');
        badgeText.textContent = 'Disabled';
        badge.innerHTML = '<i class="bi bi-circle"></i> <span id="autoSyncBadgeText">' + badgeText.textContent + '</span>';
        controls.style.display = 'none';
        historyContainer.style.display = 'none';
    } else if (status.is_paused) {
        badge.classList.add('bg-warning');
        badgeText.textContent = 'Paused';
        badge.innerHTML = '<i class="bi bi-pause-circle-fill"></i> <span id="autoSyncBadgeText">' + badgeText.textContent + '</span>';
        controls.style.display = 'block';
        controls.className = 'row g-2 mb-3';
        pauseBtn.style.display = 'none';
        resumeBtn.style.display = 'block';
        historyContainer.style.display = 'block';
    } else {
        switch(status.current_state) {
            case 'running':
                badge.classList.add('bg-primary');
                badgeText.textContent = 'Running';
                badge.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> <span id="autoSyncBadgeText">' + badgeText.textContent + '</span>';
                break;
            case 'completed':
                badge.classList.add('bg-success');
                badgeText.textContent = 'Active';
                badge.innerHTML = '<i class="bi bi-check-circle-fill"></i> <span id="autoSyncBadgeText">' + badgeText.textContent + '</span>';
                break;
            case 'failed':
                badge.classList.add('bg-danger');
                badgeText.textContent = 'Error';
                badge.innerHTML = '<i class="bi bi-exclamation-circle-fill"></i> <span id="autoSyncBadgeText">' + badgeText.textContent + '</span>';
                break;
            default:
                badge.classList.add('bg-info');
                badgeText.textContent = 'Idle';
                badge.innerHTML = '<i class="bi bi-circle-fill"></i> <span id="autoSyncBadgeText">' + badgeText.textContent + '</span>';
        }
        controls.style.display = 'block';
        controls.className = 'row g-2 mb-3';
        pauseBtn.style.display = 'block';
        resumeBtn.style.display = 'none';
        historyContainer.style.display = 'block';
    }
    
    // Update next sync time
    if (status.next_sync_estimate && status.is_running && !status.is_paused) {
        const nextSync = new Date(status.next_sync_estimate);
        const now = new Date();
        const tomorrow = new Date(now);
        tomorrow.setDate(tomorrow.getDate() + 1);
        
        // Check if next sync is tomorrow
        if (nextSync.toDateString() === tomorrow.toDateString()) {
            nextSyncValue.textContent = 'Tomorrow at ' + nextSync.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
        } else {
            nextSyncValue.textContent = nextSync.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
        }
        nextSyncTime.style.display = 'block';
    } else {
        nextSyncTime.style.display = 'none';
    }
    
    // Update sync history
    if (status.sync_history && status.sync_history.length > 0) {
        updateSyncHistory(status.sync_history);
    }
}

/**
 * Update sync history display
 */
function updateSyncHistory(history) {
    const historyList = document.getElementById('syncHistoryList');
    
    if (!history || history.length === 0) {
        historyList.innerHTML = '<div class="text-center text-muted py-2"><small>No recent activity</small></div>';
        return;
    }
    
    let html = '<div class="list-group list-group-flush">';
    history.reverse().forEach(entry => {
        const timestamp = new Date(entry.timestamp);
        const timeStr = timestamp.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
        const dateStr = timestamp.toLocaleDateString('en-GB');
        
        const iconClass = entry.success ? 'bi-check-circle text-success' : 'bi-x-circle text-danger';
        const statusText = entry.success ? 'Success' : `Failed (${entry.errors} errors)`;
        
        html += `
            <div class="list-group-item list-group-item-action py-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <i class="bi ${iconClass} me-2"></i>
                        <small><strong>${timeStr}</strong> ${dateStr}</small>
                    </div>
                    <div class="text-end">
                        <small class="text-muted">${statusText}</small>
                        ${entry.runsheets > 0 ? `<span class="badge bg-primary ms-1">${entry.runsheets} RS</span>` : ''}
                        ${entry.payslips > 0 ? `<span class="badge bg-success ms-1">${entry.payslips} PS</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    historyList.innerHTML = html;
}

/**
 * Toggle sync history visibility
 */
function toggleSyncHistory() {
    const historyList = document.getElementById('syncHistoryList');
    const icon = document.getElementById('syncHistoryToggleIcon');
    
    if (historyList.style.display === 'none') {
        historyList.style.display = 'block';
        icon.className = 'bi bi-chevron-up';
    } else {
        historyList.style.display = 'none';
        icon.className = 'bi bi-chevron-down';
    }
}

/**
 * Load sync health status
 */
async function loadSyncHealth() {
    try {
        const response = await fetch('/api/data/periodic-sync/health');
        const data = await response.json();
        
        if (data.success) {
            updateHealthStatusUI(data.health);
        }
    } catch (error) {
        console.error('Failed to load sync health:', error);
    }
}

/**
 * Update health status UI
 */
function updateHealthStatusUI(health) {
    const container = document.getElementById('syncHealthStatus');
    
    if (!health) return;
    
    // Always show health status when we have data
    container.style.display = 'block';
    
    // Gmail status
    updateHealthIcon('gmailHealthIcon', 'gmailHealthText', health.gmail_authenticated, 'Gmail');
    
    // Database status
    updateHealthIcon('dbHealthIcon', 'dbHealthText', health.database_accessible, 'Database');
    
    // Disk space status
    const diskOk = health.disk_space_ok;
    const diskText = diskOk ? `${health.disk_space_gb}GB` : 'Low Space';
    updateHealthIcon('diskHealthIcon', 'diskHealthText', diskOk, diskText);
    
    // Service status
    const serviceOk = health.sync_service_running && !health.sync_service_paused;
    const serviceText = health.sync_service_paused ? 'Paused' : 'Running';
    updateHealthIcon('serviceHealthIcon', 'serviceHealthText', serviceOk, serviceText);
}

/**
 * Update individual health icon
 */
function updateHealthIcon(iconId, textId, isHealthy, text) {
    const icon = document.getElementById(iconId);
    const textEl = document.getElementById(textId);
    
    if (isHealthy) {
        icon.className = icon.className.replace(/text-\w+/, 'text-success');
    } else {
        icon.className = icon.className.replace(/text-\w+/, 'text-danger');
    }
    
    textEl.textContent = text;
}

/**
 * Toggle periodic sync on/off
 */
async function togglePeriodicSync() {
    const toggle = document.getElementById('periodicSyncToggle');
    const isEnabled = toggle.checked;
    
    try {
        const endpoint = isEnabled ? '/api/data/periodic-sync/start' : '/api/data/periodic-sync/stop';
        const response = await fetch(endpoint, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            setTimeout(() => loadSyncStatus(), 1000);
        } else {
            showToast(data.error || 'Failed to toggle sync', 'error');
            toggle.checked = !isEnabled; // Revert toggle
        }
    } catch (error) {
        console.error('Failed to toggle sync:', error);
        showToast('Failed to toggle sync service', 'error');
        toggle.checked = !isEnabled; // Revert toggle
    }
}

/**
 * Pause sync service
 */
async function pauseSync() {
    // Ask user for duration
    const duration = prompt('Pause sync for how many minutes? (Leave empty for indefinite pause)');
    
    if (duration === null) return; // User cancelled
    
    const durationMinutes = duration === '' ? null : parseInt(duration);
    
    if (durationMinutes !== null && (isNaN(durationMinutes) || durationMinutes < 1)) {
        showToast('Please enter a valid number of minutes', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/data/periodic-sync/pause', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ duration_minutes: durationMinutes })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            setTimeout(() => loadSyncStatus(), 1000);
        } else {
            showToast(data.error || 'Failed to pause sync', 'error');
        }
    } catch (error) {
        console.error('Failed to pause sync:', error);
        showToast('Failed to pause sync service', 'error');
    }
}

/**
 * Resume sync service
 */
async function resumeSync() {
    try {
        const response = await fetch('/api/data/periodic-sync/resume', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            setTimeout(() => loadSyncStatus(), 1000);
        } else {
            showToast(data.error || 'Failed to resume sync', 'error');
        }
    } catch (error) {
        console.error('Failed to resume sync:', error);
        showToast('Failed to resume sync service', 'error');
    }
}

/**
 * Show sync configuration modal
 */
async function showSyncConfig() {
    await loadSyncConfig();
    if (syncConfigModal) {
        syncConfigModal.show();
    }
}

/**
 * Load sync configuration
 */
async function loadSyncConfig() {
    try {
        const response = await fetch('/api/data/periodic-sync/config');
        const data = await response.json();
        
        if (data.success) {
            const config = data.config;
            
            // Populate form fields
            document.getElementById('syncStartTime').value = config.sync_start_time || '18:00';
            document.getElementById('syncIntervalMinutes').value = config.sync_interval_minutes || 15;
            
            // Payslip sync settings
            const dayMap = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday'};
            document.getElementById('payslipSyncDay').value = dayMap[config.payslip_sync_day] || 'Tuesday';
            document.getElementById('payslipSyncStart').value = config.payslip_sync_start || 6;
            document.getElementById('payslipSyncEnd').value = config.payslip_sync_end || 14;
            
            // Selective sync
            document.getElementById('autoSyncRunsheetsEnabled').checked = config.auto_sync_runsheets_enabled !== false;
            document.getElementById('autoSyncPayslipsEnabled').checked = config.auto_sync_payslips_enabled !== false;
            
            // Notification preferences
            document.getElementById('notificationEmail').value = config.notification_email || '';
            document.getElementById('notifyOnSuccess').checked = config.notify_on_success !== false;
            document.getElementById('notifyOnErrorOnly').checked = config.notify_on_error_only === true;
            document.getElementById('notifyOnNewFilesOnly').checked = config.notify_on_new_files_only === true;
        }
    } catch (error) {
        console.error('Failed to load sync config:', error);
    }
}

/**
 * Save sync configuration
 */
async function saveSyncConfig() {
    const config = {
        sync_start_time: document.getElementById('syncStartTime').value,
        sync_interval_minutes: parseInt(document.getElementById('syncIntervalMinutes').value),
        payslip_sync_day: document.getElementById('payslipSyncDay').value,
        payslip_sync_start: parseInt(document.getElementById('payslipSyncStart').value),
        payslip_sync_end: parseInt(document.getElementById('payslipSyncEnd').value),
        auto_sync_runsheets_enabled: document.getElementById('autoSyncRunsheetsEnabled').checked,
        auto_sync_payslips_enabled: document.getElementById('autoSyncPayslipsEnabled').checked,
        notification_email: document.getElementById('notificationEmail').value,
        notify_on_success: document.getElementById('notifyOnSuccess').checked,
        notify_on_error_only: document.getElementById('notifyOnErrorOnly').checked,
        notify_on_new_files_only: document.getElementById('notifyOnNewFilesOnly').checked
    };
    
    try {
        const response = await fetch('/api/data/periodic-sync/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Sync configuration saved successfully', 'success');
            if (syncConfigModal) {
                syncConfigModal.hide();
            }
            setTimeout(() => loadSyncStatus(), 1000);
        } else {
            showToast(data.error || 'Failed to save configuration', 'error');
        }
    } catch (error) {
        console.error('Failed to save sync config:', error);
        showToast('Failed to save sync configuration', 'error');
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    // Use existing toast system if available, otherwise fallback to alert
    if (typeof showStatus === 'function') {
        showStatus(message, type);
    } else {
        alert(message);
    }
}

// Add CSS for spinning animation
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    .spin {
        animation: spin 1s linear infinite;
        display: inline-block;
    }
`;
document.head.appendChild(style);
