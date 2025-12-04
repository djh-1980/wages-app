/**
 * Expenses Management - HMRC MTD Compliance
 */

let categories = [];
let expenses = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadCategories();
    loadTaxYears();
    loadExpenses();
    
    // Set today's date as default
    document.getElementById('expenseDate').value = formatDateForDisplay(new Date());
});

/**
 * Load expense categories
 */
async function loadCategories() {
    try {
        const response = await fetch('/api/expenses/categories');
        const data = await response.json();
        
        if (data.categories) {
            categories = data.categories;
            populateCategoryDropdowns();
        }
    } catch (error) {
        console.error('Error loading categories:', error);
        showExpenseNotification('Failed to load categories', 'error');
    }
}

/**
 * Populate category dropdowns
 */
function populateCategoryDropdowns() {
    const modalSelect = document.getElementById('expenseCategory');
    const filterSelect = document.getElementById('categoryFilter');
    
    // Clear existing options (except first)
    modalSelect.innerHTML = '<option value="">Select category...</option>';
    filterSelect.innerHTML = '<option value="">All Categories</option>';
    
    categories.forEach(cat => {
        const modalOption = new Option(cat.name, cat.id);
        const filterOption = new Option(cat.name, cat.id);
        modalSelect.add(modalOption);
        filterSelect.add(filterOption);
    });
}

/**
 * Load tax years
 */
async function loadTaxYears() {
    try {
        const response = await fetch('/api/expenses/tax-years');
        const data = await response.json();
        
        if (data.tax_years) {
            const select = document.getElementById('taxYearFilter');
            data.tax_years.forEach(year => {
                const option = new Option(year, year);
                select.add(option);
            });
            
            // Select current tax year by default
            if (data.tax_years.length > 0) {
                select.value = data.tax_years[0];
            }
        }
    } catch (error) {
        console.error('Error loading tax years:', error);
    }
}

/**
 * Load expenses with filters
 */
async function loadExpenses() {
    try {
        const taxYear = document.getElementById('taxYearFilter').value;
        const categoryId = document.getElementById('categoryFilter').value;
        const startDate = document.getElementById('startDateFilter').value;
        const endDate = document.getElementById('endDateFilter').value;
        
        let url = '/api/expenses/list?';
        if (taxYear) url += `tax_year=${taxYear}&`;
        if (categoryId) url += `category_id=${categoryId}&`;
        if (startDate) url += `start_date=${convertDateToUK(startDate)}&`;
        if (endDate) url += `end_date=${convertDateToUK(endDate)}&`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.expenses) {
            expenses = data.expenses;
            displayExpenses();
            updateSummary();
        }
    } catch (error) {
        console.error('Error loading expenses:', error);
        showExpenseNotification('Failed to load expenses', 'error');
    }
}

/**
 * Display expenses in table
 */
function displayExpenses() {
    const tbody = document.getElementById('expensesTableBody');
    
    if (expenses.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted py-4">
                    <i class="bi bi-inbox" style="font-size: 3rem;"></i>
                    <p class="mt-2">No expenses found</p>
                    <button class="btn btn-primary btn-sm" onclick="showAddExpenseModal()">
                        <i class="bi bi-plus-circle"></i> Add Your First Expense
                    </button>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = expenses.map(expense => `
        <tr>
            <td>${expense.date}</td>
            <td>
                <span class="badge bg-secondary">${expense.category_name}</span>
                ${expense.is_recurring ? '<i class="bi bi-arrow-repeat text-warning ms-1" title="Recurring"></i>' : ''}
            </td>
            <td>${expense.description || '-'}</td>
            <td class="text-end"><strong>${CurrencyFormatter.format(expense.amount)}</strong></td>
            <td class="text-center">
                ${expense.receipt_file ? `<a href="/api/expenses/receipt/${expense.receipt_file}" target="_blank" title="View receipt"><i class="bi bi-file-earmark-image text-primary" style="font-size: 1.2rem;"></i></a>` : '<span class="text-muted">-</span>'}
            </td>
            <td><small class="text-muted">${expense.tax_year}</small></td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="editExpense(${expense.id})" title="Edit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteExpense(${expense.id})" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

/**
 * Update summary cards
 */
function updateSummary() {
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();
    
    // Calculate this month's total
    const monthTotal = expenses
        .filter(e => {
            const [day, month, year] = e.date.split('/');
            return parseInt(month) - 1 === currentMonth && parseInt(year) === currentYear;
        })
        .reduce((sum, e) => sum + e.amount, 0);
    
    // Calculate tax year total
    const yearTotal = expenses.reduce((sum, e) => sum + e.amount, 0);
    
    // Count recurring expenses
    const recurringCount = expenses.filter(e => e.is_recurring).length;
    
    document.getElementById('monthTotal').textContent = CurrencyFormatter.format(monthTotal);
    document.getElementById('yearTotal').textContent = CurrencyFormatter.format(yearTotal);
    document.getElementById('expenseCount').textContent = expenses.length;
    document.getElementById('recurringCount').textContent = recurringCount;
}

/**
 * Show add expense modal
 */
function showAddExpenseModal() {
    document.getElementById('expenseModalTitle').textContent = 'Add Expense';
    document.getElementById('expenseForm').reset();
    document.getElementById('expenseId').value = '';
    document.getElementById('expenseDate').value = formatDateForDisplay(new Date());
    document.getElementById('recurringOptions').style.display = 'none';
    document.getElementById('receiptFile').value = '';
    document.getElementById('currentReceipt').style.display = 'none';
    
    // Reset camera/upload sections
    showUpload();
    capturedPhotoBlob = null;
    
    // Show modal using Bootstrap
    const modalElement = document.getElementById('expenseModal');
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
    
    // Stop camera when modal closes
    modalElement.addEventListener('hidden.bs.modal', function () {
        stopCamera();
    });
}

/**
 * Edit expense
 */
async function editExpense(expenseId) {
    try {
        const response = await fetch(`/api/expenses/${expenseId}`);
        const data = await response.json();
        
        if (data.expense) {
            const expense = data.expense;
            document.getElementById('expenseModalTitle').textContent = 'Edit Expense';
            document.getElementById('expenseId').value = expense.id;
            document.getElementById('expenseDate').value = expense.date;
            document.getElementById('expenseCategory').value = expense.category_id;
            document.getElementById('expenseAmount').value = expense.amount;
            document.getElementById('expenseDescription').value = expense.description || '';
            document.getElementById('isRecurring').checked = expense.is_recurring;
            
            if (expense.is_recurring) {
                document.getElementById('recurringOptions').style.display = 'block';
                document.getElementById('recurringFrequency').value = expense.recurring_frequency || 'monthly';
            }
            
            // Show receipt if exists
            if (expense.receipt_file) {
                document.getElementById('currentReceipt').style.display = 'block';
                document.getElementById('receiptLink').href = `/api/expenses/receipt/${expense.receipt_file}`;
                document.getElementById('receiptLink').textContent = expense.receipt_file.split('/').pop();
            }
            
            // Show modal using Bootstrap
            const modalElement = document.getElementById('expenseModal');
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
        }
    } catch (error) {
        console.error('Error loading expense:', error);
        showExpenseNotification('Failed to load expense', 'error');
    }
}

/**
 * Save expense (add or update)
 */
async function saveExpense() {
    const expenseId = document.getElementById('expenseId').value;
    const date = document.getElementById('expenseDate').value;
    const categoryId = document.getElementById('expenseCategory').value;
    const amount = document.getElementById('expenseAmount').value;
    const description = document.getElementById('expenseDescription').value;
    const isRecurring = document.getElementById('isRecurring').checked;
    const recurringFrequency = document.getElementById('recurringFrequency').value;
    const receiptFile = document.getElementById('receiptFile').files[0];
    
    if (!date || !categoryId || !amount) {
        showExpenseNotification('Please fill in all required fields', 'error');
        return;
    }
    
    let receiptPath = null;
    
    // Upload receipt if provided
    if (receiptFile) {
        const categoryName = categories.find(c => c.id == categoryId)?.name || 'expense';
        const uploadResult = await uploadReceipt(receiptFile, date, categoryName, amount);
        if (uploadResult.success) {
            receiptPath = uploadResult.filepath;
        } else {
            showExpenseNotification('Failed to upload receipt: ' + uploadResult.error, 'error');
            return;
        }
    }
    
    const expenseData = {
        date: date,
        category_id: parseInt(categoryId),
        amount: parseFloat(amount),
        description: description,
        is_recurring: isRecurring,
        recurring_frequency: isRecurring ? recurringFrequency : null,
        receipt_file: receiptPath
    };
    
    try {
        let response;
        if (expenseId) {
            // Update existing
            response = await fetch(`/api/expenses/update/${expenseId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(expenseData)
            });
        } else {
            // Add new
            response = await fetch('/api/expenses/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(expenseData)
            });
        }
        
        const data = await response.json();
        
        if (data.success) {
            showExpenseNotification(expenseId ? 'Expense updated successfully' : 'Expense added successfully', 'success');
            
            // Close modal using Bootstrap's method
            const modalElement = document.getElementById('expenseModal');
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            }
            
            // Clear form
            document.getElementById('expenseForm').reset();
            document.getElementById('receiptFile').value = '';
            
            loadExpenses();
        } else {
            showExpenseNotification(data.error || 'Failed to save expense', 'error');
        }
    } catch (error) {
        console.error('Error saving expense:', error);
        showExpenseNotification('Failed to save expense', 'error');
    }
}

/**
 * Upload receipt file
 */
async function uploadReceipt(file, date, category, amount) {
    try {
        const formData = new FormData();
        formData.append('receipt', file);
        formData.append('date', date);
        formData.append('category', category);
        formData.append('amount', amount);
        
        const response = await fetch('/api/expenses/upload-receipt', {
            method: 'POST',
            body: formData
        });
        
        return await response.json();
    } catch (error) {
        console.error('Error uploading receipt:', error);
        return { success: false, error: error.message };
    }
}

/**
 * Remove receipt
 */
function removeReceipt() {
    document.getElementById('receiptFile').value = '';
    document.getElementById('currentReceipt').style.display = 'none';
}

// Camera functionality
let cameraStream = null;
let capturedPhotoBlob = null;

/**
 * Show upload section
 */
function showUpload() {
    document.getElementById('uploadSection').style.display = 'block';
    document.getElementById('cameraSection').style.display = 'none';
    document.getElementById('capturedPhoto').style.display = 'none';
    document.getElementById('uploadBtn').classList.add('active');
    document.getElementById('cameraBtn').classList.remove('active');
    stopCamera();
}

/**
 * Show camera section
 */
async function showCamera() {
    document.getElementById('uploadSection').style.display = 'none';
    document.getElementById('cameraSection').style.display = 'block';
    document.getElementById('capturedPhoto').style.display = 'none';
    document.getElementById('uploadBtn').classList.remove('active');
    document.getElementById('cameraBtn').classList.add('active');
    
    try {
        const video = document.getElementById('cameraPreview');
        cameraStream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                facingMode: 'environment', // Use back camera on mobile
                width: { ideal: 1920 },
                height: { ideal: 1080 }
            } 
        });
        video.srcObject = cameraStream;
    } catch (error) {
        console.error('Error accessing camera:', error);
        showExpenseNotification('Could not access camera. Please check permissions.', 'error');
        showUpload();
    }
}

/**
 * Capture photo from camera
 */
function capturePhoto() {
    const video = document.getElementById('cameraPreview');
    const canvas = document.getElementById('photoCanvas');
    const preview = document.getElementById('photoPreview');
    
    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Draw video frame to canvas
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    // Convert canvas to blob
    canvas.toBlob((blob) => {
        capturedPhotoBlob = blob;
        
        // Show preview
        const url = URL.createObjectURL(blob);
        preview.src = url;
        
        // Hide camera, show preview
        document.getElementById('cameraSection').style.display = 'none';
        document.getElementById('capturedPhoto').style.display = 'block';
        
        // Stop camera stream
        stopCamera();
    }, 'image/jpeg', 0.9);
}

/**
 * Use captured photo
 */
function usePhoto() {
    if (capturedPhotoBlob) {
        // Create a File object from the blob
        const file = new File([capturedPhotoBlob], 'receipt-photo.jpg', { type: 'image/jpeg' });
        
        // Create a DataTransfer to set the file input
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        document.getElementById('receiptFile').files = dataTransfer.files;
        
        // Hide preview, show upload section
        document.getElementById('capturedPhoto').style.display = 'none';
        document.getElementById('uploadSection').style.display = 'block';
        document.getElementById('uploadBtn').classList.add('active');
        document.getElementById('cameraBtn').classList.remove('active');
        
        showExpenseNotification('Photo ready to upload!', 'success');
    }
}

/**
 * Retake photo
 */
function retakePhoto() {
    capturedPhotoBlob = null;
    showCamera();
}

/**
 * Stop camera stream
 */
function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
}

/**
 * Delete expense
 */
async function deleteExpense(expenseId) {
    if (!confirm('Are you sure you want to delete this expense?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/expenses/delete/${expenseId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showExpenseNotification('Expense deleted successfully', 'success');
            loadExpenses();
        } else {
            showExpenseNotification(data.error || 'Failed to delete expense', 'error');
        }
    } catch (error) {
        console.error('Error deleting expense:', error);
        showExpenseNotification('Failed to delete expense', 'error');
    }
}

/**
 * Toggle recurring options
 */
function toggleRecurringOptions() {
    const isRecurring = document.getElementById('isRecurring').checked;
    document.getElementById('recurringOptions').style.display = isRecurring ? 'block' : 'none';
}

/**
 * Clear all filters
 */
function clearFilters() {
    document.getElementById('taxYearFilter').selectedIndex = 0;
    document.getElementById('categoryFilter').selectedIndex = 0;
    document.getElementById('startDateFilter').value = '';
    document.getElementById('endDateFilter').value = '';
    loadExpenses();
}

/**
 * Format date for display (DD/MM/YYYY)
 */
function formatDateForDisplay(date) {
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
}

/**
 * Convert HTML date input (YYYY-MM-DD) to UK format (DD/MM/YYYY)
 */
function convertDateToUK(dateStr) {
    if (!dateStr) return '';
    const [year, month, day] = dateStr.split('-');
    return `${day}/${month}/${year}`;
}

/**
 * Show notification
 */
function showExpenseNotification(message, type = 'info') {
    // Use existing notification system from base.js or fallback to alert
    if (typeof showToast === 'function') {
        showToast(message, type);
    } else if (typeof alert === 'function') {
        alert(message);
    } else {
        console.log(`[${type}] ${message}`);
    }
}

// ============================================
// BANK STATEMENT IMPORT
// ============================================

let parsedTransactions = [];

/**
 * Show bank import modal
 */
function showBankImportModal() {
    // Reset modal
    document.getElementById('uploadStep').style.display = 'block';
    document.getElementById('reviewStep').style.display = 'none';
    document.getElementById('importBtn').style.display = 'none';
    document.getElementById('bankStatementFile').value = '';
    parsedTransactions = [];
    
    const modalElement = document.getElementById('bankImportModal');
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

/**
 * Parse uploaded bank statement
 */
async function parseStatement() {
    const fileInput = document.getElementById('bankStatementFile');
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showExpenseNotification('Please select a CSV file', 'error');
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    // Show loading state
    const parseBtn = event.target;
    const originalText = parseBtn.innerHTML;
    parseBtn.disabled = true;
    parseBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Parsing...';
    
    try {
        showExpenseNotification('Parsing statement...', 'info');
        
        const response = await fetch('/api/bank-import/parse', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            parsedTransactions = data.transactions;
            displayParsedTransactions(data.transactions, data.summary);
            
            // Show review step
            document.getElementById('uploadStep').style.display = 'none';
            document.getElementById('reviewStep').style.display = 'block';
            document.getElementById('importBtn').style.display = 'block';
            
            showExpenseNotification(`Found ${data.summary.total_transactions} potential expenses`, 'success');
        } else {
            showExpenseNotification(data.error || 'Failed to parse statement', 'error');
            parseBtn.disabled = false;
            parseBtn.innerHTML = originalText;
        }
    } catch (error) {
        console.error('Error parsing statement:', error);
        showExpenseNotification('Failed to parse statement: ' + error.message, 'error');
        parseBtn.disabled = false;
        parseBtn.innerHTML = originalText;
    }
}

/**
 * Display parsed transactions
 */
function displayParsedTransactions(transactions, summary) {
    // Update summary
    const summaryHtml = `
        <strong>Parsed ${summary.total_transactions} transactions</strong><br>
        Total amount: ${CurrencyFormatter.format(summary.total_amount)}<br>
        Auto-categorized: ${summary.categorized_count} (${summary.categorization_rate}%)
    `;
    document.getElementById('parseSummary').innerHTML = summaryHtml;
    
    // Display transactions table
    const tbody = document.getElementById('transactionsTableBody');
    tbody.innerHTML = transactions.map((trans, index) => `
        <tr class="${trans.suggested ? 'table-success' : ''}">
            <td>
                <input type="checkbox" 
                       class="transaction-checkbox" 
                       data-index="${index}" 
                       ${trans.selected ? 'checked' : ''}>
            </td>
            <td>${trans.date}</td>
            <td>${trans.description}</td>
            <td class="text-end"><strong>${CurrencyFormatter.format(trans.amount)}</strong></td>
            <td>
                <select class="form-select form-select-sm category-select" data-index="${index}">
                    <option value="">Select category...</option>
                    ${categories.map(cat => `
                        <option value="${cat.name}" ${trans.category === cat.name ? 'selected' : ''}>
                            ${cat.name}
                        </option>
                    `).join('')}
                </select>
            </td>
        </tr>
    `).join('');
    
    // Add event listeners
    document.querySelectorAll('.transaction-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const index = parseInt(this.dataset.index);
            parsedTransactions[index].selected = this.checked;
        });
    });
    
    document.querySelectorAll('.category-select').forEach(select => {
        select.addEventListener('change', function() {
            const index = parseInt(this.dataset.index);
            parsedTransactions[index].category = this.value;
        });
    });
}

/**
 * Toggle all transactions
 */
function toggleAllTransactions() {
    const checked = document.getElementById('selectAllCheckbox').checked;
    document.querySelectorAll('.transaction-checkbox').forEach(checkbox => {
        checkbox.checked = checked;
        const index = parseInt(checkbox.dataset.index);
        parsedTransactions[index].selected = checked;
    });
}

/**
 * Select all transactions
 */
function selectAll() {
    document.getElementById('selectAllCheckbox').checked = true;
    toggleAllTransactions();
}

/**
 * Deselect all transactions
 */
function deselectAll() {
    document.getElementById('selectAllCheckbox').checked = false;
    toggleAllTransactions();
}

/**
 * Select only categorized transactions
 */
function selectCategorized() {
    document.querySelectorAll('.transaction-checkbox').forEach(checkbox => {
        const index = parseInt(checkbox.dataset.index);
        const hasCat = parsedTransactions[index].category && parsedTransactions[index].category !== '';
        checkbox.checked = hasCat;
        parsedTransactions[index].selected = hasCat;
    });
}

/**
 * Import selected transactions
 */
async function importTransactions() {
    const selectedTransactions = parsedTransactions.filter(t => t.selected);
    
    if (selectedTransactions.length === 0) {
        showExpenseNotification('Please select at least one transaction to import', 'error');
        return;
    }
    
    try {
        showExpenseNotification(`Importing ${selectedTransactions.length} expenses...`, 'info');
        
        const response = await fetch('/api/bank-import/import', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ transactions: selectedTransactions })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showExpenseNotification(`Successfully imported ${data.imported_count} expenses!`, 'success');
            
            // Close modal
            const modalElement = document.getElementById('bankImportModal');
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            }
            
            // Reload expenses
            loadExpenses();
            
            // Show errors if any
            if (data.errors && data.errors.length > 0) {
                console.warn('Import errors:', data.errors);
            }
        } else {
            showExpenseNotification(data.error || 'Failed to import transactions', 'error');
        }
    } catch (error) {
        console.error('Error importing transactions:', error);
        showExpenseNotification('Failed to import transactions', 'error');
    }
}

// ============================================================================
// Gmail Receipt Download
// ============================================================================

/**
 * Download receipts from Gmail
 */
async function downloadGmailReceipts() {
    if (!confirm('Download receipts from Gmail?\n\nThis will search for receipt emails from April 2024 onwards and download all PDF/image attachments to the receipts folder.\n\nThis may take a few minutes.')) {
        return;
    }
    
    try {
        showExpenseNotification('Downloading receipts from Gmail... This may take a few minutes.', 'info');
        
        const response = await fetch('/api/gmail/download-receipts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                after_date: '2024/04/06'  // Tax year start
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showExpenseNotification('✅ Receipts downloaded successfully! Check data/receipts folder.', 'success');
            console.log('Download output:', data.output);
        } else {
            showExpenseNotification('Failed to download receipts: ' + (data.error || 'Unknown error'), 'error');
            console.error('Download error:', data);
        }
    } catch (error) {
        console.error('Error downloading receipts:', error);
        showExpenseNotification('Failed to download receipts from Gmail', 'error');
    }
}
