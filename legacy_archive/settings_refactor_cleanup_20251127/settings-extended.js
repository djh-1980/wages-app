
// File management functions
async function hybridSync() {
    try {
        showStatus('Running smart sync...');
        const result = await HybridSyncManager.hybridSync('smart');
        showResults('Smart Sync Complete', result);
        hideStatus();
    } catch (error) {
        showError(`Smart sync failed: ${error.message}`);
        hideStatus();
    }
}

async function processLocalFiles() {
    try {
        const fileType = document.getElementById('localFileType').value;
        const daysBack = parseInt(document.getElementById('localDaysBack').value);
        
        showStatus('Processing local files...');
        const result = await HybridSyncManager.processLocalFiles({
            type: fileType,
            days_back: daysBack
        });
        
        document.getElementById('localFilesResults').innerHTML = `
            <div class="alert alert-${result.success ? 'success' : 'danger'}">
                <i class="bi bi-${result.success ? 'check-circle' : 'x-circle'}"></i>
                Processing ${result.success ? 'completed' : 'failed'}
            </div>
        `;
        document.getElementById('localFilesResults').style.display = 'block';
        hideStatus();
    } catch (error) {
        showError(`Processing failed: ${error.message}`);
        hideStatus();
    }
}

async function testGmailConnection() {
    try {
        showStatus('Testing Gmail connection...');
        const response = await fetch('/api/gmail/test-connection', { method: 'POST' });
        const result = await response.json();
        
        const resultsDiv = document.getElementById('gmailTestResults');
        if (result.success) {
            resultsDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i>
                    Gmail connected successfully! Email: ${result.email}
                </div>
            `;
        } else {
            resultsDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i>
                    Connection failed: ${result.error}
                </div>
            `;
        }
        resultsDiv.style.display = 'block';
        hideStatus();
    } catch (error) {
        showError(`Connection test failed: ${error.message}`);
        hideStatus();
    }
}

// Enhanced sync functions with real-time status
async function syncPayslips() {
    try {
        updateSyncStatus('Running', 'Syncing payslips from Gmail...');
        
        const response = await fetch('/api/data/sync-payslips', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            updateSyncStatus('Complete', 'Payslips synced successfully');
            showSuccess('✅ Payslips synced successfully!');
            updateLastSyncTime();
            loadDatabaseStats(); // Refresh stats
        } else {
            updateSyncStatus('Error', 'Payslip sync failed');
            showError(`❌ Sync failed: ${result.error}`);
        }
    } catch (error) {
        updateSyncStatus('Error', 'Connection error');
        showError(`❌ Sync failed: ${error.message}`);
    }
}

async function syncLatest() {
    try {
        // Show loading state
        const button = event.target.closest('button');
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> Syncing...';
        button.disabled = true;
        
        const response = await fetch('/api/data/sync-runsheets', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            // Show success briefly
            button.innerHTML = '<i class="bi bi-check-circle text-success"></i> Success!';
            setTimeout(() => {
                button.innerHTML = originalText;
                button.disabled = false;
            }, 2000);
            
            // Refresh sync status
            if (typeof loadSyncStatus === 'function') {
                loadSyncStatus();
            }
        } else {
            button.innerHTML = '<i class="bi bi-x-circle text-danger"></i> Failed';
            setTimeout(() => {
                button.innerHTML = originalText;
                button.disabled = false;
            }, 2000);
            console.error('Sync failed:', result.error);
        }
    } catch (error) {
        const button = event.target.closest('button');
        const originalText = '<i class="bi bi-cloud-download"></i> Manual Sync';
        button.innerHTML = '<i class="bi bi-x-circle text-danger"></i> Error';
        setTimeout(() => {
            button.innerHTML = originalText;
            button.disabled = false;
        }, 2000);
        console.error('Sync error:', error.message);
    }
}

async function syncRunSheets() {
    try {
        updateSyncStatus('Running', 'Syncing run sheets from Gmail...');
        
        const response = await fetch('/api/data/sync-runsheets', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            updateSyncStatus('Complete', 'Run sheets synced successfully');
            showSuccess('✅ Run sheets synced successfully!');
            updateLastSyncTime();
            loadDatabaseStats(); // Refresh stats
        } else {
            updateSyncStatus('Error', 'Run sheet sync failed');
            showError(`❌ Sync failed: ${result.error}`);
        }
    } catch (error) {
        updateSyncStatus('Error', 'Connection error');
        showError(`❌ Sync failed: ${error.message}`);
    }
}

function saveProfile() {
    showSuccess('Profile saved successfully!');
}

function clearCache() {
    showSuccess('Cache cleared successfully!');
}

function loadAllSettings() {
    // Load database stats
    loadDatabaseStats();
    // Load sync status
    loadSyncStatus();
    // Load periodic sync status
    loadPeriodicSyncStatus();
}

// Periodic sync functions
async function loadPeriodicSyncStatus() {
    try {
        const response = await fetch('/api/data/periodic-sync/status');
        const status = await response.json();
        
        if (status.success) {
            const toggle = document.getElementById('periodicSyncToggle');
            const label = document.getElementById('periodicSyncLabel');
            const info = document.getElementById('periodicSyncInfo');
            const badge = document.getElementById('autoSyncBadge');
            const nextSyncDiv = document.getElementById('nextSyncTime');
            const nextSyncValue = document.getElementById('nextSyncTimeValue');
            
            // Only update if elements exist (new sync UI handles this)
            if (toggle) {
                toggle.checked = status.is_running;
            }
            if (label) {
                label.textContent = status.is_running ? 'Enabled' : 'Disabled';
            }
            
            if (status.is_running) {
                if (info) info.style.display = 'block';
                if (badge) badge.style.display = 'inline-block';
                
                // Show next sync time if available
                if (status.next_sync_estimate && nextSyncValue && nextSyncDiv) {
                    const nextSync = new Date(status.next_sync_estimate);
                    nextSyncValue.textContent = nextSync.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
                    nextSyncDiv.style.display = 'block';
                }
            } else {
                if (info) info.style.display = 'none';
                if (badge) badge.style.display = 'none';
                if (nextSyncDiv) nextSyncDiv.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Failed to load periodic sync status:', error);
    }
}

async function togglePeriodicSync() {
    const toggle = document.getElementById('periodicSyncToggle');
    const label = document.getElementById('periodicSyncLabel');
    
    try {
        const action = toggle.checked ? 'start' : 'stop';
        const response = await fetch(`/api/data/periodic-sync/${action}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            label.textContent = toggle.checked ? 'Enabled' : 'Disabled';
            showSuccess(`Periodic sync ${toggle.checked ? 'enabled' : 'disabled'}`);
            loadPeriodicSyncStatus();
            
            // Update navbar badge immediately
            if (typeof checkAutoSyncStatus === 'function') {
                checkAutoSyncStatus();
            }
        } else {
            // Revert toggle on error
            toggle.checked = !toggle.checked;
            showError('Failed to toggle periodic sync');
        }
    } catch (error) {
        // Revert toggle on error
        toggle.checked = !toggle.checked;
        showError(`Failed to toggle periodic sync: ${error.message}`);
    }
}

async function forceSync() {
    try {
        updateSyncStatus('Running', 'Force syncing all recent files...');
        
        const response = await fetch('/api/data/periodic-sync/force', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            updateSyncStatus('Complete', 'Force sync initiated');
            showSuccess('⚡ Force sync started in background - check status above');
            updateLastSyncTime();
            
            // Refresh stats after a delay
            setTimeout(() => {
                loadDatabaseStats();
            }, 5000);
        } else {
            updateSyncStatus('Error', 'Force sync failed');
            showError(`❌ Force sync failed: ${result.error}`);
        }
    } catch (error) {
        updateSyncStatus('Error', 'Connection error');
        showError(`❌ Force sync failed: ${error.message}`);
    }
}

async function loadDatabaseStats() {
    try {
        const response = await fetch('/api/data/stats');
        const stats = await response.json();
        
        if (stats.success) {
            const dbPayslips = document.getElementById('dbPayslips');
            const dbRunSheets = document.getElementById('dbRunSheets');
            const dbJobs = document.getElementById('dbJobs');
            const dbSize = document.getElementById('dbSize');
            const totalRecords = document.getElementById('totalRecords');
            
            if (dbPayslips) dbPayslips.textContent = stats.payslips || '-';
            if (dbRunSheets) dbRunSheets.textContent = stats.runsheets || '-';
            if (dbJobs) dbJobs.textContent = stats.jobs || '-';
            if (dbSize) dbSize.textContent = stats.size || '-';
            if (totalRecords) totalRecords.textContent = stats.total_records || '-';
        }
    } catch (error) {
        console.error('Failed to load database stats:', error);
        // Set fallback values only if elements exist
        const dbPayslips = document.getElementById('dbPayslips');
        const dbRunSheets = document.getElementById('dbRunSheets');
        const dbJobs = document.getElementById('dbJobs');
        const dbSize = document.getElementById('dbSize');
        const totalRecords = document.getElementById('totalRecords');
        
        if (dbPayslips) dbPayslips.textContent = '-';
        if (dbRunSheets) dbRunSheets.textContent = '-';
        if (dbJobs) dbJobs.textContent = '-';
        if (dbSize) dbSize.textContent = '-';
        if (totalRecords) totalRecords.textContent = '-';
    }
}

async function loadSyncStatus() {
    try {
        const response = await fetch('/api/gmail/status');
        const status = await response.json();
        
        const badge = document.getElementById('syncStatusBadge');
        if (status.configured && status.authenticated) {
            badge.textContent = 'Connected';
            badge.className = 'fw-semibold text-success';
        } else {
            badge.textContent = 'Not Connected';
            badge.className = 'fw-semibold text-danger';
        }
    } catch (error) {
        console.error('Failed to load sync status:', error);
    }
}

// Utility functions
function updateSyncStatus(status, message) {
    const statusElement = document.getElementById('currentSyncStatus');
    const iconElement = document.getElementById('syncActivityIcon');
    
    statusElement.textContent = status;
    
    // Update icon and color based on status
    switch(status) {
        case 'Running':
            iconElement.className = 'bi bi-arrow-repeat text-primary fs-4';
            iconElement.style.animation = 'spin 1s linear infinite';
            statusElement.className = 'fw-semibold text-primary';
            break;
        case 'Complete':
            iconElement.className = 'bi bi-check-circle text-success fs-4';
            iconElement.style.animation = 'none';
            statusElement.className = 'fw-semibold text-success';
            // Auto-reset to idle after 5 seconds
            setTimeout(() => updateSyncStatus('Idle', ''), 5000);
            break;
        case 'Error':
            iconElement.className = 'bi bi-x-circle text-danger fs-4';
            iconElement.style.animation = 'none';
            statusElement.className = 'fw-semibold text-danger';
            // Auto-reset to idle after 10 seconds
            setTimeout(() => updateSyncStatus('Idle', ''), 10000);
            break;
        default: // Idle
            iconElement.className = 'bi bi-activity text-warning fs-4';
            iconElement.style.animation = 'none';
            statusElement.className = 'fw-semibold';
            break;
    }
}

function updateLastSyncTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-GB', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
    });
    document.getElementById('lastSyncTime').textContent = timeString;
}

function showStatus(message) {
    console.log('Status:', message);
}

function hideStatus() {
    // Hide status display
}

function showSuccess(message) {
    const alert = document.createElement('div');
    alert.className = 'alert alert-success alert-dismissible fade show position-fixed';
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alert.innerHTML = `
        <i class="bi bi-check-circle"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alert);
    setTimeout(() => alert.remove(), 5000);
}

function showError(message) {
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alert.innerHTML = `
        <i class="bi bi-exclamation-triangle"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alert);
    setTimeout(() => alert.remove(), 8000);
}

// Attendance functions
function toggleAttendanceMode() {
    const singleMode = document.getElementById('singleDayMode').checked;
    document.getElementById('singleDayForm').style.display = singleMode ? 'block' : 'none';
    document.getElementById('rangeDayForm').style.display = singleMode ? 'none' : 'block';
}

async function loadAttendanceRecords() {
    console.log('🔍 loadAttendanceRecords called');
    const yearFilter = document.getElementById('attendanceYearFilter');
    const year = yearFilter ? yearFilter.value : '';
    const listDiv = document.getElementById('attendanceRecordsList');
    
    console.log('📋 Year filter:', year);
    console.log('📦 Container found:', !!listDiv);
    
    if (!listDiv) {
        console.error('❌ attendanceRecordsList container not found!');
        // Create a fallback message if the container is missing
        const attendanceTab = document.getElementById('attendance');
        if (attendanceTab) {
            const fallbackDiv = document.createElement('div');
            fallbackDiv.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle"></i>
                    Attendance records container not found. Please refresh the page.
                </div>
            `;
            attendanceTab.appendChild(fallbackDiv);
        }
        return;
    }
    
    try {
        listDiv.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2 text-muted">Loading records...</p>
            </div>
        `;
        
        const url = year ? `/api/settings/attendance?year=${year}` : '/api/settings/attendance';
        console.log('🌐 Fetching attendance records from:', url);
        
        const response = await fetch(url);
        console.log('📡 Response status:', response.status);
        console.log('📡 Response ok:', response.ok);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('📊 API result:', result);
        
        if (!result.success) {
            throw new Error(result.error || 'Failed to load records');
        }
        
        const records = result.records;
        console.log('📋 Records received:', records ? records.length : 0);
        
        if (records.length === 0) {
            listDiv.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-calendar-x fs-1"></i>
                    <p class="mt-2">No attendance records found</p>
                </div>
            `;
            return;
        }
        
        // Helper function to parse DD/MM/YYYY format
        const parseDate = (dateStr) => {
            const parts = dateStr.split('/');
            if (parts.length === 3) {
                // DD/MM/YYYY format
                return new Date(parts[2], parts[1] - 1, parts[0]);
            }
            // Fallback to standard parsing
            return new Date(dateStr);
        };
        
        // Sort records by date
        records.sort((a, b) => parseDate(a.date) - parseDate(b.date));
        
        // Group consecutive days with same reason
        const groups = [];
        let currentGroup = null;
        
        records.forEach(record => {
            // Parse date properly - handle DD/MM/YYYY format
            const recordDate = parseDate(record.date);
            
            if (!currentGroup) {
                currentGroup = {
                    startDate: recordDate,
                    endDate: recordDate,
                    reason: record.reason,
                    notes: record.notes,
                    ids: [record.id],
                    records: [record]
                };
            } else {
                const lastDate = currentGroup.endDate;
                const daysDiff = Math.round((recordDate - lastDate) / (1000 * 60 * 60 * 24));
                
                // If consecutive day and same reason, add to current group
                if (daysDiff === 1 && record.reason === currentGroup.reason) {
                    currentGroup.endDate = recordDate;
                    currentGroup.ids.push(record.id);
                    currentGroup.records.push(record);
                    // Append notes if different
                    if (record.notes && record.notes !== currentGroup.notes) {
                        currentGroup.notes = currentGroup.notes ? 
                            `${currentGroup.notes}; ${record.notes}` : record.notes;
                    }
                } else {
                    // Start new group
                    groups.push(currentGroup);
                    currentGroup = {
                        startDate: recordDate,
                        endDate: recordDate,
                        reason: record.reason,
                        notes: record.notes,
                        ids: [record.id],
                        records: [record]
                    };
                }
            }
        });
        
        // Push last group
        if (currentGroup) {
            groups.push(currentGroup);
        }
        
        // Render groups
        const reasonColors = {
            'Holiday': 'success',
            'Sick': 'danger',
            'Personal': 'warning',
            'Training': 'info',
            'Other': 'secondary'
        };
        
        let html = '<div class="list-group">';
        groups.forEach(group => {
            const color = reasonColors[group.reason] || 'secondary';
            const isRange = group.startDate.getTime() !== group.endDate.getTime();
            const dayCount = group.ids.length;
            
            let dateDisplay;
            if (isRange) {
                const startStr = group.startDate.toLocaleDateString('en-GB', { 
                    weekday: 'short', 
                    month: 'short', 
                    day: 'numeric' 
                });
                const endStr = group.endDate.toLocaleDateString('en-GB', { 
                    weekday: 'short', 
                    month: 'short', 
                    day: 'numeric',
                    year: 'numeric'
                });
                dateDisplay = `${startStr} - ${endStr}`;
            } else {
                dateDisplay = group.startDate.toLocaleDateString('en-GB', { 
                    weekday: 'short', 
                    year: 'numeric', 
                    month: 'short', 
                    day: 'numeric' 
                });
            }
            
            html += `
                <div class="list-group-item">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">
                                <i class="bi bi-calendar-${isRange ? 'range' : 'event'} me-2"></i>${dateDisplay}
                            </h6>
                            <div class="mb-2">
                                <span class="badge bg-${color}">${group.reason}</span>
                                ${isRange ? `<span class="badge bg-secondary ms-1">${dayCount} day${dayCount > 1 ? 's' : ''}</span>` : ''}
                                ${group.notes ? `<small class="text-muted ms-2">${group.notes}</small>` : ''}
                            </div>
                        </div>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteAttendanceGroup([${group.ids.join(',')}])">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                    ${isRange ? `
                        <details class="mt-2">
                            <summary class="text-muted small" style="cursor: pointer;">
                                <i class="bi bi-chevron-down me-1"></i>Show individual days
                            </summary>
                            <div class="mt-2 ms-3">
                                ${group.records.map(r => {
                                    const parts = r.date.split('/');
                                    const d = new Date(parts[2], parts[1] - 1, parts[0]);
                                    return `<small class="d-block text-muted">• ${d.toLocaleDateString('en-GB', { weekday: 'short', month: 'short', day: 'numeric' })}</small>`;
                                }).join('')}
                            </div>
                        </details>
                    ` : ''}
                </div>
            `;
        });
        html += '</div>';
        
        listDiv.innerHTML = html;
    } catch (error) {
        listDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> Failed to load records: ${error.message}
            </div>
        `;
    }
}

async function addAttendanceRecord() {
    const date = document.getElementById('attendanceDate').value;
    const reason = document.getElementById('attendanceReason').value;
    const notes = document.getElementById('attendanceNotes').value;
    
    if (!date) {
        showError('Please select a date');
        return;
    }
    
    // Convert YYYY-MM-DD to DD/MM/YYYY
    const parts = date.split('-');
    const formattedDate = `${parts[2]}/${parts[1]}/${parts[0]}`;
    
    try {
        const response = await fetch('/api/settings/attendance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: formattedDate, reason, notes })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('✅ Attendance record added');
            document.getElementById('attendanceDate').value = '';
            document.getElementById('attendanceNotes').value = '';
            loadAttendanceRecords();
        } else {
            showError(`Failed to add record: ${result.error}`);
        }
    } catch (error) {
        showError(`Failed to add record: ${error.message}`);
    }
}

async function addAttendanceRange() {
    const dateFrom = document.getElementById('attendanceDateFrom').value;
    const dateTo = document.getElementById('attendanceDateTo').value;
    const reason = document.getElementById('attendanceReasonRange').value;
    const notes = document.getElementById('attendanceNotesRange').value;
    
    if (!dateFrom || !dateTo) {
        showError('Please select both from and to dates');
        return;
    }
    
    const fromDate = new Date(dateFrom);
    const toDate = new Date(dateTo);
    
    if (fromDate > toDate) {
        showError('From date must be before or equal to To date');
        return;
    }
    
    // Calculate number of days
    const dayCount = Math.round((toDate - fromDate) / (1000 * 60 * 60 * 24)) + 1;
    
    if (dayCount > 365) {
        showError('Date range cannot exceed 365 days');
        return;
    }
    
    try {
        // Generate all dates in range
        const dates = [];
        const currentDate = new Date(fromDate);
        
        while (currentDate <= toDate) {
            const day = String(currentDate.getDate()).padStart(2, '0');
            const month = String(currentDate.getMonth() + 1).padStart(2, '0');
            const year = currentDate.getFullYear();
            dates.push(`${day}/${month}/${year}`);
            currentDate.setDate(currentDate.getDate() + 1);
        }
        
        // Add all records
        const addPromises = dates.map(date =>
            fetch('/api/settings/attendance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date, reason, notes })
            })
        );
        
        await Promise.all(addPromises);
        
        showSuccess(`✅ Added ${dayCount} attendance record${dayCount > 1 ? 's' : ''}`);
        document.getElementById('attendanceDateFrom').value = '';
        document.getElementById('attendanceDateTo').value = '';
        document.getElementById('attendanceNotesRange').value = '';
        loadAttendanceRecords();
    } catch (error) {
        showError(`Failed to add records: ${error.message}`);
    }
}

async function deleteAttendanceRecord(id) {
    if (!confirm('Are you sure you want to delete this attendance record?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/settings/attendance/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('✅ Record deleted');
            loadAttendanceRecords();
        } else {
            showError(`Failed to delete record: ${result.error}`);
        }
    } catch (error) {
        showError(`Failed to delete record: ${error.message}`);
    }
}

async function deleteAttendanceGroup(ids) {
    const count = ids.length;
    const message = count > 1 ? 
        `Are you sure you want to delete these ${count} attendance records?` :
        'Are you sure you want to delete this attendance record?';
    
    if (!confirm(message)) {
        return;
    }
    
    try {
        // Delete all records in the group
        const deletePromises = ids.map(id => 
            fetch(`/api/settings/attendance/${id}`, { method: 'DELETE' })
        );
        
        await Promise.all(deletePromises);
        
        showSuccess(`✅ ${count} record${count > 1 ? 's' : ''} deleted`);
        loadAttendanceRecords();
    } catch (error) {
        showError(`Failed to delete records: ${error.message}`);
    }
}

// Missing settings functions
async function loadAllSettings() {
    // Load all settings data
    console.log('Loading all settings...');
    
    // Try to load backups list if we're on the system tab
    if (document.getElementById('backupsList')) {
        loadBackupsList();
    }
}

async function saveProfile() {
    const profileData = {
        name: document.getElementById('userName')?.value,
        email: document.getElementById('userEmail')?.value,
        phone: document.getElementById('userPhone')?.value,
        address_line1: document.getElementById('addressLine1')?.value,
        address_line2: document.getElementById('addressLine2')?.value,
        city: document.getElementById('city')?.value,
        postcode: document.getElementById('postcode')?.value,
        utr_number: document.getElementById('utrNumber')?.value,
        ni_number: document.getElementById('niNumber')?.value
    };
    
    try {
        const response = await fetch('/api/settings/profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profileData)
        });
        
        const result = await response.json();
        if (result.success) {
            showSuccess('Profile saved successfully');
        } else {
            showError(`Failed to save profile: ${result.error}`);
        }
    } catch (error) {
        showError(`Error saving profile: ${error.message}`);
    }
}

async function backupDatabase() {
    try {
        showStatus('Creating database backup...');
        const response = await fetch('/api/system/backup', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Database backup created successfully');
            loadBackupsList();
        } else {
            showError(`Backup failed: ${result.error}`);
        }
    } catch (error) {
        showError(`Backup error: ${error.message}`);
    }
}

async function optimizeDatabase() {
    try {
        showStatus('Optimizing database...');
        const response = await fetch('/api/system/optimize', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Database optimized successfully');
        } else {
            showError(`Optimization failed: ${result.error}`);
        }
    } catch (error) {
        showError(`Optimization error: ${error.message}`);
    }
}

async function validateDatabase() {
    try {
        showStatus('Validating database integrity...');
        const response = await fetch('/api/system/validate', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Database validation completed successfully');
        } else {
            showError(`Validation failed: ${result.error}`);
        }
    } catch (error) {
        showError(`Validation error: ${error.message}`);
    }
}

async function loadBackupsList() {
    const container = document.getElementById('backupsList');
    if (!container) return;
    
    try {
        console.log('🔄 Loading backups list...');
        const response = await fetch('/api/system/backups');
        
        if (response.status === 404) {
            console.log('⚠️ Backup system not configured (404)');
            container.innerHTML = '<div class="text-muted">Backup system not configured</div>';
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('📦 Backups result:', result);
        
        if (result.success && result.backups) {
            // Display backups list
            container.innerHTML = result.backups.map(backup => `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${backup.name}</strong>
                        <small class="text-muted d-block">${backup.date}</small>
                    </div>
                    <button class="btn btn-sm btn-outline-primary" onclick="downloadBackup('${backup.name}')">
                        <i class="bi bi-download"></i>
                    </button>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="text-muted">No backups available</div>';
        }
    } catch (error) {
        console.log('❌ Backup system error:', error.message);
        container.innerHTML = '<div class="text-muted">Backup system not available</div>';
    }
}

function clearCache() {
    if (confirm('This will clear your browser cache and reload the page. Continue?')) {
        localStorage.clear();
        sessionStorage.clear();
        location.reload(true);
    }
}

function viewSystemLogs() {
    window.open('/api/system/logs', '_blank');
}

function copyManagerRequestEmail() {
    const emailText = `Subject: Request for Historical Payslips and Runsheets

Hi [Manager Name],

Could you please send me the historical payslips and runsheets for the periods I'm missing in my records?

I can accept them in PDF format via email, and I'll import them into my system.

Thanks!

Best regards,
[Your Name]`;
    
    navigator.clipboard.writeText(emailText).then(() => {
        showSuccess('Email template copied to clipboard');
    });
}

// Initialize tabs and ensure proper display
function initializeSettingsTabs() {
    console.log('🚀 Initializing settings tabs');
    
    // Ensure the first tab is active if none are
    const activeTab = document.querySelector('.tab-pane.active');
    if (!activeTab) {
        console.log('⚠️ No active tab found, activating profile tab');
        const profileTab = document.getElementById('profile');
        const profileTabButton = document.getElementById('profile-tab');
        
        if (profileTab && profileTabButton) {
            profileTab.classList.add('show', 'active');
            profileTabButton.classList.add('active');
        }
    }
    
    // Add event listeners to tab buttons
    const tabButtons = document.querySelectorAll('[data-bs-toggle="pill"]');
    tabButtons.forEach(button => {
        button.addEventListener('shown.bs.tab', function(e) {
            const targetId = e.target.getAttribute('data-bs-target');
            console.log('📋 Tab shown:', targetId);
            
            // Special handling for attendance tab
            if (targetId === '#attendance') {
                setTimeout(() => {
                    if (document.getElementById('attendanceRecordsList')) {
                        loadAttendanceRecords();
                    }
                }, 100);
            }
        });
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 Settings page DOM loaded');
    initializeSettingsTabs();
    loadAllSettings();
    
    // Load attendance records if we're on the attendance tab
    setTimeout(() => {
        const attendanceTab = document.getElementById('attendance');
        if (attendanceTab && attendanceTab.classList.contains('active')) {
            if (document.getElementById('attendanceRecordsList')) {
                loadAttendanceRecords();
            }
        }
    }, 500);
});
