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

// Missing Runsheets functions
async function checkMissingRunsheets() {
    try {
        const response = await fetch('/api/sync/missing-runsheets');
        const result = await response.json();
        
        if (result.success) {
            const statusDiv = document.getElementById('missingRunsheetsStatus');
            const contentDiv = document.getElementById('missingRunsheetsContent');
            const alertDiv = document.getElementById('missingRunsheetsAlert');
            const countSpan = document.getElementById('missingCount');
            const listDiv = document.getElementById('missingDatesList');
            const container = document.getElementById('missingDatesContainer');
            
            statusDiv.style.display = 'none';
            contentDiv.style.display = 'block';
            
            countSpan.textContent = result.missing_count;
            
            if (result.missing_count === 0) {
                alertDiv.className = 'alert alert-success mb-3';
                alertDiv.innerHTML = '<i class="bi bi-check-circle me-2"></i><strong>Last 30 days:</strong> No missing dates ✅';
                listDiv.style.display = 'none';
            } else {
                alertDiv.className = 'alert alert-warning mb-3';
                alertDiv.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i><strong>Last 30 days:</strong> ${result.missing_count} missing dates`;
                
                // Show list of missing dates
                container.innerHTML = result.missing_dates.map(date => 
                    `<div class="list-group-item">
                        <i class="bi bi-calendar-x text-warning me-2"></i>${date}
                    </div>`
                ).join('');
                listDiv.style.display = 'block';
            }
        }
    } catch (error) {
        console.error('Error checking missing runsheets:', error);
        showError('Failed to check for missing runsheets');
    }
}

async function downloadMissingRunsheets() {
    const btn = document.getElementById('downloadMissingBtn');
    const originalText = btn.innerHTML;
    
    try {
        btn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Downloading...';
        btn.disabled = true;
        
        showStatus('Downloading missing runsheets from Gmail...');
        
        const response = await fetch('/api/data/download-missing-runsheets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(`Downloaded ${result.downloaded || 0} runsheets successfully!`);
            // Refresh the missing runsheets check
            setTimeout(() => checkMissingRunsheets(), 2000);
        } else {
            showError(result.error || 'Failed to download missing runsheets');
        }
    } catch (error) {
        console.error('Error downloading missing runsheets:', error);
        showError('Failed to download missing runsheets');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
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
                // Format the log with color coding
                const formattedLog = formatSyncLog(data.log);
                logWindow.innerHTML = formattedLog;
                // Scroll to bottom
                logWindow.scrollTop = logWindow.scrollHeight;
                
                // Parse and update summary
                updateSyncSummary(data.log);
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

function formatSyncLog(log) {
    // Add color coding and icons to log output
    let formatted = log
        .replace(/✅/g, '<span class="text-success">✅</span>')
        .replace(/❌/g, '<span class="text-danger">❌</span>')
        .replace(/⚠️/g, '<span class="text-warning">⚠️</span>')
        .replace(/📥/g, '<span class="text-primary">📥</span>')
        .replace(/📧/g, '<span class="text-info">📧</span>')
        .replace(/🔄/g, '<span class="text-primary">🔄</span>')
        .replace(/📈/g, '<span class="text-success">📈</span>')
        .replace(/Downloaded:/g, '<strong class="text-primary">Downloaded:</strong>')
        .replace(/Imported:/g, '<strong class="text-success">Imported:</strong>')
        .replace(/Error:/g, '<strong class="text-danger">Error:</strong>')
        .replace(/SUCCESS/g, '<strong class="text-success">SUCCESS</strong>')
        .replace(/FAILED/g, '<strong class="text-danger">FAILED</strong>');
    
    return `<pre>${formatted}</pre>`;
}

function updateSyncSummary(log) {
    // Parse log to extract key metrics
    const summaryDiv = document.getElementById('lastSyncSummary');
    const contentDiv = document.getElementById('lastSyncContent');
    
    if (!summaryDiv || !contentDiv) return;
    
    // Extract metrics from log
    let filesDownloaded = 0;
    let jobsImported = 0;
    let payUpdated = 0;
    let errors = 0;
    let errorMessages = [];
    
    // Parse downloaded files
    const downloadMatch = log.match(/Downloaded (\d+) files/i) || log.match(/📥 Downloaded (\d+)/);
    if (downloadMatch) filesDownloaded = parseInt(downloadMatch[1]);
    
    // Parse imported jobs
    const importMatch = log.match(/Imported (\d+) jobs/i) || log.match(/Runsheet jobs: (\d+)/);
    if (importMatch) jobsImported = parseInt(importMatch[1]);
    
    // Parse pay data synced
    const payMatch = log.match(/Jobs updated: (\d+)/i);
    if (payMatch) payUpdated = parseInt(payMatch[1]);
    
    // Extract error messages
    const lines = log.split('\n');
    for (let line of lines) {
        if (line.includes('❌') || line.includes('Error:') || line.includes('FAILED') || line.includes('⚠️  Errors')) {
            errorMessages.push(line.trim());
        }
    }
    errors = errorMessages.length;
    
    // Display errors in log if any
    if (errors > 0) {
        displayErrorsInLog(errorMessages);
    }
    
    // Update UI
    document.getElementById('syncFilesDownloaded').textContent = filesDownloaded;
    document.getElementById('syncJobsImported').textContent = jobsImported;
    document.getElementById('syncPayUpdated').textContent = payUpdated;
    document.getElementById('syncErrors').textContent = errors;
    
    // Update error card color
    const errorCard = document.getElementById('syncErrors').closest('.bg-light');
    if (errorCard) {
        if (errors > 0) {
            errorCard.classList.remove('bg-light');
            errorCard.classList.add('bg-danger', 'bg-opacity-10');
        } else {
            errorCard.classList.remove('bg-danger', 'bg-opacity-10');
            errorCard.classList.add('bg-light');
        }
    }
    
    // Update timestamp
    const now = new Date();
    document.getElementById('syncLastTime').textContent = now.toLocaleString();
    
    // Show content, hide loading
    summaryDiv.style.display = 'none';
    contentDiv.style.display = 'block';
}

function displayErrorsInLog(errorMessages) {
    const logWindow = document.getElementById('syncLogWindow');
    if (!logWindow || errorMessages.length === 0) return;
    
    // Create error section at the top of the log
    const errorSection = document.createElement('div');
    errorSection.className = 'alert alert-danger mb-3';
    errorSection.innerHTML = `
        <h6 class="alert-heading mb-2">
            <i class="bi bi-exclamation-triangle-fill me-2"></i>
            Errors Found (${errorMessages.length})
        </h6>
        <hr>
        <ul class="mb-0">
            ${errorMessages.map(msg => `<li>${msg}</li>`).join('')}
        </ul>
    `;
    
    // Insert at the beginning of the log window
    logWindow.insertBefore(errorSection, logWindow.firstChild);
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
    checkMissingRunsheets();
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
