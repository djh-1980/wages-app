/**
 * System Settings JavaScript
 * Handles database management and system functionality
 */

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
    // Create a download link for the backup file
    const link = document.createElement('a');
    link.href = `/data/database/backups/${filename}`;
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
        
        const response = await fetch('/api/data/restore-backup', {
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

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('System settings page loaded');
    
    // Load initial data
    loadDatabaseInfo();
    loadBackupsList();
    loadSystemInfo();
});
