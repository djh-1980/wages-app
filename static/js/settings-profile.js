/**
 * Profile Settings JavaScript
 * Handles profile management functionality
 */

// Status display functions
function showStatus(message, type = 'info') {
    const statusDiv = document.getElementById('settingsStatus');
    if (statusDiv) {
        const alertClass = type === 'success' ? 'alert-success' : 
                          type === 'danger' ? 'alert-danger' : 
                          type === 'warning' ? 'alert-warning' : 'alert-info';
        
        statusDiv.innerHTML = `
            <div class="alert ${alertClass} alert-dismissible fade show">
                <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'danger' ? 'x-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i> 
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        statusDiv.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            const alert = statusDiv.querySelector('.alert');
            if (alert) {
                alert.classList.remove('show');
                setTimeout(() => statusDiv.style.display = 'none', 300);
            }
        }, 5000);
    }
}

function showSuccess(message) {
    showStatus(message, 'success');
}

function showError(message) {
    showStatus(message, 'danger');
}

// Profile functions
async function loadProfile() {
    try {
        const response = await fetch('/api/settings/profile');
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.profile) {
                document.getElementById('userName').value = data.profile.userName || '';
                document.getElementById('userEmail').value = data.profile.userEmail || '';
                document.getElementById('userPhone').value = data.profile.userPhone || '';
                document.getElementById('utrNumber').value = data.profile.utrNumber || '';
                document.getElementById('addressLine1').value = data.profile.addressLine1 || '';
                document.getElementById('addressLine2').value = data.profile.addressLine2 || '';
                document.getElementById('city').value = data.profile.city || '';
                document.getElementById('postcode').value = data.profile.postcode || '';
                document.getElementById('niNumber').value = data.profile.niNumber || '';
                
                // Also populate the second UTR field if it exists
                const utrNumber2 = document.getElementById('utrNumber2');
                if (utrNumber2) {
                    utrNumber2.value = data.profile.utrNumber || '';
                }
            }
        }
    } catch (error) {
        console.error('Error loading profile:', error);
        showError('Failed to load profile data');
    }
}

async function saveProfile() {
    const profileData = {
        userName: document.getElementById('userName').value,
        userEmail: document.getElementById('userEmail').value,
        userPhone: document.getElementById('userPhone').value,
        utrNumber: document.getElementById('utrNumber').value,
        addressLine1: document.getElementById('addressLine1').value,
        addressLine2: document.getElementById('addressLine2').value,
        city: document.getElementById('city').value,
        postcode: document.getElementById('postcode').value,
        niNumber: document.getElementById('niNumber').value
    };
    
    // Validate required fields
    if (!profileData.userName.trim()) {
        showError('Please enter your full name');
        return;
    }
    
    if (!profileData.userEmail.trim()) {
        showError('Please enter your email address');
        return;
    }
    
    try {
        const response = await fetch('/api/settings/profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profileData)
        });
        
        if (response.ok) {
            const data = await response.json();
            showSuccess('Profile saved successfully!');
        } else {
            const errorData = await response.json();
            showError(`Failed to save profile: ${errorData.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error saving profile:', error);
        showError('Failed to save profile. Please try again.');
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('Profile settings page loaded');
    loadProfile();
    
    // Add form validation
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            saveProfile();
        });
    }
    
    // Add real-time validation
    const emailField = document.getElementById('userEmail');
    if (emailField) {
        emailField.addEventListener('blur', function() {
            const email = this.value.trim();
            if (email && !isValidEmail(email)) {
                this.classList.add('is-invalid');
                showError('Please enter a valid email address');
            } else {
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            }
        });
    }
});

// Helper function to validate email
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}
