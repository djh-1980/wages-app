/**
 * Universal Currency Formatting Utilities
 * Ensures consistent £X.XX formatting across the entire application
 */

// Main currency formatting function
function formatCurrency(amount, options = {}) {
    const {
        showSymbol = true,
        minimumFractionDigits = 2,
        maximumFractionDigits = 2,
        locale = 'en-GB'
    } = options;
    
    // Handle null, undefined, or invalid values
    if (amount === null || amount === undefined || isNaN(amount)) {
        return showSymbol ? '£0.00' : '0.00';
    }
    
    // Convert to number if it's a string
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    
    if (isNaN(numAmount)) {
        return showSymbol ? '£0.00' : '0.00';
    }
    
    // Format the number
    const formatted = numAmount.toLocaleString(locale, {
        minimumFractionDigits,
        maximumFractionDigits
    });
    
    return showSymbol ? `£${formatted}` : formatted;
}

// Shorthand functions for common use cases
function formatPounds(amount) {
    return formatCurrency(amount);
}

function formatPoundsNoSymbol(amount) {
    return formatCurrency(amount, { showSymbol: false });
}

// Format currency for table cells with proper alignment classes
function formatCurrencyCell(amount, className = 'text-end') {
    return `<span class="${className}">${formatCurrency(amount)}</span>`;
}

// Format large amounts with K/M suffixes for dashboards
function formatCurrencyCompact(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) {
        return '£0.00';
    }
    
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    
    if (numAmount >= 1000000) {
        return `£${(numAmount / 1000000).toFixed(1)}M`;
    } else if (numAmount >= 1000) {
        return `£${(numAmount / 1000).toFixed(1)}K`;
    } else {
        return formatCurrency(numAmount);
    }
}

// Format percentage with proper decimal places
function formatPercentage(value, decimals = 1) {
    if (value === null || value === undefined || isNaN(value)) {
        return '0.0%';
    }
    
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    return `${numValue.toFixed(decimals)}%`;
}

// Update all currency elements on a page
function updateAllCurrencyElements() {
    // Update elements with data-currency attribute
    document.querySelectorAll('[data-currency]').forEach(element => {
        const amount = parseFloat(element.getAttribute('data-currency'));
        element.textContent = formatCurrency(amount);
    });
    
    // Update elements with currency class
    document.querySelectorAll('.currency').forEach(element => {
        const amount = parseFloat(element.textContent.replace(/[£,]/g, ''));
        if (!isNaN(amount)) {
            element.textContent = formatCurrency(amount);
        }
    });
}

// Initialize currency formatting when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    updateAllCurrencyElements();
});

// Export functions for use in other scripts
window.CurrencyFormatter = {
    format: formatCurrency,
    formatPounds,
    formatPoundsNoSymbol,
    formatCurrencyCell,
    formatCurrencyCompact,
    formatPercentage,
    updateAll: updateAllCurrencyElements
};
