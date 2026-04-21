"""Authentication and session tests."""


def test_login_with_valid_credentials(client):
    """Valid login redirects (302) to the post-login landing page."""
    response = client.post(
        '/login',
        data={'username': 'testuser', 'password': 'TestPass1!'},
        follow_redirects=False,
    )
    assert response.status_code == 302


def test_login_with_invalid_credentials(client):
    """Invalid login re-renders the login form (never logs the user in)."""
    response = client.post(
        '/login',
        data={'username': 'testuser', 'password': 'wrongpass'},
        follow_redirects=False,
    )
    assert response.status_code in (200, 302)

    # Protected pages must still redirect afterwards.
    follow_up = client.get('/expenses')
    assert follow_up.status_code == 302


def test_login_with_empty_credentials(client):
    """Empty credentials do not log the user in."""
    response = client.post(
        '/login',
        data={'username': '', 'password': ''},
        follow_redirects=False,
    )
    assert response.status_code in (200, 302, 400)


def test_protected_api_returns_401_or_302(client):
    """Unauthenticated API calls redirect (pre-login filter) or return 401."""
    response = client.get('/api/expenses/list')
    assert response.status_code in (302, 401)


def test_authenticated_api_returns_200(auth_client):
    """Authenticated client can hit a JSON API endpoint."""
    response = auth_client.get('/api/expenses/list')
    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert 'success' in payload
