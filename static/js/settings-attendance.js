/**
 * Attendance Settings JavaScript
 * Handles attendance tracking functionality
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

// Toggle between single day and date range forms
function toggleAttendanceMode() {
    const singleMode = document.getElementById('singleDayMode').checked;
    const singleForm = document.getElementById('singleDayForm');
    const rangeForm = document.getElementById('rangeDayForm');
    
    if (singleForm && rangeForm) {
        singleForm.style.display = singleMode ? 'block' : 'none';
        rangeForm.style.display = singleMode ? 'none' : 'block';
    }
}

// Load attendance records
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
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
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
            updateAttendanceStats([]);
            return;
        }
        
        // Group records by month for better organization
        const groupedRecords = groupRecordsByMonth(records);
        
        let html = '<div class="attendance-records-container">';
        
        Object.keys(groupedRecords).forEach(monthKey => {
            const monthRecords = groupedRecords[monthKey];
            const monthName = formatMonthHeader(monthKey);
            
            html += `
                <div class="month-group mb-4">
                    <div class="month-header">
                        <h6 class="month-title">
                            <i class="bi bi-calendar3 me-2"></i>${monthName}
                            <span class="badge bg-secondary ms-2">${monthRecords.length}</span>
                        </h6>
                    </div>
                    <div class="records-grid">
            `;
            
            monthRecords.forEach(record => {
                const reasonConfig = getReasonConfig(record.reason);
                const formattedDate = formatDateDisplay(record.date);
                
                html += `
                    <div class="attendance-card">
                        <div class="card-header">
                            <div class="d-flex justify-content-between align-items-center">
                                <div class="date-info">
                                    <div class="day-number">${formattedDate.day}</div>
                                    <div class="day-month">${formattedDate.month}</div>
                                </div>
                                <div class="reason-badge">
                                    <span class="badge bg-${reasonConfig.color}">
                                        <i class="bi ${reasonConfig.icon} me-1"></i>${record.reason}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div class="card-body">
                            ${record.notes ? `
                                <div class="notes">
                                    <i class="bi bi-chat-text me-2 text-muted"></i>
                                    <span class="notes-text">${record.notes}</span>
                                </div>
                            ` : `
                                <div class="no-notes text-muted">
                                    <i class="bi bi-dash-circle me-2"></i>No additional notes
                                </div>
                            `}
                            <div class="card-actions mt-2">
                                <button class="btn btn-sm btn-outline-danger" onclick="deleteAttendanceRecord(${record.id})" title="Delete record">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        
        listDiv.innerHTML = html;
        updateAttendanceStats(records);
        
    } catch (error) {
        listDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> Failed to load records: ${error.message}
            </div>
        `;
    }
}

// Update attendance statistics
function updateAttendanceStats(records) {
    const stats = {
        Holiday: 0,
        Sick: 0,
        Personal: 0,
        total: records.length
    };
    
    records.forEach(record => {
        if (stats.hasOwnProperty(record.reason)) {
            stats[record.reason]++;
        }
    });
    
    const holidayCount = document.getElementById('holidayCount');
    const sickCount = document.getElementById('sickCount');
    const personalCount = document.getElementById('personalCount');
    const totalCount = document.getElementById('totalCount');
    
    if (holidayCount) holidayCount.textContent = stats.Holiday;
    if (sickCount) sickCount.textContent = stats.Sick;
    if (personalCount) personalCount.textContent = stats.Personal;
    if (totalCount) totalCount.textContent = stats.total;
}

// Add single attendance record
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

// Add attendance date range
async function addAttendanceRange() {
    const fromDate = document.getElementById('attendanceDateFrom').value;
    const toDate = document.getElementById('attendanceDateTo').value;
    const reason = document.getElementById('attendanceReasonRange').value;
    const notes = document.getElementById('attendanceNotesRange').value;
    
    if (!fromDate || !toDate) {
        showError('Please select both from and to dates');
        return;
    }
    
    const from = new Date(fromDate);
    const to = new Date(toDate);
    
    if (from > to) {
        showError('From date must be before to date');
        return;
    }
    
    // Calculate number of days
    const dayCount = Math.ceil((to - from) / (1000 * 60 * 60 * 24)) + 1;
    
    if (dayCount > 31) {
        showError('Date range cannot exceed 31 days');
        return;
    }
    
    try {
        // Generate all dates in range
        const dates = [];
        const currentDate = new Date(from);
        
        while (currentDate <= to) {
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
        
        showSuccess(`Added ${dayCount} attendance record${dayCount > 1 ? 's' : ''}`);
        document.getElementById('attendanceDateFrom').value = '';
        document.getElementById('attendanceDateTo').value = '';
        document.getElementById('attendanceNotesRange').value = '';
        loadAttendanceRecords();
    } catch (error) {
        showError(`Failed to add records: ${error.message}`);
    }
}

// Delete attendance record
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

// Helper functions for improved display
function groupRecordsByMonth(records) {
    const grouped = {};
    
    records.forEach(record => {
        // Parse DD/MM/YYYY format
        const [day, month, year] = record.date.split('/');
        const monthKey = `${year}-${month.padStart(2, '0')}`;
        
        if (!grouped[monthKey]) {
            grouped[monthKey] = [];
        }
        grouped[monthKey].push(record);
    });
    
    // Sort months in descending order (newest first)
    const sortedKeys = Object.keys(grouped).sort((a, b) => b.localeCompare(a));
    const sortedGrouped = {};
    
    sortedKeys.forEach(key => {
        // Sort records within each month by date (newest first)
        grouped[key].sort((a, b) => {
            const [dayA, monthA, yearA] = a.date.split('/');
            const [dayB, monthB, yearB] = b.date.split('/');
            const dateA = new Date(yearA, monthA - 1, dayA);
            const dateB = new Date(yearB, monthB - 1, dayB);
            return dateB - dateA;
        });
        sortedGrouped[key] = grouped[key];
    });
    
    return sortedGrouped;
}

function formatMonthHeader(monthKey) {
    const [year, month] = monthKey.split('-');
    const monthNames = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];
    return `${monthNames[parseInt(month) - 1]} ${year}`;
}

function formatDateDisplay(dateString) {
    const [day, month, year] = dateString.split('/');
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    return {
        day: day,
        month: monthNames[parseInt(month) - 1]
    };
}

function getReasonConfig(reason) {
    const configs = {
        'Holiday': { color: 'success', icon: 'bi-sun' },
        'Sick': { color: 'danger', icon: 'bi-thermometer-half' },
        'Personal': { color: 'warning', icon: 'bi-person' },
        'Training': { color: 'info', icon: 'bi-book' },
        'Other': { color: 'secondary', icon: 'bi-question-circle' }
    };
    
    return configs[reason] || configs['Other'];
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('Attendance settings page loaded');
    
    // Load initial data
    loadAttendanceRecords();
    
    // Set default date to today
    const today = new Date().toISOString().split('T')[0];
    const dateInput = document.getElementById('attendanceDate');
    if (dateInput) {
        dateInput.value = today;
    }
});
