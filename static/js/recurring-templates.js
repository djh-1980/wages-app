/**
 * Recurring Payment Templates Management
 */

let recurringTemplates = [];

/**
 * Show recurring templates tab
 */
function showRecurringTab() {
    const recurringTab = document.getElementById('recurring-tab');
    if (recurringTab) {
        const tab = new bootstrap.Tab(recurringTab);
        tab.show();
    }
}

/**
 * Load all recurring templates
 */
async function loadRecurringTemplates() {
    try {
        const response = await fetch('/api/recurring/templates');
        const data = await response.json();
        
        if (data.success && data.templates) {
            recurringTemplates = data.templates;
            displayRecurringTemplates();
            updateRecurringStats();
        }
    } catch (error) {
        console.error('Error loading recurring templates:', error);
        showExpenseNotification('Failed to load recurring templates', 'error');
    }
}

/**
 * Display recurring templates
 */
function displayRecurringTemplates() {
    const tbody = document.getElementById('recurringTemplatesBody');
    
    if (!tbody) return;
    
    if (recurringTemplates.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted py-4">
                    <i class="bi bi-inbox" style="font-size: 3rem;"></i>
                    <p class="mt-2">No recurring templates defined</p>
                    <button class="btn btn-primary btn-sm" onclick="showAddTemplateModal()">
                        <i class="bi bi-plus-circle"></i> Add Your First Template
                    </button>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = recurringTemplates.map(template => `
        <tr class="${!template.is_active ? 'table-secondary' : ''}">
            <td>
                <strong>${template.name}</strong>
                ${template.auto_import ? '<span class="badge bg-success ms-1" title="Auto-import enabled"><i class="bi bi-lightning-fill"></i></span>' : ''}
            </td>
            <td><span class="badge bg-secondary">${template.category_name}</span></td>
            <td class="text-end"><strong>${CurrencyFormatter.format(template.expected_amount)}</strong></td>
            <td>
                <span class="badge ${getFrequencyBadgeClass(template.frequency)}">
                    ${capitalizeFirst(template.frequency)}
                </span>
            </td>
            <td><small class="text-muted">${template.merchant_pattern}</small></td>
            <td class="text-center">${template.day_of_month || '-'}</td>
            <td>
                <small class="text-muted">
                    ${template.next_expected_date || '-'}
                    ${template.last_matched_date ? `<br><span class="text-success">Last: ${template.last_matched_date}</span>` : ''}
                </small>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="editTemplate(${template.id})" title="Edit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-${template.is_active ? 'warning' : 'success'}" 
                            onclick="toggleTemplateActive(${template.id}, ${!template.is_active})" 
                            title="${template.is_active ? 'Deactivate' : 'Activate'}">
                        <i class="bi bi-${template.is_active ? 'pause' : 'play'}-circle"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteTemplate(${template.id})" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

/**
 * Update recurring statistics
 */
function updateRecurringStats() {
    const activeCount = recurringTemplates.filter(t => t.is_active).length;
    const monthlyTotal = recurringTemplates
        .filter(t => t.is_active && t.frequency === 'monthly')
        .reduce((sum, t) => sum + t.expected_amount, 0);
    
    const dueCount = recurringTemplates.filter(t => {
        if (!t.next_expected_date || !t.is_active) return false;
        const today = new Date();
        const weekAhead = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
        const expected = parseUKDate(t.next_expected_date);
        return expected && expected >= today && expected <= weekAhead;
    }).length;
    
    document.getElementById('activeTemplatesCount').textContent = activeCount;
    document.getElementById('monthlyRecurringTotal').textContent = CurrencyFormatter.format(monthlyTotal);
    document.getElementById('dueTemplatesCount').textContent = dueCount;
}

/**
 * Show add template modal
 */
function showAddTemplateModal() {
    document.getElementById('templateModalTitle').textContent = 'Add Recurring Template';
    document.getElementById('templateForm').reset();
    document.getElementById('templateId').value = '';
    document.getElementById('templateIsActive').checked = true;
    document.getElementById('templateAutoImport').checked = false;
    document.getElementById('templateTolerance').value = '5.00';
    
    const modal = new bootstrap.Modal(document.getElementById('templateModal'));
    modal.show();
}

/**
 * Edit template
 */
async function editTemplate(templateId) {
    try {
        const response = await fetch(`/api/recurring/templates/${templateId}`);
        const data = await response.json();
        
        if (data.success && data.template) {
            const template = data.template;
            document.getElementById('templateModalTitle').textContent = 'Edit Recurring Template';
            document.getElementById('templateId').value = template.id;
            document.getElementById('templateName').value = template.name;
            document.getElementById('templateCategory').value = template.category_id;
            document.getElementById('templateAmount').value = template.expected_amount;
            document.getElementById('templateFrequency').value = template.frequency;
            document.getElementById('templateMerchant').value = template.merchant_pattern;
            document.getElementById('templateDay').value = template.day_of_month || '';
            document.getElementById('templateIsActive').checked = template.is_active;
            document.getElementById('templateTolerance').value = template.tolerance_amount;
            document.getElementById('templateAutoImport').checked = template.auto_import;
            
            const modal = new bootstrap.Modal(document.getElementById('templateModal'));
            modal.show();
        }
    } catch (error) {
        console.error('Error loading template:', error);
        showExpenseNotification('Failed to load template', 'error');
    }
}

/**
 * Save template
 */
async function saveTemplate() {
    const templateId = document.getElementById('templateId').value;
    const name = document.getElementById('templateName').value;
    const categoryId = document.getElementById('templateCategory').value;
    const amount = document.getElementById('templateAmount').value;
    const frequency = document.getElementById('templateFrequency').value;
    const merchant = document.getElementById('templateMerchant').value;
    const dayOfMonth = document.getElementById('templateDay').value;
    const isActive = document.getElementById('templateIsActive').checked;
    const tolerance = document.getElementById('templateTolerance').value;
    const autoImport = document.getElementById('templateAutoImport').checked;
    
    if (!name || !categoryId || !amount || !frequency || !merchant) {
        showExpenseNotification('Please fill in all required fields', 'error');
        return;
    }
    
    const templateData = {
        name: name,
        category_id: parseInt(categoryId),
        expected_amount: parseFloat(amount),
        frequency: frequency,
        merchant_pattern: merchant,
        day_of_month: dayOfMonth ? parseInt(dayOfMonth) : null,
        is_active: isActive,
        tolerance_amount: parseFloat(tolerance),
        auto_import: autoImport
    };
    
    try {
        let response;
        if (templateId) {
            // Update existing
            response = await fetch(`/api/recurring/templates/update/${templateId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(templateData)
            });
        } else {
            // Add new
            response = await fetch('/api/recurring/templates/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(templateData)
            });
        }
        
        const data = await response.json();
        
        if (data.success) {
            showExpenseNotification(
                templateId ? 'Template updated successfully' : 'Template added successfully',
                'success'
            );
            
            const modal = bootstrap.Modal.getInstance(document.getElementById('templateModal'));
            if (modal) modal.hide();
            
            loadRecurringTemplates();
        } else {
            showExpenseNotification(data.error || 'Failed to save template', 'error');
        }
    } catch (error) {
        console.error('Error saving template:', error);
        showExpenseNotification('Failed to save template', 'error');
    }
}

/**
 * Toggle template active status
 */
async function toggleTemplateActive(templateId, isActive) {
    try {
        const response = await fetch(`/api/recurring/templates/update/${templateId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ is_active: isActive })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showExpenseNotification(
                `Template ${isActive ? 'activated' : 'deactivated'} successfully`,
                'success'
            );
            loadRecurringTemplates();
        } else {
            showExpenseNotification(data.error || 'Failed to update template', 'error');
        }
    } catch (error) {
        console.error('Error updating template:', error);
        showExpenseNotification('Failed to update template', 'error');
    }
}

/**
 * Delete template
 */
async function deleteTemplate(templateId) {
    if (!confirm('Are you sure you want to delete this recurring template?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/recurring/templates/delete/${templateId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showExpenseNotification('Template deleted successfully', 'success');
            loadRecurringTemplates();
        } else {
            showExpenseNotification(data.error || 'Failed to delete template', 'error');
        }
    } catch (error) {
        console.error('Error deleting template:', error);
        showExpenseNotification('Failed to delete template', 'error');
    }
}

/**
 * Helper: Get badge class for frequency
 */
function getFrequencyBadgeClass(frequency) {
    const classes = {
        'weekly': 'bg-info',
        'monthly': 'bg-primary',
        'quarterly': 'bg-warning',
        'annually': 'bg-success'
    };
    return classes[frequency] || 'bg-secondary';
}

/**
 * Helper: Capitalize first letter
 */
function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Helper: Parse UK date format (DD/MM/YYYY)
 */
function parseUKDate(dateStr) {
    if (!dateStr) return null;
    const parts = dateStr.split('/');
    if (parts.length !== 3) return null;
    return new Date(parts[2], parts[1] - 1, parts[0]);
}
