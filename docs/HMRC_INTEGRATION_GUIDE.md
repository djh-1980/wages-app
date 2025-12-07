# HMRC Integration Guide

## 📋 Overview

Your TVS Wages app **does NOT directly submit to HMRC**, but it **prepares all the data** in the correct format for:
1. Your accountant to submit
2. You to manually enter into HMRC self-assessment
3. Making Tax Digital (MTD) compliance

---

## 🔄 How It Works

### Current System (What You Have)

```
Your Business Activity
        ↓
TVS Wages App (tracks everything)
        ↓
MTD-Ready Export
        ↓
Your Accountant → HMRC
   OR
You → HMRC Self-Assessment Online
```

### What the App Does

✅ **Tracks all income** (from payslips)
✅ **Tracks all expenses** (categorized by HMRC boxes)
✅ **Calculates tax year** (April 6 - April 5)
✅ **Groups by HMRC categories** (Boxes 20-29)
✅ **Generates MTD-ready reports**
✅ **Calculates net profit**
✅ **Stores receipts** (digital proof)

### What the App DOESN'T Do

❌ Submit directly to HMRC (requires OAuth, API keys, etc.)
❌ Calculate tax owed (your accountant does this)
❌ File your self-assessment (you or accountant does this)

---

## 📊 HMRC Self-Assessment Boxes

Your expenses are automatically categorized into HMRC boxes:

| Box | Category | Your Expenses |
|-----|----------|---------------|
| **Box 20** | Vehicle Costs | Van loan, insurance, tax, MOT, repairs, fuel |
| **Box 21** | Travel Costs | Parking, tolls, congestion charges |
| **Box 22** | Premises Costs | Home office, server electricity |
| **Box 23** | Admin Costs | Phone, internet, stationery, software |
| **Box 24** | Advertising | Marketing (if any) |
| **Box 25** | Interest | Bank/loan interest |
| **Box 26** | Financial Charges | Bank charges, card fees |
| **Box 27** | Professional Fees | Accountant, subscriptions |
| **Box 28** | Depreciation | Equipment depreciation |
| **Box 29** | Other Expenses | Tools, work boots, training |

---

## 💻 Getting Your Data for HMRC

### Method 1: MTD Export (Recommended)

**In the app:**
1. Go to **Expenses** page
2. Click **"Export for Accountant"** (or similar button)
3. Select tax year (e.g., 2025/2026)
4. Download JSON/CSV export

**The export includes:**
- Total income (from payslips)
- Total expenses (by HMRC box)
- Net profit
- Detailed breakdown
- All dates and descriptions

**Give this to your accountant** - they'll use it to complete your self-assessment.

### Method 2: Manual Entry (DIY)

**In the app:**
1. Go to **Expenses** → **Summary**
2. Filter by tax year (e.g., 2025/2026)
3. View totals by HMRC box

**On HMRC website:**
1. Log into your Self-Assessment account
2. Go to "Self-employment (full)" section
3. Enter each box total:
   - Box 20: £X,XXX (Vehicle costs)
   - Box 21: £XXX (Travel costs)
   - Box 22: £XXX (Premises costs)
   - etc.

### Method 3: CSV Export

**In the app:**
1. Go to **Reports** page
2. Select **"Expense Report"**
3. Choose tax year
4. Download CSV

**Use for:**
- Importing into accounting software (Xero, QuickBooks, etc.)
- Giving to your accountant
- Your own records

---

## 🎯 Making Tax Digital (MTD) Compliance

### What is MTD?

Making Tax Digital is HMRC's initiative to digitize tax records. From April 2026, self-employed people earning over £50k MUST use MTD-compatible software.

### Is Your App MTD-Ready?

**Yes!** Your app is MTD-ready because it:

✅ **Digital record keeping** - All data stored electronically
✅ **HMRC category mapping** - Expenses mapped to correct boxes
✅ **Tax year calculations** - Automatic tax year assignment
✅ **Audit trail** - All transactions dated and categorized
✅ **Receipt storage** - Digital receipts linked to expenses
✅ **Export capability** - Data can be exported in standard formats

### What's Missing for Full MTD?

To submit **directly** to HMRC (not required yet), you'd need:

❌ HMRC OAuth integration
❌ MTD API credentials
❌ Quarterly submission workflow
❌ VAT integration (if VAT registered)

**But you don't need this yet!** Your accountant can handle submissions, or you can manually enter the totals.

---

## 📅 Annual Tax Workflow

### Throughout the Year (Ongoing)

1. **Track everything** in TVS Wages app
   - Add expenses as they happen
   - Import bank statements monthly
   - Upload receipts

2. **Monthly review** (1st of month)
   - Check recurring expenses
   - Verify categorization
   - Add any missing expenses

### End of Tax Year (April 5th)

1. **Final check**
   - Review all expenses for the year
   - Ensure nothing is missing
   - Check categorization

2. **Generate reports**
   - Export MTD data
   - Download expense summary
   - Print/save receipts

3. **Give to accountant**
   - MTD export file
   - Receipt folder
   - Any notes/questions

### Self-Assessment Deadline (January 31st)

**If using accountant:**
- They submit on your behalf
- You just pay the tax bill

**If doing it yourself:**
1. Log into HMRC Self-Assessment
2. Enter income (from payslips total)
3. Enter expenses (from app summary)
4. Submit online
5. Pay tax owed

---

## 💰 What HMRC Sees

When you submit your self-assessment, HMRC sees:

```
Income: £50,000 (from your payslips)

Expenses:
- Box 20 (Vehicle): £8,500
- Box 22 (Premises): £924
- Box 23 (Admin): £600
- Box 29 (Other): £500
Total Expenses: £10,524

Net Profit: £39,476
Tax Owed: £X,XXX (HMRC calculates)
```

**HMRC does NOT see:**
- Individual transactions
- Merchant names
- Specific dates

**But you MUST keep for 5 years:**
- All receipts
- Bank statements
- Expense records (your app has these!)

---

## 🔍 HMRC Audit/Investigation

If HMRC investigates (rare, but possible):

### What They Ask For

1. **Proof of income** - Payslips, invoices (you have these)
2. **Proof of expenses** - Receipts, bank statements (you have these)
3. **Business records** - Expense log (your app is this!)

### How Your App Helps

✅ **Complete audit trail** - Every expense dated and categorized
✅ **Digital receipts** - Photos stored with expenses
✅ **Bank statement imports** - Proof of payment
✅ **Categorization logic** - Clear business purpose
✅ **Export capability** - Can provide data in any format

### What You Need to Do

1. **Keep the database** - Don't delete old data
2. **Keep receipts** - Physical or digital for 5 years
3. **Keep bank statements** - Valid proof for most expenses
4. **Be honest** - Only claim legitimate business expenses

---

## 📱 Current Features for HMRC Compliance

### ✅ What You Have Now

1. **Income Tracking**
   - All payslips recorded
   - Tax year calculation
   - Total income per year

2. **Expense Tracking**
   - HMRC category mapping
   - Automatic categorization
   - Recurring expense tracking
   - Bank statement import

3. **Receipt Management**
   - Upload receipts
   - Link to expenses
   - Digital storage

4. **Reporting**
   - Summary by HMRC box
   - Tax year filtering
   - MTD export format

5. **Audit Trail**
   - All transactions dated
   - Edit history (if implemented)
   - Complete records

### 🚀 Future Enhancements (Optional)

1. **Direct HMRC API Integration**
   - OAuth authentication
   - Quarterly submissions
   - Real-time validation

2. **VAT Integration**
   - VAT tracking
   - VAT returns
   - MTD VAT compliance

3. **Accountant Portal**
   - Share access with accountant
   - Real-time collaboration
   - Approval workflow

---

## 🎓 How to Use for Tax Filing

### Option 1: Give to Accountant (Easiest)

**Steps:**
1. Export MTD data for tax year
2. Email to accountant
3. They file on your behalf
4. Done!

**Cost:** £200-500/year
**Benefit:** No stress, expert advice

### Option 2: DIY Self-Assessment

**Steps:**
1. Get summary from app (by HMRC box)
2. Log into HMRC Self-Assessment
3. Enter totals manually
4. Submit online

**Cost:** Free
**Benefit:** Save accountant fees

**Time:** 1-2 hours per year

---

## 📊 Example Tax Calculation

### Your Situation (2025/2026)

**Income:**
- Payslips total: £50,000

**Expenses (from app):**
- Box 20 (Vehicle): £8,500
- Box 22 (Home Office + Server): £924
- Box 23 (Admin): £600
- Box 29 (Tools, boots): £500
- **Total: £10,524**

**Net Profit:**
- £50,000 - £10,524 = **£39,476**

**Tax Calculation:**
- Personal Allowance: £12,570 (tax-free)
- Taxable: £39,476 - £12,570 = £26,906
- Tax at 20%: £5,381
- National Insurance: ~£3,200
- **Total Tax: ~£8,581**

**Without expense tracking:**
- Tax on £50,000: ~£11,500
- **You save: £2,919!**

---

## 🛡️ Staying HMRC Compliant

### Do's ✅

- ✅ Track ALL business expenses
- ✅ Keep receipts for 5 years
- ✅ Only claim legitimate business expenses
- ✅ Be consistent with categorization
- ✅ Keep digital and physical records
- ✅ File on time (Jan 31st deadline)

### Don'ts ❌

- ❌ Claim personal expenses
- ❌ Exaggerate amounts
- ❌ Claim without proof
- ❌ Mix business and personal
- ❌ Delete old records
- ❌ Miss the deadline

---

## 🔧 Technical Details

### Data Export Format

**JSON Export (MTD-ready):**
```json
{
  "tax_year": "2025/2026",
  "total_income": 50000.00,
  "total_expenses": 10524.00,
  "net_profit": 39476.00,
  "expense_breakdown": [
    {
      "hmrc_box": "Vehicle costs",
      "hmrc_box_number": 20,
      "total_amount": 8500.00,
      "transaction_count": 145
    },
    ...
  ]
}
```

**CSV Export:**
```csv
Date,Category,HMRC Box,Amount,Description,Receipt
06/04/2025,Vehicle Costs,20,196.00,Van loan,
07/04/2025,Fuel,20,45.50,Shell fuel,receipt_001.jpg
...
```

### API Endpoints

- `/api/expenses/summary` - Get summary by HMRC box
- `/api/expenses/mtd-export` - Get MTD-formatted data
- `/api/expenses/list` - Get all expenses (filtered)

---

## 📞 Support & Resources

### HMRC Resources

- **Self-Assessment:** https://www.gov.uk/self-assessment-tax-returns
- **MTD Information:** https://www.gov.uk/making-tax-digital
- **Allowable Expenses:** https://www.gov.uk/expenses-if-youre-self-employed

### Your App

- **Expense Guide:** `docs/EXPENSE_CATEGORIES_GUIDE.md`
- **Tracking Guide:** `docs/EXPENSE_TRACKING_GUIDE.md`
- **Home Office:** `docs/HOME_OFFICE_SERVER_CALCULATION.md`

### Getting Help

1. **Your accountant** - Best for tax advice
2. **HMRC helpline** - 0300 200 3310
3. **App documentation** - Check the docs folder

---

## ✅ Summary

### What Your App Does

✅ Tracks all income and expenses
✅ Categorizes by HMRC boxes
✅ Calculates tax years
✅ Stores digital receipts
✅ Generates MTD-ready exports
✅ Provides complete audit trail

### What You Need to Do

1. **Keep tracking** - Add expenses as they happen
2. **Keep receipts** - Store for 5 years
3. **Annual export** - Give to accountant or use for self-assessment
4. **File on time** - January 31st deadline

### Bottom Line

Your app **doesn't submit directly to HMRC**, but it **does all the hard work** of:
- Recording everything
- Categorizing correctly
- Calculating totals
- Providing proof

You (or your accountant) just need to **transfer the totals** to HMRC once a year.

**Result:** Maximum tax deductions, minimum effort, full HMRC compliance! 🎉

---

*Last updated: December 2025*
*Review when HMRC rules change or MTD requirements update*
