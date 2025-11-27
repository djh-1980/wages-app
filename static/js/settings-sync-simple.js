/**
 * Simple Data & Sync Settings JavaScript
 * Handles basic sync functionality for the new settings page
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
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOutRight {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }
    
    floatingContainer.appendChild(notification);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

function showSuccess(message) {
    showStatus(message, 'success');
}

function showError(message) {
    showStatus(message, 'danger');
}

// Master Sync functions
async function runMasterSyncManual() {
    const btn = document.getElementById('manualSyncBtn');
    const originalText = btn.innerHTML;
    
    try {
        btn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Running...';
        btn.disabled = true;
        
        showStatus('Starting master sync...');
        
        const response = await fetch('/api/data/run-master-sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Master sync completed successfully!');
            loadLatestSyncData();
        } else {
            showError(`Master sync failed: ${result.error}`);
        }
    } catch (error) {
        showError(`Error running master sync: ${error.message}`);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function loadLatestSyncData() {
    try {
        const response = await fetch('/api/data/latest-sync-data');
        const data = await response.json();
        
        if (data.success) {
            const runsheetElement = document.getElementById('latestRunsheetDate');
            const payslipElement = document.getElementById('latestPayslipWeek');
            
            if (runsheetElement) {
                runsheetElement.textContent = data.latest_runsheet || 'No data';
            }
            if (payslipElement) {
                payslipElement.textContent = data.latest_payslip || 'No data';
            }
        }
    } catch (error) {
        console.error('Error loading latest sync data:', error);
    }
}

// Sync Log functions
async function refreshSyncLog() {
    try {
        const response = await fetch('/api/data/sync-log');
        const data = await response.json();
        
        const logWindow = document.getElementById('syncLogWindow');
        if (logWindow) {
            if (data.success && data.log) {
                logWindow.innerHTML = `<pre>${data.log}</pre>`;
                // Scroll to bottom
                logWindow.scrollTop = logWindow.scrollHeight;
            } else {
                logWindow.innerHTML = '<div class="text-muted">No log data available</div>';
            }
        }
    } catch (error) {
        console.error('Error refreshing sync log:', error);
        const logWindow = document.getElementById('syncLogWindow');
        if (logWindow) {
            logWindow.innerHTML = '<div class="text-danger">Error loading log</div>';
        }
    }
}

function clearSyncLog() {
    const logWindow = document.getElementById('syncLogWindow');
    if (logWindow) {
        logWindow.innerHTML = '<div class="text-muted">Log cleared</div>';
    }
}

// Gmail Connection functions
async function testGmailConnection() {
    const resultsDiv = document.getElementById('gmailTestResults');
    if (!resultsDiv) return;
    
    try {
        showStatus('Testing Gmail connection...');
        const response = await fetch('/api/gmail/test-connection', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            resultsDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i>
                    Gmail connected successfully! Email: ${result.email || 'Connected'}
                </div>
            `;
            showSuccess('Gmail connection test successful!');
        } else {
            resultsDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i>
                    Connection failed: ${result.error}
                </div>
            `;
            showError('Gmail connection test failed');
        }
        resultsDiv.style.display = 'block';
    } catch (error) {
        resultsDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-x-circle"></i>
                Connection test failed: ${error.message}
            </div>
        `;
        resultsDiv.style.display = 'block';
        showError('Gmail connection test failed');
    }
}

// File Upload helper function
function copyManagerRequestEmail() {
    const template = `Subject: Request for Historical Runsheets and Payslips

Hi [Manager Name],

I'm updating my wages records and need copies of some historical runsheets and payslips that I don't have in my email.

Could you please send me PDF copies of:
- Runsheets from [DATE RANGE]
- Payslips from [DATE RANGE]

These will help me keep my records complete and accurate.

Thank you!

Best regards,
[Your Name]`;

    navigator.clipboard.writeText(template).then(() => {
        showSuccess('Email template copied to clipboard!');
    }).catch(() => {
        // Fallback: show in modal
        alert(template);
        showSuccess('Email template displayed (clipboard not available)');
    });
}

// Auto-update intervals
let syncDataInterval = null;
let syncLogInterval = null;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('Data & Sync settings page loaded');
    
    // Load initial data
    loadLatestSyncData();
    refreshSyncLog();
    
    // Set up auto-updating
    startAutoUpdating();
    
    // Initialize file upload if the container exists
    const uploadContainer = document.getElementById('fileUploadContainer');
    if (uploadContainer) {
        // Wait for FileUploadManager to be available
        if (typeof FileUploadManager !== 'undefined') {
            window.fileUploader = new FileUploadManager('fileUploadContainer', {
                allowedTypes: ['application/pdf'],
                maxFileSize: 50 * 1024 * 1024, // 50MB
                multiple: true,
                autoProcess: true,
                onUploadComplete: (result) => {
                    showSuccess(`Successfully uploaded ${result.uploaded_files.length} files!`);
                    // Refresh sync data after upload
                    setTimeout(() => {
                        loadLatestSyncData();
                    }, 2000);
                }
            });
        } else {
            // Fallback if FileUploadManager isn't loaded yet
            setTimeout(() => {
                if (typeof FileUploadManager !== 'undefined') {
                    window.fileUploader = new FileUploadManager('fileUploadContainer', {
                        allowedTypes: ['application/pdf'],
                        maxFileSize: 50 * 1024 * 1024, // 50MB
                        multiple: true,
                        autoProcess: true,
                        onUploadComplete: (result) => {
                            showSuccess(`Successfully uploaded ${result.uploaded_files.length} files!`);
                            setTimeout(() => {
                                loadLatestSyncData();
                            }, 2000);
                        }
                    });
                }
            }, 1000);
        }
    }
});

// Start auto-updating
function startAutoUpdating() {
    // Update sync data every 30 seconds
    syncDataInterval = setInterval(() => {
        loadLatestSyncData();
    }, 30000);
    
    // Update sync log every 10 seconds
    syncLogInterval = setInterval(() => {
        refreshSyncLog();
    }, 10000);
}

// Stop auto-updating (useful when page is hidden)
function stopAutoUpdating() {
    if (syncDataInterval) {
        clearInterval(syncDataInterval);
        syncDataInterval = null;
    }
    if (syncLogInterval) {
        clearInterval(syncLogInterval);
        syncLogInterval = null;
    }
}

// Handle page visibility changes to pause/resume auto-updating
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        stopAutoUpdating();
    } else {
        startAutoUpdating();
    }
});

// Clean up intervals when page unloads
window.addEventListener('beforeunload', function() {
    stopAutoUpdating();
});
