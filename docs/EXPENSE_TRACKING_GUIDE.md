# Expense Tracking System - Quick Start Guide

## Overview

The TVS Wages app now includes a comprehensive expense tracking system designed for HMRC Making Tax Digital (MTD) compliance. This system helps you track all business expenses and generate tax-ready reports.

## Your Specific Setup

Based on your situation (100% business van, £50k annual income):

### Monthly Recurring Expenses to Track

1. **Van Loan**: £196/month
2. **Van Insurance**: £338/month
3. **Work Phone**: £__/month (enter your amount)
4. **Apple Insurance**: £__/month (enter your amount)
5. **Software Subscriptions**: £__/month (iCloud, etc.)
6. **Home Office**: £26/month (£6/week simplified allowance)

### One-Time/Variable Expenses

- Fuel (daily) - **Bank statement is proof!**
- Road tax (annual - £300)
- MOT (annual - £55)
- Servicing (as needed - ~£400/year)
- Repairs (as needed)
- Tyres (as needed)
- Tools and equipment
- Work boots/safety gear
- Training courses

## Getting Started

### 1. First Time Setup (5 minutes)

1. **Restart the Flask server** to initialize the database tables
2. **Navigate to Expenses** page (new menu item in navigation)
3. **Add your recurring expenses**:
   - Click "Add Expense"
   - Enter date, category, amount
   - Check "Recurring Expense"
   - Select frequency (monthly/quarterly/annually)
   - Save

### 2. Set Up Your Recurring Expenses

Add these one-time, then they'll remind you monthly:

```
Van Loan
- Date: 01/12/2024 (or your payment date)
- Category: Vehicle Costs
- Amount: 196
- Description: Van loan payment
- Recurring: Yes (Monthly)

Van Insurance
- Date: 01/12/2024
- Category: Vehicle Costs
- Amount: 338
- Description: Van insurance
- Recurring: Yes (Monthly)

Work Phone
- Date: 01/12/2024
- Category: Admin Costs
- Amount: [your amount]
- Description: Work phone contract
- Recurring: Yes (Monthly)

Apple Insurance
- Date: 01/12/2024
- Category: Admin Costs
- Amount: [your amount]
- Description: AppleCare+
- Recurring: Yes (Monthly)
```

### 3. Daily Workflow

**After each work day** (takes 2 minutes):
1. Go to Run Sheets page
2. Enter mileage and fuel (as you already do)
3. If you bought anything else (tools, boots, etc.):
   - Go to Expenses page
   - Click "Add Expense"
   - Enter details
   - Done!

### 4. Monthly Workflow (1st of month)

The system will remind you about recurring expenses. Simply:
1. Check they've been paid
2. Click to confirm (or edit if amount changed)

## HMRC Categories Explained

The system uses official HMRC Self-Assessment categories:

| Category | Box | What Goes Here |
|----------|-----|----------------|
| **Vehicle Costs** | 20 | Van loan, insurance, tax, MOT, repairs, tyres, fuel |
| **Travel Costs** | 21 | Parking, tolls (not fuel - that's in Vehicle) |
| **Admin Costs** | 23 | Phone, internet, stationery |
| **Professional Fees** | 27 | Accountant, subscriptions |
| **Other Expenses** | 29 | Tools, work boots, training, software |

## Tax Year Information

- **Tax year runs**: April 6 - April 5
- **Current tax year**: 2024/2025 (ends April 5, 2025)
- **Next tax year**: 2025/2026 (starts April 6, 2025)

The system automatically calculates which tax year each expense belongs to.

## Backfilling This Year's Expenses

Since we're near the end of the 2024/25 tax year, you should add:

### December 2024 - April 2025

1. **Van loan**: 5 months × £196 = £980
2. **Van insurance**: 5 months × £338 = £1,690
3. **Fuel**: Estimate from your records
4. **Any other expenses**: Tools, repairs, etc.

**How to backfill:**
- Add each month separately
- Use 1st of each month as the date
- Mark as recurring for future months

## Reports and Exports

### View Summary
- Filter by tax year to see totals
- See breakdown by HMRC category
- Track monthly spending

### MTD Export (Coming Soon)
- One-click export for your accountant
- HMRC-ready format
- Includes all income and expenses

## Expected Tax Savings

Based on your £50k income and estimated £12-13k expenses:

**Without tracking everything:**
- Taxable profit: ~£46,500
- Tax bill: ~£11,500

**With full expense tracking:**
- Taxable profit: ~£37,000
- Tax bill: ~£8,500
- **You save: £3,000/year!**

## Tips for Success

1. **Enter expenses immediately** - Don't wait until month-end
2. **Take photos of receipts** - Store in your phone/cloud
3. **Be consistent** - Set a reminder to check monthly
4. **Ask your accountant** - If unsure about an expense
5. **Keep it simple** - The system does the hard work

## Common Questions

**Q: What if I forget to enter an expense?**
A: Just add it later with the correct date. The system will put it in the right tax year.

**Q: Can I edit or delete expenses?**
A: Yes! Click the edit or delete button next to any expense.

**Q: What about VAT?**
A: There's a VAT field if you're VAT registered. Leave it at 0 if not.

**Q: How do I prove expenses to HMRC?**
A: Keep receipts for 5 years. Bank statements work for recurring payments.

**Q: What if my recurring amount changes?**
A: Edit the expense for that month with the new amount.

## Next Steps

1. ✅ Restart Flask server
2. ✅ Add your recurring expenses
3. ✅ Backfill December-April expenses
4. ✅ Set monthly reminder to confirm recurring expenses
5. ✅ Start tracking all business expenses going forward

## Support

If you need help:
1. Check this guide
2. Ask your accountant about specific expenses
3. Refer to HMRC self-employment guidance

---

**Remember**: You're potentially missing £2,000-4,000 in legitimate tax deductions every year by not tracking properly. This system makes it effortless!
