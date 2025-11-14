# Weekly Summary Page Fix - Production Issue

## Problem
The Weekly Summary page was not working on the live site (tvs.daniel-hanson.co.uk) but worked locally. The issue was caused by the `CurrencyFormatter` JavaScript object not being available when the page tried to initialize.

## Root Cause
1. The Weekly Summary tab is set as the active/default tab in `reports.html`
2. When the page loads, it immediately tries to call `loadWeeklySummary()` 
3. On production, due to network latency or caching, the `currency-formatter.js` script may not be fully loaded yet
4. This causes a `CurrencyFormatter is not defined` error, breaking the page

## Solution Implemented

### 1. Defensive Loading Check
Added a check to ensure `CurrencyFormatter` is loaded before initializing:

```javascript
// Load if it's the active tab on page load
if (weeklyTab.classList.contains('active')) {
    // Ensure CurrencyFormatter is loaded before initializing
    if (typeof CurrencyFormatter !== 'undefined') {
        currentWeek();
    } else {
        // Wait for CurrencyFormatter to be available
        const checkFormatter = setInterval(() => {
            if (typeof CurrencyFormatter !== 'undefined') {
                clearInterval(checkFormatter);
                currentWeek();
            }
        }, 100);
        // Timeout after 5 seconds
        setTimeout(() => clearInterval(checkFormatter), 5000);
    }
}
```

### 2. Fallback Currency Formatter
Added a local `formatCurrency` function inside `displayWeeklySummary()` that:
- Uses `CurrencyFormatter.format()` if available
- Falls back to basic `£X.XX` formatting if not

```javascript
const formatCurrency = (value) => {
    if (typeof CurrencyFormatter !== 'undefined') {
        return CurrencyFormatter.format(value);
    }
    // Fallback formatting
    return '£' + (value || 0).toFixed(2);
};
```

### 3. Updated All Currency Calls
Replaced all `CurrencyFormatter.format()` calls in `displayWeeklySummary()` with the local `formatCurrency()` function.

## Files Modified
- `static/js/weekly-summary.js` - **NEW FILE** - Dedicated module for weekly summary functionality
- `static/js/reports.js` - Removed weekly summary code (moved to dedicated module)
- `templates/reports.html` - Added weekly-summary.js script reference with cache busting

## Testing
1. **Local Testing**: Verify the page still works locally
2. **Production Testing**: After deployment, verify the Weekly Summary tab loads correctly on tvs.daniel-hanson.co.uk

## Deployment Steps

### Option 1: Git Push (Recommended)
```bash
cd /Users/danielhanson/CascadeProjects/Wages-App
git push origin main
```

Then on the server:
```bash
cd /var/www/tvs-wages
git pull origin main
sudo systemctl restart tvs-wages
```

### Option 2: Direct File Upload
If you need to deploy just this file:
```bash
scp static/js/reports.js user@server:/var/www/tvs-wages/static/js/
```

Then restart the service:
```bash
sudo systemctl restart tvs-wages
```

## Verification
After deployment, test the following:
1. Navigate to https://tvs.daniel-hanson.co.uk/reports
2. Verify the Weekly Summary tab loads without errors
3. Check browser console (F12) for any JavaScript errors
4. Verify all currency values display correctly (£X.XX format)
5. Test navigation between weeks using Previous/Next buttons
6. Test "Jump to Current Week" button

## Additional Notes
- The fix is backward compatible and won't affect local development
- The 5-second timeout ensures the page doesn't hang if there's a real loading issue
- The fallback formatter ensures currency values always display, even if the main formatter fails
- This pattern can be applied to other pages if similar issues occur

## Architecture Improvement
Following your site's best practices, the weekly summary functionality has been extracted into its own dedicated module (`weekly-summary.js`), similar to how `runsheets.js`, `paypoint.js`, and `wages.js` are organized. This provides:

- **Better code organization** - Each feature has its own file
- **Easier maintenance** - Changes to weekly summary don't affect other reports
- **Clearer dependencies** - Script loading order is explicit in the template
- **Improved caching** - Individual modules can be cached separately
- **Follows site patterns** - Consistent with existing architecture

## Commits
```
commit a164ac0 - Fix Weekly Summary page loading issue on production
commit 8591949 - Refactor: Extract weekly summary to dedicated module
```
