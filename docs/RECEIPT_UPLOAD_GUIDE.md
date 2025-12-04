# Receipt Upload System - Quick Guide

## ✅ What's Been Added

Your expense tracking system now includes **automatic receipt scanning and storage**!

## 📸 How It Works

### When Adding an Expense:

1. **Take Photo** - Snap a photo of your receipt with your phone
2. **Upload** - Click "Choose File" in the expense form
3. **Auto-Organized** - System automatically organizes by tax year and month
4. **View Anytime** - Click the receipt icon to view it

### File Organization:

```
data/receipts/
  2024-25/
    12-December/
      04-12-2024_Fuel_65.50.jpg
      15-12-2024_Vehicle_Costs_338.00.pdf
      20-12-2024_Tools_45.99.jpg
    01-January/
      05-01-2025_Fuel_70.00.jpg
  2025-26/
    04-April/
      ...
```

## 📱 Supported File Types

- **Photos**: JPG, JPEG, PNG, GIF
- **Documents**: PDF
- **Max size**: 10MB per file

## 💡 Best Practices

### What to Photograph:

✅ **DO photograph:**
- One-off purchases (tools, boots, repairs)
- Large expenses (over £50)
- Cash purchases
- Anything unusual HMRC might question

❌ **DON'T need to photograph:**
- Fuel (bank statement is proof)
- Recurring payments (van loan, insurance)
- Direct debits (bank statement is proof)
- Regular card payments at same places

### Photography Tips:

1. **Good lighting** - Make sure text is readable
2. **Flat surface** - Lay receipt flat, no wrinkles
3. **Full receipt** - Capture entire receipt including:
   - Date
   - Store name
   - Amount
   - Items purchased
4. **Clear focus** - Make sure it's not blurry

## 🔍 Viewing Receipts

### In Expense List:
- Look for the 📄 icon in the "Receipt" column
- Click to view full-size image/PDF
- Opens in new tab

### No Receipt Icon?
- Means no receipt uploaded (that's fine!)
- Bank statement is valid proof for most expenses
- Can add receipt later by editing expense

## 📊 Your Workflow

### Daily (30 seconds):
1. Buy something for work (tools, fuel, etc.)
2. Take photo of receipt
3. Add expense in app
4. Upload photo
5. Done!

### Weekly (2 minutes):
- Review expenses
- Check all receipts uploaded
- Add any missed expenses

### Monthly (5 minutes):
- Confirm recurring expenses
- Review all expenses for month
- Check receipt storage

## 🎯 Real Example

**Scenario**: You buy new work boots for £80

**Old way:**
1. Buy boots ✅
2. Get receipt ✅
3. Shove in wallet ❌
4. Lose receipt ❌
5. Can't claim £80 ❌
6. Pay £16-32 extra tax ❌

**New way:**
1. Buy boots ✅
2. Take photo of receipt ✅
3. Open app ✅
4. Add expense: £80, "Work boots", upload photo ✅
5. Receipt stored forever ✅
6. Claim full £80 ✅
7. Save £16-32 in tax ✅

## 🔐 Security & Storage

- **Secure storage**: Files stored in your data folder
- **Organized**: Automatic tax year/month organization
- **Backed up**: Include receipts in your backups
- **Private**: Only you can access via the app
- **HMRC compliant**: Photos are valid proof

## ❓ Common Questions

**Q: Do I need receipts for everything?**
A: No! Bank statements are valid for most expenses. Only photograph:
- Cash purchases
- One-off large expenses
- Anything unusual

**Q: What if I forget to photograph a receipt?**
A: Add the expense anyway. Note "Bank statement" in description. You can add photo later if you find it.

**Q: Can I upload old receipts?**
A: Yes! Edit the expense and upload the photo. System will organize it correctly.

**Q: What if receipt is faded/damaged?**
A: Photograph it anyway. Even a faded receipt is better than nothing. Bank statement can supplement.

**Q: How long do I keep receipts?**
A: HMRC requires 5 years. The app stores them forever (or until you delete).

**Q: Can I delete receipts?**
A: Yes, but don't! Storage is cheap. Keep everything for HMRC compliance.

## 💰 Tax Savings Reminder

**With proper receipt storage:**
- Claim ALL legitimate expenses
- No lost receipts = no lost deductions
- Estimated savings: **£2,000-4,000/year**

**Your specific situation:**
- Income: £50,000
- Expenses: £12,500 (with proper tracking)
- Tax saved: **£3,000-3,500/year**

## 🚀 Next Steps

1. ✅ Restart Flask server (to enable receipt upload)
2. ✅ Add an expense with a receipt
3. ✅ Test viewing the receipt
4. ✅ Start photographing all receipts going forward

---

**Remember**: A 10-second photo can save you £20-40 in tax. Always photograph receipts for non-routine expenses!
