/**
 * Expenses Management - HMRC MTD Compliance
 */

let categories = [];
let expenses = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadCategories();
    loadTaxYears();
    
    // Check for MTD submission mode
    const urlParams = new URLSearchParams(window.location.search);
    const mode = urlParams.get('mode');
    
    if (mode === 'mtd_submission') {
        setupMTDSubmissionMode(urlParams);
    }
    
    loadExpenses();
    
    // Set today's date as default (YYYY-MM-DD for date input)
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    document.getElementById('expenseDate').value = `${yyyy}-${mm}-${dd}`;
    
    // Load recurring templates when tab is shown
    document.getElementById('recurring-tab').addEventListener('shown.bs.tab', function() {
        loadRecurringTemplates();
    });
    
    // Fix mobile camera capture: scroll to show photo preview after capture
    const receiptFileInput = document.getElementById('receiptFile');
    if (receiptFileInput) {
        receiptFileInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                // Scroll the input into view after photo capture
                setTimeout(() => {
                    this.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 300);
            }
        });
    }
    
    // Reset bank import modal when closed
    const bankImportModal = document.getElementById('bankImportModal');
    if (bankImportModal) {
        bankImportModal.addEventListener('hidden.bs.modal', function() {
            // Reset to upload step
            document.getElementById('uploadStep').style.display = 'block';
            document.getElementById('reviewStep').style.display = 'none';
            document.getElementById('importBtn').style.display = 'none';
            
            // Clear file input
            document.getElementById('bankStatementFile').value = '';
            
            // Clear parsed transactions
            parsedTransactions = [];
            
            // Clear table
            const tbody = document.getElementById('transactionsTableBody');
            if (tbody) {
                tbody.innerHTML = '';
            }
            
            // Clear search
            const searchInput = document.getElementById('transactionSearch');
            if (searchInput) {
                searchInput.value = '';
            }
            const filterCount = document.getElementById('filterCount');
            if (filterCount) {
                filterCount.textContent = '';
            }
            
            // Reset parse button
            const parseBtn = document.querySelector('#uploadStep button[onclick="parseStatement()"]');
            if (parseBtn) {
                parseBtn.disabled = false;
                parseBtn.innerHTML = '<i class="bi bi-gear"></i> Parse Statement';
            }
        });
    }
});

/**
 * Show recurring tab
 */
function showRecurringTab() {
    const recurringTab = new bootstrap.Tab(document.getElementById('recurring-tab'));
    recurringTab.show();
}

/**
 * Load expense categories
 */
async function loadCategories() {
    try {
        const response = await fetch('/api/expenses/categories');
        const responseData = await response.json();
        const data = responseData.success ? responseData.data : responseData;
        
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
    const templateSelect = document.getElementById('templateCategory');
    const bulkSelect = document.getElementById('bulkCategorySelect');
    
    // Clear existing options (except first)
    modalSelect.innerHTML = '<option value="">Select category...</option>';
    filterSelect.innerHTML = '<option value="">All Categories</option>';
    if (templateSelect) {
        templateSelect.innerHTML = '<option value="">Select category...</option>';
    }
    if (bulkSelect) {
        bulkSelect.innerHTML = '<option value="">Select category to apply...</option>';
    }
    
    categories.forEach(cat => {
        const modalOption = new Option(cat.name, cat.id);
        const filterOption = new Option(cat.name, cat.id);
        modalSelect.add(modalOption);
        filterSelect.add(filterOption);
        
        if (templateSelect) {
            const templateOption = new Option(cat.name, cat.id);
            templateSelect.add(templateOption);
        }
        
        if (bulkSelect) {
            const bulkOption = new Option(cat.name, cat.name);
            bulkSelect.add(bulkOption);
        }
    });
}

/**
 * Load tax years
 */
async function loadTaxYears() {
    try {
        const response = await fetch('/api/expenses/tax-years');
        const responseData = await response.json();
        const data = responseData.success ? responseData.data : responseData;
        
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
        const responseData = await response.json();
        const data = responseData.success ? responseData.data : responseData;
        
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
                <td colspan="8" class="text-center text-muted py-4">
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
            <td><small class="badge bg-info">${expense.hmrc_box || 'Other'}</small></td>
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
    // Set today's date in YYYY-MM-DD format for date input
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    document.getElementById('expenseDate').value = `${yyyy}-${mm}-${dd}`;
    document.getElementById('recurringOptions').style.display = 'none';
    document.getElementById('receiptFile').value = '';
    document.getElementById('currentReceipt').style.display = 'none';
    
    // Reset camera/upload sections
    showUpload();
    capturedPhotoBlob = null;
    
    // Hide and clear photo confirmation
    const photoConfirmation = document.getElementById('photoConfirmation');
    if (photoConfirmation) {
        photoConfirmation.style.display = 'none';
        photoConfirmation.innerHTML = '';
    }
    
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
        const responseData = await response.json();
        const data = responseData.success ? responseData.data : responseData;
        
        if (data.expense) {
            const expense = data.expense;
            document.getElementById('expenseModalTitle').textContent = 'Edit Expense';
            document.getElementById('expenseId').value = expense.id;
            // Convert date from DD/MM/YYYY to YYYY-MM-DD for date input
            const [day, month, year] = expense.date.split('/');
            document.getElementById('expenseDate').value = `${year}-${month}-${day}`;
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
    const dateInput = document.getElementById('expenseDate').value;
    const categoryId = document.getElementById('expenseCategory').value;
    const amount = document.getElementById('expenseAmount').value;
    const description = document.getElementById('expenseDescription').value;
    const isRecurring = document.getElementById('isRecurring').checked;
    const recurringFrequency = document.getElementById('recurringFrequency').value;
    const receiptFile = document.getElementById('receiptFile').files[0];
    
    if (!dateInput || !categoryId || !amount) {
        showExpenseNotification('Please fill in all required fields', 'error');
        return;
    }
    
    // Convert date from YYYY-MM-DD to DD/MM/YYYY for backend
    const [year, month, day] = dateInput.split('-');
    const date = `${day}/${month}/${year}`;
    
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
                headers: getJSONHeaders(),
                body: JSON.stringify(expenseData)
            });
        } else {
            // Add new
            response = await fetch('/api/expenses/add', {
                method: 'POST',
                headers: getJSONHeaders(),
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
            headers: getCSRFHeaders(),
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
    
    // Hide and clear photo confirmation
    const photoConfirmation = document.getElementById('photoConfirmation');
    if (photoConfirmation) {
        photoConfirmation.style.display = 'none';
        photoConfirmation.innerHTML = '';
    }
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
        
        // Fix iOS scroll issue - scroll captured photo into view
        setTimeout(() => {
            document.getElementById('capturedPhoto').scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
        }, 100);
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
        
        // Show confirmation below buttons
        const photoConfirmation = document.getElementById('photoConfirmation');
        if (photoConfirmation) {
            photoConfirmation.innerHTML = '📷 Photo attached and ready to save';
            photoConfirmation.style.display = 'block';
        }
    }
}

/**
 * Retake photo
 */
function retakePhoto() {
    capturedPhotoBlob = null;
    
    // Hide and clear photo confirmation
    const photoConfirmation = document.getElementById('photoConfirmation');
    if (photoConfirmation) {
        photoConfirmation.style.display = 'none';
        photoConfirmation.innerHTML = '';
    }
    
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
            method: 'DELETE',
            headers: getCSRFHeaders()
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
    // Reset modal to upload step
    document.getElementById('uploadStep').style.display = 'block';
    document.getElementById('reviewStep').style.display = 'none';
    document.getElementById('importBtn').style.display = 'none';
    document.getElementById('bankStatementFile').value = '';
    parsedTransactions = [];
    
    // Reset parse button state
    const parseBtn = document.querySelector('#uploadStep button[onclick="parseStatement()"]');
    if (parseBtn) {
        parseBtn.disabled = false;
        parseBtn.innerHTML = '<i class="bi bi-gear"></i> Parse Statement';
    }
    
    // Clear search if it exists
    const searchInput = document.getElementById('transactionSearch');
    if (searchInput) {
        searchInput.value = '';
    }
    const filterCount = document.getElementById('filterCount');
    if (filterCount) {
        filterCount.textContent = '';
    }
    
    const modalElement = document.getElementById('bankImportModal');
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

/**
 * Go back to upload step
 */
function backToUpload() {
    document.getElementById('uploadStep').style.display = 'block';
    document.getElementById('reviewStep').style.display = 'none';
    document.getElementById('importBtn').style.display = 'none';
    
    // Reset parse button
    const parseBtn = document.querySelector('#uploadStep button[onclick="parseStatement()"]');
    if (parseBtn) {
        parseBtn.disabled = false;
        parseBtn.innerHTML = '<i class="bi bi-gear"></i> Parse Statement';
    }
    
    // Clear file input
    document.getElementById('bankStatementFile').value = '';
    
    // Clear search
    const searchInput = document.getElementById('transactionSearch');
    if (searchInput) {
        searchInput.value = '';
    }
    const filterCount = document.getElementById('filterCount');
    if (filterCount) {
        filterCount.textContent = '';
    }
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
            headers: getCSRFHeaders(),
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
    // Count recurring matches
    const recurringCount = transactions.filter(t => t.is_recurring).length;
    const autoImportCount = transactions.filter(t => t.auto_import).length;
    
    // Update summary
    const duplicateInfo = summary.duplicate_count > 0 ? 
        `<br><span class="badge bg-secondary">${summary.duplicate_count} already imported (filtered out)</span>` : '';
    
    const summaryHtml = `
        <strong>Parsed ${summary.total_transactions} transactions</strong>${summary.original_count ? ` (${summary.original_count} in file)` : ''}<br>
        Total amount: ${CurrencyFormatter.format(summary.total_amount)}<br>
        Auto-categorized: ${summary.categorized_count} (${summary.categorization_rate}%)
        ${recurringCount > 0 ? `<br><span class="badge bg-warning">${recurringCount} matched to recurring templates</span>` : ''}
        ${autoImportCount > 0 ? `<br><span class="badge bg-success">${autoImportCount} will auto-import</span>` : ''}
        ${duplicateInfo}
    `;
    document.getElementById('parseSummary').innerHTML = summaryHtml;
    
    // Display transactions table
    const tbody = document.getElementById('transactionsTableBody');
    tbody.innerHTML = transactions.map((trans, index) => {
        const rowClass = trans.is_recurring ? 'table-warning' : (trans.suggested ? 'table-success' : '');
        const recurringBadge = trans.is_recurring ? 
            `<span class="badge bg-warning ms-1" title="Matched to: ${trans.template_name} (${trans.confidence}% confidence)">
                <i class="bi bi-arrow-repeat"></i> Recurring
            </span>` : '';
        const autoImportBadge = trans.auto_import ? 
            `<span class="badge bg-success ms-1" title="Will be auto-imported">
                <i class="bi bi-lightning-fill"></i> Auto
            </span>` : '';
        
        // Auto-populate notes for recurring transactions if not already set
        if (trans.is_recurring && trans.template_name && !trans.notes) {
            trans.notes = `Recurring: ${trans.template_name}`;
        }
        
        return `
            <tr class="${rowClass}">
                <td>
                    <input type="checkbox" 
                           class="transaction-checkbox" 
                           data-index="${index}" 
                           ${trans.selected ? 'checked' : ''}>
                </td>
                <td>${trans.date}</td>
                <td>
                    ${trans.description}
                    ${recurringBadge}
                    ${autoImportBadge}
                </td>
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
                <td>
                    <input type="text" 
                           class="form-control form-control-sm notes-input" 
                           data-index="${index}"
                           placeholder="Add notes..."
                           value="${trans.notes || (trans.is_recurring && trans.template_name ? `Recurring: ${trans.template_name}` : '')}">
                </td>
            </tr>
        `;
    }).join('');
    
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
    
    document.querySelectorAll('.notes-input').forEach(input => {
        input.addEventListener('input', function() {
            const index = parseInt(this.dataset.index);
            parsedTransactions[index].notes = this.value;
        });
    });
}

/**
 * Toggle all transactions
 */
function toggleAllTransactions() {
    const selectAll = document.getElementById('selectAllCheckbox').checked;
    document.querySelectorAll('.transaction-checkbox:not([style*="display: none"])').forEach(checkbox => {
        const row = checkbox.closest('tr');
        if (row.style.display !== 'none') {
            checkbox.checked = selectAll;
            const index = parseInt(checkbox.dataset.index);
            parsedTransactions[index].selected = selectAll;
        }
    });
}

/**
 * Filter transactions based on search input
 */
function filterTransactions() {
    const searchTerm = document.getElementById('transactionSearch').value.toLowerCase();
    const rows = document.querySelectorAll('#transactionsTableBody tr');
    let visibleCount = 0;
    
    rows.forEach(row => {
        const description = row.cells[2].textContent.toLowerCase();
        const amount = row.cells[3].textContent.toLowerCase();
        const category = row.cells[4].querySelector('select')?.value.toLowerCase() || '';
        
        const matches = description.includes(searchTerm) || 
                       amount.includes(searchTerm) || 
                       category.includes(searchTerm);
        
        if (matches) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    
    // Update filter count
    const filterCount = document.getElementById('filterCount');
    if (searchTerm) {
        filterCount.textContent = `Showing ${visibleCount} of ${rows.length} transactions`;
        filterCount.style.color = visibleCount === 0 ? '#dc3545' : '#6c757d';
    } else {
        filterCount.textContent = '';
    }
}

/**
 * Clear transaction search
 */
function clearTransactionSearch() {
    document.getElementById('transactionSearch').value = '';
    filterTransactions();
}

/**
 * Select only recurring transactions
 */
function selectRecurring() {
    document.querySelectorAll('.transaction-checkbox').forEach(checkbox => {
        const row = checkbox.closest('tr');
        if (row.style.display !== 'none') {
            const index = parseInt(checkbox.dataset.index);
            const isRecurring = parsedTransactions[index].is_recurring;
            checkbox.checked = isRecurring;
            parsedTransactions[index].selected = isRecurring;
        }
    });
}

/**
 * Apply bulk category to all visible transactions
 */
function applyBulkCategory() {
    const bulkSelect = document.getElementById('bulkCategorySelect');
    const selectedCategory = bulkSelect.value;
    
    if (!selectedCategory) {
        showExpenseNotification('Please select a category first', 'error');
        return;
    }
    
    let appliedCount = 0;
    
    // Apply to all visible rows
    document.querySelectorAll('#transactionsTableBody tr').forEach(row => {
        if (row.style.display !== 'none') {
            const categorySelect = row.cells[4].querySelector('select');
            if (categorySelect) {
                const index = parseInt(categorySelect.dataset.index);
                categorySelect.value = selectedCategory;
                parsedTransactions[index].category = selectedCategory;
                appliedCount++;
            }
        }
    });
    
    // Reset bulk select
    bulkSelect.value = '';
    
    showExpenseNotification(`Applied "${selectedCategory}" to ${appliedCount} visible transactions`, 'success');
}

/**
 * Apply bulk notes to all visible transactions
 */
function applyBulkNotes() {
    const bulkInput = document.getElementById('bulkNotesInput');
    const notes = bulkInput.value.trim();
    
    if (!notes) {
        showExpenseNotification('Please enter notes first', 'error');
        return;
    }
    
    let appliedCount = 0;
    
    // Apply to all visible rows
    document.querySelectorAll('#transactionsTableBody tr').forEach(row => {
        if (row.style.display !== 'none') {
            const notesInput = row.cells[5].querySelector('input');
            if (notesInput) {
                const index = parseInt(notesInput.dataset.index);
                notesInput.value = notes;
                parsedTransactions[index].notes = notes;
                appliedCount++;
            }
        }
    });
    
    // Reset bulk input
    bulkInput.value = '';
    
    showExpenseNotification(`Applied notes to ${appliedCount} visible transactions`, 'success');
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
        const row = checkbox.closest('tr');
        if (row.style.display !== 'none') {
            const index = parseInt(checkbox.dataset.index);
            const hasCat = parsedTransactions[index].category && parsedTransactions[index].category !== '';
            checkbox.checked = hasCat;
            parsedTransactions[index].selected = hasCat;
        }
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
            headers: getJSONHeaders(),
            body: JSON.stringify({ transactions: selectedTransactions })
        });
        
        const data = await response.json();
        
        if (data.success) {
            let message = `Successfully imported ${data.imported_count} expenses!`;
            if (data.auto_imported_count > 0) {
                message += ` (${data.auto_imported_count} auto-imported from recurring templates)`;
            }
            showExpenseNotification(message, 'success');
            
            // Remove imported transactions from the list
            parsedTransactions = parsedTransactions.filter(t => !t.selected);
            
            // If no transactions left, close modal
            if (parsedTransactions.length === 0) {
                const modalElement = document.getElementById('bankImportModal');
                const modal = bootstrap.Modal.getInstance(modalElement);
                if (modal) {
                    modal.hide();
                }
            } else {
                // Clear search to show all remaining transactions
                const searchInput = document.getElementById('transactionSearch');
                if (searchInput) {
                    searchInput.value = '';
                }
                const filterCount = document.getElementById('filterCount');
                if (filterCount) {
                    filterCount.textContent = '';
                }
                
                // Update the display with remaining transactions
                const summary = {
                    total_transactions: parsedTransactions.length,
                    total_amount: parsedTransactions.reduce((sum, t) => sum + t.amount, 0),
                    categorized_count: parsedTransactions.filter(t => t.category).length,
                    categorization_rate: Math.round((parsedTransactions.filter(t => t.category).length / parsedTransactions.length) * 100)
                };
                displayParsedTransactions(parsedTransactions, summary);
                
                showExpenseNotification(`${parsedTransactions.length} transactions remaining. Import more or click "Back to Upload"`, 'info');
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
            headers: getJSONHeaders(),
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

// ============================================================================
// HMRC MTD Submission
// ============================================================================

let hmrcSubmissionData = null;

/**
 * Setup MTD submission mode from URL parameters
 */
function setupMTDSubmissionMode(urlParams) {
    const fromDate = urlParams.get('from_date');
    const toDate = urlParams.get('to_date');
    const taxYear = urlParams.get('tax_year');
    const periodId = urlParams.get('period_id');
    
    if (!fromDate || !toDate || !taxYear || !periodId) {
        console.error('Missing required MTD submission parameters');
        return;
    }
    
    // Set date range filters
    const filterFromDate = document.getElementById('filterFromDate');
    const filterToDate = document.getElementById('filterToDate');
    const filterTaxYear = document.getElementById('filterTaxYear');
    
    if (filterFromDate) filterFromDate.value = fromDate;
    if (filterToDate) filterToDate.value = toDate;
    if (filterTaxYear) filterTaxYear.value = taxYear;
    
    // Lock the fields (make readonly)
    if (filterFromDate) filterFromDate.readOnly = true;
    if (filterToDate) filterToDate.readOnly = true;
    if (filterTaxYear) filterTaxYear.disabled = true;
    
    // Format dates for display
    const formatDisplayDate = (dateStr) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
    };
    
    // Show blue banner at the top
    const pageHeader = document.querySelector('.page-header');
    if (pageHeader) {
        const banner = document.createElement('div');
        banner.className = 'alert alert-info mb-3';
        banner.innerHTML = `
            <i class="bi bi-info-circle"></i>
            <strong>Submitting ${periodId} (${formatDisplayDate(fromDate)} - ${formatDisplayDate(toDate)}) to HMRC MTD.</strong>
            Figures are taken from your digital records for this period.
        `;
        pageHeader.after(banner);
    }
    
    // Update submit button label
    const submitBtn = document.getElementById('hmrcSubmitBtn');
    if (submitBtn) {
        submitBtn.innerHTML = `<i class="bi bi-send-fill"></i> Submit ${periodId} to HMRC MTD`;
    }
    
    // Store MTD submission context
    window.mtdSubmissionContext = {
        fromDate,
        toDate,
        taxYear,
        periodId
    };
}

/**
 * Check HMRC connection status and show/hide submit button
 */
async function checkHMRCConnection() {
    try {
        const response = await fetch('/api/hmrc/auth/status');
        const responseData = await response.json();
        const data = responseData.success ? responseData.data : responseData;
        
        const submitBtn = document.getElementById('hmrcSubmitBtn');
        if (data.connected) {
            submitBtn.style.display = 'block';
        } else {
            submitBtn.style.display = 'none';
        }
    } catch (error) {
        console.error('Error checking HMRC connection:', error);
    }
}

/**
 * Show HMRC submission modal
 */
function showHMRCSubmitModal() {
    // Populate tax years
    const taxYearSelect = document.getElementById('hmrcTaxYear');
    const currentYear = new Date().getFullYear();
    const currentMonth = new Date().getMonth() + 1;
    
    // Tax year starts April 6
    let startYear = currentMonth >= 4 ? currentYear : currentYear - 1;
    
    taxYearSelect.innerHTML = '';
    for (let i = 0; i < 3; i++) {
        const year = startYear - i;
        const option = document.createElement('option');
        option.value = `${year}/${year + 1}`;
        option.textContent = `${year}/${year + 1}`;
        if (i === 0) option.selected = true;
        taxYearSelect.appendChild(option);
    }
    
    // Reset modal
    document.getElementById('hmrcStep1').style.display = 'block';
    document.getElementById('hmrcStep2').style.display = 'none';
    document.getElementById('hmrcStep3').style.display = 'none';
    
    const modal = new bootstrap.Modal(document.getElementById('hmrcSubmitModal'));
    modal.show();
}

/**
 * Preview HMRC submission
 */
async function previewHMRCSubmission() {
    // Check if we're in MTD submission mode
    const mtdContext = window.mtdSubmissionContext;
    let taxYear, quarter, fromDate, toDate;
    
    if (mtdContext) {
        // Use context from MTD submission mode
        taxYear = mtdContext.taxYear;
        quarter = mtdContext.periodId;
        fromDate = mtdContext.fromDate;
        toDate = mtdContext.toDate;
    } else {
        // Use values from modal
        taxYear = document.getElementById('hmrcTaxYear').value;
        quarter = document.getElementById('hmrcQuarter').value;
    }
    
    try {
        showExpenseNotification('Loading submission preview...', 'info');
        
        // Build URL with optional date parameters
        let url = `/api/hmrc/period/preview?tax_year=${taxYear}&period_id=${quarter}`;
        if (fromDate && toDate) {
            url += `&from_date=${fromDate}&to_date=${toDate}`;
        }
        
        console.log('Preview request:', { tax_year: taxYear, period_id: quarter, from_date: fromDate, to_date: toDate });
        
        const response = await fetch(url);
        const responseData = await response.json();
        const data = responseData.success ? responseData.data : responseData;
        
        if (data.success || responseData.success) {
            hmrcSubmissionData = data.submission_data;
            displayHMRCPreview(data.submission_data, data.validation);
            
            // Move to step 2
            document.getElementById('hmrcStep1').style.display = 'none';
            document.getElementById('hmrcStep2').style.display = 'block';
        } else {
            showExpenseNotification('Failed to load preview: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error loading preview:', error);
        showExpenseNotification('Failed to load submission preview', 'error');
    }
}

/**
 * Display HMRC preview data
 */
function displayHMRCPreview(submissionData, validation) {
    const previewDiv = document.getElementById('hmrcPreviewData');
    
    let html = '<div class="card mb-3">';
    html += '<div class="card-header"><strong>Period Information</strong></div>';
    html += '<div class="card-body">';
    html += `<p><strong>From:</strong> ${submissionData.periodDates?.periodStartDate || 'N/A'}</p>`;
    html += `<p><strong>To:</strong> ${submissionData.periodDates?.periodEndDate || 'N/A'}</p>`;
    html += '</div></div>';
    
    // Income
    if (submissionData.periodIncome) {
        html += '<div class="card mb-3">';
        html += '<div class="card-header"><strong>Income</strong></div>';
        html += '<div class="card-body">';
        const turnover = parseFloat(submissionData.periodIncome.turnover) || 0;
        const otherIncome = parseFloat(submissionData.periodIncome.other) || 0;
        html += `<p><strong>Turnover:</strong> £${turnover.toFixed(2)}</p>`;
        html += `<p><strong>Other:</strong> £${otherIncome.toFixed(2)}</p>`;
        html += '</div></div>';
    }
    
    // Expenses
    if (submissionData.periodExpenses) {
        html += '<div class="card mb-3">';
        html += '<div class="card-header"><strong>Expenses</strong></div>';
        html += '<div class="card-body">';
        
        const expenseFields = {
            'costOfGoodsBought': 'Cost of Goods',
            'cisPaymentsToSubcontractors': 'CIS Payments',
            'staffCosts': 'Staff Costs',
            'travelCosts': 'Travel Costs',
            'premisesRunningCosts': 'Premises Costs',
            'maintenanceCosts': 'Maintenance',
            'adminCosts': 'Admin Costs',
            'advertisingCosts': 'Advertising',
            'businessEntertainmentCosts': 'Entertainment',
            'interest': 'Interest',
            'financialCharges': 'Financial Charges',
            'badDebt': 'Bad Debt',
            'professionalFees': 'Professional Fees',
            'depreciation': 'Depreciation',
            'other': 'Other Expenses'
        };
        
        for (const [key, label] of Object.entries(expenseFields)) {
            if (submissionData.periodExpenses[key]) {
                const amount = parseFloat(submissionData.periodExpenses[key].amount || submissionData.periodExpenses[key]) || 0;
                if (amount > 0) {
                    html += `<p><strong>${label}:</strong> £${amount.toFixed(2)}</p>`;
                }
            }
        }
        
        html += '</div></div>';
    }
    
    // Validation
    if (validation && !validation.valid) {
        html += '<div class="alert alert-danger">';
        html += '<strong>Validation Errors:</strong><ul>';
        validation.errors.forEach(error => {
            html += `<li>${error}</li>`;
        });
        html += '</ul></div>';
    } else {
        html += '<div class="alert alert-success">';
        html += '<i class="bi bi-check-circle"></i> Submission data is valid and ready to send';
        html += '</div>';
    }
    
    previewDiv.innerHTML = html;
}

/**
 * Go back to step 1
 */
function backToStep1() {
    document.getElementById('hmrcStep1').style.display = 'block';
    document.getElementById('hmrcStep2').style.display = 'none';
}

/**
 * Confirm and submit to HMRC
 */
async function confirmHMRCSubmission() {
    if (!confirm('Are you sure you want to submit this data to HMRC?\n\nThis will create an official submission record.')) {
        return;
    }
    
    // Check if we're in MTD submission mode
    const mtdContext = window.mtdSubmissionContext;
    let taxYear, quarter, fromDate, toDate;
    
    if (mtdContext) {
        // Use context from MTD submission mode
        taxYear = mtdContext.taxYear;
        quarter = mtdContext.periodId;
        fromDate = mtdContext.fromDate;
        toDate = mtdContext.toDate;
    } else {
        // Use values from modal
        taxYear = document.getElementById('hmrcTaxYear').value;
        quarter = document.getElementById('hmrcQuarter').value;
    }
    
    // Get NINO and Business ID from localStorage
    const nino = localStorage.getItem('hmrc_nino');
    const businessId = localStorage.getItem('hmrc_business_id');
    
    if (!nino || !businessId) {
        showExpenseNotification('Please configure your NINO and Business ID in HMRC settings first', 'error');
        return;
    }
    
    try {
        showExpenseNotification('Submitting to HMRC...', 'info');
        
        const requestBody = {
            nino: nino,
            business_id: businessId,
            tax_year: taxYear,
            period_id: quarter
        };
        
        // Include from_date and to_date if available
        if (fromDate && toDate) {
            requestBody.from_date = fromDate;
            requestBody.to_date = toDate;
        }
        
        // Log the exact dates being sent to API
        console.log('HMRC Submission Request:', {
            from_date: requestBody.from_date || 'Not provided (will be calculated)',
            to_date: requestBody.to_date || 'Not provided (will be calculated)',
            tax_year: requestBody.tax_year,
            period_id: requestBody.period_id
        });
        
        const response = await fetch('/api/hmrc/period/submit', {
            method: 'POST',
            headers: getJSONHeaders(),
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        // If in MTD submission mode and successful, redirect back to MTD page
        if (mtdContext && data.success) {
            showExpenseNotification('Submission successful! Redirecting to HMRC MTD page...', 'success');
            setTimeout(() => {
                window.location.href = '/settings/hmrc?submission_success=true';
            }, 2000);
            return;
        }
        
        // Show result
        displayHMRCResult(data);
        
        // Move to step 3
        document.getElementById('hmrcStep2').style.display = 'none';
        document.getElementById('hmrcStep3').style.display = 'block';
        
    } catch (error) {
        console.error('Error submitting to HMRC:', error);
        showExpenseNotification('Failed to submit to HMRC', 'error');
    }
}

/**
 * Display HMRC submission result
 */
function displayHMRCResult(result) {
    const resultDiv = document.getElementById('hmrcResult');
    
    if (result.success) {
        let html = '<div class="alert alert-success">';
        html += '<h5><i class="bi bi-check-circle"></i> Submission Successful!</h5>';
        html += '<p>Your quarterly update has been submitted to HMRC.</p>';
        if (result.data && result.data.id) {
            html += `<p><strong>Receipt ID:</strong> ${result.data.id}</p>`;
        }
        html += '</div>';
        
        resultDiv.innerHTML = html;
        showExpenseNotification('Successfully submitted to HMRC!', 'success');
    } else {
        let html = '<div class="alert alert-danger">';
        html += '<h5><i class="bi bi-x-circle"></i> Submission Failed</h5>';
        html += `<p>${result.error || 'Unknown error occurred'}</p>`;
        if (result.details) {
            html += '<pre>' + JSON.stringify(result.details, null, 2) + '</pre>';
        }
        html += '</div>';
        
        resultDiv.innerHTML = html;
        showExpenseNotification('Submission failed: ' + (result.error || 'Unknown error'), 'error');
    }
}

// Check HMRC connection on page load
document.addEventListener('DOMContentLoaded', function() {
    checkHMRCConnection();
});
