# Bank Import Enhancements

## Overview
Enhanced the bank statement import modal with search/filter functionality and improved navigation for better transaction management.

---

## New Features

### 1. **Search/Filter Transactions**
Real-time search across all transaction fields:
- **Description**: Search merchant names and transaction details
- **Amount**: Find specific amounts (e.g., "299.99" or "£35")
- **Category**: Filter by category name

**Features:**
- Live filtering as you type
- Shows count: "Showing X of Y transactions"
- Red text when no matches found
- Clear button (X) to reset search
- Persists across selection operations

**Usage:**
```
Search Examples:
- "SANTANDER" - Find all Santander transactions
- "299.99" - Find specific amount
- "Vehicle" - Find all vehicle cost transactions
- "FUEL" - Find all fuel purchases
```

### 2. **Bulk Category & Notes Assignment**
Apply category or notes to all visible (filtered) transactions at once:

**Bulk Category:**
- **Dropdown**: Select category from full list
- **Apply to Visible**: Assigns category to all visible rows
- **Works with Search**: Filter first, then bulk assign

**Bulk Notes:**
- **Text Input**: Enter notes to apply
- **Apply to Visible**: Adds same notes to all visible rows
- **Useful for**: Project codes, client names, batch context

**Powerful Workflow:**
1. Search for "TESCO" (finds 15 transactions)
2. Select "Fuel" from bulk category dropdown → Apply
3. Type "Project ABC deliveries" in bulk notes → Apply
4. All 15 Tesco transactions now have category AND notes

### 3. **Enhanced Selection Buttons**
Four smart selection options that respect the current filter:

- **Select All**: Selects all visible transactions
- **Deselect All**: Deselects all visible transactions
- **Select Categorized**: Selects only auto-categorized transactions
- **Select Recurring**: Selects only recurring template matches

All buttons work with filtered results, so you can:
1. Search for "FUEL"
2. Click "Select All" to select only fuel transactions
3. Import just those transactions

### 3. **Smart Transaction Removal**
Imported transactions are automatically removed from the list:
- After successful import, imported transactions disappear
- Remaining transactions stay in the list
- Updated summary shows remaining count
- Clear message: "X transactions remaining"
- Modal auto-closes if all transactions imported

**Benefits:**
- No duplicate imports
- Clear visual feedback
- Easy to import in batches
- Can review and import remaining transactions

### 4. **Back to Upload Button**
Navigate back to upload a different file without closing the modal:
- Resets parse button state (removes spinner)
- Clears file input
- Clears search filter
- Returns to upload step

**Use Case:**
- Uploaded wrong file? Click "Back to Upload"
- Want to import multiple statements? Use back button between files

### 5. **Notes Field for Context**
Add custom notes to any transaction before importing:
- **Input field** on each transaction row
- **Auto-populated** for recurring transactions with template name
- **Bulk apply** same notes to multiple transactions
- **Appends to description** when imported
- **Useful for**: Adding context, project codes, client names, etc.
- **Preserved** in expense records

**Auto-Population for Recurring:**
```
Transaction matched to "Van Finance" template
Notes auto-filled: "Recurring: Van Finance"
You can edit or keep as-is
```

**Manual Example:**
```
Transaction: "TESCO PFS 5277"
Add note: "Client visit - Project ABC"
Imported as: "TESCO PFS 5277 - Client visit - Project ABC"
```

**Bulk Example:**
```
Search "TESCO" → 15 transactions found
Bulk notes: "Project ABC deliveries"
All 15 get same note applied instantly
```

### 6. **Improved Modal Reset**
When opening the bank import modal:
- Clears previous search
- Resets parse button (no stuck spinner)
- Clears filter count
- Fresh state every time

---

## Technical Implementation

### HTML Changes (`templates/expenses.html`)

**Added Search Bar:**
```html
<div class="input-group">
    <span class="input-group-text"><i class="bi bi-search"></i></span>
    <input type="text" id="transactionSearch" 
           placeholder="Search by description, amount, or category..." 
           onkeyup="filterTransactions()">
    <button class="btn btn-outline-secondary" onclick="clearTransactionSearch()">
        <i class="bi bi-x"></i>
    </button>
</div>
<div class="form-text" id="filterCount"></div>
```

**Added Back Button:**
```html
<button class="btn btn-outline-secondary" onclick="backToUpload()">
    <i class="bi bi-arrow-left"></i> Back to Upload
</button>
```

**Enhanced Button Group:**
```html
<div class="btn-group w-100">
    <button onclick="selectAll()">Select All</button>
    <button onclick="deselectAll()">Deselect All</button>
    <button onclick="selectCategorized()">Select Categorized</button>
    <button onclick="selectRecurring()">Select Recurring</button>
</div>
```

### JavaScript Functions (`static/js/expenses.js`)

**1. filterTransactions()**
```javascript
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
        
        row.style.display = matches ? '' : 'none';
        if (matches) visibleCount++;
    });
    
    // Update filter count
    if (searchTerm) {
        filterCount.textContent = `Showing ${visibleCount} of ${rows.length} transactions`;
    }
}
```

**2. clearTransactionSearch()**
```javascript
function clearTransactionSearch() {
    document.getElementById('transactionSearch').value = '';
    filterTransactions();
}
```

**3. selectRecurring()**
```javascript
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
```

**4. backToUpload()**
```javascript
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
    
    // Clear file input and search
    document.getElementById('bankStatementFile').value = '';
    document.getElementById('transactionSearch').value = '';
    document.getElementById('filterCount').textContent = '';
}
```

**5. Enhanced Selection Functions**
All selection functions now check `row.style.display !== 'none'` to respect filter:
```javascript
function selectCategorized() {
    document.querySelectorAll('.transaction-checkbox').forEach(checkbox => {
        const row = checkbox.closest('tr');
        if (row.style.display !== 'none') {  // Only visible rows
            const index = parseInt(checkbox.dataset.index);
            const hasCat = parsedTransactions[index].category;
            checkbox.checked = hasCat;
            parsedTransactions[index].selected = hasCat;
        }
    });
}
```

---

## User Workflows

### Workflow 1: Bulk Categorize and Import
1. Upload bank statement CSV
2. Click "Parse Statement"
3. Search "TESCO" (finds 15 transactions)
4. Select "Fuel" from bulk dropdown
5. Click "Apply to Visible" (all 15 categorized)
6. Click "Select All" → Import
7. Search "ASDA" → Bulk assign "Fuel" → Import
8. Continue for other merchants

### Workflow 2: Filter and Import Specific Transactions
1. Upload bank statement CSV
2. Click "Parse Statement"
3. Type "FUEL" in search box
4. Review filtered fuel transactions
5. Click "Select All" (selects only visible fuel transactions)
6. Click "Import Selected"
7. Imported transactions removed from list automatically

### Workflow 3: Import Only Recurring Payments
1. Upload bank statement CSV
2. Click "Parse Statement"
3. Click "Select Recurring" button
4. Review selected recurring matches
5. Click "Import Selected"
6. Recurring transactions removed, others remain

### Workflow 4: Batch Import in Stages
1. Upload statement with 50 transactions
2. Parse statement
3. Search "FUEL" → Bulk assign "Fuel" → Select All → Import (10 transactions)
4. Search "SANTANDER" → Bulk assign "Vehicle Costs" → Select All → Import (5 transactions)
5. Review remaining 35 transactions
6. Select desired ones → Import
7. Modal closes when all done

### Workflow 5: Import Multiple Statements
1. Upload first statement
2. Parse and import all transactions
3. Modal closes automatically
4. Click "Import Bank Statement" again
5. Upload second statement
6. Parse and import
7. Repeat as needed

### Workflow 6: Find Specific Transaction
1. Upload statement with 100+ transactions
2. Type merchant name or amount in search
3. Instantly see matching transactions
4. Select/deselect as needed
5. Import selected
6. Clear search to see remaining transactions

---

## Benefits

### Time Savings
- **Before**: Scroll through 100+ transactions to find specific ones
- **After**: Type search term, instantly see matches

### Accuracy
- Filter before selecting reduces import errors
- Easy to verify recurring matches
- Quick spot-checking of amounts

### Flexibility
- Import all at once or filter by type
- Handle multiple statements in one session
- Easy navigation between steps

### User Experience
- No stuck spinners when switching files
- Clear visual feedback (filter count)
- Intuitive search and selection
- Professional workflow

---

## Edge Cases Handled

1. **Empty Search**: Shows all transactions, hides filter count
2. **No Matches**: Shows "Showing 0 of X" in red text
3. **Select All with Filter**: Only selects visible transactions
4. **Back Button**: Fully resets state including spinner
5. **Modal Reopen**: Clears previous search and state
6. **Category Dropdown**: Included in search (can search by category)

---

## Future Enhancements

Potential improvements:
1. **Advanced Filters**: Date range, amount range sliders
2. **Save Filters**: Remember common search patterns
3. **Bulk Actions**: Bulk category assignment for filtered results
4. **Export Filtered**: Export only filtered transactions
5. **Search History**: Recent searches dropdown
6. **Regex Search**: Advanced pattern matching
7. **Multi-Column Sort**: Sort by date, amount, etc.

---

## Files Modified

- `templates/expenses.html` - Added search bar, back button, enhanced button group
- `static/js/expenses.js` - Added filter functions, enhanced selection logic

---

**Last Updated**: December 4, 2024
**Version**: 1.1.0
