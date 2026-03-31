/**
 * CSRF Token Helper for AJAX Requests
 * Provides utility functions to get CSRF token and create headers
 */

function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
}

function getCSRFHeaders(additionalHeaders = {}) {
    return {
        'X-CSRFToken': getCSRFToken(),
        ...additionalHeaders
    };
}

function getJSONHeaders() {
    return {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken()
    };
}
