/**
 * Missing Jobs functionality for comparing payslip jobs against runsheet jobs
 */

let currentMissingJobs = [];
let currentPayslipId = null;

/**
 * Check for missing jobs in a payslip
 */
async function checkMissingJobs(payslipId) {
    currentPayslipId = payslipId;
    
    const modalEl = document.getElementById('missingJobsModal');
    if (!modalEl) {
        alert('Missing jobs modal not found');
        return;
    }
    
    const modal = new bootstrap.Modal(modalEl);
    const modalBody = document.getElementById('missingJobsModalBody');
    
    modalBody.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2 text-muted">Checking for missing jobs...</p>
        </div>
    `;
    
    modal.show();
    
    try {
        const response = await fetch(`/api/payslips/${payslipId}/missing-jobs`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to check missing jobs');
        }
        
        currentMissingJobs = data.missing_jobs;
        
        if (currentMissingJobs.length === 0) {
            modalBody.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle-fill me-2"></i>
                    <strong>All jobs accounted for!</strong>
                    <p class="mb-0 mt-2">All ${data.total_jobs} jobs from this payslip exist in your runsheets.</p>
                </div>
            `;
            
            // Hide the "Add Selected Jobs" button
            document.getElementById('addSelectedJobsBtn').style.display = 'none';
            return;
        }
        
        // Show the "Add Selected Jobs" button
        document.getElementById('addSelectedJobsBtn').style.display = 'block';
        
        let html = `
            <div class="alert alert-warning">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                <strong>${currentMissingJobs.length} job(s) found in payslip but not in runsheets</strong>
                <p class="mb-0 mt-2">These jobs were paid but don't appear in your runsheet records. Select which ones to add.</p>
            </div>
            
            <div class="mb-3">
                <button class="btn btn-sm btn-outline-primary" onclick="selectAllMissingJobs(true)">
                    <i class="bi bi-check-square"></i> Select All
                </button>
                <button class="btn btn-sm btn-outline-secondary ms-2" onclick="selectAllMissingJobs(false)">
                    <i class="bi bi-square"></i> Deselect All
                </button>
            </div>
            
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th style="width: 50px;">
                                <input type="checkbox" class="form-check-input" id="selectAllCheckbox" 
                                       onchange="selectAllMissingJobs(this.checked)" checked>
                            </th>
                            <th>Job #</th>
                            <th>Customer</th>
                            <th>Activity</th>
                            <th>Address</th>
                            <th>Postcode</th>
                            <th>Date</th>
                            <th class="text-end">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        currentMissingJobs.forEach((job, index) => {
            html += `
                <tr>
                    <td>
                        <input type="checkbox" class="form-check-input missing-job-checkbox" 
                               data-index="${index}" checked>
                    </td>
                    <td><small class="text-muted">#${job.job_number || 'N/A'}</small></td>
                    <td>${truncate(job.client || 'N/A', 30)}</td>
                    <td><small>${truncate(job.activity || 'N/A', 25)}</small></td>
                    <td><small>${truncate(job.job_address || 'N/A', 35)}</small></td>
                    <td><small class="text-muted">${job.postcode || 'N/A'}</small></td>
                    <td><small class="text-muted">${job.date || 'N/A'}</small></td>
                    <td class="text-end"><strong>${formatCurrency(job.amount)}</strong></td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
            
            <div class="alert alert-info mt-3">
                <i class="bi bi-info-circle me-2"></i>
                <small>Jobs will be added to runsheets with status "pending" and source "payslip_import"</small>
            </div>
        `;
        
        modalBody.innerHTML = html;
        
    } catch (error) {
        console.error('Error checking missing jobs:', error);
        modalBody.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                Failed to check missing jobs: ${error.message}
            </div>
        `;
    }
}

/**
 * Select/deselect all missing jobs
 */
function selectAllMissingJobs(checked) {
    const checkboxes = document.querySelectorAll('.missing-job-checkbox');
    checkboxes.forEach(cb => cb.checked = checked);
    
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = checked;
    }
}

/**
 * Add selected missing jobs to run_sheet_jobs
 */
async function addSelectedMissingJobs() {
    const checkboxes = document.querySelectorAll('.missing-job-checkbox:checked');
    
    if (checkboxes.length === 0) {
        alert('Please select at least one job to add');
        return;
    }
    
    const selectedJobs = [];
    checkboxes.forEach(cb => {
        const index = parseInt(cb.dataset.index);
        selectedJobs.push(currentMissingJobs[index]);
    });
    
    const addBtn = document.getElementById('addSelectedJobsBtn');
    const originalText = addBtn.innerHTML;
    addBtn.disabled = true;
    addBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Adding...';
    
    try {
        const response = await fetch('/api/payslips/add-missing-jobs', {
            method: 'POST',
            headers: getJSONHeaders(),
            body: JSON.stringify({ jobs: selectedJobs })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to add jobs');
        }
        
        // Show success message
        const modalBody = document.getElementById('missingJobsModalBody');
        modalBody.innerHTML = `
            <div class="alert alert-success">
                <i class="bi bi-check-circle-fill me-2"></i>
                <strong>Jobs added successfully!</strong>
                <p class="mb-0 mt-2">${data.added_count} job(s) added to runsheets.</p>
                ${data.errors.length > 0 ? `<p class="mb-0 mt-2 text-warning"><small>${data.errors.length} job(s) failed to add (may already exist)</small></p>` : ''}
            </div>
        `;
        
        // Hide the add button
        addBtn.style.display = 'none';
        
        // Show notification
        if (typeof showNotification === 'function') {
            showNotification(`${data.added_count} job(s) added to runsheets`, 'success');
        }
        
        // Close modal after 2 seconds
        setTimeout(() => {
            bootstrap.Modal.getInstance(document.getElementById('missingJobsModal')).hide();
        }, 2000);
        
    } catch (error) {
        console.error('Error adding missing jobs:', error);
        alert('Failed to add jobs: ' + error.message);
        addBtn.disabled = false;
        addBtn.innerHTML = originalText;
    }
}

/**
 * Helper function to truncate text
 */
function truncate(str, maxLength) {
    if (!str) return '';
    if (str.length <= maxLength) return str;
    return str.substring(0, maxLength - 3) + '...';
}
