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
            headers: getJSONHeaders(),
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

// Password change functions
async function changePassword(e) {
    e.preventDefault();
    
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    // Client-side validation
    if (!currentPassword || !newPassword || !confirmPassword) {
        showError('All password fields are required');
        return;
    }
    
    if (newPassword.length < 8) {
        showError('New password must be at least 8 characters');
        return;
    }
    
    if (!/\d/.test(newPassword)) {
        showError('New password must contain at least one number');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showError('New passwords do not match');
        return;
    }
    
    try {
        const response = await fetch('/api/user/change-password', {
            method: 'POST',
            headers: getJSONHeaders(),
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword,
                confirm_password: confirmPassword
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showSuccess('✓ Password changed successfully! You can now use your new password to log in.');
            // Clear the form
            document.getElementById('changePasswordForm').reset();
            // Remove validation classes
            document.querySelectorAll('#changePasswordForm .form-control').forEach(field => {
                field.classList.remove('is-valid', 'is-invalid');
            });
        } else {
            showError(data.error || 'Failed to change password');
        }
    } catch (error) {
        console.error('Error changing password:', error);
        showError('Failed to change password. Please try again.');
    }
}

// Load user account information
async function loadUserInfo() {
    try {
        const response = await fetch('/api/user/profile');
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.user) {
                document.getElementById('username').value = data.user.username || '';
                document.getElementById('accountStatus').value = data.user.is_active ? 'Active' : 'Inactive';
            }
        }
    } catch (error) {
        console.error('Error loading user info:', error);
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('Profile settings page loaded');
    loadProfile();
    loadEmailSettings();
    loadUserInfo();
    
    // Add password change form handler
    const passwordForm = document.getElementById('changePasswordForm');
    if (passwordForm) {
        passwordForm.addEventListener('submit', changePassword);
    }
    
    // Add real-time validation for email
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
    
    // Add real-time validation for password strength
    const newPasswordField = document.getElementById('newPassword');
    if (newPasswordField) {
        newPasswordField.addEventListener('input', function() {
            const password = this.value;
            const hasMinLength = password.length >= 8;
            const hasNumber = /\d/.test(password);
            
            if (password.length > 0) {
                if (!hasMinLength) {
                    this.classList.add('is-invalid');
                    this.classList.remove('is-valid');
                } else if (!hasNumber) {
                    this.classList.add('is-invalid');
                    this.classList.remove('is-valid');
                } else {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                }
            } else {
                this.classList.remove('is-invalid', 'is-valid');
            }
        });
    }
    
    // Add real-time validation for password confirmation
    const confirmPasswordField = document.getElementById('confirmPassword');
    if (confirmPasswordField) {
        confirmPasswordField.addEventListener('input', function() {
            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = this.value;
            
            if (confirmPassword.length > 0) {
                if (newPassword !== confirmPassword) {
                    this.classList.add('is-invalid');
                    this.classList.remove('is-valid');
                } else {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                }
            } else {
                this.classList.remove('is-invalid', 'is-valid');
            }
        });
    }
});

// Helper function to validate email
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Email notification settings functions
async function loadEmailSettings() {
    try {
        const response = await fetch('/api/settings/email-notifications');
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.settings) {
                document.getElementById('managerEmail').value = data.settings.manager_email || '';
                document.getElementById('userEmailNotif').value = data.settings.user_email || '';
                document.getElementById('autoSendConfirmations').checked = data.settings.auto_send_confirmations || false;
            }
        }
    } catch (error) {
        console.error('Error loading email settings:', error);
    }
}

async function saveEmailSettings() {
    const settings = {
        manager_email: document.getElementById('managerEmail').value,
        user_email: document.getElementById('userEmailNotif').value,
        auto_send_confirmations: document.getElementById('autoSendConfirmations').checked
    };
    
    // Validate email addresses
    if (settings.manager_email && !isValidEmail(settings.manager_email)) {
        showError('Please enter a valid manager email address');
        return;
    }
    
    if (settings.user_email && !isValidEmail(settings.user_email)) {
        showError('Please enter a valid user email address');
        return;
    }
    
    try {
        const response = await fetch('/api/settings/email-notifications', {
            method: 'POST',
            headers: getJSONHeaders(),
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            const data = await response.json();
            showSuccess('Email settings saved successfully!');
        } else {
            const errorData = await response.json();
            showError(`Failed to save email settings: ${errorData.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error saving email settings:', error);
        showError('Failed to save email settings. Please try again.');
    }
}
