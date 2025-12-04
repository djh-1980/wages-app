# Recurring Payments & Bank Import Enhancement Guide

## Overview

A comprehensive system for managing recurring payments and automating bank statement imports with smart template matching. This system dramatically reduces manual data entry and ensures consistent expense tracking for HMRC compliance.

---

## Key Features

### 1. **Recurring Payment Templates**
Define templates for regular expenses (van finance, insurance, phone bills, etc.) that automatically match and categorize bank transactions.

**Template Properties:**
- **Name**: Descriptive identifier (e.g., "Van Finance")
- **Category**: HMRC expense category
- **Expected Amount**: Typical payment amount
- **Tolerance**: ±Amount variance allowed (default £5)
- **Frequency**: Weekly, Monthly, Quarterly, or Annually
- **Merchant Pattern**: Text to match in bank descriptions
- **Day of Month**: Expected payment day (for monthly)
- **Auto-Import**: Automatically import without review

### 2. **Smart Bank Statement Import**
Upload RBS CSV bank statements and let the system:
- Parse all debit transactions
- Match against recurring templates (60%+ confidence)
- Auto-categorize based on merchant patterns
- Highlight recurring payments with confidence scores
- Auto-import approved recurring transactions

### 3. **Visual Indicators**
- **Yellow rows**: Matched to recurring template
- **Green rows**: Auto-categorized by merchant rules
- **Warning badge**: Shows template name and confidence
- **Lightning badge**: Will auto-import
- **Recurring icon**: Marked as recurring expense

---

## How to Use

### Setting Up Recurring Templates

1. **Navigate to Expenses Page**
   - Click "Manage Recurring Payments" button
   - Or select "Recurring Templates" tab

2. **Add New Template**
   ```
   Example: Van Finance
   - Name: Van Finance
   - Category: Vehicle Costs
   - Expected Amount: £299.99
   - Tolerance: £5.00
   - Frequency: Monthly
   - Day of Month: 15
   - Merchant Pattern: SANTANDER VAN
   - Auto-Import: ✓ (if you want automatic import)
   ```

3. **Common Templates to Create**
   - Van Finance/Loan
   - Van Insurance
   - Phone Bill
   - Internet/Broadband
   - Fuel Cards
   - Tool Subscriptions
   - Accountant Fees

### Importing Bank Statements

1. **Download Statement from RBS**
   - Log into RBS online banking
   - Go to Statements → Export as CSV
   - Select date range (e.g., last month)

2. **Import to TVS Wages**
   - Click "Import Bank Statement"
   - Select downloaded CSV file
   - Click "Parse Statement"

3. **Review Transactions**
   - **Yellow rows**: Matched to templates (check confidence)
   - **Green rows**: Auto-categorized
   - **White rows**: Need manual categorization
   - Adjust categories if needed
   - Check/uncheck transactions to import

4. **Import Selected**
   - Click "Import Selected"
   - System shows: "Successfully imported X expenses! (Y auto-imported from recurring templates)"

### Managing Templates

**Edit Template:**
- Click pencil icon
- Update any field
- Save changes

**Activate/Deactivate:**
- Click pause/play icon
- Inactive templates won't match transactions

**Delete Template:**
- Click trash icon
- Confirm deletion

---

## Smart Matching Algorithm

The system uses a confidence-based scoring system:

### Scoring Breakdown
- **Merchant Match** (50 points): Pattern found in description
- **Partial Match** (25 points): Some words match
- **Amount Match** (30 points): Within tolerance range
- **Exact Amount** (+10 points): Exact match bonus
- **Date Proximity** (20 points): Within 3 days of expected
- **Date Near** (10 points): Within 7 days of expected

### Confidence Threshold
- **60%+ required** for automatic matching
- **80%+ recommended** for auto-import

### Example Match
```
Transaction: "SANTANDER VAN FINANCE DD" £299.99 on 16/12/2024
Template: "Van Finance" - "SANTANDER VAN" £299.99 expected 15th

Score:
+ 50 (merchant match: "SANTANDER VAN")
+ 40 (exact amount: £299.99)
+ 20 (date: 1 day difference)
= 110/120 = 92% confidence ✓ MATCHED
```

---

## Database Schema

### `recurring_templates` Table
```sql
CREATE TABLE recurring_templates (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    expected_amount REAL NOT NULL,
    frequency TEXT NOT NULL,
    merchant_pattern TEXT NOT NULL,
    day_of_month INTEGER,
    is_active BOOLEAN DEFAULT 1,
    tolerance_amount REAL DEFAULT 5.0,
    auto_import BOOLEAN DEFAULT 0,
    next_expected_date TEXT,
    last_matched_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES expense_categories(id)
);
```

### Enhanced `expenses` Table
Existing table now properly tracks:
- `is_recurring`: Boolean flag
- `recurring_frequency`: weekly/monthly/quarterly/annually

---

## API Endpoints

### Recurring Templates
- `GET /api/recurring/templates` - List all templates
- `GET /api/recurring/templates/<id>` - Get single template
- `POST /api/recurring/templates/add` - Create template
- `PUT /api/recurring/templates/update/<id>` - Update template
- `DELETE /api/recurring/templates/delete/<id>` - Delete template
- `GET /api/recurring/templates/due` - Get templates due this week
- `GET /api/recurring/templates/statistics` - Get summary stats
- `POST /api/recurring/match-transaction` - Test transaction matching
- `POST /api/recurring/create-from-template` - Create expense from template

### Bank Import (Enhanced)
- `POST /api/bank-import/parse` - Parse CSV with template matching
- `POST /api/bank-import/import` - Import with recurring tracking

---

## Benefits

### Time Savings
- **Before**: Manually enter 20+ recurring expenses monthly
- **After**: Auto-import with one click, review in seconds

### Accuracy
- Consistent categorization
- No missed recurring payments
- Automatic amount variance detection

### HMRC Compliance
- Complete audit trail
- Proper categorization
- Tax year tracking maintained

### Financial Insights
- Track monthly recurring costs
- Identify payment patterns
- Budget planning support

---

## Best Practices

### Template Setup
1. **Start with high-frequency payments** (monthly bills)
2. **Use specific merchant patterns** (avoid generic terms)
3. **Set realistic tolerances** (£5 for most, £10-20 for variable costs)
4. **Enable auto-import carefully** (only for 100% reliable payments)

### Bank Import Workflow
1. **Import monthly** (after statement available)
2. **Review yellow rows first** (recurring matches)
3. **Categorize white rows** (one-time expenses)
4. **Update templates** if patterns change

### Maintenance
1. **Review templates quarterly**
2. **Deactivate unused templates**
3. **Update amounts** when prices change
4. **Check match confidence** regularly

---

## Troubleshooting

### Template Not Matching

**Problem**: Transaction not matching expected template

**Solutions**:
1. Check merchant pattern is in transaction description
2. Verify amount is within tolerance
3. Check template is active
4. Review confidence threshold (needs 60%+)

### Wrong Category

**Problem**: Transaction categorized incorrectly

**Solutions**:
1. Update template category
2. Adjust merchant pattern to be more specific
3. Check for conflicting templates

### Auto-Import Issues

**Problem**: Auto-import not working

**Solutions**:
1. Verify auto-import checkbox is enabled
2. Check template is active
3. Ensure confidence score is high enough
4. Review last_matched_date for duplicates

---

## Example Templates

### Van Finance
```
Name: Van Finance
Category: Vehicle Costs
Amount: £299.99
Tolerance: £5.00
Frequency: Monthly
Day: 15
Pattern: SANTANDER VAN
Auto-Import: Yes
```

### Phone Bill
```
Name: Mobile Phone
Category: Admin Costs
Amount: £35.00
Tolerance: £10.00
Frequency: Monthly
Day: 1
Pattern: EE MOBILE
Auto-Import: Yes
```

### Van Insurance
```
Name: Van Insurance
Category: Vehicle Costs
Amount: £89.99
Tolerance: £5.00
Frequency: Monthly
Day: 20
Pattern: INSURANCE VAN
Auto-Import: Yes
```

### Fuel Card
```
Name: Fuel Card
Category: Fuel
Amount: £200.00
Tolerance: £100.00
Frequency: Weekly
Pattern: SHELL FUEL CARD
Auto-Import: No (variable amount)
```

---

## Future Enhancements

Potential improvements for future versions:

1. **Pattern Learning**: AI-based pattern detection from history
2. **Duplicate Detection**: Prevent importing same transaction twice
3. **Multi-Bank Support**: Barclays, Lloyds, etc. CSV formats
4. **Scheduled Reminders**: Alert when recurring payment missing
5. **Budget Tracking**: Compare actual vs expected recurring costs
6. **Bulk Template Import**: CSV import for multiple templates
7. **Template Sharing**: Export/import template sets
8. **Mobile App**: Camera-based receipt capture integration

---

## Files Modified/Created

### Backend
- `app/models/recurring_template.py` - Template model with matching logic
- `app/routes/api_recurring.py` - Template management API
- `app/models/bank_statement.py` - Enhanced with template matching
- `app/routes/api_bank_import.py` - Enhanced import with recurring tracking
- `app/database.py` - Added recurring_templates table

### Frontend
- `templates/expenses.html` - Added recurring templates tab and modal
- `static/js/recurring-templates.js` - Template management UI
- `static/js/expenses.js` - Enhanced bank import display

### Configuration
- `app/__init__.py` - Registered recurring API blueprint

---

## Support

For issues or questions:
1. Check this guide first
2. Review API documentation
3. Check browser console for errors
4. Verify database schema is up to date

---

**Last Updated**: December 4, 2024
**Version**: 1.0.0
