// Settings page helper functions

// Settings page functionality
function showSettingsSection(section) {
    document.getElementById(section + '-tab').click();
}

// File management functions
async function hybridSync() {
    try {
        showStatus('Running smart sync...');
        const result = await HybridSyncManager.hybridSync('smart');
        showResults('Smart Sync Complete', result);
        hideStatus();
    } catch (error) {
        showError(`Smart sync failed: ${error.message}`);
        hideStatus();
    }
}

async function processLocalFiles() {
    try {
        const fileType = document.getElementById('localFileType').value;
        const daysBack = parseInt(document.getElementById('localDaysBack').value);
        
        showStatus('Processing local files...');
        const result = await HybridSyncManager.processLocalFiles({
            type: fileType,
            days_back: daysBack
        });
        
        document.getElementById('localFilesResults').innerHTML = `
            <div class="alert alert-${result.success ? 'success' : 'danger'}">
                <i class="bi bi-${result.success ? 'check-circle' : 'x-circle'}"></i>
                Processing ${result.success ? 'completed' : 'failed'}
            </div>
        `;
        document.getElementById('localFilesResults').style.display = 'block';
        hideStatus();
    } catch (error) {
        showError(`Processing failed: ${error.message}`);
        hideStatus();
    }
}

async function testGmailConnection() {
    try {
        showStatus('Testing Gmail connection...');
        const response = await fetch('/api/gmail/test-connection', { method: 'POST' });
        const result = await response.json();
        
        const resultsDiv = document.getElementById('gmailTestResults');
        if (result.success) {
            resultsDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i>
                    Gmail connected successfully! Email: ${result.email}
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
        hideStatus();
    } catch (error) {
        showError(`Connection test failed: ${error.message}`);
        hideStatus();
    }
}

// Helper functions for status display
function showStatus(message) {
    // Implementation depends on your UI framework
    console.log('Status:', message);
}

function hideStatus() {
    // Implementation depends on your UI framework
    console.log('Hiding status');
}

function showError(message) {
    // Implementation depends on your UI framework
    console.error('Error:', message);
}

function showResults(title, result) {
    // Implementation depends on your UI framework
    console.log(title, result);
}
