/**
 * Verbal Pay Confirmation functionality
 * Allows recording verbal pay amounts from boss and comparing with actual payslips
 */

// Test that this script is loading
console.log('🟢 verbal-pay.js loaded successfully');

// Show verbal pay modal
async function showVerbalPayModal() {
    const now = new Date();
    
    // Get current company year from API
    let companyYear = 2025; // fallback
    let weekNumber = 1;
    
    try {
        const response = await fetch('/api/settings/company-year');
        const data = await response.json();
        if (data.success) {
            companyYear = data.current_year;
            weekNumber = data.current_week;
        }
    } catch (error) {
        console.error('Error fetching company year:', error);
    }
    
    // Find the previous Saturday (week-ending date)
    const dayOfWeek = now.getDay(); // 0 = Sunday, 1 = Monday, 2 = Tuesday, 6 = Saturday
    let daysToSubtract;
    
    if (dayOfWeek === 0) { // Sunday
        daysToSubtract = 1; // Yesterday was Saturday
    } else if (dayOfWeek === 6) { // Saturday
        daysToSubtract = 0; // Today is Saturday
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
    
    document.getElementById('verbalWeekNumber').value = weekNumber;
    document.getElementById('verbalWeekNumber').placeholder = 'e.g., 34';
    document.getElementById('verbalYear').value = companyYear;
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
        showError('Please fill in all required fields with valid positive numbers');
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
            try {
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
            } catch (matchError) {
                console.error('Error updating match status:', matchError);
            }
            
            return {
                hasConfirmation: true,
                verbalAmount: verbalAmount,
                expectedGross: expectedGross,
                payslipAmount: grossPay,
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
