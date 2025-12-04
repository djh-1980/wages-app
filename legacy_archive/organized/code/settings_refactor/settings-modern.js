/**
 * Modern Settings Page JavaScript
 * Simple, reliable, no complex tab switching
 */

// Status display functions
function showStatus(message, type = 'info') {
    const statusDiv = document.getElementById('settingsStatus');
    if (statusDiv) {
        const alertClass = type === 'success' ? 'alert-success' : 
                          type === 'danger' ? 'alert-danger' : 
                          type === 'warning' ? 'alert-warning' : 'alert-info';
        
        statusDiv.innerHTML = `
            <div class="alert ${alertClass} alert-dismissible fade show">
                <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'danger' ? 'x-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i> 
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        statusDiv.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            const alert = statusDiv.querySelector('.alert');
            if (alert) {
                alert.classList.remove('show');
                setTimeout(() => statusDiv.style.display = 'none', 300);
            }
        }, 5000);
    }
}

function showSuccess(message) {
    showStatus(message, 'success');
}

function showError(message) {
    showStatus(message, 'danger');
}

// Profile functions
async function loadProfile() {
    try {
        const response = await fetch('/api/settings/profile');
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.profile) {
                document.getElementById('userName').value = data.profile.userName || '';
                document.getElementById('userEmail').value = data.profile.userEmail || '';
                document.getElementById('userPhone').value = data.profile.userPhone || '';
                document.getElementById('utrNumber').value = data.profile.utrNumber || '';
            }
        }
    } catch (error) {
        console.error('Error loading profile:', error);
    }
}

async function saveProfile() {
    const profileData = {
        userName: document.getElementById('userName').value,
        userEmail: document.getElementById('userEmail').value,
        userPhone: document.getElementById('userPhone').value,
        utrNumber: document.getElementById('utrNumber').value
    };
    
    try {
        const response = await fetch('/api/settings/profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profileData)
        });
        
        if (response.ok) {
            const data = await response.json();
            showSuccess('Profile saved successfully!');
        } else {
            showError('Failed to save profile. Please try again.');
        }
    } catch (error) {
        console.error('Error saving profile:', error);
        showError('Failed to save profile. Please try again.');
    }
}

// Sync functions
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
            document.getElementById('latestRunsheetDate').textContent = data.latest_runsheet || 'No data';
            document.getElementById('latestPayslipWeek').textContent = data.latest_payslip || 'No data';
        }
    } catch (error) {
        console.error('Error loading latest sync data:', error);
    }
}

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

// Attendance functions
async function loadAttendanceRecords() {
    const yearFilter = document.getElementById('attendanceYearFilter');
    const year = yearFilter ? yearFilter.value : '';
    const listDiv = document.getElementById('attendanceRecordsList');
    
    if (!listDiv) return;
    
    try {
        listDiv.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2 text-muted">Loading records...</p>
            </div>
        `;
        
        const url = year ? `/api/settings/attendance?year=${year}` : '/api/settings/attendance';
        const response = await fetch(url);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Response error:', response.status, response.statusText, errorText);
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('Attendance API response:', result);
        
        if (!result.success) {
            throw new Error(result.error || 'Failed to load records');
        }
        
        const records = result.records || [];
        
        if (records.length === 0) {
            listDiv.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-calendar-x fs-1"></i>
                    <p class="mt-2">No attendance records found</p>
                </div>
            `;
            return;
        }
        
        // Display records
        let html = '<div class="list-group">';
        records.forEach(record => {
            const reasonColors = {
                'Holiday': 'success',
                'Sick': 'danger',
                'Personal': 'warning',
                'Training': 'info',
                'Other': 'secondary'
            };
            const color = reasonColors[record.reason] || 'secondary';
            
            html += `
                <div class="list-group-item">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">
                                <i class="bi bi-calendar-event me-2"></i>${record.date}
                            </h6>
                            <div class="mb-2">
                                <span class="badge bg-${color}">${record.reason}</span>
                                ${record.notes ? `<small class="text-muted ms-2">${record.notes}</small>` : ''}
                            </div>
                        </div>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteAttendanceRecord(${record.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
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
            showSuccess('Attendance record added successfully');
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
            showSuccess('Record deleted successfully');
            loadAttendanceRecords();
        } else {
            showError(`Failed to delete record: ${result.error}`);
        }
    } catch (error) {
        showError(`Failed to delete record: ${error.message}`);
    }
}

// System functions
async function loadDatabaseInfo() {
    try {
        const response = await fetch('/api/data/database/info');
        if (!response.ok) return;
        
        const data = await response.json();
        
        document.getElementById('dbPayslips').textContent = data.records?.payslips || 0;
        document.getElementById('dbRunSheets').textContent = data.records?.runsheets || 0;
        document.getElementById('dbJobs').textContent = data.records?.jobs || 0;
        
        const sizeStr = formatFileSize(data.size_bytes || 0);
        document.getElementById('dbSize').textContent = sizeStr;
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

function clearCache() {
    if (confirm('This will clear your browser cache and reload the page. Continue?')) {
        localStorage.clear();
        sessionStorage.clear();
        location.reload(true);
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

// Initialize everything when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('Modern settings page loaded');
    
    // Load initial data
    loadProfile();
    loadLatestSyncData();
    loadAttendanceRecords();
    loadDatabaseInfo();
    
    // Smooth scrolling for any internal links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});
