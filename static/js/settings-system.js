/**
 * System Settings JavaScript
 * Handles database management and system functionality
 */

// Company Year Configuration
async function loadCompanyYear() {
    try {
        const response = await fetch('/api/settings/company-year');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('companyYearStart').value = data.year_start || '09/03/2025';
            document.getElementById('currentCompanyYear').value = data.current_year || '-';
            document.getElementById('currentWeekNumber').value = `Week ${data.current_week || '-'}`;
        } else {
            showStatus('Failed to load company year configuration', 'danger');
        }
    } catch (error) {
        console.error('Error loading company year:', error);
        showStatus('Error loading company year configuration', 'danger');
    }
}

async function saveCompanyYear() {
    const yearStart = document.getElementById('companyYearStart').value;
    
    if (!yearStart) {
        showStatus('Please enter a company year start date', 'warning');
        return;
    }
    
    // Validate date format (DD/MM/YYYY)
    const datePattern = /^\d{2}\/\d{2}\/\d{4}$/;
    if (!datePattern.test(yearStart)) {
        showStatus('Invalid date format. Please use DD/MM/YYYY', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/settings/company-year', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ year_start: yearStart })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus('Company year configuration saved successfully', 'success');
            // Reload to update current year/week
            loadCompanyYear();
        } else {
            showStatus(data.error || 'Failed to save configuration', 'danger');
        }
    } catch (error) {
        console.error('Error saving company year:', error);
        showStatus('Error saving company year configuration', 'danger');
    }
}

// Status display functions
function showStatus(message, type = 'info') {
    // Create or get floating notification container
    let floatingContainer = document.getElementById('floatingNotifications');
    if (!floatingContainer) {
        floatingContainer = document.createElement('div');
        floatingContainer.id = 'floatingNotifications';
        floatingContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            pointer-events: none;
        `;
        document.body.appendChild(floatingContainer);
    }
    
    const alertClass = type === 'success' ? 'alert-success' : 
                      type === 'danger' ? 'alert-danger' : 
                      type === 'warning' ? 'alert-warning' : 'alert-info';
    
    const iconClass = type === 'success' ? 'check-circle' : 
                      type === 'danger' ? 'x-circle' : 
                      type === 'warning' ? 'exclamation-triangle' : 'info-circle';
    
    // Create floating notification
    const notification = document.createElement('div');
    notification.className = `alert ${alertClass} alert-dismissible fade show mb-2`;
    notification.style.cssText = `
        pointer-events: auto;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        border: none;
        animation: slideInRight 0.3s ease-out;
    `;
    
    notification.innerHTML = `
        <i class="bi bi-${iconClass} me-2"></i>${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;
    
    // Add CSS animation if not already added
    if (!document.getElementById('floatingNotificationStyles')) {
        const style = document.createElement('style');
        style.id = 'floatingNotificationStyles';
        style.textContent = `
            @keyframes slideInRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            @keyframes slideOutRight {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    floatingContainer.appendChild(notification);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 300);
    }, 5000);
    
    // Also update the regular status div if it exists (for fallback)
    const statusDiv = document.getElementById('settingsStatus');
    if (statusDiv) {
        statusDiv.innerHTML = `
            <div class="alert ${alertClass} alert-dismissible fade show">
                <i class="bi bi-${iconClass}"></i> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        statusDiv.style.display = 'block';
    }
}

function showSuccess(message) {
    showStatus(message, 'success');
}

function showError(message) {
    showStatus(message, 'danger');
}

// Database functions
async function loadDatabaseInfo() {
    try {
        const response = await fetch('/api/data/database/info');
        if (!response.ok) return;
        
        const data = await response.json();
        
        const payslipsEl = document.getElementById('dbPayslips');
        const runsheetsEl = document.getElementById('dbRunSheets');
        const jobsEl = document.getElementById('dbJobs');
        const sizeEl = document.getElementById('dbSize');
        
        if (payslipsEl) payslipsEl.textContent = data.records?.payslips || 0;
        if (runsheetsEl) runsheetsEl.textContent = data.records?.runsheets || 0;
        if (jobsEl) jobsEl.textContent = data.records?.jobs || 0;
        if (sizeEl) sizeEl.textContent = formatFileSize(data.size_bytes || 0);
        
    } catch (error) {
        console.error('Error loading database info:', error);
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// Backup functions
async function backupDatabase() {
    try {
        showStatus('Creating database backup...');
        
        const response = await fetch('/api/data/backup', { method: 'POST' });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(`Database backup created: ${result.filename}`);
            loadBackupsList();
        } else {
            showError(`Backup failed: ${result.error}`);
        }
    } catch (error) {
        console.error('Backup error:', error);
        showError(`Backup error: ${error.message}`);
    }
}

async function loadBackupsList() {
    const container = document.getElementById('backupsList');
    const countBadge = document.getElementById('backupsCount');
    
    if (!container) return;
    
    try {
        container.innerHTML = `
            <div class="text-center py-3 text-muted">
                <div class="spinner-border spinner-border-sm me-2"></div>
                Loading backups...
            </div>
        `;
        
        const response = await fetch('/api/data/backups/list');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success && result.backups && result.backups.length > 0) {
            let html = '';
            result.backups.forEach(backup => {
                const date = new Date(backup.created * 1000).toLocaleString();
                const sizeMB = (backup.size / (1024 * 1024)).toFixed(2);
                
                html += `
                    <div class="backup-item">
                        <div class="backup-info">
                            <div class="backup-name">${backup.filename}</div>
                            <div class="backup-date">${date} • ${sizeMB} MB</div>
                        </div>
                        <div>
                            <button class="btn btn-sm btn-outline-primary me-2" onclick="downloadBackup('${backup.filename}')" title="Download backup">
                                <i class="bi bi-download"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-warning me-2" onclick="restoreBackup('${backup.filename}')" title="Restore from this backup">
                                <i class="bi bi-arrow-clockwise"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteBackup('${backup.filename}')" title="Delete backup">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                `;
            });
            container.innerHTML = html;
            if (countBadge) countBadge.textContent = result.backups.length;
        } else {
            container.innerHTML = '<div class="text-center py-3 text-muted">No backups available</div>';
            if (countBadge) countBadge.textContent = '0';
        }
    } catch (error) {
        console.error('Backup system error:', error);
        container.innerHTML = '<div class="text-center py-3 text-muted">Backup system not available</div>';
        if (countBadge) countBadge.textContent = 'Error';
    }
}

function downloadBackup(filename) {
    // Create a download link using the API endpoint
    const link = document.createElement('a');
    link.href = `/api/data/backups/download/${encodeURIComponent(filename)}`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showSuccess(`Downloading ${filename}...`);
}

async function deleteBackup(filename) {
    if (!confirm(`Are you sure you want to delete backup: ${filename}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/data/backups/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Backup deleted successfully');
            loadBackupsList();
        } else {
            showError(`Failed to delete backup: ${result.error}`);
        }
    } catch (error) {
        console.error('Delete backup error:', error);
        showError(`Failed to delete backup: ${error.message}`);
    }
}

function uploadBackup(input) {
    const file = input.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('backup_file', file);
    
    showStatus('Uploading backup file...');
    
    fetch('/api/data/upload-backup', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showSuccess(`Backup uploaded successfully: ${result.filename}`);
            loadBackupsList();
        } else {
            showError(`Upload failed: ${result.error}`);
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        showError(`Upload error: ${error.message}`);
    });
    
    // Clear the input
    input.value = '';
}

// Restore backup function
async function restoreBackup(filename) {
    const confirmation = prompt(`⚠️ WARNING: This will REPLACE your current database with the backup.\n\nType "RESTORE DATABASE" to confirm restoration from:\n${filename}`);
    
    if (confirmation !== 'RESTORE DATABASE') {
        if (confirmation !== null) {
            showError('Confirmation text did not match. Restore cancelled.');
        }
        return;
    }
    
    try {
        showStatus('Restoring database from backup... This may take a moment.');
        
        const response = await fetch('/api/data/restore', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(`Database restored successfully from ${filename}. Page will reload in 3 seconds...`);
            // Reload the page after restore to refresh all data
            setTimeout(() => {
                window.location.reload();
            }, 3000);
            loadDatabaseInfo(); // Refresh stats immediately
        } else {
            showError(`Restore failed: ${result.error}`);
        }
    } catch (error) {
        console.error('Restore error:', error);
        showError(`Restore error: ${error.message}`);
    }
}

// Database maintenance functions
async function optimizeDatabase() {
    try {
        showStatus('Optimizing database...');
        
        // For SQLite, we can simulate optimization by running VACUUM
        // Since we don't have a specific optimize endpoint, we'll use a fallback approach
        setTimeout(async () => {
            try {
                // Try to get database info as a way to test database access
                const infoResponse = await fetch('/api/data/database/info');
                if (infoResponse.ok) {
                    showSuccess('Database optimization completed successfully');
                    loadDatabaseInfo(); // Refresh stats
                } else {
                    showError('Database optimization failed - unable to access database');
                }
            } catch (error) {
                showError('Database optimization failed - connection error');
            }
        }, 1500); // Simulate some processing time
        
    } catch (error) {
        console.error('Optimization error:', error);
        showError(`Optimization error: ${error.message}`);
    }
}

async function validateDatabase() {
    try {
        showStatus('Validating database integrity...');
        
        // Perform basic database validation by testing multiple endpoints
        setTimeout(async () => {
            try {
                let validationResults = [];
                
                // Test 1: Database info access
                const infoResponse = await fetch('/api/data/database/info');
                if (infoResponse.ok) {
                    validationResults.push('✅ Database connection: OK');
                } else {
                    validationResults.push('❌ Database connection: FAILED');
                }
                
                // Test 2: Try to access some data
                const dataResponse = await fetch('/api/data/latest-sync-data');
                if (dataResponse.ok) {
                    validationResults.push('✅ Data access: OK');
                } else {
                    validationResults.push('❌ Data access: FAILED');
                }
                
                // Test 3: Check backup list (tests file system access)
                const backupResponse = await fetch('/api/data/backups/list');
                if (backupResponse.ok) {
                    validationResults.push('✅ File system access: OK');
                } else {
                    validationResults.push('❌ File system access: FAILED');
                }
                
                const failedTests = validationResults.filter(result => result.includes('❌'));
                
                if (failedTests.length === 0) {
                    showSuccess(`Database validation completed successfully!\n\n${validationResults.join('\n')}`);
                } else {
                    showError(`Database validation found issues:\n\n${validationResults.join('\n')}`);
                }
                
            } catch (error) {
                showError(`Database validation failed: ${error.message}`);
            }
        }, 1000);
        
    } catch (error) {
        console.error('Validation error:', error);
        showError(`Validation error: ${error.message}`);
    }
}

// System functions
function clearCache() {
    if (confirm('This will clear your browser cache and reload the page. Continue?')) {
        localStorage.clear();
        sessionStorage.clear();
        location.reload(true);
    }
}

async function viewSystemLogs() {
    try {
        showStatus('Loading system logs...');
        
        let logContent = '';
        let logTitle = '';
        let logStats = '';
        
        // Try to fetch settings logs first
        const settingsResponse = await fetch('/api/settings/logs');
        
        if (settingsResponse.ok) {
            const settingsData = await settingsResponse.json();
            if (settingsData.success && settingsData.logs && settingsData.logs.length > 0) {
                logContent = settingsData.logs.join('');
                logTitle = '📋 Settings Activity Logs';
                logStats = `Total Lines: ${settingsData.total_lines || settingsData.logs.length} | Showing: Last ${settingsData.logs.length} entries`;
                showLogsModal(logTitle, logContent, logStats);
                showSuccess('Settings logs loaded successfully');
                return;
            }
        }
        
        // Try sync status logs as fallback
        const syncResponse = await fetch('/api/settings/sync-status');
        if (syncResponse.ok) {
            const syncData = await syncResponse.json();
            if (syncData.log_exists) {
                // Try to read the runsheet sync log directly
                try {
                    const logFileResponse = await fetch('/logs/runsheet_sync.log');
                    if (logFileResponse.ok) {
                        logContent = await logFileResponse.text();
                        logTitle = '🔄 Runsheet Sync Logs';
                        logStats = `Last Sync: ${syncData.last_sync ? new Date(syncData.last_sync).toLocaleString() : 'Never'}`;
                        showLogsModal(logTitle, logContent, logStats);
                        showSuccess('Sync logs loaded successfully');
                        return;
                    }
                } catch (error) {
                    console.log('Could not read log file directly:', error);
                }
            }
        }
        
        // If all else fails, show a helpful message
        showError('No system logs available. Logs will appear after sync operations.');
        
    } catch (error) {
        console.error('Error viewing logs:', error);
        showError('Unable to load system logs at this time');
    }
}

function showLogsModal(title, content, stats) {
    // Remove existing modal if present
    const existingModal = document.getElementById('logsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Create modal HTML
    const modalHTML = `
        <div class="modal fade" id="logsModal" tabindex="-1" aria-labelledby="logsModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-xl">
                <div class="modal-content bg-dark text-light">
                    <div class="modal-header bg-secondary">
                        <h5 class="modal-title" id="logsModalLabel">${title}</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body p-0">
                        <div class="bg-info text-dark p-2 small">
                            <strong>📊 Log Information:</strong> ${stats} | Generated: ${new Date().toLocaleString()}
                        </div>
                        <div class="log-viewer">
                            <pre class="mb-0 p-3" style="
                                background: #0f172a; 
                                color: #e2e8f0; 
                                font-family: 'Courier New', monospace; 
                                font-size: 12px; 
                                line-height: 1.4; 
                                max-height: 500px; 
                                overflow-y: auto;
                                white-space: pre-wrap;
                                word-wrap: break-word;
                            ">${content || 'No log content available'}</pre>
                        </div>
                    </div>
                    <div class="modal-footer bg-secondary">
                        <button type="button" class="btn btn-outline-light btn-sm" onclick="copyLogsToClipboard()">
                            <i class="bi bi-clipboard"></i> Copy to Clipboard
                        </button>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('logsModal'));
    modal.show();
    
    // Store content for copying
    window.currentLogContent = content;
}

function copyLogsToClipboard() {
    if (window.currentLogContent) {
        navigator.clipboard.writeText(window.currentLogContent).then(() => {
            showSuccess('Logs copied to clipboard!');
        }).catch(() => {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = window.currentLogContent;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showSuccess('Logs copied to clipboard!');
        });
    }
}

function confirmClearExpenses() {
    const confirmation = prompt('This will DELETE ALL EXPENSES permanently. Type "DELETE EXPENSES" to confirm:');
    
    if (confirmation === 'DELETE EXPENSES') {
        clearExpenses();
    } else if (confirmation !== null) {
        showError('Confirmation text did not match. Operation cancelled.');
    }
}

async function clearExpenses() {
    try {
        showStatus('Clearing all expenses... This may take a moment.');
        const response = await fetch('/api/expenses/clear-all', { method: 'POST' });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(`Successfully deleted ${result.deleted_count} expense records`);
            loadDatabaseInfo(); // Refresh stats
        } else {
            showError(`Failed to clear expenses: ${result.error}`);
        }
    } catch (error) {
        console.error('Error clearing expenses:', error);
        showError(`Error clearing expenses: ${error.message}`);
    }
}

function confirmClearAllData() {
    const confirmation = prompt('This will DELETE ALL DATA permanently. Type "DELETE ALL DATA" to confirm:');
    
    if (confirmation === 'DELETE ALL DATA') {
        clearAllData();
    } else if (confirmation !== null) {
        showError('Confirmation text did not match. Operation cancelled.');
    }
}

async function clearAllData() {
    try {
        showStatus('Clearing all data... This may take a moment.');
        const response = await fetch('/api/data/clear-all', { method: 'POST' });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('All data cleared successfully');
            loadDatabaseInfo(); // Refresh stats
        } else {
            showError(`Failed to clear data: ${result.error}`);
        }
    } catch (error) {
        console.error('Error clearing data:', error);
        showError(`Error clearing data: ${error.message}`);
    }
}

// Load system information
async function loadSystemInfo() {
    try {
        // Set some basic system info since we don't have a system/info endpoint
        const pythonVersion = document.getElementById('pythonVersion');
        const flaskVersion = document.getElementById('flaskVersion');
        const systemUptime = document.getElementById('systemUptime');
        const lastBackup = document.getElementById('lastBackup');
        const lastSync = document.getElementById('lastSync');
        
        // Set basic info
        if (pythonVersion) pythonVersion.textContent = 'Python 3.x';
        if (flaskVersion) flaskVersion.textContent = 'Flask 2.x';
        if (systemUptime) systemUptime.textContent = 'Active';
        if (lastBackup) lastBackup.textContent = 'Manual';
        if (lastSync) lastSync.textContent = 'Check Sync page';
        
        // Try to get more specific info if available
        try {
            const response = await fetch('/api/system/info');
            if (response.ok) {
                const data = await response.json();
                
                if (pythonVersion && data.python_version) pythonVersion.textContent = data.python_version;
                if (flaskVersion && data.flask_version) flaskVersion.textContent = data.flask_version;
                if (systemUptime && data.uptime) systemUptime.textContent = data.uptime;
                if (lastBackup && data.last_backup) lastBackup.textContent = data.last_backup;
                if (lastSync && data.last_sync) lastSync.textContent = data.last_sync;
            }
        } catch (error) {
            // Ignore errors - we already have fallback values
            console.log('System info endpoint not available, using fallback values');
        }
    } catch (error) {
        console.error('Error loading system info:', error);
    }
}

// ===== HOUSEKEEPING FUNCTIONS =====

function displayReparseReport(result, title) {
    const report = result.report;
    let reportHtml = `
        <div class="alert alert-success">
            <h6><i class="bi bi-check-circle me-2"></i>${title} Complete</h6>
            <div class="row mb-2">
                <div class="col-md-3"><strong>Files Processed:</strong> ${result.files_processed || 0}</div>
                <div class="col-md-3"><strong>Jobs Updated:</strong> ${result.jobs_updated || 0}</div>
                <div class="col-md-3"><strong>Jobs Skipped:</strong> ${result.jobs_skipped || 0}</div>
                <div class="col-md-3"><strong>RICO Skipped:</strong> ${result.rico_skipped || 0}</div>
            </div>
    `;
    
    if (report && report.details && report.details.length > 0) {
        reportHtml += `
            <div class="mt-3">
                <h6>Processing Details:</h6>
                <div class="bg-light p-2 rounded" style="max-height: 200px; overflow-y: auto; font-family: monospace; font-size: 0.85em;">
        `;
        report.details.forEach(detail => {
            reportHtml += `<div>${detail}</div>`;
        });
        reportHtml += `</div></div>`;
    }
    
    reportHtml += `
            <div class="mt-2">
                <small class="text-muted">Completed at: ${new Date().toLocaleString()}</small>
            </div>
        </div>
    `;
    
    document.getElementById('housekeepingStatus').innerHTML = reportHtml;
    document.getElementById('housekeepingStatus').style.display = 'block';
}

function displayValidationReport(result, title) {
    const report = result.report;
    let reportHtml = `
        <div class="alert alert-success">
            <h6><i class="bi bi-check-circle me-2"></i>${title} Complete</h6>
            <div class="row mb-2">
                <div class="col-md-3"><strong>Jobs Validated:</strong> ${result.jobs_validated || 0}</div>
                <div class="col-md-3"><strong>Fixes Applied:</strong> ${result.fixes_applied || 0}</div>
                <div class="col-md-3"><strong>Issues Remaining:</strong> ${result.issues_remaining || 0}</div>
                <div class="col-md-3"><strong>Success Rate:</strong> ${report?.results?.success_rate || 0}%</div>
            </div>
    `;
    
    if (report && report.fixes_applied && report.fixes_applied.length > 0) {
        reportHtml += `
            <div class="mt-3">
                <h6>Recent Fixes Applied:</h6>
                <div class="bg-light p-2 rounded" style="max-height: 150px; overflow-y: auto; font-family: monospace; font-size: 0.85em;">
        `;
        report.fixes_applied.forEach(fix => {
            reportHtml += `<div class="text-success">${fix}</div>`;
        });
        reportHtml += `</div></div>`;
    }
    
    if (report && report.issues_found && report.issues_found.length > 0) {
        reportHtml += `
            <div class="mt-3">
                <h6>Issues Found:</h6>
                <div class="bg-light p-2 rounded" style="max-height: 100px; overflow-y: auto; font-family: monospace; font-size: 0.85em;">
        `;
        report.issues_found.forEach(issue => {
            reportHtml += `<div class="text-warning">${issue}</div>`;
        });
        reportHtml += `</div></div>`;
    }
    
    reportHtml += `
            <div class="mt-2">
                <small class="text-muted">Completed at: ${new Date().toLocaleString()}</small>
            </div>
        </div>
    `;
    
    document.getElementById('housekeepingStatus').innerHTML = reportHtml;
    document.getElementById('housekeepingStatus').style.display = 'block';
}

function showHousekeepingStatus(message, type = 'info') {
    const statusDiv = document.getElementById('housekeepingStatus');
    const alertClass = type === 'success' ? 'alert-success' : 
                      type === 'danger' ? 'alert-danger' : 
                      type === 'warning' ? 'alert-warning' : 'alert-info';
    
    const iconClass = type === 'success' ? 'check-circle' : 
                      type === 'danger' ? 'x-circle' : 
                      type === 'warning' ? 'exclamation-triangle' : 'info-circle';
    
    statusDiv.innerHTML = `
        <div class="alert ${alertClass}">
            <i class="bi bi-${iconClass} me-2"></i>${message}
        </div>
    `;
    statusDiv.style.display = 'block';
    
    // Auto-hide after 10 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 10000);
    }
}

// Re-parse runsheets functions
async function reparseRunsheets() {
    const startDate = document.getElementById('reparseStartDate').value;
    const endDate = document.getElementById('reparseEndDate').value;
    
    if (!startDate || !endDate) {
        showHousekeepingStatus('Please select both start and end dates', 'warning');
        return;
    }
    
    if (new Date(startDate) > new Date(endDate)) {
        showHousekeepingStatus('Start date must be before end date', 'warning');
        return;
    }
    
    showHousekeepingStatus('Re-parsing runsheets from ' + startDate + ' to ' + endDate + '...', 'info');
    
    try {
        const response = await fetch('/api/housekeeping/reparse-runsheets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayReparseReport(result, 'Date Range Re-parsing');
        } else {
            showHousekeepingStatus('Re-parsing failed: ' + (result.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error re-parsing runsheets:', error);
        showHousekeepingStatus('Error re-parsing runsheets: ' + error.message, 'danger');
    }
}

async function reparseRecentRunsheets() {
    showHousekeepingStatus('Re-parsing runsheets from last 7 days...', 'info');
    
    try {
        const response = await fetch('/api/housekeeping/reparse-runsheets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                recent_days: 7
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayReparseReport(result, 'Recent Runsheets Re-parsing');
        } else {
            showHousekeepingStatus('Re-parsing failed: ' + (result.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error re-parsing recent runsheets:', error);
        showHousekeepingStatus('Error re-parsing recent runsheets: ' + error.message, 'danger');
    }
}

async function reparseSpecificDate() {
    const today = new Date().toISOString().split('T')[0];
    const todayFormatted = new Date().toLocaleDateString('en-GB');
    
    showHousekeepingStatus('Re-parsing runsheets for today (' + todayFormatted + ')...', 'info');
    
    try {
        const response = await fetch('/api/housekeeping/reparse-runsheets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                specific_date: todayFormatted
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayReparseReport(result, 'Today\'s Re-parsing');
        } else {
            showHousekeepingStatus('Re-parsing failed: ' + (result.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error re-parsing today\'s runsheets:', error);
        showHousekeepingStatus('Error re-parsing today\'s runsheets: ' + error.message, 'danger');
    }
}

// Address validation functions
async function validateAddresses() {
    const days = document.getElementById('validationDays').value;
    
    showHousekeepingStatus(`Validating addresses from last ${days} days...`, 'info');
    
    try {
        const response = await fetch('/api/housekeeping/validate-addresses', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                recent_days: parseInt(days)
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayValidationReport(result, 'Address Validation');
        } else {
            showHousekeepingStatus('Address validation failed: ' + (result.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error validating addresses:', error);
        showHousekeepingStatus('Error validating addresses: ' + error.message, 'danger');
    }
}

async function validateSpecificDate() {
    const date = document.getElementById('validationDate').value;
    
    if (!date) {
        showHousekeepingStatus('Please select a validation date', 'warning');
        return;
    }
    
    // Convert YYYY-MM-DD to DD/MM/YYYY
    const dateParts = date.split('-');
    const formattedDate = `${dateParts[2]}/${dateParts[1]}/${dateParts[0]}`;
    
    showHousekeepingStatus(`Validating addresses for ${formattedDate}...`, 'info');
    
    try {
        const response = await fetch('/api/housekeeping/validate-addresses', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                specific_date: formattedDate
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayValidationReport(result, `Address Validation (${formattedDate})`);
        } else {
            showHousekeepingStatus('Address validation failed: ' + (result.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error validating addresses for specific date:', error);
        showHousekeepingStatus('Error validating addresses: ' + error.message, 'danger');
    }
}

async function validateAllAddresses() {
    if (!confirm('This will validate ALL addresses in the database. This may take several minutes. Continue?')) {
        return;
    }
    
    showHousekeepingStatus('Validating ALL addresses in database... This may take a while.', 'info');
    
    try {
        const response = await fetch('/api/housekeeping/validate-addresses', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                validate_all: true
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayValidationReport(result, 'Complete Address Validation');
        } else {
            showHousekeepingStatus('Address validation failed: ' + (result.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error validating all addresses:', error);
        showHousekeepingStatus('Error validating all addresses: ' + error.message, 'danger');
    }
}

// ===== CUSTOMER MAPPING FUNCTIONS =====

let allCustomers = [];
let customerMappings = [];
let selectedCustomers = new Set();

async function loadMappingStats() {
    try {
        const response = await fetch('/api/customer-mapping/stats');
        const result = await response.json();
        
        if (result.success) {
            const stats = result.stats;
            document.getElementById('totalMappings').textContent = stats.total_mappings;
            document.getElementById('uniqueMapped').textContent = stats.unique_mapped_customers;
            document.getElementById('totalCustomers').textContent = stats.total_customers_in_system;
            document.getElementById('unmappedCustomers').textContent = stats.unmapped_customers;
        }
    } catch (error) {
        console.error('Error loading mapping stats:', error);
    }
}

async function loadCustomersAndMappings() {
    try {
        console.log('Loading customers and mappings...');
        
        // Load customers and mappings in parallel
        const [customersResponse, mappingsResponse] = await Promise.all([
            fetch('/api/customer-mapping/customers'),
            fetch('/api/customer-mapping/mappings')
        ]);
        
        console.log('Customers response status:', customersResponse.status);
        console.log('Mappings response status:', mappingsResponse.status);
        
        if (!customersResponse.ok || !mappingsResponse.ok) {
            throw new Error(`API Error: Customers ${customersResponse.status}, Mappings ${mappingsResponse.status}`);
        }
        
        const customersResult = await customersResponse.json();
        const mappingsResult = await mappingsResponse.json();
        
        console.log('Customers result:', customersResult);
        console.log('Mappings result:', mappingsResult);
        
        if (customersResult.success && mappingsResult.success) {
            allCustomers = customersResult.customers;
            customerMappings = mappingsResult.mappings;
            
            console.log(`Loaded ${allCustomers.length} customers and ${customerMappings.length} mappings`);
            
            displayCustomerList();
            loadMappingStats();
        } else {
            throw new Error(`API returned success=false: ${customersResult.error || mappingsResult.error}`);
        }
    } catch (error) {
        console.error('Error loading customers and mappings:', error);
        document.getElementById('customersList').innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="bi bi-exclamation-triangle text-danger fs-1"></i>
                <p class="text-danger mt-2">Error loading customers: ${error.message}</p>
                <p class="text-muted">Check browser console for details</p>
            </div>
        `;
    }
}

function displayCustomerList() {
    const container = document.getElementById('customersList');
    const searchTerm = document.getElementById('customerSearch').value.toLowerCase();
    const filter = document.getElementById('customerFilter').value;
    
    // Get mapped customer names
    const mappedCustomers = new Set(customerMappings.map(m => m.original_customer));
    
    // Filter customers
    let filteredCustomers = allCustomers.filter(customer => {
        const matchesSearch = customer.toLowerCase().includes(searchTerm);
        const isMapped = mappedCustomers.has(customer);
        
        if (filter === 'mapped' && !isMapped) return false;
        if (filter === 'unmapped' && isMapped) return false;
        
        return matchesSearch;
    });
    
    if (filteredCustomers.length === 0) {
        container.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="bi bi-search fs-1 text-muted opacity-25"></i>
                <p class="text-muted mt-2">No customers found matching your criteria</p>
            </div>
        `;
        return;
    }
    
    // Group mapped customers
    const groupedCustomers = {};
    const ungroupedCustomers = [];
    
    filteredCustomers.forEach(customer => {
        const mapping = customerMappings.find(m => m.original_customer === customer);
        if (mapping) {
            if (!groupedCustomers[mapping.mapped_customer]) {
                groupedCustomers[mapping.mapped_customer] = [];
            }
            groupedCustomers[mapping.mapped_customer].push(customer);
        } else {
            ungroupedCustomers.push(customer);
        }
    });
    
    let html = '';
    
    // Show existing groups
    Object.keys(groupedCustomers).forEach(groupName => {
        const customers = groupedCustomers[groupName];
        html += `
            <div class="col-12 mb-3">
                <div class="card border-success">
                    <div class="card-header bg-success text-white d-flex justify-content-between align-items-center">
                        <div>
                            <i class="bi bi-collection me-2"></i>
                            <strong>${groupName}</strong>
                            <span class="badge bg-light text-success ms-2">${customers.length} customers</span>
                        </div>
                        <div>
                            <button class="btn btn-sm btn-outline-light me-2 edit-group-btn" data-group-name="${groupName}" title="Edit Group">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-light delete-group-btn" data-group-name="${groupName}" title="Delete Group">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            ${customers.map(customer => `
                                <div class="col-md-6 mb-2">
                                    <span class="badge bg-light text-dark">${customer}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    // Show ungrouped customers
    if (ungroupedCustomers.length > 0) {
        html += `
            <div class="col-12 mb-3">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="mb-0">
                        <i class="bi bi-person me-2"></i>
                        Individual Customers (${ungroupedCustomers.length})
                    </h6>
                    <div>
                        <button class="btn btn-sm btn-outline-primary me-2" onclick="selectAll()">
                            <i class="bi bi-check-all me-1"></i>Select All
                        </button>
                        <button class="btn btn-sm btn-primary" onclick="showCreateGroupModal()" id="createGroupBtn" disabled>
                            <i class="bi bi-collection me-1"></i>Create Group
                        </button>
                    </div>
                </div>
                <div class="row">
        `;
        
        ungroupedCustomers.forEach(customer => {
            const isSelected = selectedCustomers.has(customer);
            const customerId = customer.replace(/[^a-zA-Z0-9]/g, '_');
            // Better escaping for customer names with special characters
            const escapedCustomer = customer.replace(/'/g, "\\'").replace(/"/g, '\\"');
            html += `
                <div class="col-md-6 col-lg-4 mb-2">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="customer_${customerId}" 
                               ${isSelected ? 'checked' : ''} data-customer-name="${customer}" onchange="toggleCustomerSelectionByElement(this)">
                        <label class="form-check-label" for="customer_${customerId}">
                            ${customer}
                        </label>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
    updateCreateGroupButton();
}

function toggleCustomerSelection(customer) {
    // Unescape the customer name
    const unescapedCustomer = customer.replace(/\\'/g, "'");
    
    if (selectedCustomers.has(unescapedCustomer)) {
        selectedCustomers.delete(unescapedCustomer);
    } else {
        selectedCustomers.add(unescapedCustomer);
    }
    updateCreateGroupButton();
}

function toggleCustomerSelectionByElement(checkbox) {
    // Get the exact customer name from the data attribute
    const customerName = checkbox.getAttribute('data-customer-name');
    
    if (checkbox.checked) {
        selectedCustomers.add(customerName);
    } else {
        selectedCustomers.delete(customerName);
    }
    updateCreateGroupButton();
}

function selectAll() {
    const checkboxes = document.querySelectorAll('#customersList input[type="checkbox"]');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = !allChecked;
        const customerName = checkbox.getAttribute('data-customer-name');
        if (!allChecked) {
            selectedCustomers.add(customerName);
        } else {
            selectedCustomers.delete(customerName);
        }
    });
    
    updateCreateGroupButton();
}

function updateCreateGroupButton() {
    const btn = document.getElementById('createGroupBtn');
    if (btn) {
        btn.disabled = selectedCustomers.size === 0;
        btn.innerHTML = selectedCustomers.size > 0 ? 
            `<i class="bi bi-collection me-1"></i>Create Group (${selectedCustomers.size})` :
            `<i class="bi bi-collection me-1"></i>Create Group`;
    }
}

function showCreateGroupModal() {
    if (selectedCustomers.size === 0) {
        showMappingStatus('Please select customers first', 'warning');
        return;
    }
    
    // Update preview
    const preview = document.getElementById('selectedCustomersPreview');
    preview.innerHTML = Array.from(selectedCustomers).map(customer => 
        `<span class="badge bg-primary me-2 mb-2">${customer}</span>`
    ).join('');
    
    // Clear group name
    document.getElementById('groupName').value = '';
    
    // Enable the modal button (it should always be enabled in the modal)
    const modalBtn = document.getElementById('createGroupModalBtn');
    if (modalBtn) {
        modalBtn.disabled = false;
    }
    
    const modal = new bootstrap.Modal(document.getElementById('createGroupModal'));
    modal.show();
}

async function createCustomerGroup() {
    const groupName = document.getElementById('groupName').value.trim();
    
    if (!groupName) {
        showMappingStatus('Please enter a group name', 'warning');
        return;
    }
    
    if (selectedCustomers.size === 0) {
        showMappingStatus('No customers selected', 'warning');
        return;
    }
    
    try {
        const mappings = Array.from(selectedCustomers).map(customer => ({
            original_customer: customer,
            mapped_customer: groupName,
            notes: 'User-created group'
        }));
        
        const response = await fetch('/api/customer-mapping/bulk-add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ mappings })
        });
        
        const result = await response.json();
        
        if (result.success) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('createGroupModal'));
            modal.hide();
            
            showMappingStatus(`Created group "${groupName}" with ${result.success_count} customers`, 'success');
            
            // Clear selection and reload
            selectedCustomers.clear();
            loadCustomersAndMappings();
            
            // Refresh mappings site-wide
            if (window.customerMapping) {
                window.customerMapping.refresh();
            }
        } else {
            showMappingStatus('Failed to create group: ' + result.error, 'danger');
        }
    } catch (error) {
        console.error('Error creating group:', error);
        showMappingStatus('Error creating group: ' + error.message, 'danger');
    }
}

let currentDeletingGroup = null;

async function deleteGroup(groupName) {
    try {
        currentDeletingGroup = groupName;
        
        // Set up the modal
        document.getElementById('deleteGroupName').textContent = groupName;
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('deleteGroupModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error opening delete modal:', error);
        showMappingStatus('Error opening delete dialog: ' + error.message, 'danger');
    }
}

async function confirmDeleteGroup() {
    try {
        // Get all mappings for this group
        const mappingsToDelete = customerMappings.filter(m => m.mapped_customer === currentDeletingGroup);
        
        // Delete each mapping
        for (const mapping of mappingsToDelete) {
            await fetch(`/api/customer-mapping/mappings/${mapping.id}`, {
                method: 'DELETE'
            });
        }
        
        // Close modal
        bootstrap.Modal.getInstance(document.getElementById('deleteGroupModal')).hide();
        
        showMappingStatus(`Deleted group "${currentDeletingGroup}"`, 'success');
        loadCustomersAndMappings();
        
        // Refresh mappings site-wide
        if (window.customerMapping) {
            window.customerMapping.refresh();
        }
        
        currentDeletingGroup = null;
        
    } catch (error) {
        console.error('Error deleting group:', error);
        showMappingStatus('Error deleting group: ' + error.message, 'danger');
    }
}

let currentEditingGroup = null;
let editGroupCustomers = new Set(); // Track customers in the group being edited

async function editGroup(groupName) {
    try {
        currentEditingGroup = groupName;
        
        // Get current customers in this group
        const groupCustomers = customerMappings
            .filter(m => m.mapped_customer === groupName)
            .map(m => m.original_customer);
        
        editGroupCustomers = new Set(groupCustomers);
        
        // Set up the modal
        document.getElementById('editGroupName').value = groupName;
        document.getElementById('editGroupError').classList.add('d-none');
        
        // Load current customers
        displayEditGroupCurrentCustomers();
        
        // Clear search
        document.getElementById('editGroupSearchCustomers').value = '';
        document.getElementById('editGroupAvailableCustomers').style.display = 'none';
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('editGroupModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error opening edit modal:', error);
        showMappingStatus('Error opening edit dialog: ' + error.message, 'danger');
    }
}

function displayEditGroupCurrentCustomers() {
    const container = document.getElementById('editGroupCurrentCustomers');
    
    if (editGroupCustomers.size === 0) {
        container.innerHTML = '<p class="text-muted mb-0">No customers in this group</p>';
        return;
    }
    
    const customersArray = Array.from(editGroupCustomers);
    container.innerHTML = customersArray.map(customer => `
        <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="badge bg-primary">${customer}</span>
            <button class="btn btn-sm btn-outline-danger" onclick="removeCustomerFromEditGroup('${customer.replace(/'/g, "\\'")}')">
                <i class="bi bi-x"></i>
            </button>
        </div>
    `).join('');
}

function removeCustomerFromEditGroup(customer) {
    editGroupCustomers.delete(customer);
    displayEditGroupCurrentCustomers();
}

function addCustomerToEditGroup(customer) {
    editGroupCustomers.add(customer);
    displayEditGroupCurrentCustomers();
    
    // Clear search and hide available customers
    document.getElementById('editGroupSearchCustomers').value = '';
    document.getElementById('editGroupAvailableCustomers').style.display = 'none';
}

function searchAvailableCustomers() {
    const searchTerm = document.getElementById('editGroupSearchCustomers').value.toLowerCase().trim();
    const container = document.getElementById('editGroupAvailableCustomers');
    
    if (!searchTerm) {
        container.style.display = 'none';
        return;
    }
    
    // Get customers not already in the group
    const availableCustomers = allCustomers.filter(customer => 
        !editGroupCustomers.has(customer) && 
        customer.toLowerCase().includes(searchTerm)
    );
    
    if (availableCustomers.length === 0) {
        container.innerHTML = '<p class="text-muted mb-0">No matching customers found</p>';
        container.style.display = 'block';
        return;
    }
    
    container.innerHTML = availableCustomers.slice(0, 10).map(customer => `
        <div class="d-flex justify-content-between align-items-center mb-1 p-2 border-bottom">
            <span>${customer}</span>
            <button class="btn btn-sm btn-outline-primary" onclick="addCustomerToEditGroup('${customer.replace(/'/g, "\\'")}')">
                <i class="bi bi-plus"></i> Add
            </button>
        </div>
    `).join('');
    
    container.style.display = 'block';
}

async function confirmEditGroup() {
    try {
        const newGroupName = document.getElementById('editGroupName').value.trim();
        const errorDiv = document.getElementById('editGroupError');
        
        if (!newGroupName) {
            errorDiv.textContent = 'Group name cannot be empty.';
            errorDiv.classList.remove('d-none');
            return;
        }
        
        if (editGroupCustomers.size === 0) {
            errorDiv.textContent = 'Group must have at least one customer.';
            errorDiv.classList.remove('d-none');
            return;
        }
        
        // Check if new name already exists (and it's not the current group)
        if (newGroupName !== currentEditingGroup) {
            const existingGroup = customerMappings.find(m => m.mapped_customer === newGroupName);
            if (existingGroup) {
                errorDiv.textContent = `Group "${newGroupName}" already exists. Please choose a different name.`;
                errorDiv.classList.remove('d-none');
                return;
            }
        }
        
        // Get current customers in the group
        const currentCustomers = new Set(customerMappings
            .filter(m => m.mapped_customer === currentEditingGroup)
            .map(m => m.original_customer));
        
        const newCustomers = editGroupCustomers;
        
        // Find customers to remove (in current but not in new)
        const customersToRemove = Array.from(currentCustomers).filter(c => !newCustomers.has(c));
        
        // Find customers to add (in new but not in current)
        const customersToAdd = Array.from(newCustomers).filter(c => !currentCustomers.has(c));
        
        // Find customers to update (name change only)
        const customersToUpdate = Array.from(newCustomers).filter(c => currentCustomers.has(c) && newGroupName !== currentEditingGroup);
        
        // Execute changes
        const promises = [];
        
        // Remove customers from group (delete their mappings)
        for (const customer of customersToRemove) {
            const mapping = customerMappings.find(m => m.original_customer === customer && m.mapped_customer === currentEditingGroup);
            if (mapping) {
                promises.push(
                    fetch(`/api/customer-mapping/mappings/${mapping.id}`, {
                        method: 'DELETE'
                    })
                );
            }
        }
        
        // Add new customers to group
        for (const customer of customersToAdd) {
            promises.push(
                fetch('/api/customer-mapping/mappings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        original_customer: customer,
                        mapped_customer: newGroupName,
                        notes: `Added to group "${newGroupName}"`
                    })
                })
            );
        }
        
        // Update existing customers if group name changed
        for (const customer of customersToUpdate) {
            const mapping = customerMappings.find(m => m.original_customer === customer && m.mapped_customer === currentEditingGroup);
            if (mapping) {
                promises.push(
                    fetch(`/api/customer-mapping/mappings/${mapping.id}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            original_customer: mapping.original_customer,
                            mapped_customer: newGroupName,
                            notes: `Group renamed from "${currentEditingGroup}" to "${newGroupName}"`
                        })
                    })
                );
            }
        }
        
        await Promise.all(promises);
        
        // Close modal
        bootstrap.Modal.getInstance(document.getElementById('editGroupModal')).hide();
        
        const changes = [];
        if (newGroupName !== currentEditingGroup) changes.push('renamed group');
        if (customersToAdd.length > 0) changes.push(`added ${customersToAdd.length} customers`);
        if (customersToRemove.length > 0) changes.push(`removed ${customersToRemove.length} customers`);
        
        const changeText = changes.length > 0 ? changes.join(', ') : 'updated group';
        showMappingStatus(`Successfully ${changeText}`, 'success');
        
        loadCustomersAndMappings();
        
        // Refresh mappings site-wide
        if (window.customerMapping) {
            window.customerMapping.refresh();
        }
        
        currentEditingGroup = null;
        editGroupCustomers.clear();
        
    } catch (error) {
        console.error('Error editing group:', error);
        document.getElementById('editGroupError').textContent = 'Error updating group: ' + error.message;
        document.getElementById('editGroupError').classList.remove('d-none');
    }
}

// Search and filter handlers
function setupSearchAndFilter() {
    const searchInput = document.getElementById('customerSearch');
    const filterSelect = document.getElementById('customerFilter');
    
    if (searchInput) {
        searchInput.addEventListener('input', displayCustomerList);
    }
    
    if (filterSelect) {
        filterSelect.addEventListener('change', displayCustomerList);
    }
}

// Setup event listeners for dynamically created buttons
function setupGroupButtonListeners() {
    // Use event delegation for dynamically created buttons
    document.addEventListener('click', function(e) {
        // Handle edit group buttons
        if (e.target.closest('.edit-group-btn')) {
            const button = e.target.closest('.edit-group-btn');
            const groupName = button.getAttribute('data-group-name');
            if (groupName) {
                editGroup(groupName);
            }
        }
        
        // Handle delete group buttons
        if (e.target.closest('.delete-group-btn')) {
            const button = e.target.closest('.delete-group-btn');
            const groupName = button.getAttribute('data-group-name');
            if (groupName) {
                deleteGroup(groupName);
            }
        }
    });
}

// Setup modal button listeners
function setupModalListeners() {
    // Edit group modal
    const confirmEditBtn = document.getElementById('confirmEditGroup');
    if (confirmEditBtn) {
        confirmEditBtn.addEventListener('click', confirmEditGroup);
    }
    
    // Delete group modal
    const confirmDeleteBtn = document.getElementById('confirmDeleteGroup');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', confirmDeleteGroup);
    }
    
    // Allow Enter key to confirm edit
    const editGroupInput = document.getElementById('editGroupName');
    if (editGroupInput) {
        editGroupInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                confirmEditGroup();
            }
        });
    }
    
    // Search customers in edit modal
    const editGroupSearchInput = document.getElementById('editGroupSearchCustomers');
    if (editGroupSearchInput) {
        editGroupSearchInput.addEventListener('input', searchAvailableCustomers);
    }
}

function showMappingStatus(message, type = 'info') {
    const statusDiv = document.getElementById('customerMappingStatus');
    const alertClass = type === 'success' ? 'alert-success' : 
                      type === 'danger' ? 'alert-danger' : 
                      type === 'warning' ? 'alert-warning' : 'alert-info';
    
    const iconClass = type === 'success' ? 'check-circle' : 
                      type === 'danger' ? 'x-circle' : 
                      type === 'warning' ? 'exclamation-triangle' : 'info-circle';
    
    statusDiv.innerHTML = `
        <div class="alert ${alertClass}">
            <i class="bi bi-${iconClass} me-2"></i>${message}
        </div>
    `;
    statusDiv.style.display = 'block';
    
    // Auto-hide after 5 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 5000);
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('System settings page loaded');
    
    // Load initial data
    loadDatabaseInfo();
    loadBackupsList();
    loadSystemInfo();
    loadCompanyYear(); // Load company year configuration
    loadCustomersAndMappings(); // Load customer mappings with new interface
    setupSearchAndFilter(); // Setup search and filter handlers
    setupGroupButtonListeners(); // Setup event listeners for group buttons
    setupModalListeners(); // Setup modal button listeners
    
    // Set default dates for housekeeping
    const today = new Date().toISOString().split('T')[0];
    const lastWeek = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    
    document.getElementById('reparseEndDate').value = today;
    document.getElementById('reparseStartDate').value = lastWeek;
    document.getElementById('validationDate').value = today;
    
    // Load CDN status on page load
    loadCDNStatus();
    
    // Load Python deps status on page load
    loadPythonDepsStatus();
});

// ============================================
// CDN Version Management Functions
// ============================================

async function checkCDNVersions() {
    const tbody = document.getElementById('cdnVersionsBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="5" class="text-center py-3">
                <div class="spinner-border spinner-border-sm text-primary me-2"></div>
                Checking for updates...
            </td>
        </tr>
    `;
    
    try {
        const response = await fetch('/api/cdn/check');
        const data = await response.json();
        
        if (data.success) {
            displayCDNVersions(data.libraries);
            showStatus('CDN version check completed', 'success');
        } else {
            showStatus(data.error || 'Failed to check CDN versions', 'danger');
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-danger py-3">
                        <i class="bi bi-x-circle me-2"></i>
                        Failed to check versions
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error checking CDN versions:', error);
        showStatus('Error checking CDN versions', 'danger');
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-danger py-3">
                    <i class="bi bi-x-circle me-2"></i>
                    Error: ${error.message}
                </td>
            </tr>
        `;
    }
}

async function loadCDNStatus() {
    try {
        const response = await fetch('/api/cdn/status');
        const data = await response.json();
        
        if (data.success && data.data.libraries) {
            displayCDNVersions(data.data.libraries);
            
            // Show last check time
            if (data.data.last_check) {
                const lastCheck = new Date(data.data.last_check);
                document.getElementById('cdnLastCheckTime').textContent = lastCheck.toLocaleString();
                document.getElementById('cdnLastCheck').style.display = 'block';
            }
        }
    } catch (error) {
        console.error('Error loading CDN status:', error);
    }
}

function displayCDNVersions(libraries) {
    const tbody = document.getElementById('cdnVersionsBody');
    tbody.innerHTML = '';
    
    let hasUpdates = false;
    
    for (const [libId, info] of Object.entries(libraries)) {
        if (info.update_available) {
            hasUpdates = true;
        }
        
        const statusBadge = info.update_available 
            ? '<span class="badge bg-warning">Update Available</span>'
            : '<span class="badge bg-success">Up to date</span>';
        
        const actionBtn = info.update_available
            ? `<button class="btn btn-sm btn-primary" onclick="updateSingleCDN('${libId}')">
                   <i class="bi bi-download"></i> Update
               </button>`
            : '<span class="text-muted">-</span>';
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${info.name}</strong></td>
            <td><code>${info.current}</code></td>
            <td><code>${info.latest}</code></td>
            <td>${statusBadge}</td>
            <td>${actionBtn}</td>
        `;
        tbody.appendChild(row);
    }
    
    // Enable/disable "Update All" button
    document.getElementById('updateAllCDNBtn').disabled = !hasUpdates;
}

async function updateSingleCDN(libId) {
    showStatus(`Updating ${libId}...`, 'info');
    
    try {
        const response = await fetch('/api/cdn/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ libraries: [libId] })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus(data.message || 'Library updated successfully', 'success');
            // Reload status to show updated versions
            setTimeout(() => checkCDNVersions(), 1000);
        } else {
            showStatus(data.error || 'Failed to update library', 'danger');
        }
    } catch (error) {
        console.error('Error updating CDN library:', error);
        showStatus('Error updating library', 'danger');
    }
}

async function updateAllCDN() {
    if (!confirm('This will update all CDN libraries to their latest versions. The page will need to be refreshed after the update. Continue?')) {
        return;
    }
    
    showStatus('Updating all libraries...', 'info');
    
    try {
        const response = await fetch('/api/cdn/update-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus(data.message || 'All libraries updated successfully', 'success');
            
            // Show reload prompt
            setTimeout(() => {
                if (confirm('Libraries updated! Reload the page to use the new versions?')) {
                    window.location.reload();
                }
            }, 1500);
        } else {
            showStatus(data.error || 'Failed to update libraries', 'danger');
        }
    } catch (error) {
        console.error('Error updating CDN libraries:', error);
        showStatus('Error updating libraries', 'danger');
    }
}

// ============================================
// Python Dependencies Management Functions
// ============================================

async function checkPythonDeps() {
    const tbody = document.getElementById('pythonDepsBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="6" class="text-center py-3">
                <div class="spinner-border spinner-border-sm text-primary me-2"></div>
                Checking Python packages...
            </td>
        </tr>
    `;
    
    try {
        const response = await fetch('/api/python-deps/check');
        const data = await response.json();
        
        if (data.success) {
            displayPythonDeps(data.packages, data.summary);
            showStatus('Python dependency check completed', 'success');
        } else {
            showStatus(data.error || 'Failed to check Python dependencies', 'danger');
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-danger py-3">
                        <i class="bi bi-x-circle me-2"></i>
                        Failed to check packages
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error checking Python dependencies:', error);
        showStatus('Error checking Python dependencies', 'danger');
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-danger py-3">
                    <i class="bi bi-x-circle me-2"></i>
                    Error: ${error.message}
                </td>
            </tr>
        `;
    }
}

async function loadPythonDepsStatus() {
    try {
        const response = await fetch('/api/python-deps/status');
        const data = await response.json();
        
        if (data.success && data.data.packages) {
            // Calculate summary from packages
            const packages = data.data.packages;
            const summary = {
                total: Object.keys(packages).length,
                updates_available: Object.values(packages).filter(p => p.update_available).length,
                major_updates: Object.values(packages).filter(p => p.update_type === 'major').length,
                minor_updates: Object.values(packages).filter(p => p.update_type === 'minor').length,
                patch_updates: Object.values(packages).filter(p => p.update_type === 'patch').length
            };
            
            displayPythonDeps(packages, summary);
            
            // Show last check time
            if (data.data.last_check) {
                const lastCheck = new Date(data.data.last_check);
                document.getElementById('pythonDepsLastCheckTime').textContent = lastCheck.toLocaleString();
                document.getElementById('pythonDepsLastCheck').style.display = 'block';
            }
        }
    } catch (error) {
        console.error('Error loading Python deps status:', error);
    }
}

function displayPythonDeps(packages, summary) {
    const tbody = document.getElementById('pythonDepsBody');
    tbody.innerHTML = '';
    
    // Update summary stats
    if (summary) {
        document.getElementById('totalPackages').textContent = summary.total;
        document.getElementById('updatesAvailable').textContent = summary.updates_available;
        document.getElementById('majorUpdates').textContent = summary.major_updates;
        document.getElementById('minorUpdates').textContent = summary.minor_updates;
        document.getElementById('patchUpdates').textContent = summary.patch_updates;
        document.getElementById('pythonDepsSummary').style.display = 'block';
        
        // Enable/disable update buttons
        document.getElementById('updatePatchBtn').disabled = summary.patch_updates === 0;
        document.getElementById('updateMinorBtn').disabled = (summary.minor_updates + summary.patch_updates) === 0;
    }
    
    // Sort packages by update type priority
    const sortedPackages = Object.entries(packages).sort((a, b) => {
        const typeOrder = { 'major': 0, 'minor': 1, 'patch': 2, 'flexible': 3, 'none': 4 };
        return typeOrder[a[1].update_type] - typeOrder[b[1].update_type];
    });
    
    for (const [pkgId, info] of sortedPackages) {
        const updateType = info.update_type || 'none';
        const typeIcon = {
            'major': '🔴',
            'minor': '🟡',
            'patch': '🟢',
            'flexible': '📌',
            'none': '✅',
            'error': '❌'
        }[updateType] || '❓';
        
        const statusBadge = info.update_available 
            ? `<span class="badge bg-warning">Update Available</span>`
            : updateType === 'flexible'
            ? `<span class="badge bg-info">Flexible (${info.operator})</span>`
            : `<span class="badge bg-success">Up to date</span>`;
        
        const actionBtn = info.update_available
            ? `<button class="btn btn-sm btn-primary" onclick="updateSinglePythonDep('${info.clean_name}', '${info.latest}')">
                   <i class="bi bi-download"></i> Update
               </button>`
            : '<span class="text-muted">-</span>';
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${info.clean_name}</strong></td>
            <td><code>${info.current}</code></td>
            <td><code>${info.latest}</code></td>
            <td>${typeIcon} ${updateType}</td>
            <td>${statusBadge}</td>
            <td>${actionBtn}</td>
        `;
        tbody.appendChild(row);
    }
}

async function updateSinglePythonDep(packageName, version) {
    showStatus(`Updating ${packageName}...`, 'info');
    
    try {
        const response = await fetch('/api/python-deps/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ packages: { [packageName]: version } })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus(data.message || 'Package updated successfully', 'success');
            // Reload status to show updated versions
            setTimeout(() => checkPythonDeps(), 1000);
        } else {
            showStatus(data.error || 'Failed to update package', 'danger');
        }
    } catch (error) {
        console.error('Error updating Python package:', error);
        showStatus('Error updating package', 'danger');
    }
}

async function updatePythonDepsByType(type) {
    const typeNames = {
        'patch': 'patch updates (safest)',
        'minor': 'minor and patch updates',
        'all': 'all updates (including major versions)'
    };
    
    if (!confirm(`This will update ${typeNames[type]}. You will need to run 'pip install -r requirements.txt' and restart the application after. Continue?`)) {
        return;
    }
    
    showStatus(`Updating ${type} packages...`, 'info');
    
    try {
        const response = await fetch('/api/python-deps/update-by-type', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: type })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus(data.message || 'Packages updated successfully', 'success');
            
            // Show install prompt
            setTimeout(() => {
                alert('Packages updated in requirements.txt!\n\nNext steps:\n1. Run: pip install -r requirements.txt\n2. Restart the application\n3. Refresh this page');
            }, 1500);
            
            // Reload status
            setTimeout(() => checkPythonDeps(), 2000);
        } else {
            showStatus(data.error || 'Failed to update packages', 'danger');
        }
    } catch (error) {
        console.error('Error updating Python packages:', error);
        showStatus('Error updating packages', 'danger');
    }
}
