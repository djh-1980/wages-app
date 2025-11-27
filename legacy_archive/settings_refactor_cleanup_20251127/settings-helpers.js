// Settings page helper functions

// Settings page functionality
function showSettingsSection(section) {
    console.log('🔄 Switching to section:', section);
    const tabElement = document.getElementById(section + '-tab');
    const tabPane = document.getElementById(section);
    
    if (tabElement && tabPane) {
        console.log('✅ Tab element found, switching to:', section);
        
        // Hide all tab panes first
        const allPanes = document.querySelectorAll('.tab-pane');
        const allTabs = document.querySelectorAll('[data-bs-toggle="pill"]');
        
        allPanes.forEach(pane => {
            pane.classList.remove('show', 'active');
        });
        
        allTabs.forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Show the selected tab
        tabPane.classList.add('show', 'active');
        tabElement.classList.add('active');
        
        console.log('✅ Tab switched successfully to:', section);
        
        // Special handling for specific tabs
        if (section === 'attendance') {
            setTimeout(() => {
                if (document.getElementById('attendanceRecordsList')) {
                    loadAttendanceRecords();
                }
            }, 100);
        }
    } else {
        console.error('❌ Tab element or pane not found for section:', section);
        console.log('Tab element:', tabElement);
        console.log('Tab pane:', tabPane);
    }
}

async function testGmailConnection() {
    const resultsDiv = document.getElementById('gmailTestResults');
    if (!resultsDiv) {
        console.error('Gmail test results div not found');
        return;
    }
    
    try {
        showStatus('Testing Gmail connection...');
        const response = await fetch('/api/gmail/test-connection', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            resultsDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i>
                    Gmail connected successfully! Email: ${result.email || 'Connected'}
                </div>
            `;
        } else {
            resultsDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i>
                    Connection failed: ${result.error}
                </div>
            `;
        }
        resultsDiv.style.display = 'block';
    } catch (error) {
        resultsDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-x-circle"></i>
                Connection test failed: ${error.message}
            </div>
        `;
        resultsDiv.style.display = 'block';
    }
}

// Helper functions for status display
function showStatus(message, type = 'info') {
    const statusDiv = document.getElementById('settingsStatus');
    if (statusDiv) {
        statusDiv.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show">
                <i class="bi bi-info-circle"></i> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        statusDiv.style.display = 'block';
    } else {
        console.log('Status:', message);
    }
}

function hideStatus() {
    const statusDiv = document.getElementById('settingsStatus');
    if (statusDiv) {
        statusDiv.style.display = 'none';
    }
}

function showError(message) {
    showStatus(message, 'danger');
}

function showSuccess(message) {
    showStatus(message, 'success');
}

function showResults(title, result) {
    console.log(title, result);
    if (result && result.success) {
        showSuccess(`${title}: ${result.message || 'Operation completed successfully'}`);
    } else {
        showError(`${title}: ${result?.error || 'Operation failed'}`);
    }
}
