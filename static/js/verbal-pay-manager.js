/**
 * Verbal Pay Manager
 * Comprehensive management interface for verbal pay confirmations
 */

let allConfirmations = [];
let currentModal = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadAnalytics();
    loadConfirmations();
    
    // Setup notes counter
    document.getElementById('modalNotes').addEventListener('input', function() {
        document.getElementById('notesCount').textContent = this.value.length;
    });
});

// Load analytics
async function loadAnalytics() {
    try {
        const response = await fetch('/api/verbal-pay/analytics');
        const data = await response.json();
        
        if (data.success) {
            const analytics = data.analytics;
            document.getElementById('totalCount').textContent = analytics.total_confirmations;
            document.getElementById('matchedCount').textContent = analytics.matched_count;
            document.getElementById('mismatchedCount').textContent = analytics.mismatched_count;
            document.getElementById('accuracyRate').textContent = analytics.accuracy_rate + '%';
        }
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

// Load all confirmations
async function loadConfirmations() {
    try {
        const response = await fetch('/api/verbal-pay/confirmations');
        const data = await response.json();
        
        if (data.success) {
            allConfirmations = data.confirmations;
            displayConfirmations(allConfirmations);
        }
    } catch (error) {
        console.error('Error loading confirmations:', error);
        document.getElementById('confirmationsList').innerHTML = `
            <div class="alert alert-danger">Failed to load confirmations</div>
        `;
    }
}

// Display confirmations
function displayConfirmations(confirmations) {
    const container = document.getElementById('confirmationsList');
    
    if (confirmations.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-inbox" style="font-size: 3rem; color: #dee2e6;"></i>
                <p class="text-muted mt-3">No confirmations found</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="row g-3">';
    
    confirmations.forEach(conf => {
        const status = conf.payslip_id ? (conf.matched ? 'matched' : 'mismatched') : 'pending';
        const statusBadge = status === 'matched' ? 
            '<span class="badge bg-success">Matched</span>' :
            status === 'mismatched' ?
            '<span class="badge bg-danger">Mismatched</span>' :
            '<span class="badge bg-warning">Pending</span>';
        
        const expectedGross = (conf.verbal_amount - 15).toFixed(2);
        const difference = conf.payslip_amount ? 
            (conf.payslip_amount - (conf.verbal_amount - 15)).toFixed(2) : null;
        
        html += `
            <div class="col-md-6 col-lg-4">
                <div class="card verbal-card ${status}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h5 class="mb-0">Week ${conf.week_number}, ${conf.year}</h5>
                            ${statusBadge}
                        </div>
                        <div class="mb-2">
                            <strong>Verbal Amount:</strong> £${conf.verbal_amount.toFixed(2)}<br>
                            <small class="text-muted">Expected Gross: £${expectedGross}</small>
                        </div>
                        ${conf.payslip_amount ? `
                            <div class="mb-2">
                                <strong>Payslip Gross:</strong> £${conf.payslip_amount.toFixed(2)}
                                ${difference ? `<br><small class="${parseFloat(difference) === 0 ? 'text-success' : 'text-danger'}">
                                    Difference: £${difference}
                                </small>` : ''}
                            </div>
                        ` : ''}
                        ${conf.notes ? `
                            <div class="mb-2">
                                <small class="text-muted">${conf.notes}</small>
                            </div>
                        ` : ''}
                        <div class="d-flex gap-2 mt-3">
                            <button class="btn btn-sm btn-outline-primary" onclick="editConfirmation(${conf.id})">
                                <i class="bi bi-pencil"></i> Edit
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteConfirmation(${conf.id}, ${conf.week_number})">
                                <i class="bi bi-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// Filter confirmations
function filterConfirmations() {
    const year = document.getElementById('filterYear').value;
    const status = document.getElementById('filterStatus').value;
    const search = document.getElementById('searchBox').value.toLowerCase();
    
    let filtered = allConfirmations;
    
    if (year) {
        filtered = filtered.filter(c => c.year == year);
    }
    
    if (status) {
        filtered = filtered.filter(c => {
            if (status === 'matched') return c.matched && c.payslip_id;
            if (status === 'mismatched') return !c.matched && c.payslip_id;
            if (status === 'pending') return !c.payslip_id;
            return true;
        });
    }
    
    if (search) {
        filtered = filtered.filter(c => 
            c.week_number.toString().includes(search) ||
            (c.notes && c.notes.toLowerCase().includes(search))
        );
    }
    
    displayConfirmations(filtered);
}

// Show add modal
async function showAddModal() {
    document.getElementById('modalTitle').textContent = 'Add Verbal Confirmation';
    document.getElementById('editConfirmationId').value = '';
    document.getElementById('modalWeekNumber').value = '';
    document.getElementById('modalAmount').value = '';
    document.getElementById('modalNotes').value = '';
    document.getElementById('notesCount').textContent = '0';
    
    // Get current week and year
    try {
        const response = await fetch('/api/settings/company-year');
        const data = await response.json();
        if (data.success) {
            document.getElementById('modalYear').value = data.current_year;
            document.getElementById('modalWeekNumber').value = data.current_week;
        }
    } catch (error) {
        document.getElementById('modalYear').value = 2025;
    }
    
    currentModal = new bootstrap.Modal(document.getElementById('confirmationModal'));
    currentModal.show();
}

// Edit confirmation
async function editConfirmation(id) {
    const conf = allConfirmations.find(c => c.id === id);
    if (!conf) return;
    
    document.getElementById('modalTitle').textContent = 'Edit Verbal Confirmation';
    document.getElementById('editConfirmationId').value = conf.id;
    document.getElementById('modalWeekNumber').value = conf.week_number;
    document.getElementById('modalYear').value = conf.year;
    document.getElementById('modalAmount').value = conf.verbal_amount;
    document.getElementById('modalNotes').value = conf.notes || '';
    document.getElementById('notesCount').textContent = (conf.notes || '').length;
    
    // Disable week/year editing
    document.getElementById('modalWeekNumber').disabled = true;
    document.getElementById('modalYear').disabled = true;
    
    currentModal = new bootstrap.Modal(document.getElementById('confirmationModal'));
    currentModal.show();
}

// Save confirmation
async function saveConfirmation() {
    const id = document.getElementById('editConfirmationId').value;
    const weekNumber = parseInt(document.getElementById('modalWeekNumber').value);
    const year = parseInt(document.getElementById('modalYear').value);
    const amount = parseFloat(document.getElementById('modalAmount').value);
    const notes = document.getElementById('modalNotes').value;
    
    if (!weekNumber || !year || !amount) {
        alert('Please fill in all required fields');
        return;
    }
    
    try {
        let response;
        if (id) {
            // Update existing
            response = await fetch(`/api/verbal-pay/confirmations/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ verbal_amount: amount, notes: notes })
            });
        } else {
            // Create new
            response = await fetch('/api/verbal-pay/confirmations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    week_number: weekNumber,
                    year: year,
                    verbal_amount: amount,
                    notes: notes
                })
            });
        }
        
        const data = await response.json();
        
        if (data.success) {
            currentModal.hide();
            // Re-enable fields
            document.getElementById('modalWeekNumber').disabled = false;
            document.getElementById('modalYear').disabled = false;
            loadAnalytics();
            loadConfirmations();
            showNotification(data.message, 'success');
        } else {
            alert(data.error || 'Failed to save confirmation');
        }
    } catch (error) {
        console.error('Error saving confirmation:', error);
        alert('Failed to save confirmation');
    }
}

// Delete confirmation
async function deleteConfirmation(id, weekNumber) {
    if (!confirm(`Delete confirmation for Week ${weekNumber}?`)) return;
    
    try {
        const response = await fetch(`/api/verbal-pay/confirmations/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            loadAnalytics();
            loadConfirmations();
            showNotification('Confirmation deleted', 'success');
        } else {
            alert(data.error || 'Failed to delete confirmation');
        }
    } catch (error) {
        console.error('Error deleting confirmation:', error);
        alert('Failed to delete confirmation');
    }
}

// Show bulk import modal
function showBulkImportModal() {
    document.getElementById('bulkImportData').value = '';
    document.getElementById('bulkImportResults').style.display = 'none';
    const modal = new bootstrap.Modal(document.getElementById('bulkImportModal'));
    modal.show();
}

// Process bulk import
async function processBulkImport() {
    const data = document.getElementById('bulkImportData').value;
    const lines = data.split('\n').filter(line => line.trim());
    
    if (lines.length === 0) {
        alert('Please enter data to import');
        return;
    }
    
    const confirmations = [];
    
    for (const line of lines) {
        const parts = line.split(',').map(p => p.trim());
        if (parts.length >= 3) {
            confirmations.push({
                week_number: parseInt(parts[0]),
                year: parseInt(parts[1]),
                verbal_amount: parseFloat(parts[2]),
                notes: parts[3] || ''
            });
        }
    }
    
    try {
        const response = await fetch('/api/verbal-pay/bulk-import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ confirmations: confirmations })
        });
        
        const result = await response.json();
        
        if (result.success) {
            const resultsDiv = document.getElementById('bulkImportResults');
            resultsDiv.style.display = 'block';
            
            let html = `<div class="alert alert-success">
                Imported ${result.results.success_count} confirmations successfully
            </div>`;
            
            if (result.results.error_count > 0) {
                html += `<div class="alert alert-warning">
                    ${result.results.error_count} errors:<br>
                    <ul class="mb-0">`;
                result.results.errors.forEach(err => {
                    html += `<li>Week ${err.week}: ${err.error}</li>`;
                });
                html += `</ul></div>`;
            }
            
            resultsDiv.innerHTML = html;
            loadAnalytics();
            loadConfirmations();
        } else {
            alert(result.error || 'Failed to import');
        }
    } catch (error) {
        console.error('Error importing:', error);
        alert('Failed to import confirmations');
    }
}

// Show notification
function showNotification(message, type = 'info') {
    if (typeof showStatus === 'function') {
        showStatus(message, type);
    } else {
        alert(message);
    }
}
