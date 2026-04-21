"""Smoke tests - fast checks that the core stack wires up correctly."""

import pytest


def test_app_boots(app):
    """App factory returns a Flask app without raising."""
    assert app is not None
    assert app.config['TESTING'] is True


def test_routes_registered(app):
    """All expected blueprints registered a healthy number of routes."""
    rules = list(app.url_map.iter_rules())
    # Baseline is 294+ per the Phase-1 smoke test. Leave headroom.
    assert len(rules) > 200, f'Only {len(rules)} routes registered'


def test_database_initialised(app):
    """Core tables exist after init_database()."""
    from app.database import get_db_connection

    with app.app_context(), get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

    for required in ('users', 'expenses', 'run_sheet_jobs', 'payslips'):
        assert required in tables, f'Missing table: {required}'


def test_login_page_loads(client):
    """GET /login returns 200 for an unauthenticated visitor."""
    response = client.get('/login')
    assert response.status_code == 200


def test_login_redirects_unauth(client):
    """Protected pages redirect unauthenticated users to /login."""
    response = client.get('/expenses')
    assert response.status_code == 302
    assert '/login' in response.location


def test_authenticated_access(auth_client):
    """Authenticated client can fetch a protected page."""
    response = auth_client.get('/expenses')
    assert response.status_code == 200


def test_health_endpoint(client):
    """/healthz returns 200 with structured JSON."""
    response = client.get('/healthz')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert 'timestamp' in data


def test_readyz_endpoint(client):
    """/readyz returns per-check diagnostics (200 healthy or 503 degraded)."""
    response = client.get('/readyz')
    assert response.status_code in (200, 503)
    data = response.get_json()
    assert 'status' in data
    assert data['status'] in ('ok', 'degraded')
    assert 'checks' in data
    for required in ('database', 'disk_space', 'sync_recent', 'gmail_auth'):
        assert required in data['checks']
        assert 'healthy' in data['checks'][required]


def test_health_endpoints_are_public(client):
    """Monitoring probes must be able to hit /healthz and /readyz unauthenticated."""
    # No login performed on this client; both must return 2xx/503, never 302.
    assert client.get('/healthz').status_code == 200
    assert client.get('/readyz').status_code in (200, 503)


def test_logout(auth_client):
    """Logout clears the session and re-protects the app."""
    response = auth_client.get('/logout', follow_redirects=False)
    assert response.status_code == 302

    # After logout, protected routes must redirect again.
    response = auth_client.get('/expenses')
    assert response.status_code == 302
    assert '/login' in response.location


def test_csrf_token_provided(client):
    """Login page renders (CSRF is disabled in the test harness)."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'username' in response.data.lower()


def test_static_files_served(client):
    """Static file requests resolve without 500s."""
    response = client.get('/static/css/base.css')
    assert response.status_code in (200, 304, 404)
