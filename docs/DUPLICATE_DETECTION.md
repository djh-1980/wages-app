# Duplicate Transaction Detection

## Overview
Automatic duplicate detection prevents re-importing transactions that have already been added to expenses. The system checks date, description, and amount to identify duplicates.

---

## How It Works

### Automatic Filtering
When you upload a bank statement CSV:
1. System parses all transactions from the file
2. **Checks each transaction** against existing expenses
3. **Filters out duplicates** automatically
4. Shows only new transactions for import
5. Displays count of filtered duplicates

### Duplicate Criteria
A transaction is considered a duplicate if **all three** match exactly:
- **Date**: Same transaction date (DD/MM/YYYY)
- **Description**: Exact description match
- **Amount**: Exact amount match (£)

### Visual Feedback
```
Parsed 45 transactions (54 in file)
Total amount: £1,234.56
Auto-categorized: 30 (67%)
🔘 9 already imported (filtered out)
```

---

## Use Cases

### Scenario 1: Re-uploading Same Statement
```
First Upload:
- File has 100 transactions
- Import all 100
- Modal closes

Second Upload (same file):
- File has 100 transactions
- System shows: "Parsed 0 transactions (100 in file)"
- Badge: "100 already imported (filtered out)"
- Nothing to import ✓
```

### Scenario 2: Overlapping Statements
```
Upload Statement 1 (Jan 1-31):
- 80 transactions
- Import all 80

Upload Statement 2 (Jan 15 - Feb 15):
- 90 transactions total
- 40 from Jan 15-31 (duplicates)
- 50 from Feb 1-15 (new)
- System shows: "Parsed 50 transactions (90 in file)"
- Badge: "40 already imported (filtered out)"
- Import the 50 new ones ✓
```

### Scenario 3: Partial Import
```
Upload Statement:
- 100 transactions parsed
- Import 60 fuel transactions
- Click "Back to Upload"

Re-upload Same Statement:
- System shows: "Parsed 40 transactions (100 in file)"
- Badge: "60 already imported (filtered out)"
- Only the 40 unimported ones show ✓
```

---

## Benefits

### Prevents Duplicates
- **No accidental re-imports**
- Safe to upload same file multiple times
- Overlapping date ranges handled automatically

### Time Savings
- Don't need to remember what you've imported
- No manual checking required
- Upload any statement anytime

### Data Integrity
- Expenses remain accurate
- No inflated totals
- Clean audit trail

### Flexible Workflow
- Import in batches across sessions
- Upload overlapping statements
- Re-upload for missing transactions

---

## Technical Implementation

### Backend Check (`expense.py`)
```python
@staticmethod
def transaction_exists(date, description, amount):
    """Check if transaction already exists."""
    query = """
        SELECT COUNT(*) as count
        FROM expenses
        WHERE date = ? AND description = ? AND amount = ?
    """
    result = execute_query(query, (date, description, amount), fetch_one=True)
    return result['count'] > 0
```

### Parse Endpoint (`api_bank_import.py`)
```python
# Filter out already imported transactions
filtered_transactions = []
duplicate_count = 0

for trans in transactions:
    if not ExpenseModel.transaction_exists(trans['date'], trans['description'], trans['amount']):
        filtered_transactions.append(trans)
    else:
        duplicate_count += 1

summary['duplicate_count'] = duplicate_count
summary['original_count'] = len(transactions)
```

### Frontend Display (`expenses.js`)
```javascript
const duplicateInfo = summary.duplicate_count > 0 ? 
    `<br><span class="badge bg-secondary">${summary.duplicate_count} already imported (filtered out)</span>` : '';
```

---

## Edge Cases Handled

### 1. Identical Transactions on Same Day
If you legitimately have two identical transactions (same merchant, same amount, same day):
- First one imports normally
- Second one is filtered as duplicate
- **Workaround**: Manually add the second one with a note in description

### 2. Similar But Different Transactions
Transactions that differ in any field are NOT duplicates:
- "TESCO PFS" vs "TESCO STORE" → Different (description)
- £20.00 vs £20.01 → Different (amount)
- 01/01/2025 vs 02/01/2025 → Different (date)

### 3. Amended Transactions
If you delete an expense and re-import:
- Transaction no longer exists in database
- Will appear in next import
- Can be imported again

### 4. Performance
- Duplicate check is fast (indexed query)
- No noticeable delay even with 1000+ transactions
- Runs during parse, not during import

---

## Limitations

### What It Doesn't Do:
1. **Doesn't check across categories**: Same transaction in different categories is still a duplicate
2. **Doesn't check partial matches**: Must be exact match on all three fields
3. **Doesn't track file names**: Doesn't remember which CSV files you've uploaded
4. **Doesn't check pending imports**: Only checks completed imports in expenses table

### Why These Limitations:
- **Simplicity**: Easy to understand and debug
- **Performance**: Fast duplicate checking
- **Accuracy**: No false positives from fuzzy matching
- **Reliability**: Works consistently every time

---

## Future Enhancements

Potential improvements:
1. **Fuzzy Matching**: Detect similar descriptions (e.g., "TESCO PFS" vs "TESCO PFS FUEL")
2. **Amount Tolerance**: Allow small differences (e.g., ±£0.01 for rounding)
3. **Import History**: Track which CSV files have been processed
4. **Duplicate Report**: Show list of filtered duplicates for review
5. **Manual Override**: Option to import duplicates if needed
6. **Batch Duplicate Check**: Check all at once before parsing

---

## Troubleshooting

### Problem: Transaction Not Showing Up
**Cause**: It's been imported before
**Solution**: Check expenses list to confirm it exists

### Problem: Duplicate Showing as New
**Cause**: Description or amount differs slightly
**Solution**: Check exact values in expenses vs CSV

### Problem: Want to Import Duplicate
**Cause**: Legitimate duplicate transaction
**Solution**: Manually add via "Add Expense" button with note

---

## Files Modified

- `app/models/expense.py` - Added `transaction_exists()` method
- `app/routes/api_bank_import.py` - Added duplicate filtering in parse endpoint
- `static/js/expenses.js` - Added duplicate count display in summary

---

**Last Updated**: December 4, 2024
**Version**: 1.0.0
