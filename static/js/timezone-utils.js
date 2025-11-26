/**
 * UK Timezone Utilities for Frontend
 * Provides consistent UK timezone handling across all JavaScript
 */

// UK timezone constant
const UK_TIMEZONE = 'Europe/London';

/**
 * Get current date/time in UK timezone
 */
function nowUK() {
    return new Date().toLocaleString("en-US", {timeZone: UK_TIMEZONE});
}

/**
 * Convert any date to UK timezone
 */
function toUKTimezone(date) {
    if (typeof date === 'string') {
        date = new Date(date);
    }
    return new Date(date.toLocaleString("en-US", {timeZone: UK_TIMEZONE}));
}

/**
 * Format date as DD/MM/YYYY in UK timezone
 */
function formatUKDate(date) {
    if (typeof date === 'string') {
        date = new Date(date);
    }
    const ukDate = toUKTimezone(date);
    const day = String(ukDate.getDate()).padStart(2, '0');
    const month = String(ukDate.getMonth() + 1).padStart(2, '0');
    const year = ukDate.getFullYear();
    return `${day}/${month}/${year}`;
}

/**
 * Format date as YYYY-MM-DD in UK timezone (for API calls)
 */
function formatUKDateISO(date) {
    if (typeof date === 'string') {
        date = new Date(date);
    }
    const ukDate = toUKTimezone(date);
    const day = String(ukDate.getDate()).padStart(2, '0');
    const month = String(ukDate.getMonth() + 1).padStart(2, '0');
    const year = ukDate.getFullYear();
    return `${year}-${month}-${day}`;
}

/**
 * Get UK week start (Sunday) for any date
 */
function getUKWeekStart(date) {
    if (typeof date === 'string') {
        date = new Date(date + 'T12:00:00');
    }
    const ukDate = toUKTimezone(date);
    
    // Find Sunday of this week
    const dayOfWeek = ukDate.getDay(); // 0 = Sunday
    const daysToSubtract = dayOfWeek;
    
    ukDate.setDate(ukDate.getDate() - daysToSubtract);
    return ukDate;
}

/**
 * Navigate weeks safely in UK timezone
 */
function navigateWeeks(currentWeekStart, weeksToAdd) {
    const date = new Date(currentWeekStart + 'T12:00:00');
    const ukDate = toUKTimezone(date);
    
    // Add/subtract weeks
    ukDate.setDate(ukDate.getDate() + (weeksToAdd * 7));
    
    // Ensure result is still a Sunday
    if (ukDate.getDay() !== 0) {
        const daysToSunday = ukDate.getDay();
        ukDate.setDate(ukDate.getDate() - daysToSunday);
    }
    
    return formatUKDateISO(ukDate);
}

// Export for use in other scripts
window.UKTimezone = {
    nowUK,
    toUKTimezone,
    formatUKDate,
    formatUKDateISO,
    getUKWeekStart,
    navigateWeeks,
    TIMEZONE: UK_TIMEZONE
};
