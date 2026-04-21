"""Shared pytest fixtures for the TVS TCMS test suite.

Every test gets its own isolated temp-file SQLite database, a fresh Flask
app instance, and (where requested) a pre-authenticated test client. All
fixtures clean up after themselves.
"""

import os
import tempfile

import pytest


# Make sure the app is created in testing mode even if the surrounding
# environment has FLASK_ENV=development. This must be set before any
# import of `app` that reads FLASK_ENV at module-load time.
os.environ.setdefault('FLASK_ENV', 'testing')


@pytest.fixture
def app():
    """Create a Flask app backed by an isolated temp-file SQLite database."""
    from app import create_app
    from app.database import init_database
    from app.models.user import User

    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    test_config = {
        'TESTING': True,
        'DATABASE_PATH': db_path,
        'WTF_CSRF_ENABLED': False,
        'RATELIMIT_ENABLED': False,
        'SECRET_KEY': 'test-secret-key',
        'HMRC_ENVIRONMENT': 'sandbox',
        'AUTO_SYNC_ENABLED': False,
        'SERVER_NAME': 'localhost.localdomain',
    }

    app = create_app('testing', test_config=test_config)

    with app.app_context():
        init_database()
        # Seed a known admin user for auth tests.
        User.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass1!',
            is_admin=True,
        )

    yield app

    os.close(db_fd)
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def client(app):
    """Flask test client (unauthenticated)."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Flask test client that has already logged in as `testuser`."""
    response = client.post(
        '/login',
        data={'username': 'testuser', 'password': 'TestPass1!'},
        follow_redirects=False,
    )
    # The login route redirects on success; surface any failure clearly.
    assert response.status_code == 302, (
        f'Test login failed: status={response.status_code}, '
        f'body={response.get_data(as_text=True)[:200]}'
    )
    return client


@pytest.fixture
def runner(app):
    """Flask CLI runner."""
    return app.test_cli_runner()
