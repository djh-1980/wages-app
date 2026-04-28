"""Route tests for /api/hmrc/period/cumulative/<tax_year>.

The HMRCClient is mocked at the route level so no real HMRC sandbox
calls are made. The HMRC connection-status check is also mocked so we
can assert the route's behaviour independently of real OAuth state.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from app.database import execute_query, get_db_connection


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------

PAYLOAD_PATH = 'app.routes.api_hmrc'


@pytest.fixture
def connected(monkeypatch):
    """Force ``HMRCAuthService.get_connection_status`` to report connected."""
    from app.services.hmrc_auth import HMRCAuthService

    monkeypatch.setattr(
        HMRCAuthService,
        'get_connection_status',
        lambda self: {'connected': True, 'environment': 'sandbox'},
    )


@pytest.fixture
def disconnected(monkeypatch):
    """Force ``HMRCAuthService`` to report not connected."""
    from app.services.hmrc_auth import HMRCAuthService

    monkeypatch.setattr(
        HMRCAuthService,
        'get_connection_status',
        lambda self: {'connected': False, 'environment': 'sandbox'},
    )


def _seed_minimal(app):
    """Insert a single Q1 expense + payslip so the calculator returns
    non-empty figures."""
    cat = execute_query(
        'SELECT id FROM expense_categories WHERE name = ?',
        ('Vehicle Costs',),
        fetch_one=True,
    )
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO expenses (date, category_id, description, amount) '
            'VALUES (?, ?, ?, ?)',
            ('2025-05-15', cat['id'], 'Test', 50.00),
        )
        cur.execute(
            'INSERT INTO payslips (period_end, gross_subcontractor_payment) '
            'VALUES (?, ?)',
            ('15/05/2025', 1000.00),
        )
        conn.commit()


def _hmrc_ok(receipt_id='cumulative-receipt-1'):
    return {
        'success': True,
        'data': {'id': receipt_id},
        'status_code': 201,
    }


def _hmrc_4xx():
    return {
        'success': False,
        'error': 'Validation failed',
        'status_code': 422,
        'validation_errors': [
            {
                'field': '/periodIncome/turnover',
                'message': 'Must be non-negative',
                'code': 'FORMAT_VALUE',
            }
        ],
    }


def _hmrc_5xx():
    return {
        'success': False,
        'error': 'Service unavailable',
        'status_code': 503,
    }


# ---------------------------------------------------------------------------
# auth & connection guards
# ---------------------------------------------------------------------------

def test_unauthenticated_post_blocked(client):
    """The app-wide before_request guard (auth_protection.protect_all_routes)
    redirects unauthenticated callers to /login with a 302. We assert that
    the request never reaches the cumulative submission code path."""
    response = client.post(
        '/api/hmrc/period/cumulative/2025-26',
        json={'nino': 'AA123456A', 'business_id': 'X1', 'period_id': 'Q1'},
        follow_redirects=False,
    )
    assert response.status_code in (302, 401), response.status_code
    if response.status_code == 302:
        assert '/login' in response.headers.get('Location', '')


def test_unauthenticated_get_blocked(client):
    response = client.get(
        '/api/hmrc/period/cumulative/2025-26', follow_redirects=False,
    )
    assert response.status_code in (302, 401), response.status_code


def test_post_without_hmrc_connection_returns_400(auth_client, disconnected):
    response = auth_client.post(
        '/api/hmrc/period/cumulative/2025-26',
        json={'nino': 'AA123456A', 'business_id': 'X1', 'period_id': 'Q1'},
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body['success'] is False
    assert 'connected' in body['error'].lower()


# ---------------------------------------------------------------------------
# input validation
# ---------------------------------------------------------------------------

def test_missing_nino_returns_400(auth_client, connected):
    response = auth_client.post(
        '/api/hmrc/period/cumulative/2025-26',
        json={'business_id': 'X1', 'period_id': 'Q1'},
    )
    assert response.status_code == 400
    assert 'nino' in response.get_json()['error'].lower()


def test_must_provide_exactly_one_window_argument(auth_client, connected):
    response = auth_client.post(
        '/api/hmrc/period/cumulative/2025-26',
        json={'nino': 'AA123456A', 'business_id': 'X1'},
    )
    assert response.status_code == 400


def test_calculator_value_error_returns_400(auth_client, app, connected):
    # Period end before tax year start - calculator raises ValueError.
    response = auth_client.post(
        '/api/hmrc/period/cumulative/2025-26',
        json={
            'nino': 'AA123456A',
            'business_id': 'X1',
            'period_end_date': '2025-04-05',
        },
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# successful submission
# ---------------------------------------------------------------------------

def test_successful_submission_stores_cumulative_row(auth_client, app, connected):
    with app.app_context():
        _seed_minimal(app)

    with patch(
        f'{PAYLOAD_PATH}.HMRCClient.submit_cumulative_period',
        return_value=_hmrc_ok(),
    ) as mock_submit:
        response = auth_client.post(
            '/api/hmrc/period/cumulative/2025-26',
            json={
                'nino': 'AA123456A',
                'business_id': 'XAIS12345678901',
                'period_id': 'Q1',
            },
        )

    assert response.status_code == 200, response.get_data(as_text=True)
    body = response.get_json()
    assert body['success'] is True
    assert body['period_dates']['periodStartDate'] == '2025-04-06'
    assert body['period_dates']['periodEndDate'] == '2025-07-05'
    assert 'submission_id' in body

    # The route must call HMRCClient with normalised tax year.
    args = mock_submit.call_args.args
    assert args[0] == 'AA123456A'
    assert args[1] == 'XAIS12345678901'
    assert args[2] == '2025-26'
    sent_payload = args[3]
    # Internal meta must NOT leak into the HMRC payload.
    assert 'meta' not in sent_payload
    assert sent_payload['periodIncome']['turnover'] == 1000.0

    # Row stored with submission_type='cumulative'.
    with app.app_context():
        row = execute_query(
            'SELECT * FROM hmrc_submissions WHERE id = ?',
            (body['submission_id'],),
            fetch_one=True,
        )
    assert row['submission_type'] == 'cumulative'
    assert row['status'] == 'submitted'
    assert row['nino'] == 'AA123456A'
    assert row['period_start_date'] == '2025-04-06'
    assert row['period_end_date'] == '2025-07-05'


def test_successful_submission_locks_records(auth_client, app, connected):
    with app.app_context():
        _seed_minimal(app)

    with patch(
        f'{PAYLOAD_PATH}.HMRCClient.submit_cumulative_period',
        return_value=_hmrc_ok(),
    ):
        response = auth_client.post(
            '/api/hmrc/period/cumulative/2025-26',
            json={
                'nino': 'AA123456A',
                'business_id': 'X1',
                'period_id': 'Q1',
            },
        )
    assert response.status_code == 200, response.get_data(as_text=True)
    submission_id = response.get_json()['submission_id']

    with app.app_context():
        from app.services.hmrc_lock import is_date_locked

        row = execute_query(
            'SELECT locked_at FROM hmrc_submissions WHERE id = ?',
            (submission_id,),
            fetch_one=True,
        )
        assert row['locked_at'] is not None

        # Any date inside the cumulative window must now be locked.
        assert is_date_locked('2025-05-15') is True
        # Outside the window: not locked.
        assert is_date_locked('2025-08-01') is False


# ---------------------------------------------------------------------------
# duplicate detection
# ---------------------------------------------------------------------------

def test_duplicate_submission_returns_409(auth_client, app, connected):
    with app.app_context():
        _seed_minimal(app)

    with patch(
        f'{PAYLOAD_PATH}.HMRCClient.submit_cumulative_period',
        return_value=_hmrc_ok(receipt_id='first-receipt'),
    ):
        first = auth_client.post(
            '/api/hmrc/period/cumulative/2025-26',
            json={
                'nino': 'AA123456A',
                'business_id': 'X1',
                'period_id': 'Q1',
            },
        )
    assert first.status_code == 200

    # Second attempt with same NINO + tax_year + period_end - 409.
    with patch(
        f'{PAYLOAD_PATH}.HMRCClient.submit_cumulative_period',
        return_value=_hmrc_ok(receipt_id='second-receipt'),
    ) as mock_second:
        second = auth_client.post(
            '/api/hmrc/period/cumulative/2025-26',
            json={
                'nino': 'AA123456A',
                'business_id': 'X1',
                'period_id': 'Q1',
            },
        )

    assert second.status_code == 409
    body = second.get_json()
    assert body['success'] is False
    assert body['hmrc_receipt_id'] == 'first-receipt'
    # Second submission must NOT have hit HMRC.
    mock_second.assert_not_called()


def test_force_flag_bypasses_duplicate_check(auth_client, app, connected):
    with app.app_context():
        _seed_minimal(app)

    with patch(
        f'{PAYLOAD_PATH}.HMRCClient.submit_cumulative_period',
        return_value=_hmrc_ok(),
    ):
        first = auth_client.post(
            '/api/hmrc/period/cumulative/2025-26',
            json={
                'nino': 'AA123456A',
                'business_id': 'X1',
                'period_id': 'Q1',
            },
        )
    assert first.status_code == 200

    with patch(
        f'{PAYLOAD_PATH}.HMRCClient.submit_cumulative_period',
        return_value=_hmrc_ok(receipt_id='forced-receipt'),
    ) as mock_second:
        forced = auth_client.post(
            '/api/hmrc/period/cumulative/2025-26?force=true',
            json={
                'nino': 'AA123456A',
                'business_id': 'X1',
                'period_id': 'Q1',
            },
        )

    assert forced.status_code == 200
    mock_second.assert_called_once()


# ---------------------------------------------------------------------------
# HMRC error surfacing
# ---------------------------------------------------------------------------

def test_hmrc_4xx_surfaces_validation_errors(auth_client, app, connected):
    with app.app_context():
        _seed_minimal(app)

    with patch(
        f'{PAYLOAD_PATH}.HMRCClient.submit_cumulative_period',
        return_value=_hmrc_4xx(),
    ):
        response = auth_client.post(
            '/api/hmrc/period/cumulative/2025-26',
            json={
                'nino': 'AA123456A',
                'business_id': 'X1',
                'period_id': 'Q1',
            },
        )

    assert response.status_code == 422
    body = response.get_json()
    assert body['success'] is False
    assert body['validation_errors'][0]['field'] == '/periodIncome/turnover'

    # We still record the failed submission so the audit trail is intact.
    with app.app_context():
        row = execute_query(
            'SELECT status, submission_type FROM hmrc_submissions WHERE id = ?',
            (body['submission_id'],),
            fetch_one=True,
        )
    assert row['status'] == 'failed'
    assert row['submission_type'] == 'cumulative'


def test_hmrc_5xx_surfaces_error_envelope(auth_client, app, connected):
    with app.app_context():
        _seed_minimal(app)

    with patch(
        f'{PAYLOAD_PATH}.HMRCClient.submit_cumulative_period',
        return_value=_hmrc_5xx(),
    ):
        response = auth_client.post(
            '/api/hmrc/period/cumulative/2025-26',
            json={
                'nino': 'AA123456A',
                'business_id': 'X1',
                'period_id': 'Q1',
            },
        )

    assert response.status_code == 503
    body = response.get_json()
    assert body['success'] is False
    assert 'unavailable' in body['error'].lower()


# ---------------------------------------------------------------------------
# GET endpoint
# ---------------------------------------------------------------------------

def test_get_returns_404_when_no_cumulative_submission(auth_client, app):
    response = auth_client.get('/api/hmrc/period/cumulative/2025-26')
    assert response.status_code == 404
    body = response.get_json()
    assert body['success'] is False


def test_get_returns_latest_cumulative_for_tax_year(auth_client, app, connected):
    with app.app_context():
        _seed_minimal(app)

    # Submit Q1 then Q2 for the same TY; GET should return Q2 (latest).
    with patch(
        f'{PAYLOAD_PATH}.HMRCClient.submit_cumulative_period',
        side_effect=[_hmrc_ok('q1-receipt'), _hmrc_ok('q2-receipt')],
    ):
        q1 = auth_client.post(
            '/api/hmrc/period/cumulative/2025-26',
            json={'nino': 'AA123456A', 'business_id': 'X1', 'period_id': 'Q1'},
        )
        assert q1.status_code == 200

        q2 = auth_client.post(
            '/api/hmrc/period/cumulative/2025-26',
            json={'nino': 'AA123456A', 'business_id': 'X1', 'period_id': 'Q2'},
        )
        assert q2.status_code == 200, q2.get_data(as_text=True)

    response = auth_client.get('/api/hmrc/period/cumulative/2025-26')
    assert response.status_code == 200
    body = response.get_json()
    assert body['success'] is True
    record = body['data']
    assert record['submission_type'] == 'cumulative'
    assert record['period_end_date'] == '2025-10-05'   # Q2 end
    assert record['hmrc_receipt_id'] == 'q2-receipt'
    # JSON blobs hydrated for the UI.
    assert isinstance(record['submission_data'], dict)
    assert record['submission_data']['periodDates']['periodEndDate'] == '2025-10-05'


class TestPreview:
    """?preview=1 returns calculated totals without contacting HMRC."""

    def test_preview_returns_totals_without_calling_hmrc(self, auth_client, app, connected):
        with app.app_context():
            _seed_minimal(app)

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.submit_cumulative_period',
        ) as mock_submit:
            response = auth_client.post(
                '/api/hmrc/period/cumulative/2025-26?preview=1',
                json={'period_id': 'Q1'},
            )

        assert response.status_code == 200, response.get_data(as_text=True)
        body = response.get_json()
        assert body['success'] is True
        assert body['preview'] is True

        # Must NOT have called HMRC.
        mock_submit.assert_not_called()

        # Must NOT have written anything to hmrc_submissions.
        with app.app_context():
            row = execute_query(
                'SELECT COUNT(*) AS n FROM hmrc_submissions',
                fetch_one=True,
            )
        assert row['n'] == 0

        # Response carries the calculated totals and the per-quarter breakdown.
        sub = body['data']['submission_data']
        assert sub['periodDates'] == {
            'periodStartDate': '2025-04-06',
            'periodEndDate': '2025-07-05',
        }
        assert sub['periodIncome']['turnover'] == 1000.00
        assert body['breakdown'][0]['period_id'] == 'Q1'
        assert body['breakdown'][0]['turnover'] == 1000.00

    def test_preview_works_without_hmrc_connection(self, auth_client, app, disconnected):
        """Preview must not require an active OAuth session - it never
        talks to HMRC. NINO + business_id are also not required."""
        with app.app_context():
            _seed_minimal(app)

        response = auth_client.post(
            '/api/hmrc/period/cumulative/2025-26?preview=1',
            json={'period_id': 'Q1'},
        )

        assert response.status_code == 200, response.get_data(as_text=True)
        body = response.get_json()
        assert body['success'] is True
        assert body['preview'] is True

    def test_preview_still_validates_window_argument(self, auth_client, app, connected):
        """Even in preview mode, exactly one of period_id /
        period_end_date is required."""
        response = auth_client.post(
            '/api/hmrc/period/cumulative/2025-26?preview=1',
            json={},
        )
        assert response.status_code == 400


def test_get_ignores_legacy_period_submissions(auth_client, app):
    """Only ``submission_type='cumulative'`` rows count for the GET."""
    with app.app_context():
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO hmrc_submissions
                  (tax_year, period_id, submission_date, status,
                   hmrc_receipt_id, submission_data, response_data,
                   nino, period_start_date, period_end_date,
                   submission_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    '2025-26', 'Q1', datetime.now().isoformat(), 'submitted',
                    'legacy-receipt', '{}', '{}', 'AA123456A',
                    '2025-04-06', '2025-07-05', 'period',
                ),
            )
            conn.commit()

    response = auth_client.get('/api/hmrc/period/cumulative/2025-26')
    assert response.status_code == 404
