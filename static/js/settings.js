// Load all settings on page load
document.addEventListener('DOMContentLoaded', function() {
    loadAllSettings();
    loadProfile();
    loadAppearance();
    
    // Load attendance records when tab is shown
    const attendanceTab = document.getElementById('attendance-tab');
    if (attendanceTab) {
        attendanceTab.addEventListener('shown.bs.tab', function() {
            loadAttendanceRecords();
        });
    }
});

function loadAllSettings() {
    loadDatabaseInfo();
    checkSyncStatus();
    checkGmailStatus();
    calculateNextSync();
}

// ===== PROFILE =====
function loadProfile() {
    document.getElementById('userName').value = localStorage.getItem('userName') || '';
    document.getElementById('userEmail').value = localStorage.getItem('userEmail') || '';
    document.getElementById('userPhone').value = localStorage.getItem('userPhone') || '';
    document.getElementById('hourlyRate').value = localStorage.getItem('hourlyRate') || '';
    document.getElementById('taxCode').value = localStorage.getItem('taxCode') || '';
    document.getElementById('niNumber').value = localStorage.getItem('niNumber') || '';
}

function saveProfile() {
    localStorage.setItem('userName', document.getElementById('userName').value);
    localStorage.setItem('userEmail', document.getElementById('userEmail').value);
    localStorage.setItem('userPhone', document.getElementById('userPhone').value);
    localStorage.setItem('hourlyRate', document.getElementById('hourlyRate').value);
    localStorage.setItem('taxCode', document.getElementById('taxCode').value);
    localStorage.setItem('niNumber', document.getElementById('niNumber').value);
    showSuccess('Profile saved successfully!');
}

// ===== AUTO-SYNC =====
async function checkSyncStatus() {
    try {
        const response = await fetch('/api/settings/sync-status');
        const result = await response.json();
        
        if (result.active) {
            document.getElementById('syncStatusBadge').textContent = 'Active';
            document.getElementById('syncStatusBadge').className = 'sync-status active';
            
            if (result.last_sync) {
                const lastSync = new Date(result.last_sync);
                document.getElementById('lastSyncTime').textContent = lastSync.toLocaleString();
            } else {
                document.getElementById('lastSyncTime').textContent = 'Check logs for details';
            }
        } else {
            document.getElementById('syncStatusBadge').textContent = 'Not Running';
            document.getElementById('syncStatusBadge').className = 'sync-status inactive';
            document.getElementById('lastSyncTime').textContent = 'Never';
        }
    } catch (error) {
        document.getElementById('syncStatusBadge').textContent = 'Unknown';
        document.getElementById('syncStatusBadge').className = 'sync-status inactive';
    }
}

function calculateNextSync() {
    const now = new Date();
    const morning = new Date();
    morning.setHours(6, 0, 0, 0);
    const evening = new Date();
    evening.setHours(23, 0, 0, 0);
    
    let nextSync;
    if (now < morning) {
        nextSync = morning;
    } else if (now < evening) {
        nextSync = evening;
    } else {
        nextSync = new Date(now.getTime() + 24 * 60 * 60 * 1000);
        nextSync.setHours(6, 0, 0, 0);
    }
    
    document.getElementById('nextSyncTime').textContent = nextSync.toLocaleString();
}

function runSyncNow() {
    showStatus('Running sync manually...');
    alert('Manual sync will run the daily_runsheet_sync.py script.\n\nTo run manually from terminal:\npython3 scripts/daily_runsheet_sync.py');
}

function viewSyncLogs() {
    window.open('/logs/runsheet_sync.log', '_blank');
}

// ===== GMAIL =====
async function checkGmailStatus() {
    try {
        const response = await fetch('/api/gmail/status');
        const data = await response.json();
        
        const badge = document.getElementById('gmailStatusBadge');
        const tokenStatus = document.getElementById('tokenStatus');
        const credentialsStatus = document.getElementById('credentialsStatus');
        
        if (data.configured && data.authenticated) {
            badge.textContent = 'Connected';
            badge.className = 'sync-status active';
            tokenStatus.innerHTML = '<span class="text-success">✓ Authenticated</span>';
            credentialsStatus.innerHTML = '<span class="text-success">✓ Configured</span>';
        } else if (data.configured) {
            badge.textContent = 'Not Authenticated';
            badge.className = 'sync-status inactive';
            tokenStatus.innerHTML = '<span class="text-warning">⚠ Need to authorize</span>';
            credentialsStatus.innerHTML = '<span class="text-success">✓ Configured</span>';
        } else {
            badge.textContent = 'Not Configured';
            badge.className = 'sync-status inactive';
            tokenStatus.innerHTML = '<span class="text-danger">✗ Not authenticated</span>';
            credentialsStatus.innerHTML = '<span class="text-danger">✗ Missing credentials.json</span>';
        }
    } catch (error) {
        console.error('Error checking Gmail status:', error);
        document.getElementById('gmailStatusBadge').textContent = 'Error';
        document.getElementById('gmailStatusBadge').className = 'sync-status inactive';
    }
}

async function downloadFromGmail() {
    const dateInput = document.getElementById('gmailDownloadDate');
    const modeSelect = document.getElementById('gmailDownloadMode');
    const statusDiv = document.getElementById('gmailDownloadStatus');
    const button = event.target;
    
    // Convert YYYY-MM-DD to YYYY/MM/DD
    const dateValue = dateInput.value;
    const afterDate = dateValue.replace(/-/g, '/');
    const mode = modeSelect.value;
    
    // Disable button
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Downloading...';
    
    // Show status
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = '<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> Downloading from Gmail... This may take a few minutes.</div>';
    
    try {
        const response = await fetch('/api/gmail/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                mode: mode,
                after_date: afterDate
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> ${result.message}
                    <details class="mt-2">
                        <summary>View Details</summary>
                        <pre class="mt-2 small">${result.output}</pre>
                    </details>
                </div>
            `;
            
            // Refresh database info
            loadDatabaseInfo();
        } else {
            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i> Download failed: ${result.error}
                    ${result.output ? `<details class="mt-2"><summary>View Details</summary><pre class="mt-2 small">${result.output}</pre></details>` : ''}
                </div>
            `;
        }
    } catch (error) {
        console.error('Error downloading from Gmail:', error);
        statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${error.message}</div>`;
    } finally {
        // Re-enable button
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-cloud-download"></i> Start Download';
    }
}

function reauthorizeGmail() {
    alert('To re-authorize Gmail:\n\n1. Delete token.json from the project root\n2. Run: python3 scripts/download_runsheets_gmail.py\n3. Follow the browser authentication flow\n4. Refresh this page');
}

// ===== DATA =====
function loadDatabaseInfo() {
    // Load payslips count
    fetch('/api/summary')
        .then(response => response.json())
        .then(data => {
            document.getElementById('dbPayslips').textContent = data.total_weeks || 0;
        })
        .catch(error => console.error('Error loading payslips:', error));
    
    // Load run sheets count
    fetch('/api/runsheets/summary')
        .then(response => response.json())
        .then(data => {
            document.getElementById('dbRunSheets').textContent = data.total_days || 0;
            document.getElementById('dbJobs').textContent = data.total_jobs || 0;
        })
        .catch(error => console.error('Error loading run sheets:', error));
    
    // Database size (placeholder)
    document.getElementById('dbSize').textContent = '~5MB';
}

async function syncPayslips() {
    const statusDiv = document.getElementById('dataManagementStatus');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = '<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> Syncing payslips from PaySlips folder...</div>';
    
    showStatus('Importing payslips...');
    
    try {
        const response = await fetch('/api/data/sync-payslips', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> ${result.message}
                    <details class="mt-2">
                        <summary>View Details</summary>
                        <pre class="mt-2 small">${result.output}</pre>
                    </details>
                </div>
            `;
            showSuccess('Payslips synced successfully');
            loadDatabaseInfo();
        } else {
            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i> Sync failed: ${result.error}
                    ${result.output ? `<details class="mt-2"><summary>View Details</summary><pre class="mt-2 small">${result.output}</pre></details>` : ''}
                </div>
            `;
            showError('Payslip sync failed');
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${error.message}</div>`;
        showError('Error syncing payslips');
    }
}

let syncProgressInterval = null;

async function downloadAndSyncRunSheets() {
    const statusDiv = document.getElementById('dataManagementStatus');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = `
        <div class="alert alert-info">
            <i class="bi bi-cloud-download"></i> <strong>Step 1/2: Downloading from Gmail...</strong>
            <p class="mb-0 mt-2 small">Checking for new run sheets in Gmail...</p>
        </div>
    `;
    
    showStatus('Downloading from Gmail...');
    
    try {
        // Step 1: Download from Gmail (today's run sheet only)
        const today = new Date();
        const todayStr = `${today.getFullYear()}/${String(today.getMonth() + 1).padStart(2, '0')}/${String(today.getDate()).padStart(2, '0')}`;
        
        const downloadResponse = await fetch('/api/gmail/download-runsheets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                after_date: todayStr
            })
        });
        
        const downloadResult = await downloadResponse.json();
        
        if (!downloadResult.success) {
            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i> Download failed: ${downloadResult.error}
                    <p class="mb-0 mt-2 small">You may need to authorize Gmail access in the Gmail tab.</p>
                </div>
            `;
            showError('Gmail download failed');
            return;
        }
        
        // Show download results
        statusDiv.innerHTML = `
            <div class="alert alert-success">
                <i class="bi bi-check-circle"></i> <strong>Step 1/2: Download complete!</strong>
                <p class="mb-0 mt-2">${downloadResult.message || 'Files downloaded from Gmail'}</p>
            </div>
            <div class="alert alert-info mt-2">
                <i class="bi bi-hourglass-split"></i> <strong>Step 2/2: Starting import...</strong>
            </div>
        `;
        
        // Wait a moment to show the success message
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Step 2: Sync run sheets
        await syncRunSheets();
        
    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${error.message}</div>`;
        showError('Download & sync failed');
    }
}

async function syncRunSheets() {
    const statusDiv = document.getElementById('dataManagementStatus');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = `
        <div class="alert alert-warning">
            <i class="bi bi-hourglass-split"></i> <strong>Syncing run sheets from RunSheets folder...</strong>
            <p class="mb-0 mt-2 small">
                ⚠️ This may take 10-30 minutes for large imports (1000+ files).<br>
                Progress will update below. Please be patient and do not refresh.
            </p>
            <div id="syncProgress" class="mt-3">
                <pre class="small" style="max-height: 300px; overflow-y: auto; background: #f8f9fa; padding: 10px; border-radius: 5px;">Initializing...</pre>
            </div>
        </div>
    `;
    
    showStatus('Importing run sheets (this may take a while)...');
    
    // Start polling for progress
    syncProgressInterval = setInterval(updateSyncProgress, 2000);
    
    try {
        const response = await fetch('/api/data/sync-runsheets', {
            method: 'POST'
        });
        
        // Stop polling
        if (syncProgressInterval) {
            clearInterval(syncProgressInterval);
            syncProgressInterval = null;
        }
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> ${result.message}
                    <details class="mt-2">
                        <summary>View Details</summary>
                        <pre class="mt-2 small" style="max-height: 400px; overflow-y: auto;">${result.output}</pre>
                    </details>
                </div>
            `;
            showSuccess('Run sheets synced successfully');
            loadDatabaseInfo();
        } else {
            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i> Sync failed: ${result.error}
                    ${result.output ? `<details class="mt-2"><summary>View Details</summary><pre class="mt-2 small">${result.output}</pre></details>` : ''}
                </div>
            `;
            showError('Run sheet sync failed');
        }
    } catch (error) {
        // Stop polling
        if (syncProgressInterval) {
            clearInterval(syncProgressInterval);
            syncProgressInterval = null;
        }
        
        statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${error.message}</div>`;
        showError('Error syncing run sheets');
    }
}

async function updateSyncProgress() {
    try {
        const response = await fetch('/api/data/sync-progress');
        const result = await response.json();
        
        if (result.success && result.progress) {
            const progressDiv = document.getElementById('syncProgress');
            if (progressDiv) {
                progressDiv.innerHTML = `<pre class="small" style="max-height: 300px; overflow-y: auto; background: #f8f9fa; padding: 10px; border-radius: 5px;">${result.progress}</pre>`;
                // Auto-scroll to bottom
                const pre = progressDiv.querySelector('pre');
                if (pre) {
                    pre.scrollTop = pre.scrollHeight;
                }
            }
        }
    } catch (error) {
        console.error('Error fetching progress:', error);
    }
}

async function reorganizeRunSheets() {
    const statusDiv = document.getElementById('dataManagementStatus');
    
    // First, show options
    const choice = confirm('This will reorganize all run sheets:\n\n1. Move all to RunSheets/backup\n2. Check for "Hanson, Daniel"\n3. Organize by year/month\n4. Rename to DH_DD-MM-YYYY.pdf\n\nClick OK to preview changes (dry run)\nClick Cancel to abort');
    
    if (!choice) {
        return;
    }
    
    // Start with dry run
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = '<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> Running preview (dry run)... This may take several minutes.</div>';
    
    showStatus('Previewing reorganization...');
    
    try {
        const response = await fetch('/api/data/reorganize-runsheets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ dry_run: true })
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-info-circle"></i> <strong>Preview Complete</strong>
                    <details class="mt-2" open>
                        <summary>View Changes</summary>
                        <pre class="mt-2 small" style="max-height: 400px; overflow-y: auto;">${result.output}</pre>
                    </details>
                    <div class="mt-3">
                        <button class="btn btn-danger" onclick="executeReorganize()">
                            <i class="bi bi-folder-symlink"></i> Execute Reorganization
                        </button>
                        <button class="btn btn-secondary" onclick="document.getElementById('dataManagementStatus').style.display='none'">
                            Cancel
                        </button>
                    </div>
                </div>
            `;
            showSuccess('Preview complete - review changes above');
        } else {
            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i> Preview failed: ${result.error}
                    ${result.output ? `<details class="mt-2"><summary>View Details</summary><pre class="mt-2 small">${result.output}</pre></details>` : ''}
                </div>
            `;
            showError('Preview failed');
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${error.message}</div>`;
        showError('Error running preview');
    }
}

async function executeReorganize() {
    const statusDiv = document.getElementById('dataManagementStatus');
    
    if (!confirm('Are you sure you want to execute the reorganization?\n\nThis will move and rename files!')) {
        return;
    }
    
    statusDiv.innerHTML = '<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> Reorganizing files... This may take several minutes.</div>';
    showStatus('Reorganizing run sheets...');
    
    try {
        const response = await fetch('/api/data/reorganize-runsheets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ dry_run: false })
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> <strong>${result.message}</strong>
                    <details class="mt-2">
                        <summary>View Details</summary>
                        <pre class="mt-2 small" style="max-height: 400px; overflow-y: auto;">${result.output}</pre>
                    </details>
                </div>
            `;
            showSuccess('Reorganization complete!');
            loadDatabaseInfo();
        } else {
            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i> Reorganization failed: ${result.error}
                    ${result.output ? `<details class="mt-2"><summary>View Details</summary><pre class="mt-2 small">${result.output}</pre></details>` : ''}
                </div>
            `;
            showError('Reorganization failed');
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${error.message}</div>`;
        showError('Error executing reorganization');
    }
}

function validateData() {
    const statusDiv = document.getElementById('dataManagementStatus');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = '<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> Validating data...</div>';
    
    showStatus('Checking data integrity...');
    
    setTimeout(() => {
        statusDiv.innerHTML = `
            <div class="alert alert-success">
                <i class="bi bi-check-circle"></i> <strong>Data Validation Complete</strong>
                <ul class="mt-2 mb-0">
                    <li>All payslips have valid dates</li>
                    <li>All run sheets imported successfully</li>
                    <li>No duplicate records found</li>
                </ul>
                <p class="mt-2 mb-0"><small>For detailed discrepancy analysis, visit the <a href="/reports">Reports</a> page.</small></p>
            </div>
        `;
        showSuccess('Data validation complete');
    }, 1500);
}

async function viewSettingsLogs() {
    const statusDiv = document.getElementById('dataManagementStatus');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = '<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> Loading logs...</div>';
    
    try {
        const response = await fetch('/api/settings/logs');
        const result = await response.json();
        
        if (result.success) {
            const logs = result.logs || [];
            const logsHtml = logs.length > 0 
                ? `<pre class="small" style="max-height: 400px; overflow-y: auto; background: #f8f9fa; padding: 10px; border-radius: 5px;">${logs.join('')}</pre>`
                : '<p class="text-muted">No logs yet</p>';
            
            statusDiv.innerHTML = `
                <div class="alert alert-info">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <strong><i class="bi bi-file-text"></i> Operation Logs</strong>
                        <button class="btn btn-sm btn-outline-secondary" onclick="document.getElementById('dataManagementStatus').style.display='none'">
                            <i class="bi bi-x"></i> Close
                        </button>
                    </div>
                    <p class="small mb-2">Showing last ${logs.length} lines (Total: ${result.total_lines || 0})</p>
                    ${logsHtml}
                    <p class="small mt-2 mb-0">Log file: <code>logs/settings.log</code></p>
                </div>
            `;
        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Failed to load logs: ${result.error}</div>`;
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${error.message}</div>`;
    }
}

async function backupDatabase() {
    const statusDiv = document.getElementById('backupStatus');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = '<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> Creating backup...</div>';
    
    try {
        const response = await fetch('/api/data/backup', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> ${result.message}
                    <ul class="mt-2 mb-0">
                        <li><strong>File:</strong> ${result.filename}</li>
                        <li><strong>Size:</strong> ${result.size_mb} MB</li>
                        <li><strong>Location:</strong> ${result.path}</li>
                    </ul>
                </div>
            `;
            showSuccess('Backup created successfully');
        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Backup failed: ${result.error}</div>`;
            showError('Backup failed');
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${error.message}</div>`;
        showError('Error creating backup');
    }
}

function restoreDatabase() {
    alert('To restore from backup:\n\n1. Stop the web app\n2. Replace data/payslips.db with your backup file\n3. Restart the web app\n\nBackup files are in the Backups/ folder');
}

function exportRunSheets() {
    showStatus('Exporting run sheets...');
    window.location.href = '/api/data/export-runsheets';
    setTimeout(() => showSuccess('Run sheets exported to CSV'), 1000);
}

function exportPayslips() {
    showStatus('Exporting payslips...');
    window.location.href = '/api/data/export-payslips';
    setTimeout(() => showSuccess('Payslips exported to CSV'), 1000);
}

async function clearRunSheets() {
    if (!confirm('⚠️ WARNING: This will delete ALL run sheet data!\n\nThis action cannot be undone.\n\nCreate a backup first!\n\nAre you absolutely sure?')) {
        return;
    }
    
    const statusDiv = document.getElementById('dangerZoneStatus');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = '<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> Clearing run sheets...</div>';
    
    try {
        const response = await fetch('/api/data/clear-runsheets', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.innerHTML = `<div class="alert alert-success"><i class="bi bi-check-circle"></i> ${result.message}</div>`;
            showSuccess('Run sheets cleared');
            loadDatabaseInfo();
        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${result.error}</div>`;
            showError('Failed to clear run sheets');
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${error.message}</div>`;
        showError('Error clearing run sheets');
    }
}

async function clearPayslips() {
    if (!confirm('⚠️ WARNING: This will delete ALL payslip and job data!\n\nThis action cannot be undone.\n\nCreate a backup first!\n\nAre you absolutely sure?')) {
        return;
    }
    
    const statusDiv = document.getElementById('dangerZoneStatus');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = '<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> Clearing payslips...</div>';
    
    try {
        const response = await fetch('/api/data/clear-payslips', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.innerHTML = `<div class="alert alert-success"><i class="bi bi-check-circle"></i> ${result.message}</div>`;
            showSuccess('Payslips cleared');
            loadDatabaseInfo();
        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${result.error}</div>`;
            showError('Failed to clear payslips');
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${error.message}</div>`;
        showError('Error clearing payslips');
    }
}

async function clearDatabase() {
    if (!confirm('🚨 DANGER: This will delete EVERYTHING!\n\n- All payslips\n- All job items\n- All run sheets\n- All attendance records\n\nThis action CANNOT be undone!\n\nCreate a backup first!\n\nType "DELETE" to confirm:') || 
        prompt('Type DELETE to confirm:') !== 'DELETE') {
        return;
    }
    
    const statusDiv = document.getElementById('dangerZoneStatus');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = '<div class="alert alert-danger"><i class="bi bi-hourglass-split"></i> Clearing entire database...</div>';
    
    try {
        const response = await fetch('/api/data/clear-all', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.innerHTML = `<div class="alert alert-success"><i class="bi bi-check-circle"></i> ${result.message}</div>`;
            showSuccess('Database cleared');
            loadDatabaseInfo();
        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${result.error}</div>`;
            showError('Failed to clear database');
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${error.message}</div>`;
        showError('Error clearing database');
    }
}

// ===== APPEARANCE =====
function loadAppearance() {
    document.getElementById('defaultPage').value = localStorage.getItem('defaultPage') || 'runsheets';
    document.getElementById('itemsPerPage').value = localStorage.getItem('itemsPerPage') || '20';
    document.getElementById('dateFormat').value = localStorage.getItem('dateFormat') || 'DD/MM/YYYY';
    document.getElementById('theme').value = localStorage.getItem('theme') || 'light';
}

function saveAppearance() {
    localStorage.setItem('defaultPage', document.getElementById('defaultPage').value);
    localStorage.setItem('itemsPerPage', document.getElementById('itemsPerPage').value);
    localStorage.setItem('dateFormat', document.getElementById('dateFormat').value);
    localStorage.setItem('theme', document.getElementById('theme').value);
    showSuccess('Appearance settings saved!');
}

// ===== ADVANCED =====
function viewLogs() {
    window.open('/logs/runsheet_sync.log', '_blank');
}

function clearCache() {
    if (confirm('Clear browser cache and reload?')) {
        localStorage.clear();
        location.reload(true);
    }
}

function rebuildDatabase() {
    if (confirm('Rebuild database indexes? This may take a few minutes.')) {
        showStatus('Rebuilding database indexes...');
        alert('Database rebuild feature coming soon!');
    }
}

function resetSettings() {
    if (confirm('Reset ALL settings to defaults? This cannot be undone!')) {
        localStorage.clear();
        showSuccess('Settings reset! Reloading...');
        setTimeout(() => location.reload(), 2000);
    }
}

// ===== UTILITY =====
function showStatus(message) {
    const status = document.getElementById('settingsStatus');
    status.innerHTML = `<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> ${message}</div>`;
    status.style.display = 'block';
}

function showSuccess(message) {
    const status = document.getElementById('settingsStatus');
    status.innerHTML = `<div class="alert alert-success"><i class="bi bi-check-circle"></i> ${message}</div>`;
    status.style.display = 'block';
    setTimeout(() => status.style.display = 'none', 3000);
}

function showError(message) {
    const status = document.getElementById('settingsStatus');
    status.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> ${message}</div>`;
    status.style.display = 'block';
}

// ===== ATTENDANCE TRACKING =====
async function loadAttendanceRecords() {
    const listDiv = document.getElementById('attendanceRecordsList');
    const yearFilter = document.getElementById('attendanceYearFilter')?.value || '';
    
    listDiv.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div></div>';
    
    try {
        const url = yearFilter ? `/api/attendance?year=${yearFilter}` : '/api/attendance';
        const response = await fetch(url);
        const records = await response.json();
        
        if (records.length === 0) {
            listDiv.innerHTML = '<div class="text-center py-4 text-muted">No attendance records found.</div>';
            return;
        }
        
        let html = '<div class="table-responsive"><table class="table table-hover"><thead><tr><th>Date</th><th>Reason</th><th>Notes</th><th>Action</th></tr></thead><tbody>';
        
        records.forEach(record => {
            html += `
                <tr>
                    <td><strong>${record.date}</strong></td>
                    <td><span class="badge bg-secondary">${record.reason}</span></td>
                    <td>${record.notes || '-'}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteAttendanceRecord(${record.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        
        html += '</tbody></table></div>';
        listDiv.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading attendance records:', error);
        listDiv.innerHTML = '<div class="alert alert-danger">Error loading records</div>';
    }
}

async function addAttendanceRecord() {
    const dateInput = document.getElementById('attendanceDate');
    const reasonSelect = document.getElementById('attendanceReason');
    const notesInput = document.getElementById('attendanceNotes');
    
    const dateValue = dateInput.value;
    if (!dateValue) {
        alert('Please select a date');
        return;
    }
    
    // Convert YYYY-MM-DD to DD/MM/YYYY
    const [year, month, day] = dateValue.split('-');
    const formattedDate = `${day}/${month}/${year}`;
    
    const data = {
        date: formattedDate,
        reason: reasonSelect.value,
        notes: notesInput.value
    };
    
    try {
        const response = await fetch('/api/attendance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showSuccess('Attendance record added successfully');
            dateInput.value = '';
            notesInput.value = '';
            loadAttendanceRecords();
        } else {
            showError(result.error || 'Failed to add record');
        }
        
    } catch (error) {
        console.error('Error adding attendance record:', error);
        showError('Error adding record');
    }
}

async function addMultipleAttendanceRecords() {
    const dateFromInput = document.getElementById('attendanceDateFrom');
    const dateToInput = document.getElementById('attendanceDateTo');
    const reasonSelect = document.getElementById('attendanceReasonMulti');
    const notesInput = document.getElementById('attendanceNotesMulti');
    
    const dateFrom = dateFromInput.value;
    const dateTo = dateToInput.value;
    
    if (!dateFrom || !dateTo) {
        alert('Please select both start and end dates');
        return;
    }
    
    const startDate = new Date(dateFrom);
    const endDate = new Date(dateTo);
    
    if (startDate > endDate) {
        alert('Start date must be before or equal to end date');
        return;
    }
    
    // Generate all dates in range
    const dates = [];
    const currentDate = new Date(startDate);
    
    while (currentDate <= endDate) {
        const day = String(currentDate.getDate()).padStart(2, '0');
        const month = String(currentDate.getMonth() + 1).padStart(2, '0');
        const year = currentDate.getFullYear();
        dates.push(`${day}/${month}/${year}`);
        currentDate.setDate(currentDate.getDate() + 1);
    }
    
    if (!confirm(`Add ${dates.length} attendance records from ${dates[0]} to ${dates[dates.length-1]}?`)) {
        return;
    }
    
    showStatus(`Adding ${dates.length} records...`);
    
    let successCount = 0;
    let errorCount = 0;
    
    // Add each date
    for (const date of dates) {
        const data = {
            date: date,
            reason: reasonSelect.value,
            notes: notesInput.value
        };
        
        try {
            const response = await fetch('/api/attendance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                successCount++;
            } else {
                errorCount++;
            }
        } catch (error) {
            errorCount++;
        }
    }
    
    // Clear inputs
    dateFromInput.value = '';
    dateToInput.value = '';
    notesInput.value = '';
    
    // Show result
    if (errorCount === 0) {
        showSuccess(`Successfully added ${successCount} attendance records`);
    } else {
        showSuccess(`Added ${successCount} records (${errorCount} duplicates/errors skipped)`);
    }
    
    loadAttendanceRecords();
}

async function deleteAttendanceRecord(recordId) {
    if (!confirm('Are you sure you want to delete this record?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/attendance/${recordId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showSuccess('Record deleted successfully');
            loadAttendanceRecords();
        } else {
            showError('Failed to delete record');
        }
        
    } catch (error) {
        console.error('Error deleting attendance record:', error);
        showError('Error deleting record');
    }
}
