"""Route tests for the Periods of Account endpoints under /api/hmrc/.

The HMRCClient is mocked at the route level so no real HMRC sandbox
calls are made. The HMRC connection-status check is also mocked so we
can assert the route's behaviour independently of real OAuth state.

Two-phase write contract under test:
    1. Route calls HMRCClient first.
    2. Local mirror only changes after HMRC confirms success.
    3. HMRC failures must NOT corrupt the local mirror.
"""

from unittest.mock import patch

import pytest


PAYLOAD_PATH = 'app.routes.api_hmrc'


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def connected(monkeypatch):
    """Force HMRCAuthService to report connected."""
    from app.services.hmrc_auth import HMRCAuthService

    monkeypatch.setattr(
        HMRCAuthService,
        'get_connection_status',
        lambda self: {'connected': True, 'environment': 'sandbox'},
    )


@pytest.fixture
def disconnected(monkeypatch):
    """Force HMRCAuthService to report not connected."""
    from app.services.hmrc_auth import HMRCAuthService

    monkeypatch.setattr(
        HMRCAuthService,
        'get_connection_status',
        lambda self: {'connected': False, 'environment': 'sandbox'},
    )


# ---- HMRC client return-value helpers --------------------------------------

def _hmrc_create_ok(period_id='POA-1'):
    return {
        'success': True,
        'data': {'periodId': period_id},
        'status_code': 201,
    }


def _hmrc_update_ok():
    return {'success': True, 'data': {}, 'status_code': 200}


def _hmrc_delete_ok():
    return {'success': True, 'data': {}, 'status_code': 204}


def _hmrc_4xx():
    return {
        'success': False,
        'error': 'Validation failed',
        'status_code': 422,
        'validation_errors': [
            {'field': '/startDate', 'message': 'Must be ISO', 'code': 'FORMAT_DATE'}
        ],
    }


def _hmrc_5xx():
    return {
        'success': False,
        'error': 'Service unavailable',
        'status_code': 503,
    }


# ---- direct service helper -------------------------------------------------

def _seed_local_period(app, tax_year='2025-26', period_id='POA-1'):
    """Create + tag a local period with a known HMRC periodId."""
    from app.services import periods_of_account_service as svc

    with app.app_context():
        svc.create_standard_period(tax_year, business_id='X1')
        return svc.update_period(tax_year, period_id=period_id)


# ===========================================================================
# Auth & connection guards
# ===========================================================================

class TestAuthAndConnection:
    POA_URL = '/api/hmrc/period-of-account/2025-26'
    LIST_URL = '/api/hmrc/periods-of-account'

    def test_unauthenticated_post_blocked(self, client):
        response = client.post(
            self.POA_URL,
            json={'nino': 'AA123456A', 'business_id': 'X1'},
            follow_redirects=False,
        )
        assert response.status_code in (302, 401)

    def test_unauthenticated_list_blocked(self, client):
        response = client.get(self.LIST_URL, follow_redirects=False)
        assert response.status_code in (302, 401)

    def test_unauthenticated_get_blocked(self, client):
        response = client.get(self.POA_URL, follow_redirects=False)
        assert response.status_code in (302, 401)

    def test_unauthenticated_put_blocked(self, client):
        response = client.put(
            self.POA_URL,
            json={'nino': 'AA123456A', 'business_id': 'X1'},
            follow_redirects=False,
        )
        assert response.status_code in (302, 401)

    def test_unauthenticated_delete_blocked(self, client):
        response = client.delete(
            self.POA_URL,
            json={'nino': 'AA123456A', 'business_id': 'X1'},
            follow_redirects=False,
        )
        assert response.status_code in (302, 401)

    def test_post_without_hmrc_connection_returns_400(self, auth_client, disconnected):
        response = auth_client.post(
            self.POA_URL,
            json={'nino': 'AA123456A', 'business_id': 'X1'},
        )
        assert response.status_code == 400
        body = response.get_json()
        assert body['success'] is False
        assert 'connected' in body['error'].lower()

    def test_put_without_hmrc_connection_returns_400(self, auth_client, disconnected):
        response = auth_client.put(
            self.POA_URL,
            json={'nino': 'AA123456A', 'business_id': 'X1'},
        )
        assert response.status_code == 400

    def test_delete_without_hmrc_connection_returns_400(self, auth_client, disconnected):
        response = auth_client.delete(
            self.POA_URL,
            json={'nino': 'AA123456A', 'business_id': 'X1'},
        )
        assert response.status_code == 400


# ===========================================================================
# POST /period-of-account/<tax_year>
# ===========================================================================

class TestCreate:
    URL = '/api/hmrc/period-of-account/2025-26'

    def test_missing_nino_returns_400(self, auth_client, connected):
        response = auth_client.post(self.URL, json={'business_id': 'X1'})
        assert response.status_code == 400

    def test_missing_business_id_returns_400(self, auth_client, connected):
        response = auth_client.post(self.URL, json={'nino': 'AA123456A'})
        assert response.status_code == 400

    def test_successful_standard_create(self, auth_client, app, connected):
        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.create_period_of_account',
            return_value=_hmrc_create_ok(period_id='POA-77'),
        ) as mock_create:
            response = auth_client.post(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'XAIS12345678901'},
            )

        assert response.status_code == 200, response.get_data(as_text=True)
        body = response.get_json()
        assert body['success'] is True
        # HMRC was called with the standard 6 Apr -> 5 Apr window.
        mock_create.assert_called_once()
        args = mock_create.call_args.args
        assert args[0] == 'AA123456A'
        assert args[1] == 'XAIS12345678901'
        sent_payload = args[2]
        assert sent_payload == {
            'startDate': '2025-04-06',
            'endDate': '2026-04-05',
        }

        # Local mirror persisted with HMRC's periodId.
        from app.services import periods_of_account_service as svc
        with app.app_context():
            local = svc.get_for_tax_year('2025-26')
        assert local is not None
        assert local['period_start_date'] == '2025-04-06'
        assert local['period_end_date'] == '2026-04-05'
        assert local['period_type'] == 'standard'
        assert local['period_id'] == 'POA-77'
        assert local['business_id'] == 'XAIS12345678901'

    def test_successful_custom_create(self, auth_client, app, connected):
        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.create_period_of_account',
            return_value=_hmrc_create_ok(period_id='POA-CUST'),
        ) as mock_create:
            response = auth_client.post(
                self.URL,
                json={
                    'nino': 'AA123456A',
                    'business_id': 'X1',
                    'period_type': 'non-standard',
                    'start_date': '2025-04-01',
                    'end_date': '2026-03-31',
                },
            )

        assert response.status_code == 200
        sent_payload = mock_create.call_args.args[2]
        assert sent_payload == {
            'startDate': '2025-04-01',
            'endDate': '2026-03-31',
        }

        from app.services import periods_of_account_service as svc
        with app.app_context():
            local = svc.get_for_tax_year('2025-26')
        assert local['period_type'] == 'non-standard'
        assert local['period_start_date'] == '2025-04-01'

    def test_custom_create_missing_dates_returns_400(self, auth_client, connected):
        response = auth_client.post(
            self.URL,
            json={
                'nino': 'AA123456A',
                'business_id': 'X1',
                'period_type': 'non-standard',
            },
        )
        assert response.status_code == 400

    def test_hmrc_4xx_does_not_create_local_row(self, auth_client, app, connected):
        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.create_period_of_account',
            return_value=_hmrc_4xx(),
        ):
            response = auth_client.post(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1'},
            )

        assert response.status_code == 422
        body = response.get_json()
        assert body['success'] is False
        assert body['validation_errors'][0]['field'] == '/startDate'

        # Critical: local mirror MUST NOT have been created.
        from app.services import periods_of_account_service as svc
        with app.app_context():
            assert svc.get_for_tax_year('2025-26') is None

    def test_hmrc_5xx_does_not_create_local_row(self, auth_client, app, connected):
        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.create_period_of_account',
            return_value=_hmrc_5xx(),
        ):
            response = auth_client.post(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1'},
            )

        assert response.status_code == 503
        from app.services import periods_of_account_service as svc
        with app.app_context():
            assert svc.get_for_tax_year('2025-26') is None

    def test_duplicate_local_period_returns_409_without_calling_hmrc(
        self, auth_client, app, connected,
    ):
        _seed_local_period(app)

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.create_period_of_account',
            return_value=_hmrc_create_ok(),
        ) as mock_create:
            response = auth_client.post(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1'},
            )

        assert response.status_code == 409
        mock_create.assert_not_called()


# ===========================================================================
# GET list / GET single
# ===========================================================================

class TestRead:
    LIST_URL = '/api/hmrc/periods-of-account'

    def test_list_returns_local_rows(self, auth_client, app):
        from app.services import periods_of_account_service as svc

        with app.app_context():
            svc.create_standard_period('2024-25')
            svc.create_standard_period('2025-26')

        response = auth_client.get(self.LIST_URL)
        assert response.status_code == 200
        body = response.get_json()
        assert body['success'] is True
        years = sorted(r['tax_year'] for r in body['data'])
        assert years == ['2024-25', '2025-26']

    def test_list_excludes_soft_deleted(self, auth_client, app):
        from app.services import periods_of_account_service as svc

        with app.app_context():
            svc.create_standard_period('2024-25')
            svc.create_standard_period('2025-26')
            svc.delete_period('2024-25')

        response = auth_client.get(self.LIST_URL)
        body = response.get_json()
        years = [r['tax_year'] for r in body['data']]
        assert years == ['2025-26']

    def test_list_does_not_require_hmrc_connection(
        self, auth_client, app, disconnected,
    ):
        from app.services import periods_of_account_service as svc
        with app.app_context():
            svc.create_standard_period('2025-26')

        response = auth_client.get(self.LIST_URL)
        assert response.status_code == 200

    def test_get_returns_404_when_no_period(self, auth_client, app):
        response = auth_client.get('/api/hmrc/period-of-account/2099-00')
        assert response.status_code == 404

    def test_get_returns_local_record_for_tax_year(self, auth_client, app):
        from app.services import periods_of_account_service as svc
        with app.app_context():
            svc.create_standard_period('2025-26')

        response = auth_client.get('/api/hmrc/period-of-account/2025-26')
        assert response.status_code == 200
        body = response.get_json()
        assert body['data']['tax_year'] == '2025-26'
        assert body['data']['period_start_date'] == '2025-04-06'

    def test_get_does_not_require_hmrc_connection(
        self, auth_client, app, disconnected,
    ):
        from app.services import periods_of_account_service as svc
        with app.app_context():
            svc.create_standard_period('2025-26')

        response = auth_client.get('/api/hmrc/period-of-account/2025-26')
        assert response.status_code == 200


# ===========================================================================
# PUT /period-of-account/<tax_year>
# ===========================================================================

class TestUpdate:
    URL = '/api/hmrc/period-of-account/2025-26'

    def test_404_when_local_period_missing(self, auth_client, app, connected):
        response = auth_client.put(
            self.URL, json={'nino': 'AA123456A', 'business_id': 'X1'},
        )
        assert response.status_code == 404

    def test_409_when_no_hmrc_period_id_recorded(
        self, auth_client, app, connected,
    ):
        from app.services import periods_of_account_service as svc
        with app.app_context():
            svc.create_standard_period('2025-26')  # no period_id set

        response = auth_client.put(
            self.URL,
            json={
                'nino': 'AA123456A',
                'business_id': 'X1',
                'start_date': '2025-05-01',
                'end_date': '2026-04-30',
            },
        )
        assert response.status_code == 409

    def test_successful_update_propagates_to_local(
        self, auth_client, app, connected,
    ):
        _seed_local_period(app, period_id='POA-9')

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.update_period_of_account',
            return_value=_hmrc_update_ok(),
        ) as mock_update:
            response = auth_client.put(
                self.URL,
                json={
                    'nino': 'AA123456A',
                    'business_id': 'X1',
                    'start_date': '2025-05-01',
                    'end_date': '2026-04-30',
                    'period_type': 'non-standard',
                },
            )

        assert response.status_code == 200, response.get_data(as_text=True)
        # HMRC was called with the right period_id and dates.
        args = mock_update.call_args.args
        assert args[2] == 'POA-9'
        assert args[3] == {
            'startDate': '2025-05-01',
            'endDate': '2026-04-30',
        }

        # Local mirror reflects the new dates.
        from app.services import periods_of_account_service as svc
        with app.app_context():
            local = svc.get_for_tax_year('2025-26')
        assert local['period_start_date'] == '2025-05-01'
        assert local['period_end_date'] == '2026-04-30'
        assert local['period_type'] == 'non-standard'

    def test_hmrc_4xx_leaves_local_unchanged(self, auth_client, app, connected):
        seeded = _seed_local_period(app, period_id='POA-9')

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.update_period_of_account',
            return_value=_hmrc_4xx(),
        ):
            response = auth_client.put(
                self.URL,
                json={
                    'nino': 'AA123456A',
                    'business_id': 'X1',
                    'start_date': '2025-05-01',
                    'end_date': '2026-04-30',
                },
            )

        assert response.status_code == 422
        from app.services import periods_of_account_service as svc
        with app.app_context():
            local = svc.get_for_tax_year('2025-26')
        # Critical: local dates UNCHANGED (still original 6 Apr -> 5 Apr).
        assert local['period_start_date'] == seeded['period_start_date']
        assert local['period_end_date'] == seeded['period_end_date']

    def test_hmrc_5xx_leaves_local_unchanged(self, auth_client, app, connected):
        seeded = _seed_local_period(app, period_id='POA-9')

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.update_period_of_account',
            return_value=_hmrc_5xx(),
        ):
            response = auth_client.put(
                self.URL,
                json={
                    'nino': 'AA123456A',
                    'business_id': 'X1',
                    'start_date': '2025-05-01',
                    'end_date': '2026-04-30',
                },
            )

        assert response.status_code == 503
        from app.services import periods_of_account_service as svc
        with app.app_context():
            local = svc.get_for_tax_year('2025-26')
        assert local['period_start_date'] == seeded['period_start_date']


# ===========================================================================
# DELETE /period-of-account/<tax_year>
# ===========================================================================

class TestDelete:
    URL = '/api/hmrc/period-of-account/2025-26'

    def test_404_when_local_period_missing(self, auth_client, app, connected):
        response = auth_client.delete(
            self.URL, json={'nino': 'AA123456A', 'business_id': 'X1'},
        )
        assert response.status_code == 404

    def test_missing_nino_returns_400(self, auth_client, app, connected):
        _seed_local_period(app, period_id='POA-1')
        response = auth_client.delete(self.URL, json={'business_id': 'X1'})
        assert response.status_code == 400

    def test_409_when_no_hmrc_period_id_recorded(
        self, auth_client, app, connected,
    ):
        from app.services import periods_of_account_service as svc
        with app.app_context():
            svc.create_standard_period('2025-26')  # no period_id

        response = auth_client.delete(
            self.URL,
            json={'nino': 'AA123456A', 'business_id': 'X1'},
        )
        assert response.status_code == 409

    def test_successful_delete_soft_deletes_local(
        self, auth_client, app, connected,
    ):
        _seed_local_period(app, period_id='POA-9')

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.delete_period_of_account',
            return_value=_hmrc_delete_ok(),
        ) as mock_delete:
            response = auth_client.delete(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1'},
            )

        assert response.status_code == 200
        args = mock_delete.call_args.args
        assert args == ('AA123456A', 'X1', 'POA-9')

        from app.services import periods_of_account_service as svc
        with app.app_context():
            assert svc.get_for_tax_year('2025-26') is None
            # The row still exists in the table with deleted_at set.
            all_rows = svc.list_periods(include_deleted=True)
        assert any(
            r['tax_year'] == '2025-26' and r['deleted_at'] is not None
            for r in all_rows
        )

    def test_hmrc_4xx_does_not_soft_delete_local(
        self, auth_client, app, connected,
    ):
        _seed_local_period(app, period_id='POA-9')

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.delete_period_of_account',
            return_value=_hmrc_4xx(),
        ):
            response = auth_client.delete(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1'},
            )

        assert response.status_code == 422

        # Critical: local mirror still active (not soft-deleted).
        from app.services import periods_of_account_service as svc
        with app.app_context():
            local = svc.get_for_tax_year('2025-26')
        assert local is not None
        assert local['deleted_at'] is None

    def test_hmrc_5xx_does_not_soft_delete_local(
        self, auth_client, app, connected,
    ):
        _seed_local_period(app, period_id='POA-9')

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.delete_period_of_account',
            return_value=_hmrc_5xx(),
        ):
            response = auth_client.delete(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1'},
            )

        assert response.status_code == 503
        from app.services import periods_of_account_service as svc
        with app.app_context():
            local = svc.get_for_tax_year('2025-26')
        assert local is not None
