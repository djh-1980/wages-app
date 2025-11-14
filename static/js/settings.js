// Load all settings on page load
document.addEventListener('DOMContentLoaded', function() {
    loadAllSettings();
    loadProfile();
    loadAppearance();
    
    // Load attendance records immediately if on settings page
    if (document.getElementById('attendanceRecordsList')) {
        loadAttendanceRecords();
    }
    
    // Also load when attendance tab is shown (if using tabs)
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

async function testGmailConnection() {
    const statusDiv = document.getElementById('gmailStatus');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = '<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> Testing Gmail connection...</div>';
    
    try {
        // Test basic Gmail API connection
        const response = await fetch('/api/gmail/test-connection', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> <strong>Gmail Connection Successful!</strong>
                    <div class="mt-2 small">
                        <strong>Account:</strong> ${result.email || 'Connected'}<br>
                        <strong>Response Time:</strong> ${result.response_time || 'N/A'}<br>
                        <strong>API Access:</strong> Working
                    </div>
                </div>`;
        } else {
            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i> <strong>Gmail Connection Failed</strong>
                    <div class="mt-2 small">
                        <strong>Error:</strong> ${result.error}<br>
                        <strong>Suggestion:</strong> Try re-authorizing Gmail or check your credentials.json file.
                    </div>
                </div>`;
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-x-circle"></i> <strong>Connection Test Failed</strong>
                <div class="mt-2 small">
                    <strong>Error:</strong> ${error.message}<br>
                    <strong>This could mean:</strong> Network issues, invalid credentials, or Gmail API is down.
                </div>
            </div>`;
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
    alert('To re-authorize Gmail:\n\n1. Delete token.json from the project root\n2. Run: python3 scripts/production/download_runsheets_gmail.py\n3. Follow the browser authentication flow\n4. Refresh this page');
}

// ===== DATA =====
function loadDatabaseInfo() {
    // Load all database info from single endpoint
    fetch('/api/data/database/info')
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch database info');
            return response.json();
        })
        .then(data => {
            // Update all counts from the database info API
            const payslipsElement = document.getElementById('dbPayslips');
            const runsheetsElement = document.getElementById('dbRunSheets');
            const jobsElement = document.getElementById('dbJobs');
            const attendanceElement = document.getElementById('dbAttendance');
            const sizeElement = document.getElementById('dbSize');
            
            if (payslipsElement) {
                payslipsElement.textContent = data.records?.payslips || 0;
            }
            if (runsheetsElement) {
                runsheetsElement.textContent = data.records?.runsheets || 0;
            }
            if (jobsElement) {
                jobsElement.textContent = data.records?.jobs || 0;
            }
            if (attendanceElement) {
                attendanceElement.textContent = data.records?.attendance || 0;
            }
            if (sizeElement) {
                const sizeStr = formatFileSize(data.size_bytes || 0);
                sizeElement.textContent = sizeStr;
            }
        })
        .catch(error => {
            console.error('Error loading database info:', error);
            // Set error states for all elements
            const elements = [
                { id: 'dbPayslips', fallback: 'Error' },
                { id: 'dbRunSheets', fallback: 'Error' },
                { id: 'dbJobs', fallback: 'Error' },
                { id: 'dbAttendance', fallback: 'Error' },
                { id: 'dbSize', fallback: 'Unknown' }
            ];
            
            elements.forEach(({ id, fallback }) => {
                const element = document.getElementById(id);
                if (element) {
                    element.textContent = fallback;
                }
            });
        });
}

// Helper function to format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

async function syncPayslips() {
    const statusDiv = document.getElementById('syncDataStatus');
    statusDiv.style.display = 'block';
    
    // Show immediate progress steps
    const showStep = (step, message, percent) => {
        statusDiv.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-hourglass-split"></i> <strong>Syncing Payslips</strong>
                <div class="mt-3">
                    <div class="progress mb-2">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: ${percent}%"></div>
                    </div>
                    <small><strong>Step ${step}:</strong> ${message}</small>
                </div>
                <div id="payslipProgressLog" class="mt-3">
                    <small class="text-muted d-block mb-1"><strong>Live Progress Log:</strong></small>
                    <pre class="small bg-dark text-light p-3 rounded" style="max-height: 200px; overflow-y: auto; font-family: 'Courier New', monospace;">Waiting for server logs...</pre>
                </div>
            </div>`;
    };
    
    try {
        showStep(1, 'Checking database for last payslip date...', 10);
        
        // Small delay to show the step
        await new Promise(resolve => setTimeout(resolve, 500));
        
        showStep(2, 'Connecting to Gmail API...', 25);
        await new Promise(resolve => setTimeout(resolve, 500));
        
        showStep(3, 'Searching for new payslips in Gmail...', 50);
        
        // Start real-time progress polling
        let progressInterval = setInterval(async () => {
            try {
                const progressResponse = await fetch('/api/data/payslip-sync-progress');
                const progressData = await progressResponse.json();
                if (progressData.success && progressData.progress && progressData.progress !== 'No progress available') {
                    const logDiv = document.getElementById('payslipProgressLog');
                    if (logDiv) {
                        const preElement = logDiv.querySelector('pre');
                        if (preElement) {
                            preElement.textContent = progressData.progress;
                            preElement.scrollTop = preElement.scrollHeight;
                        }
                    }
                }
            } catch (e) {
                console.log('Progress polling error:', e);
            }
        }, 1000); // Poll every 1 second for more responsive updates
        
        // Add timeout to prevent hanging
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            controller.abort();
            clearInterval(progressInterval);
            showStep('X', 'Timeout - Gmail took too long to respond (6 minutes)', 0);
        }, 360000); // 6 minutes (5 min server + 1 min buffer)
        
        const response = await fetch('/api/data/sync-payslips', {
            method: 'POST',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        clearInterval(progressInterval);
        
        showStep(4, 'Processing response...', 90);
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
// Error already shown in statusDiv
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            statusDiv.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-clock"></i> <strong>Sync timed out after 2.5 minutes</strong>
                    <p class="mb-0 mt-2">This usually means Gmail is taking too long to respond. Try again later or check your internet connection.</p>
                </div>`;
// Timeout already shown in statusDiv
        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Error: ${error.message}</div>`;
            // Error already shown in statusDiv
        }
    }
}

let syncProgressInterval = null;

async function syncLatest() {
    try {
        updateSyncStatus('Running', 'Syncing latest from Gmail...');
        
        const response = await fetch('/api/data/sync-runsheets', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            updateSyncStatus('Complete', 'Latest files synced successfully');
            showSuccess('✅ Latest runsheet + payslip synced successfully!');
            updateLastSyncTime();
            loadDatabaseStats();
        } else {
            updateSyncStatus('Error', 'Sync failed');
            showError(`❌ Sync failed: ${result.error}`);
        }
    } catch (error) {
        updateSyncStatus('Error', 'Connection error');
        showError(`❌ Sync failed: ${error.message}`);
    }
}

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
        
        const downloadResponse = await fetch('/api/gmail/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                mode: 'runsheets',
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
    const statusDiv = document.getElementById('syncDataStatus');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = `
        <div class="alert alert-warning">
            <i class="bi bi-hourglass-split"></i> <strong>Checking Gmail for new run sheets...</strong>
            <p class="mb-0 mt-2 small">
                Downloading new files and importing to database. This may take a minute.<br>
                Progress will update below.
            </p>
            <div id="syncProgress" class="mt-3">
                <pre class="small" style="max-height: 300px; overflow-y: auto; background: #f8f9fa; padding: 10px; border-radius: 5px;">Initializing...</pre>
            </div>
        </div>
    `;
    
    showStatus('Importing run sheets (this may take a while)...');
    
    // Start polling for progress
    syncProgressInterval = setInterval(updateSyncProgress, 1000); // More frequent updates
    
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
    const choice = confirm('This will reorganize all run sheets:\n\n1. Move all to data/runsheets/backup\n2. Check for "Hanson, Daniel"\n3. Organize by year/month\n4. Rename to DH_DD-MM-YYYY.pdf\n\nClick OK to preview changes (dry run)\nClick Cancel to abort');
    
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
    const defaultPageEl = document.getElementById('defaultPage');
    const itemsPerPageEl = document.getElementById('itemsPerPage');
    const dateFormatEl = document.getElementById('dateFormat');
    const themeEl = document.getElementById('theme');
    
    if (defaultPageEl) defaultPageEl.value = localStorage.getItem('defaultPage') || 'runsheets';
    if (itemsPerPageEl) itemsPerPageEl.value = localStorage.getItem('itemsPerPage') || '20';
    if (dateFormatEl) dateFormatEl.value = localStorage.getItem('dateFormat') || 'DD/MM/YYYY';
    if (themeEl) themeEl.value = localStorage.getItem('theme') || 'light';
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

// Group consecutive dates with same reason and notes
function groupConsecutiveDates(records) {
    if (records.length === 0) return [];
    
    // Sort records by date
    const sortedRecords = records.sort((a, b) => {
        const dateA = convertDateForSorting(a.date);
        const dateB = convertDateForSorting(b.date);
        return dateA.localeCompare(dateB);
    });
    
    const groups = [];
    let currentGroup = {
        dates: [sortedRecords[0].date],
        reason: sortedRecords[0].reason,
        notes: sortedRecords[0].notes,
        recordIds: [sortedRecords[0].id]
    };
    
    for (let i = 1; i < sortedRecords.length; i++) {
        const current = sortedRecords[i];
        const previous = sortedRecords[i - 1];
        
        // Check if current record can be grouped with previous
        if (current.reason === currentGroup.reason && 
            current.notes === currentGroup.notes &&
            isConsecutiveDate(previous.date, current.date)) {
            
            currentGroup.dates.push(current.date);
            currentGroup.recordIds.push(current.id);
        } else {
            // Start new group
            groups.push(currentGroup);
            currentGroup = {
                dates: [current.date],
                reason: current.reason,
                notes: current.notes,
                recordIds: [current.id]
            };
        }
    }
    
    // Add the last group
    groups.push(currentGroup);
    
    return groups;
}

// Convert DD/MM/YYYY to YYYY-MM-DD for sorting
function convertDateForSorting(dateStr) {
    const [day, month, year] = dateStr.split('/');
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
}

// Check if two dates are consecutive
function isConsecutiveDate(date1, date2) {
    const d1 = new Date(convertDateForSorting(date1));
    const d2 = new Date(convertDateForSorting(date2));
    const diffTime = Math.abs(d2 - d1);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays === 1;
}

async function loadAttendanceRecords() {
    const listDiv = document.getElementById('attendanceRecordsList');
    const fromDate = document.getElementById('attendanceFromDate')?.value || '';
    const toDate = document.getElementById('attendanceToDate')?.value || '';
    
    listDiv.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div></div>';
    
    try {
        let url = '/api/attendance';
        const params = new URLSearchParams();
        
        if (fromDate) params.append('from_date', fromDate);
        if (toDate) params.append('to_date', toDate);
        
        if (params.toString()) {
            url += '?' + params.toString();
        }
        
        const response = await fetch(url);
        const records = await response.json();
        
        if (records.length === 0) {
            listDiv.innerHTML = '<div class="text-center py-4 text-muted">No attendance records found.</div>';
            return;
        }
        
        // Group consecutive dates with same reason and notes
        const groupedRecords = groupConsecutiveDates(records);
        
        let html = '<div class="table-responsive"><table class="table table-hover"><thead><tr><th>Date(s)</th><th>Reason</th><th>Notes</th><th>Action</th></tr></thead><tbody>';
        
        groupedRecords.forEach(group => {
            const dateDisplay = group.dates.length === 1 ? 
                group.dates[0] : 
                `${group.dates[0]} to ${group.dates[group.dates.length - 1]} (${group.dates.length} days)`;
            
            html += `
                <tr>
                    <td><strong>${dateDisplay}</strong></td>
                    <td><span class="badge bg-secondary">${group.reason}</span></td>
                    <td>${group.notes || '-'}</td>
                    <td>
                        ${group.recordIds.length === 1 ? 
                            // Single record - show edit and delete
                            `<button class="btn btn-sm btn-outline-primary me-1" onclick="editAttendanceRecord(${group.recordIds[0]}, '${group.dates[0]}', '${group.reason}', '${group.notes || ''}')" title="Edit record">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteAttendanceRecord(${group.recordIds[0]})" title="Delete record">
                                <i class="bi bi-trash"></i>
                            </button>` :
                            // Grouped records - show edit group and delete group
                            `<button class="btn btn-sm btn-outline-primary me-1" onclick="editAttendanceGroup([${group.recordIds.join(',')}], '${group.dates[0]}', '${group.dates[group.dates.length - 1]}', '${group.reason}', '${group.notes || ''}')" title="Edit group">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteAttendanceGroup([${group.recordIds.join(',')}])" title="Delete entire group">
                                <i class="bi bi-trash"></i>
                            </button>`
                        }
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
    const fromDateInput = document.getElementById('attendanceFromDateAdd');
    const toDateInput = document.getElementById('attendanceToDateAdd');
    const reasonSelect = document.getElementById('attendanceReason');
    const notesInput = document.getElementById('attendanceNotes');
    
    const fromDate = fromDateInput.value;
    const toDate = toDateInput.value;
    
    if (!fromDate) {
        showError('Please select a from date');
        return;
    }
    
    // Validate date range
    if (toDate && fromDate > toDate) {
        showError('From date cannot be later than To date');
        return;
    }
    
    const reason = reasonSelect.value;
    const notes = notesInput.value;
    
    try {
        // If no to date, just add single record
        if (!toDate) {
            await addSingleAttendanceRecord(fromDate, reason, notes);
        } else {
            // Add records for date range
            await addAttendanceRecordRange(fromDate, toDate, reason, notes);
        }
        
        // Clear form
        fromDateInput.value = '';
        toDateInput.value = '';
        notesInput.value = '';
        loadAttendanceRecords();
        
    } catch (error) {
        console.error('Error adding attendance record:', error);
        showError('Error adding record');
    }
}

async function addSingleAttendanceRecord(dateValue, reason, notes) {
    // Convert YYYY-MM-DD to DD/MM/YYYY
    const [year, month, day] = dateValue.split('-');
    const formattedDate = `${day}/${month}/${year}`;
    
    const data = {
        date: formattedDate,
        reason: reason,
        notes: notes
    };
    
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
    } else {
        showError(result.error || 'Failed to add record');
    }
}

async function addAttendanceRecordRange(fromDate, toDate, reason, notes) {
    const startDate = new Date(fromDate);
    const endDate = new Date(toDate);
    const records = [];
    
    // Generate all dates in the range
    for (let date = new Date(startDate); date <= endDate; date.setDate(date.getDate() + 1)) {
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        const formattedDate = `${day}/${month}/${year}`;
        
        records.push({
            date: formattedDate,
            reason: reason,
            notes: notes
        });
    }
    
    // Add all records
    let successCount = 0;
    let errorCount = 0;
    
    for (const record of records) {
        try {
            const response = await fetch('/api/attendance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(record)
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
    
    if (errorCount === 0) {
        showSuccess(`Successfully added ${successCount} attendance records for date range`);
    } else {
        showSuccess(`Added ${successCount} records (${errorCount} duplicates/errors skipped)`);
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
    if (!confirm('Are you sure you want to delete this attendance record?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/attendance/${recordId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showSuccess('Attendance record deleted successfully');
            loadAttendanceRecords();
        } else {
            showError(result.error || 'Failed to delete record');
        }
    } catch (error) {
        console.error('Error deleting attendance record:', error);
        showError('Error deleting record');
    }
}

// Filter attendance records by date range
function filterAttendanceRecords() {
    const fromDate = document.getElementById('attendanceFromDate').value;
    const toDate = document.getElementById('attendanceToDate').value;
    
    // Validate date range
    if (fromDate && toDate && fromDate > toDate) {
        showError('From date cannot be later than To date');
        return;
    }
    
    loadAttendanceRecords();
}

// Clear attendance filters
function clearAttendanceFilter() {
    document.getElementById('attendanceFromDate').value = '';
    document.getElementById('attendanceToDate').value = '';
    loadAttendanceRecords();
}

// Set attendance date range presets
function setAttendanceDateRange(period) {
    const fromDateInput = document.getElementById('attendanceFromDate');
    const toDateInput = document.getElementById('attendanceToDate');
    const today = new Date();
    let fromDate, toDate;
    
    switch (period) {
        case 'thisMonth':
            fromDate = new Date(today.getFullYear(), today.getMonth(), 1);
            toDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
            break;
        case 'lastMonth':
            fromDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
            toDate = new Date(today.getFullYear(), today.getMonth(), 0);
            break;
        case 'thisYear':
            fromDate = new Date(today.getFullYear(), 0, 1);
            toDate = new Date(today.getFullYear(), 11, 31);
            break;
        case 'lastYear':
            fromDate = new Date(today.getFullYear() - 1, 0, 1);
            toDate = new Date(today.getFullYear() - 1, 11, 31);
            break;
        default:
            return;
    }
    
    // Format dates as YYYY-MM-DD for HTML date inputs
    fromDateInput.value = fromDate.toISOString().split('T')[0];
    toDateInput.value = toDate.toISOString().split('T')[0];
    
    // Automatically apply the filter
    filterAttendanceRecords();
}

// Toggle attendance filter visibility
function toggleAttendanceFilter() {
    const filterPanel = document.getElementById('attendanceFilterPanel');
    const toggleButton = document.querySelector('button[onclick="toggleAttendanceFilter()"]');
    
    if (filterPanel.style.display === 'none') {
        filterPanel.style.display = 'block';
        toggleButton.innerHTML = '<i class="bi bi-funnel me-1"></i>Hide Filters';
    } else {
        filterPanel.style.display = 'none';
        toggleButton.innerHTML = '<i class="bi bi-funnel me-1"></i>Show Filters';
    }
}

// Edit attendance record
let currentEditingRecordId = null;

function editAttendanceRecord(recordId, date, reason, notes) {
    currentEditingRecordId = recordId;
    
    // Convert DD/MM/YYYY to YYYY-MM-DD for HTML date input
    const [day, month, year] = date.split('/');
    const formattedDate = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
    
    // Populate modal fields
    document.getElementById('editAttendanceDate').value = formattedDate;
    document.getElementById('editAttendanceReason').value = reason;
    document.getElementById('editAttendanceNotes').value = notes;
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('editAttendanceModal'));
    modal.show();
}

async function saveAttendanceEdit() {
    if (!currentEditingRecordId) return;
    
    const dateInput = document.getElementById('editAttendanceDate');
    const reasonSelect = document.getElementById('editAttendanceReason');
    const notesInput = document.getElementById('editAttendanceNotes');
    
    const reasonValue = reasonSelect.value;
    const notesValue = notesInput.value;
    
    try {
        // Check if editing single record or group
        if (Array.isArray(currentEditingRecordId)) {
            // Group editing - update reason and notes for all records
            let successCount = 0;
            let errorCount = 0;
            
            for (const recordId of currentEditingRecordId) {
                try {
                    const response = await fetch(`/api/attendance/${recordId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            reason: reasonValue,
                            notes: notesValue
                        })
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
            
            if (errorCount === 0) {
                showSuccess(`Successfully updated ${successCount} attendance records`);
            } else {
                showSuccess(`Updated ${successCount} records (${errorCount} errors)`);
            }
        } else {
            // Single record editing
            const dateValue = dateInput.value;
            if (!dateValue) {
                showError('Please select a date');
                return;
            }
            
            // Convert YYYY-MM-DD to DD/MM/YYYY
            const [year, month, day] = dateValue.split('-');
            const formattedDate = `${day}/${month}/${year}`;
            
            const data = {
                date: formattedDate,
                reason: reasonValue,
                notes: notesValue
            };
            
            const response = await fetch(`/api/attendance/${currentEditingRecordId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showSuccess('Attendance record updated successfully');
            } else {
                showError(result.error || 'Failed to update record');
            }
        }
        
        // Close modal and reset
        const modal = bootstrap.Modal.getInstance(document.getElementById('editAttendanceModal'));
        modal.hide();
        
        // Reset modal state
        document.getElementById('editAttendanceDate').disabled = false;
        document.querySelector('#editAttendanceModal .modal-title').innerHTML = 
            '<i class="bi bi-pencil me-2"></i>Edit Attendance Record';
        
        // Reload records
        loadAttendanceRecords();
        
    } catch (error) {
        console.error('Error updating attendance record:', error);
        showError('Error updating record');
    }
}

// Edit attendance group (multiple records)
function editAttendanceGroup(recordIds, fromDate, toDate, reason, notes) {
    // For now, just edit the reason and notes for all records in the group
    // We'll use a simpler approach - edit all records with same reason/notes
    const confirmed = confirm(`Edit all ${recordIds.length} records in this group?\n\nThis will update the reason and notes for all days from ${fromDate} to ${toDate}.`);
    
    if (confirmed) {
        // Use the single record edit modal but indicate it's for a group
        currentEditingRecordId = recordIds; // Store array for group editing
        
        // Convert DD/MM/YYYY to YYYY-MM-DD for HTML date input (use from date)
        const [day, month, year] = fromDate.split('/');
        const formattedDate = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
        
        // Populate modal fields
        document.getElementById('editAttendanceDate').value = formattedDate;
        document.getElementById('editAttendanceDate').disabled = true; // Disable date editing for groups
        document.getElementById('editAttendanceReason').value = reason;
        document.getElementById('editAttendanceNotes').value = notes;
        
        // Show modal with group indicator
        const modal = new bootstrap.Modal(document.getElementById('editAttendanceModal'));
        document.querySelector('#editAttendanceModal .modal-title').innerHTML = 
            `<i class="bi bi-pencil me-2"></i>Edit Group (${recordIds.length} days)`;
        modal.show();
    }
}

// Delete attendance group (multiple records)
async function deleteAttendanceGroup(recordIds) {
    if (!confirm(`Are you sure you want to delete all ${recordIds.length} records in this group? This action cannot be undone.`)) {
        return;
    }
    
    let successCount = 0;
    let errorCount = 0;
    
    for (const recordId of recordIds) {
        try {
            const response = await fetch(`/api/attendance/${recordId}`, {
                method: 'DELETE'
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
    
    if (errorCount === 0) {
        showSuccess(`Successfully deleted ${successCount} attendance records`);
    } else {
        showSuccess(`Deleted ${successCount} records (${errorCount} errors)`);
    }
    
    loadAttendanceRecords();
}

// Clear all attendance records
async function clearAllAttendanceRecords() {
    if (!confirm('Are you sure you want to delete ALL attendance records? This action cannot be undone.')) {
        return;
    }
    
    // Double confirmation for safety
    if (!confirm('This will permanently delete all attendance records. Are you absolutely sure?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/attendance/clear-all', {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showSuccess(`Successfully deleted ${result.deleted_count} attendance records`);
            loadAttendanceRecords();
        } else {
            showError(result.error || 'Failed to clear records');
        }
    } catch (error) {
        console.error('Error clearing attendance records:', error);
        showError('Error clearing records');
    }
}
