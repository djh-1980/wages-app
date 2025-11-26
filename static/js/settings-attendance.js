/**
 * Attendance System Functions for Settings Page
 */

// Toggle between single day and date range modes
function toggleAttendanceMode() {
    const singleMode = document.getElementById('singleDayMode').checked;
    const singleForm = document.getElementById('singleDayForm');
    const rangeForm = document.getElementById('rangeDayForm');
    
    if (singleMode) {
        singleForm.style.display = 'block';
        rangeForm.style.display = 'none';
    } else {
        singleForm.style.display = 'none';
        rangeForm.style.display = 'block';
    }
}

// Add single attendance record
async function addAttendanceRecord() {
    const date = document.getElementById('attendanceDate').value;
    const reason = document.getElementById('attendanceReason').value;
    const notes = document.getElementById('attendanceNotes').value;
    
    if (!date) {
        showStatus('Please select a date', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/attendance/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                date: date,
                reason: reason,
                notes: notes
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showStatus('Attendance record added successfully', 'success');
            // Clear form
            document.getElementById('attendanceDate').value = '';
            document.getElementById('attendanceNotes').value = '';
            // Reload records
            loadAttendanceRecords();
        } else {
            showStatus(`Failed to add record: ${result.error}`, 'danger');
        }
    } catch (error) {
        showStatus(`Error adding record: ${error.message}`, 'danger');
    }
}

// Add attendance date range
async function addAttendanceRange() {
    const dateFrom = document.getElementById('attendanceDateFrom').value;
    const dateTo = document.getElementById('attendanceDateTo').value;
    const reason = document.getElementById('attendanceReasonRange').value;
    const notes = document.getElementById('attendanceNotesRange').value;
    
    if (!dateFrom || !dateTo) {
        showStatus('Please select both start and end dates', 'warning');
        return;
    }
    
    if (new Date(dateFrom) > new Date(dateTo)) {
        showStatus('Start date must be before end date', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/attendance/add-range', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                date_from: dateFrom,
                date_to: dateTo,
                reason: reason,
                notes: notes
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showStatus(`Added ${result.count} attendance records successfully`, 'success');
            // Clear form
            document.getElementById('attendanceDateFrom').value = '';
            document.getElementById('attendanceDateTo').value = '';
            document.getElementById('attendanceNotesRange').value = '';
            // Reload records
            loadAttendanceRecords();
        } else {
            showStatus(`Failed to add records: ${result.error}`, 'danger');
        }
    } catch (error) {
        showStatus(`Error adding records: ${error.message}`, 'danger');
    }
}

// Load attendance records
async function loadAttendanceRecords() {
    const yearFilter = document.getElementById('attendanceYearFilter').value;
    const container = document.getElementById('attendanceRecordsList');
    
    // Show loading
    container.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-2 text-muted">Loading records...</p>
        </div>
    `;
    
    try {
        const url = yearFilter ? `/api/attendance/records?year=${yearFilter}` : '/api/attendance/records';
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.success) {
            displayAttendanceRecords(result.records);
        } else {
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    Failed to load records: ${result.error}
                </div>
            `;
        }
    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                Error loading records: ${error.message}
            </div>
        `;
    }
}

// Display attendance records
function displayAttendanceRecords(records) {
    const container = document.getElementById('attendanceRecordsList');
    
    if (!records || records.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4 text-muted">
                <i class="bi bi-calendar-x fs-1 mb-3"></i>
                <p>No attendance records found</p>
                <small>Add your first record using the form above</small>
            </div>
        `;
        return;
    }
    
    const recordsHtml = records.map(record => `
        <div class="list-group-item d-flex justify-content-between align-items-center">
            <div>
                <div class="d-flex align-items-center">
                    <i class="bi bi-calendar-event text-primary me-2"></i>
                    <strong>${formatDate(record.date)}</strong>
                    <span class="badge bg-secondary ms-2">${record.reason}</span>
                </div>
                ${record.notes ? `<small class="text-muted mt-1 d-block">${record.notes}</small>` : ''}
            </div>
            <button class="btn btn-sm btn-outline-danger" onclick="deleteAttendanceRecord(${record.id})">
                <i class="bi bi-trash"></i>
            </button>
        </div>
    `).join('');
    
    container.innerHTML = `
        <div class="list-group">
            ${recordsHtml}
        </div>
    `;
}

// Delete attendance record
async function deleteAttendanceRecord(recordId) {
    if (!confirm('Are you sure you want to delete this attendance record?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/attendance/delete/${recordId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showStatus('Attendance record deleted successfully', 'success');
            loadAttendanceRecords();
        } else {
            showStatus(`Failed to delete record: ${result.error}`, 'danger');
        }
    } catch (error) {
        showStatus(`Error deleting record: ${error.message}`, 'danger');
    }
}

// Format date for display
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Show status message
function showStatus(message, type = 'info') {
    const statusDiv = document.getElementById('settingsStatus');
    if (!statusDiv) return;
    
    statusDiv.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="bi bi-${getStatusIcon(type)}"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    statusDiv.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 5000);
}

// Get appropriate icon for status type
function getStatusIcon(type) {
    switch (type) {
        case 'success': return 'check-circle';
        case 'danger': return 'exclamation-triangle';
        case 'warning': return 'exclamation-triangle';
        default: return 'info-circle';
    }
}

// Initialize attendance system when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Load attendance records on page load
    if (document.getElementById('attendanceRecordsList')) {
        loadAttendanceRecords();
    }
});
