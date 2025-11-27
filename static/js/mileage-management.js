/**
 * Mileage Management functionality
 * Handles adding, editing, and managing mileage entries
 */

// Test that this script is loading
console.log('🟢 mileage-management.js loaded successfully');

// Show add mileage modal
function showAddMileageModal() {
    // Set today's date as default
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('mileageDate').value = today;
    
    // Clear form
    document.getElementById('mileageForm').reset();
    document.getElementById('mileageDate').value = today;
    document.getElementById('mileageModalTitle').textContent = 'Add Mileage Entry';
    
    const modal = new bootstrap.Modal(document.getElementById('addMileageModal'));
    modal.show();
}

// Calculate total miles when start/end mileage changes
document.addEventListener('DOMContentLoaded', function() {
    const startMileageInput = document.getElementById('startMileage');
    const endMileageInput = document.getElementById('endMileage');
    const totalMilesInput = document.getElementById('totalMiles');
    
    function calculateTotalMiles() {
        const start = parseFloat(startMileageInput.value) || 0;
        const end = parseFloat(endMileageInput.value) || 0;
        
        if (start > 0 && end > 0 && end > start) {
            const total = end - start;
            totalMilesInput.value = total.toFixed(1);
        } else {
            totalMilesInput.value = '';
        }
    }
    
    if (startMileageInput && endMileageInput) {
        startMileageInput.addEventListener('input', calculateTotalMiles);
        endMileageInput.addEventListener('input', calculateTotalMiles);
    }
});

// Save mileage entry
async function saveMileageEntry() {
    const date = document.getElementById('mileageDate').value;
    const startMileage = parseFloat(document.getElementById('startMileage').value);
    const endMileage = parseFloat(document.getElementById('endMileage').value);
    const fuelCost = parseFloat(document.getElementById('fuelCost').value) || 0;
    const notes = document.getElementById('mileageNotes').value;
    
    // Validation
    if (!date || !startMileage || !endMileage) {
        showError('Please fill in all required fields');
        return;
    }
    
    if (endMileage <= startMileage) {
        showError('End mileage must be greater than start mileage');
        return;
    }
    
    const totalMiles = endMileage - startMileage;
    
    try {
        const response = await fetch('/api/mileage/entries', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date: date,
                start_mileage: startMileage,
                end_mileage: endMileage,
                total_miles: totalMiles,
                fuel_cost: fuelCost,
                notes: notes
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess(`Mileage entry saved for ${date}`);
            bootstrap.Modal.getInstance(document.getElementById('addMileageModal')).hide();
            
            // Reload mileage data
            loadMileageEntries();
            loadMileageData(); // Refresh charts if function exists
        } else {
            showError(data.error || 'Failed to save mileage entry');
        }
    } catch (error) {
        console.error('Error saving mileage entry:', error);
        showError('Failed to save mileage entry');
    }
}

// Load missing mileage report
async function loadMissingMileageReport() {
    const reportContent = document.getElementById('missingMileageReportContent');
    
    if (!reportContent) return;
    
    // Show loading
    reportContent.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3 text-muted">Loading missing mileage report...</p>
        </div>
    `;
    
    // Get filter values
    const year = document.getElementById('missingMileageYear')?.value || '';
    const month = document.getElementById('missingMileageMonth')?.value || '';
    
    try {
        let url = '/api/mileage/missing-report';
        const params = new URLSearchParams();
        if (year) params.append('year', year);
        if (month) params.append('month', month);
        if (params.toString()) url += '?' + params.toString();
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            displayMissingMileageReport(data);
        } else {
            reportContent.innerHTML = `
                <div class="text-center py-4 text-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    <p class="mt-2">Error loading missing mileage report</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading missing mileage report:', error);
        reportContent.innerHTML = `
            <div class="text-center py-4 text-danger">
                <i class="bi bi-exclamation-triangle"></i>
                <p class="mt-2">Error loading missing mileage report</p>
            </div>
        `;
    }
}

// Display missing mileage report
function displayMissingMileageReport(data) {
    const reportContent = document.getElementById('missingMileageReportContent');
    
    const missingDates = data.missing_days || [];
    
    if (missingDates.length === 0) {
        reportContent.innerHTML = `
            <div class="text-center py-5">
                <div class="text-success mb-3">
                    <i class="bi bi-check-circle" style="font-size: 3rem;"></i>
                </div>
                <h5 class="text-success">No Missing Mileage Data</h5>
                <p class="text-muted">All working days have mileage records!</p>
            </div>
        `;
        return;
    }
    
    const formatDate = (dateStr) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-GB', { 
            weekday: 'short', 
            day: '2-digit', 
            month: '2-digit', 
            year: 'numeric' 
        });
    };
    
    let html = `
        <div class="alert alert-warning" role="alert">
            <i class="bi bi-exclamation-triangle-fill"></i>
            <strong>Missing Mileage Data Found!</strong>
            The following dates have no mileage records in the database:
        </div>
        
        <div class="row g-3">
    `;
    
    missingDates.forEach(date => {
        html += `
            <div class="col-md-6 col-lg-4">
                <div class="card border-warning">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="card-title mb-1">${formatDate(date)}</h6>
                                <small class="text-muted">No mileage data</small>
                            </div>
                            <i class="bi bi-exclamation-triangle text-warning"></i>
                        </div>
                        <div class="mt-3">
                            <button class="btn btn-success btn-sm w-100" onclick="addMileageForDate('${date}', 0)">
                                <i class="bi bi-plus-circle me-1"></i>Add Mileage
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += `
        </div>
        <div class="mt-4">
            <p class="text-muted">
                <i class="bi bi-info-circle"></i>
                <strong>Total missing days:</strong> ${missingDates.length}
            </p>
        </div>
    `;
    
    reportContent.innerHTML = html;
}

// Add mileage from inline row inputs
async function addMileageFromRow(date) {
    const milesInput = document.getElementById(`miles_${date}`);
    const fuelInput = document.getElementById(`fuel_${date}`);
    
    const miles = parseFloat(milesInput.value) || 0;
    const fuelCost = parseFloat(fuelInput.value) || 0;
    
    if (miles <= 0) {
        showError('Please enter a valid mileage amount');
        milesInput.focus();
        return;
    }
    
    try {
        const response = await fetch('/api/mileage/entries', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date: date,
                start_mileage: 0, // We don't have start/end, just total
                end_mileage: miles,
                total_miles: miles,
                fuel_cost: fuelCost,
                notes: `Added from discrepancies page on ${new Date().toLocaleDateString('en-GB')}`
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess(`Mileage added for ${new Date(date).toLocaleDateString('en-GB')}: ${miles} miles`);
            
            // Remove this row from the display
            const rowElement = milesInput.closest('.list-group-item');
            if (rowElement) {
                rowElement.style.transition = 'opacity 0.3s';
                rowElement.style.opacity = '0.5';
                setTimeout(() => {
                    rowElement.remove();
                    // Update the total count
                    updateMissingDaysCount();
                }, 300);
            }
        } else {
            showError(data.error || 'Failed to save mileage entry');
        }
    } catch (error) {
        console.error('Error saving mileage entry:', error);
        showError('Failed to save mileage entry');
    }
}

// Update missing days count after removing items
function updateMissingDaysCount() {
    const remainingItems = document.querySelectorAll('#discrepancyReportContent .list-group-item').length;
    const countElement = document.querySelector('#discrepancyReportContent .text-muted strong');
    if (countElement) {
        countElement.textContent = `Total missing days: ${remainingItems}`;
    }
    
    // If no items left, show success message
    if (remainingItems === 0) {
        const reportContent = document.getElementById('discrepancyReportContent');
        if (reportContent) {
            reportContent.innerHTML = `
                <div class="text-center py-5">
                    <div class="text-success mb-3">
                        <i class="bi bi-check-circle" style="font-size: 3rem;"></i>
                    </div>
                    <h5 class="text-success">All Mileage Data Added!</h5>
                    <p class="text-muted">No missing mileage records found.</p>
                </div>
            `;
        }
    }
}

// Add mileage for specific date (modal version)
function addMileageForDate(date, estimatedMiles) {
    // Pre-fill the modal with the date and estimated miles
    document.getElementById('mileageDate').value = date;
    
    if (estimatedMiles > 0) {
        // If we have estimated miles, suggest start/end mileage
        document.getElementById('endMileage').value = estimatedMiles;
        document.getElementById('totalMiles').value = estimatedMiles;
    }
    
    // Clear other fields
    document.getElementById('startMileage').value = '';
    document.getElementById('fuelCost').value = '';
    document.getElementById('mileageNotes').value = `Added for missing mileage on ${new Date(date).toLocaleDateString('en-GB')}`;
    
    // Change modal title
    document.getElementById('mileageModalTitle').textContent = `Add Missing Mileage - ${new Date(date).toLocaleDateString('en-GB')}`;
    
    const modal = new bootstrap.Modal(document.getElementById('addMileageModal'));
    modal.show();
}

// Display mileage entries in table
function displayMileageEntries(entries) {
    const tableBody = document.getElementById('mileageEntriesTable');
    
    if (entries.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4 text-muted">
                    No mileage entries found
                </td>
            </tr>
        `;
        return;
    }
    
    const formatCurrency = (value) => {
        return '£' + (value || 0).toFixed(2);
    };
    
    const formatDate = (dateStr) => {
        return new Date(dateStr).toLocaleDateString('en-GB');
    };
    
    tableBody.innerHTML = entries.map(entry => `
        <tr>
            <td><strong>${formatDate(entry.date)}</strong></td>
            <td>${entry.start_mileage}</td>
            <td>${entry.end_mileage}</td>
            <td><span class="badge bg-primary">${entry.total_miles} miles</span></td>
            <td>${entry.fuel_cost ? formatCurrency(entry.fuel_cost) : '-'}</td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-outline-primary" onclick="editMileageEntry(${entry.id})" title="Edit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteMileageEntry(${entry.id})" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Show missing mileage alert
function showMissingMileageAlert(missingDates) {
    const alert = document.getElementById('missingMileageAlert');
    const text = document.getElementById('missingMileageText');
    
    if (alert && text) {
        const datesList = missingDates.map(date => {
            const dayName = new Date(date.split('/').reverse().join('-')).toLocaleDateString('en-GB', { weekday: 'short' });
            return `<strong>${dayName} ${date}</strong>`;
        }).join(', ');
        
        text.innerHTML = ` Please add mileage for: ${datesList}`;
        alert.classList.remove('d-none');
    }
}

// Hide missing mileage alert
function hideMissingMileageAlert() {
    const alert = document.getElementById('missingMileageAlert');
    if (alert) {
        alert.classList.add('d-none');
    }
}

// Edit mileage entry
async function editMileageEntry(entryId) {
    try {
        const response = await fetch(`/api/mileage/entries/${entryId}`);
        const data = await response.json();
        
        if (data.success && data.entry) {
            const entry = data.entry;
            
            // Populate form with existing data
            document.getElementById('mileageDate').value = entry.date;
            document.getElementById('startMileage').value = entry.start_mileage;
            document.getElementById('endMileage').value = entry.end_mileage;
            document.getElementById('totalMiles').value = entry.total_miles;
            document.getElementById('fuelCost').value = entry.fuel_cost || '';
            document.getElementById('mileageNotes').value = entry.notes || '';
            
            // Change modal title and store entry ID
            document.getElementById('mileageModalTitle').textContent = 'Edit Mileage Entry';
            document.getElementById('addMileageModal').dataset.entryId = entryId;
            
            const modal = new bootstrap.Modal(document.getElementById('addMileageModal'));
            modal.show();
        } else {
            showError('Failed to load mileage entry');
        }
    } catch (error) {
        console.error('Error loading mileage entry:', error);
        showError('Failed to load mileage entry');
    }
}

// Delete mileage entry
async function deleteMileageEntry(entryId) {
    if (!confirm('Are you sure you want to delete this mileage entry?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/mileage/entries/${entryId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('Mileage entry deleted successfully');
            loadMileageEntries();
            loadMileageData(); // Refresh charts if function exists
        } else {
            showError(data.error || 'Failed to delete mileage entry');
        }
    } catch (error) {
        console.error('Error deleting mileage entry:', error);
        showError('Failed to delete mileage entry');
    }
}

// Show success message
function showSuccess(message) {
    if (typeof showNotification === 'function') {
        showNotification(message, 'success');
    } else {
        alert(message);
    }
}

// Show error message
function showError(message) {
    if (typeof showNotification === 'function') {
        showNotification(message, 'error');
    } else {
        alert(message);
    }
}

// Handle discrepancy type change
function changeDiscrepancyType() {
    const discrepancyType = document.getElementById('discrepancyType').value;
    const titleElement = document.getElementById('discrepancyTitle');
    const descriptionElement = document.getElementById('discrepancyDescription');
    
    if (discrepancyType === 'mileage') {
        titleElement.textContent = 'Missing Mileage Data';
        descriptionElement.textContent = 'Days with no mileage records in the database';
    } else {
        titleElement.textContent = 'Wages vs Run Sheets Discrepancies';
        descriptionElement.textContent = 'Compare payslip jobs with run sheet jobs to find mismatches';
    }
    
    // Load the appropriate report
    loadDiscrepancyReportEnhanced();
}

// Enhanced loadDiscrepancyReport to handle both types
function loadDiscrepancyReportEnhanced() {
    const discrepancyType = document.getElementById('discrepancyType')?.value || 'wages';
    
    if (discrepancyType === 'mileage') {
        loadMissingMileageReportForDiscrepancies();
    } else {
        // Call the original discrepancy report function if it exists
        if (typeof loadDiscrepancyReport === 'function') {
            loadDiscrepancyReport();
        }
    }
}

// Store reference to original function before we modify anything
let originalLoadDiscrepancyReport = null;

// Capture the original function when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for other scripts to load
    setTimeout(() => {
        if (typeof window.loadDiscrepancyReport === 'function') {
            originalLoadDiscrepancyReport = window.loadDiscrepancyReport;
            
            // Now override it with our enhanced version
            window.loadDiscrepancyReport = function() {
                const discrepancyType = document.getElementById('discrepancyType')?.value || 'wages';
                
                if (discrepancyType === 'mileage') {
                    loadMissingMileageReportForDiscrepancies();
                } else {
                    // Call the original wages discrepancy logic
                    if (originalLoadDiscrepancyReport) {
                        originalLoadDiscrepancyReport();
                    } else {
                        loadOriginalDiscrepancyReport();
                    }
                }
            };
        }
    }, 100);
});

function loadOriginalDiscrepancyReport() {
    // Fallback - show message that wages discrepancy isn't implemented yet
    const reportContent = document.getElementById('discrepancyReportContent');
    if (reportContent) {
        reportContent.innerHTML = `
            <div class="text-center py-5">
                <div class="text-info mb-3">
                    <i class="bi bi-info-circle" style="font-size: 3rem;"></i>
                </div>
                <h5 class="text-info">Wages Discrepancy Report</h5>
                <p class="text-muted">This feature will show discrepancies between wages and runsheets.</p>
            </div>
        `;
    }
}

// Load missing mileage report for discrepancies page
async function loadMissingMileageReportForDiscrepancies() {
    const reportContent = document.getElementById('discrepancyReportContent');
    
    if (!reportContent) return;
    
    // Show loading
    reportContent.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3 text-muted">Loading missing mileage data...</p>
        </div>
    `;
    
    // Get filter values
    const year = document.getElementById('discrepancyYear')?.value || '';
    const month = document.getElementById('discrepancyMonth')?.value || '';
    
    try {
        let url = '/api/mileage/missing-report';
        const params = new URLSearchParams();
        if (year) params.append('year', year);
        if (month) params.append('month', month);
        if (params.toString()) url += '?' + params.toString();
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            displayMissingMileageForDiscrepancies(data.missing_days || []);
        } else {
            reportContent.innerHTML = `
                <div class="text-center py-4 text-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    <p class="mt-2">Error loading missing mileage report: ${data.error}</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading missing mileage report:', error);
        reportContent.innerHTML = `
            <div class="text-center py-4 text-danger">
                <i class="bi bi-exclamation-triangle"></i>
                <p class="mt-2">Error loading missing mileage report</p>
            </div>
        `;
    }
}

// Display missing mileage data in discrepancies format
function displayMissingMileageForDiscrepancies(missingDates) {
    const reportContent = document.getElementById('discrepancyReportContent');
    
    if (missingDates.length === 0) {
        reportContent.innerHTML = `
            <div class="text-center py-5">
                <div class="text-success mb-3">
                    <i class="bi bi-check-circle" style="font-size: 3rem;"></i>
                </div>
                <h5 class="text-success">No Missing Mileage Data</h5>
                <p class="text-muted">All working days have mileage records!</p>
            </div>
        `;
        return;
    }
    
    // Validate date format (DD/MM/YYYY)
    const isValidDateFormat = (dateStr) => {
        if (!dateStr || typeof dateStr !== 'string') return false;
        
        // Check basic format DD/MM/YYYY
        const dateRegex = /^\d{2}\/\d{2}\/\d{4}$/;
        if (!dateRegex.test(dateStr)) return false;
        
        // Try to parse the date
        const parts = dateStr.split('/');
        const day = parseInt(parts[0], 10);
        const month = parseInt(parts[1], 10);
        const year = parseInt(parts[2], 10);
        
        // Basic validation
        if (day < 1 || day > 31) return false;
        if (month < 1 || month > 12) return false;
        if (year < 2020 || year > 2030) return false;
        
        return true;
    };
    
    const formatDate = (dateStr) => {
        if (!isValidDateFormat(dateStr)) {
            return 'Invalid Date';
        }
        
        // Convert DD/MM/YYYY to YYYY-MM-DD for Date constructor
        const parts = dateStr.split('/');
        const isoDate = `${parts[2]}-${parts[1]}-${parts[0]}`;
        const date = new Date(isoDate);
        
        if (isNaN(date.getTime())) {
            return 'Invalid Date';
        }
        
        return date.toLocaleDateString('en-GB', { 
            weekday: 'short', 
            day: '2-digit', 
            month: '2-digit', 
            year: 'numeric' 
        });
    };
    
    let html = `
        <div class="alert alert-warning" role="alert">
            <i class="bi bi-exclamation-triangle-fill"></i>
            <strong>Missing Mileage Data Found!</strong>
            The following dates have no mileage records in the database:
        </div>
        
        <div class="list-group">
    `;
    
    missingDates.forEach(date => {
        // Validate date format and skip invalid dates
        if (!date || date === '' || !isValidDateFormat(date)) {
            console.warn('Skipping invalid date:', date);
            return;
        }
        
        const formattedDate = formatDate(date);
        if (formattedDate === 'Invalid Date') {
            console.warn('Skipping date that cannot be formatted:', date);
            return;
        }
        
        html += `
            <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">${formattedDate}</h6>
                        <small class="text-muted">No mileage data recorded</small>
                    </div>
                    <div class="d-flex gap-2 align-items-center">
                        <i class="bi bi-exclamation-triangle text-warning"></i>
                        <div class="d-flex gap-2 align-items-center">
                            <div class="input-group input-group-sm" style="width: 120px;">
                                <input type="number" class="form-control" id="miles_${date}" placeholder="Miles" step="0.1" min="0">
                                <span class="input-group-text">mi</span>
                            </div>
                            <div class="input-group input-group-sm" style="width: 100px;">
                                <span class="input-group-text">£</span>
                                <input type="number" class="form-control" id="fuel_${date}" placeholder="Fuel" step="0.01" min="0">
                            </div>
                            <button class="btn btn-success btn-sm" onclick="addMileageFromRow('${date}')">
                                <i class="bi bi-plus-circle me-1"></i>Add Mileage
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += `
        </div>
        <div class="mt-3">
            <div class="d-flex justify-content-between align-items-center">
                <span class="text-muted">
                    <i class="bi bi-info-circle"></i>
                    <strong>Total missing days:</strong> ${missingDates.length}
                </span>
                <button class="btn btn-primary" onclick="showAddMileageModal()">
                    <i class="bi bi-plus-lg me-1"></i>Add New Mileage Entry
                </button>
            </div>
        </div>
    `;
    
    reportContent.innerHTML = html;
}

// Make functions globally accessible
window.showAddMileageModal = showAddMileageModal;
window.saveMileageEntry = saveMileageEntry;
window.loadMissingMileageReport = loadMissingMileageReport;
window.addMileageForDate = addMileageForDate;
window.addMileageFromRow = addMileageFromRow;
window.editMileageEntry = editMileageEntry;
window.deleteMileageEntry = deleteMileageEntry;
window.changeDiscrepancyType = changeDiscrepancyType;
window.loadDiscrepancyReportEnhanced = loadDiscrepancyReportEnhanced;

// Load missing mileage report when the mileage tab is shown
document.addEventListener('DOMContentLoaded', function() {
    const mileageTab = document.getElementById('mileage-tab');
    if (mileageTab) {
        mileageTab.addEventListener('shown.bs.tab', function() {
            loadMissingMileageReport();
        });
    }
    
    // Also handle discrepancies tab
    const discrepanciesTab = document.getElementById('discrepancies-tab');
    if (discrepanciesTab) {
        discrepanciesTab.addEventListener('shown.bs.tab', function() {
            // Load the appropriate report based on dropdown selection
            const discrepancyType = document.getElementById('discrepancyType')?.value || 'wages';
            if (discrepancyType === 'mileage') {
                loadMissingMileageReportForDiscrepancies();
            } else {
                loadOriginalDiscrepancyReport();
            }
        });
    }
});
