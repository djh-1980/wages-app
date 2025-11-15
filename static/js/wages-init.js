// Wages page initialization script

// Load data when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Load summary data
    loadSummary();
    
    // Load tax years for filters
    loadTaxYears();
    
    // Load weekly trend chart
    loadWeeklyTrend();
    
    // Load top clients
    loadTopClients();
});
