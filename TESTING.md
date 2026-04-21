# Running Tests

The TVS TCMS test suite uses [pytest](https://pytest.org) with the Flask app
factory. Every test runs against its own isolated temp-file SQLite database
and a freshly-seeded admin user, so tests are independent and can run in any
order.

## Install dev dependencies

```bash
./venv/bin/pip install -r requirements-dev.txt
```

## Running

```bash
# All tests
./venv/bin/pytest

# A single file
./venv/bin/pytest tests/test_smoke.py

# A single test
./venv/bin/pytest tests/test_auth.py::test_login_with_valid_credentials

# Skip slow tests
./venv/bin/pytest -m "not slow"

# With coverage report (HTML in htmlcov/)
./venv/bin/pytest --cov=app --cov-report=term-missing --cov-report=html
```

## Markers

| Marker        | Meaning                                                       |
|---------------|---------------------------------------------------------------|
| `slow`        | Takes more than a second or two; opt in with `-m slow`.       |
| `hmrc`        | Hits the HMRC sandbox; deselected by default.                 |
| `integration` | Needs database / network; included by default.                |

## Writing new tests

- Put them under `tests/` with a `test_*.py` filename.
- Use the `app`, `client`, `auth_client`, or `runner` fixtures from
  `tests/conftest.py` — they handle DB setup, user seeding and cleanup.
- Never hit the real database or a live network service. Use mocks for
  HMRC, Gmail, and any external HTTP calls.
- Every new test must run in under a second. If it must be slow, mark it
  `@pytest.mark.slow`.

## CI

Tests run automatically on pushes and pull requests to `main` via
`.github/workflows/tests.yml`.
