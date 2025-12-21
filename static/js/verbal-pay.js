/**
 * Verbal Pay Confirmation functionality
 * Allows recording verbal pay amounts from boss and comparing with actual payslips
 */

// Test that this script is loading
console.log('🟢 verbal-pay.js loaded successfully');

// Show verbal pay modal
function showVerbalPayModal() {
    const now = new Date();
    
    // Find the previous Saturday (week-ending date)
    // Tuesday = 2, so we need to go back 3 days to get to Saturday
    const dayOfWeek = now.getDay(); // 0 = Sunday, 1 = Monday, 2 = Tuesday, 6 = Saturday
    let daysToSubtract;
    
    if (dayOfWeek === 0) { // Sunday
        daysToSubtract = 1; // Yesterday was Saturday
    } else if (dayOfWeek === 6) { // Saturday
        daysToSubtract = 7; // Last Saturday
    } else { // Monday (1) through Friday (5)
        daysToSubtract = dayOfWeek + 1; // Monday=2 days back, Tuesday=3 days back, etc.
    }
    
    const previousSaturday = new Date(now);
    previousSaturday.setDate(now.getDate() - daysToSubtract);
    
    // Format as DD/MM/YYYY for display
    const day = String(previousSaturday.getDate()).padStart(2, '0');
    const month = String(previousSaturday.getMonth() + 1).padStart(2, '0');
    const year = previousSaturday.getFullYear();
    const weekEndingDate = `${day}/${month}/${year}`;
    
    // Calculate week number based on company year (starts 09/03/2025)
    // Week 1 ending: 22/03/2025 (Saturday)
    // Week 33 ending: 01/11/2025 (verified)
    const firstSaturday = new Date(2025, 2, 22); // 22/03/2025 (month is 0-indexed)
    
    let weekNumber = 1;
    if (previousSaturday >= firstSaturday) {
        // Calculate weeks since first Saturday (inclusive)
        const daysDiff = Math.floor((previousSaturday - firstSaturday) / (1000 * 60 * 60 * 24));
        weekNumber = Math.floor(daysDiff / 7) + 1;
    } else {
        // Before company year start - shouldn't happen but handle it
        weekNumber = 1;
    }
    
    document.getElementById('verbalWeekNumber').value = weekNumber;
    document.getElementById('verbalWeekNumber').placeholder = 'e.g., 34';
    document.getElementById('verbalYear').value = 2025; // Company year
    document.getElementById('verbalAmount').value = '';
    document.getElementById('verbalNotes').value = `Week ending ${weekEndingDate}`;
    
    const modal = new bootstrap.Modal(document.getElementById('verbalPayModal'));
    modal.show();
}

// Save verbal confirmation
async function saveVerbalConfirmation() {
    console.log('🔵 saveVerbalConfirmation() called');
    const weekNumber = parseInt(document.getElementById('verbalWeekNumber').value);
    const year = parseInt(document.getElementById('verbalYear').value);
    
    // Clean the amount value by removing commas and other formatting
    const amountValue = document.getElementById('verbalAmount').value;
    const cleanAmount = amountValue.toString().replace(/,/g, '').replace(/[^\d.-]/g, '');
    const verbalAmount = parseFloat(cleanAmount);
    
    const notes = document.getElementById('verbalNotes').value;
    
    // Debug logging
    console.log('Form values:', { weekNumber, year, verbalAmount, notes });
    console.log('Validation check:', { 
        weekNumberValid: !isNaN(weekNumber) && weekNumber > 0,
        yearValid: !isNaN(year) && year > 0,
        amountValid: !isNaN(verbalAmount) && verbalAmount > 0
    });
    
    if (isNaN(weekNumber) || weekNumber <= 0 || isNaN(year) || year <= 0 || isNaN(verbalAmount) || verbalAmount <= 0) {
        showError('Please fill in all required fields');
        return;
    }
    
    if (verbalAmount <= 0) {
        showError('Amount must be greater than zero');
        return;
    }
    
    try {
        const response = await fetch('/api/verbal-pay/confirmations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                week_number: weekNumber,
                year: year,
                verbal_amount: verbalAmount,
                notes: notes
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess(`Verbal confirmation saved for Week ${weekNumber}, ${year}`);
            bootstrap.Modal.getInstance(document.getElementById('verbalPayModal')).hide();
            
            // Reload payslips to show match status
            if (typeof loadPayslips === 'function') {
                loadPayslips();
            }
        } else {
            showError(data.error || 'Failed to save confirmation');
        }
    } catch (error) {
        console.error('Error saving verbal confirmation:', error);
        showError('Failed to save confirmation');
    }
}

// Check if payslip matches verbal confirmation
async function checkVerbalMatch(payslipId, weekString, grossPay, netPay) {
    // Parse week string (e.g., "Week 46, 2025")
    const match = weekString.match(/Week (\d+), (\d{4})/);
    if (!match) return null;
    
    const weekNumber = parseInt(match[1]);
    const year = parseInt(match[2]);
    
    try {
        const response = await fetch(`/api/verbal-pay/confirmations/week/${weekNumber}/year/${year}`);
        const data = await response.json();
        
        if (data.success && data.confirmation) {
            const verbalAmount = data.confirmation.verbal_amount;
            
            // Standard weekly deductions: £11 company margin + £4 PDA licence = £15
            const STANDARD_DEDUCTIONS = 15.00;
            
            // Subtract deductions from verbal amount to get expected gross pay
            const expectedGross = verbalAmount - STANDARD_DEDUCTIONS;
            
            // Compare expected gross with actual payslip gross pay
            const matched = Math.abs(expectedGross - grossPay) < 0.01;
            const deductions = grossPay - netPay;
            
            // Update match status in database
            await fetch('/api/verbal-pay/match-payslip', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    week_number: weekNumber,
                    year: year,
                    payslip_id: payslipId,
                    gross_pay: grossPay,
                    net_pay: netPay
                })
            });
            
            return {
                hasConfirmation: true,
                verbalAmount: verbalAmount,
                expectedGross: expectedGross,
                grossPay: grossPay,
                netPay: netPay,
                deductions: deductions,
                matched: matched,
                difference: grossPay - expectedGross
            };
        }
        
        return { hasConfirmation: false };
    } catch (error) {
        console.error('Error checking verbal match:', error);
        return null;
    }
}

// Add match indicator to payslip row
function addMatchIndicator(row, matchInfo) {
    if (!matchInfo || !matchInfo.hasConfirmation) {
        return;
    }
    
    const indicator = document.createElement('span');
    indicator.className = 'ms-2';
    indicator.style.cursor = 'pointer';
    indicator.title = `Verbal: £${matchInfo.verbalAmount.toFixed(2)}\nPayslip: £${matchInfo.payslipAmount.toFixed(2)}`;
    
    if (matchInfo.matched) {
        indicator.innerHTML = '<i class="bi bi-check-circle-fill text-success"></i>';
        indicator.title += '\n✓ Amounts match!';
    } else {
        indicator.innerHTML = '<i class="bi bi-exclamation-triangle-fill text-warning"></i>';
        const diff = matchInfo.difference;
        indicator.title += `\n⚠ Difference: £${Math.abs(diff).toFixed(2)} ${diff > 0 ? 'more' : 'less'}`;
    }
    
    // Find the total pay cell and add indicator
    const cells = row.querySelectorAll('td');
    if (cells.length >= 3) {
        cells[2].appendChild(indicator);
    }
}

// Show success message
function showSuccess(message) {
    // Use existing notification system if available
    if (typeof showNotification === 'function') {
        showNotification(message, 'success');
    } else {
        alert(message);
    }
}

// Show error message
function showError(message) {
    // Use existing notification system if available
    if (typeof showNotification === 'function') {
        showNotification(message, 'error');
    } else {
        alert(message);
    }
}

// Make functions globally accessible for HTML onclick handlers
window.showVerbalPayModal = showVerbalPayModal;
window.saveVerbalConfirmation = saveVerbalConfirmation;
