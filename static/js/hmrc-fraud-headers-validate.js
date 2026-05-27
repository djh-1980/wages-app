/**
 * Wire the "Validate Fraud Headers Now" button on the HMRC settings page
 * to the GET /api/hmrc/fraud-headers/validate endpoint, which proxies the
 * request through HMRC's Test Fraud Prevention Headers API and renders
 * the result.
 */
(function () {
    'use strict';

    function show(el) { el.classList.remove('d-none'); }
    function setAlert(el, cls, html) {
        el.className = 'alert ' + cls;
        el.innerHTML = html;
    }

    function render(payload) {
        const resultBox = document.getElementById('fraudHeadersResult');
        const alertBox = document.getElementById('fraudHeadersAlert');
        const details = document.getElementById('fraudHeadersDetails');
        if (!resultBox || !alertBox || !details) return;

        show(resultBox);
        details.textContent = JSON.stringify(payload, null, 2);

        const data = (payload && payload.data) || {};
        const code = data.code || 'UNKNOWN';
        const message = data.message || payload.error || 'No response from HMRC.';

        if (code === 'VALID_HEADERS') {
            setAlert(
                alertBox,
                'alert-success',
                '<strong><i class="fas fa-check-circle"></i> VALID_HEADERS</strong><br>' + message
            );
        } else if (code === 'POTENTIALLY_INVALID_HEADERS') {
            setAlert(
                alertBox,
                'alert-warning',
                '<strong><i class="fas fa-exclamation-triangle"></i> POTENTIALLY_INVALID_HEADERS</strong><br>' + message
            );
        } else if (code === 'INVALID_HEADERS') {
            setAlert(
                alertBox,
                'alert-danger',
                '<strong><i class="fas fa-times-circle"></i> INVALID_HEADERS</strong><br>' + message
            );
        } else {
            setAlert(
                alertBox,
                'alert-secondary',
                '<strong>' + code + '</strong><br>' + message
            );
        }
    }

    async function recordContextNow() {
        // Re-capture the browser context and POST it so the session is
        // guaranteed populated before we validate. The capture function
        // lives in hmrc-fraud-headers.js but its `payload` is private,
        // so we duplicate the minimum here.
        try {
            const STORAGE_KEY = 'tvstcms.hmrc.deviceId';
            let deviceId = localStorage.getItem(STORAGE_KEY);
            if (!deviceId) {
                deviceId = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
                    const r = (Math.random() * 16) | 0;
                    const v = c === 'x' ? r : (r & 0x3) | 0x8;
                    return v.toString(16);
                });
                localStorage.setItem(STORAGE_KEY, deviceId);
            }
            const body = {
                js_user_agent: navigator.userAgent || '',
                window_width: window.innerWidth,
                window_height: window.innerHeight,
                screen_width: screen && screen.width,
                screen_height: screen && screen.height,
                screen_scaling: (window.devicePixelRatio || 1).toString(),
                screen_colour_depth: screen && (screen.colorDepth || screen.pixelDepth || 24),
                timezone: (Intl.DateTimeFormat().resolvedOptions().timeZone) || '',
                device_id: deviceId,
            };
            const headers =
                typeof getJSONHeaders === 'function'
                    ? getJSONHeaders()
                    : { 'Content-Type': 'application/json' };
            await fetch('/api/hmrc/fraud-headers/record', {
                method: 'POST',
                credentials: 'same-origin',
                headers,
                body: JSON.stringify(body),
            });
        } catch (e) {
            // Best-effort.
        }
    }

    async function validate() {
        const btn = document.getElementById('validateFraudHeadersBtn');
        if (!btn) return;
        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Validating...';
        try {
            await recordContextNow();
            const r = await fetch('/api/hmrc/fraud-headers/validate', {
                method: 'GET',
                credentials: 'same-origin',
                headers: { Accept: 'application/json' },
            });
            const body = await r.json();
            render(body);
        } catch (e) {
            render({ success: false, error: String(e) });
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const btn = document.getElementById('validateFraudHeadersBtn');
        if (btn) btn.addEventListener('click', validate);
    });
})();
