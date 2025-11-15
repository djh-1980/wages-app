// Runsheets page initialization script

// Load data on page load
document.addEventListener('DOMContentLoaded', function() {
    populateYearFilter();
    loadRunSheetsSummary();
    loadRunSheetsList(1);
});
