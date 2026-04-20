/**
 * HMRC fraud-prevention browser context capture.
 *
 * HMRC requires WEB_APP_VIA_SERVER applications to forward a number of
 * client-side values (browser UA, screen dimensions, window size, timezone,
 * plugins, DNT, device ID) on every API call. The browser captures these
 * here and POSTs them to the backend, which stashes them in the Flask
 * session and replays them on every HMRC API request made via HMRCClient.
 *
 * Load this script on every page that can trigger an HMRC API call
 * (settings/hmrc, MTD sandbox, etc.).
 */

(function () {
    'use strict';

    const STORAGE_KEY = 'tvstcms.hmrc.deviceId';
    const ENDPOINT = '/api/hmrc/fraud-headers/record';

    function getOrCreateDeviceId() {
        try {
            let id = localStorage.getItem(STORAGE_KEY);
            if (!id) {
                // RFC 4122 v4 UUID
                id = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
                    const r = (Math.random() * 16) | 0;
                    const v = c === 'x' ? r : (r & 0x3) | 0x8;
                    return v.toString(16);
                });
                localStorage.setItem(STORAGE_KEY, id);
            }
            return id;
        } catch (e) {
            // Fallback if localStorage is blocked (Safari private mode etc.)
            return 'no-storage-' + Date.now();
        }
    }

    function collectPlugins() {
        try {
            if (!navigator.plugins || navigator.plugins.length === 0) return '';
            return Array.from(navigator.plugins)
                .map((p) => encodeURIComponent(p.name || ''))
                .filter(Boolean)
                .join(',');
        } catch (e) {
            return '';
        }
    }

    function collectDoNotTrack() {
        if (navigator.doNotTrack === '1' || window.doNotTrack === '1') return '1';
        if (navigator.doNotTrack === '0' || window.doNotTrack === '0') return '0';
        return 'unspecified';
    }

    function collectTimezone() {
        try {
            return Intl.DateTimeFormat().resolvedOptions().timeZone || '';
        } catch (e) {
            return '';
        }
    }

    function payload() {
        const screenScaling = (window.devicePixelRatio || 1).toString();
        return {
            js_user_agent: navigator.userAgent || '',
            plugins: collectPlugins(),
            do_not_track: collectDoNotTrack(),
            window_width: window.innerWidth,
            window_height: window.innerHeight,
            screen_width: screen && screen.width,
            screen_height: screen && screen.height,
            screen_scaling: screenScaling,
            screen_colour_depth: screen && (screen.colorDepth || screen.pixelDepth || 24),
            timezone: collectTimezone(),
            device_id: getOrCreateDeviceId(),
        };
    }

    function post() {
        try {
            const headers =
                typeof getJSONHeaders === 'function'
                    ? getJSONHeaders()
                    : { 'Content-Type': 'application/json' };
            fetch(ENDPOINT, {
                method: 'POST',
                headers,
                body: JSON.stringify(payload()),
                credentials: 'same-origin',
            }).catch(() => {
                // Best-effort; failure is non-fatal - HMRCClient will warn if
                // context is missing when a real submission is attempted.
            });
        } catch (e) {
            // Never throw from this helper.
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', post);
    } else {
        post();
    }
})();
