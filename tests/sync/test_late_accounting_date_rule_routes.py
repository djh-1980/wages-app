"""Route tests for the Late Accounting Date Rule (LADR) endpoints.

The HMRCClient is mocked at the route level so no real HMRC sandbox
calls are made. The HMRC connection-status check is also mocked so we
can assert the route's behaviour independently of real OAuth state.

Two-phase write contract under test:
    1. Mutating routes call HMRCClient first.
    2. Local cache (settings table key=hmrc_ladr_<biz>_<ty>) is only
       updated after HMRC confirms success.
    3. HMRC failures must NOT corrupt the cache.

GET behaviour:
    - Connected + identifiers -> fresh fetch + cache refresh.
    - Disconnected            -> serve cache with stale=True.
"""

from unittest.mock import patch

import pytest


PAYLOAD_PATH = 'app.routes.api_hmrc'


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def connected(monkeypatch):
    from app.services.hmrc_auth import HMRCAuthService

    monkeypatch.setattr(
        HMRCAuthService,
        'get_connection_status',
        lambda self: {'connected': True, 'environment': 'sandbox'},
    )


@pytest.fixture
def disconnected(monkeypatch):
    from app.services.hmrc_auth import HMRCAuthService

    monkeypatch.setattr(
        HMRCAuthService,
        'get_connection_status',
        lambda self: {'connected': False, 'environment': 'sandbox'},
    )


# ---- HMRC return-value helpers --------------------------------------------

def _hmrc_get_applied():
    return {
        'success': True,
        'data': {'lateAccountingDateRuleDisapplied': False},
        'status_code': 200,
    }


def _hmrc_get_disapplied():
    return {
        'success': True,
        'data': {'lateAccountingDateRuleDisapplied': True},
        'status_code': 200,
    }


def _hmrc_204():
    return {'success': True, 'data': {}, 'status_code': 204}


def _hmrc_4xx():
    return {
        'success': False,
        'error': 'Validation failed',
        'status_code': 422,
        'validation_errors': [
            {'field': '/taxYear', 'message': 'Out of range', 'code': 'RULE_TY'}
        ],
    }


def _hmrc_5xx():
    return {
        'success': False,
        'error': 'Service unavailable',
        'status_code': 503,
    }


def _seed_cache(app, business_id='X1', tax_year='2025-26',
                status='Applied'):
    from app.services import hmrc_ladr_cache as ladr_cache
    with app.app_context():
        return ladr_cache.set(business_id, tax_year, status,
                              hmrc_response={'seed': True})


# ===========================================================================
# Auth & connection guards
# ===========================================================================

class TestAuthAndConnection:
    GET_URL = '/api/hmrc/late-accounting-date-rule/2025-26?nino=AA123456A&business_id=X1'
    POST_URL = '/api/hmrc/late-accounting-date-rule/2025-26/disapply'
    DELETE_URL = '/api/hmrc/late-accounting-date-rule/2025-26/disapply'

    def test_unauthenticated_get_blocked(self, client):
        response = client.get(self.GET_URL, follow_redirects=False)
        assert response.status_code in (302, 401)

    def test_unauthenticated_post_blocked(self, client):
        response = client.post(
            self.POST_URL,
            json={'nino': 'AA123456A', 'business_id': 'X1'},
            follow_redirects=False,
        )
        assert response.status_code in (302, 401)

    def test_unauthenticated_delete_blocked(self, client):
        response = client.delete(
            self.DELETE_URL,
            json={'nino': 'AA123456A', 'business_id': 'X1'},
            follow_redirects=False,
        )
        assert response.status_code in (302, 401)

    def test_post_without_hmrc_connection_returns_400(
        self, auth_client, disconnected,
    ):
        response = auth_client.post(
            self.POST_URL,
            json={'nino': 'AA123456A', 'business_id': 'X1'},
        )
        assert response.status_code == 400
        body = response.get_json()
        assert body['success'] is False
        assert 'connected' in body['error'].lower()

    def test_delete_without_hmrc_connection_returns_400(
        self, auth_client, disconnected,
    ):
        response = auth_client.delete(
            self.DELETE_URL,
            json={'nino': 'AA123456A', 'business_id': 'X1'},
        )
        assert response.status_code == 400


# ===========================================================================
# GET /late-accounting-date-rule/<tax_year>
# ===========================================================================

class TestGetRoute:
    def _url(self, tax_year='2025-26', nino='AA123456A', business_id='X1'):
        return (
            f'/api/hmrc/late-accounting-date-rule/{tax_year}'
            f'?nino={nino}&business_id={business_id}'
        )

    def test_400_when_identifiers_missing(self, auth_client, app, connected):
        response = auth_client.get('/api/hmrc/late-accounting-date-rule/2025-26')
        assert response.status_code == 400
        assert 'nino' in response.get_json()['error'].lower()

    def test_connected_fresh_fetch_returns_applied(
        self, auth_client, app, connected,
    ):
        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.get_late_accounting_date_rule',
            return_value=_hmrc_get_applied(),
        ) as mock_get:
            response = auth_client.get(self._url())

        assert response.status_code == 200
        body = response.get_json()
        assert body['success'] is True
        assert body['data']['status'] == 'Applied'
        assert body['data']['stale'] is False
        assert body['data']['source'] == 'hmrc'
        assert body['data']['last_synced_at']
        # HMRC was called with the right args.
        args = mock_get.call_args.args
        assert args == ('AA123456A', 'X1', '2025-26')

        # Cache was populated.
        from app.services import hmrc_ladr_cache as ladr_cache
        with app.app_context():
            cached = ladr_cache.get('X1', '2025-26')
        assert cached['status'] == 'Applied'

    def test_connected_fresh_fetch_returns_disapplied(
        self, auth_client, app, connected,
    ):
        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.get_late_accounting_date_rule',
            return_value=_hmrc_get_disapplied(),
        ):
            response = auth_client.get(self._url())

        assert response.status_code == 200
        body = response.get_json()
        assert body['data']['status'] == 'Disapplied'

    def test_disconnected_serves_cache_with_stale_flag(
        self, auth_client, app, disconnected,
    ):
        _seed_cache(app, status='Disapplied')

        response = auth_client.get(self._url())

        assert response.status_code == 200
        body = response.get_json()
        assert body['data']['status'] == 'Disapplied'
        assert body['data']['stale'] is True
        assert body['data']['source'] == 'cache'
        assert body['data']['last_synced_at']

    def test_disconnected_with_no_cache_returns_404(
        self, auth_client, app, disconnected,
    ):
        response = auth_client.get(self._url())
        assert response.status_code == 404

    def test_normalises_tax_year_in_route_layer(
        self, auth_client, app, connected,
    ):
        """The HMRC client normalises tax_year. We confirm that the route
        layer hands the URL-segment value through unchanged so the client's
        normaliser remains the single source of truth.

        Slashes are not used in URL segments (Flask treats them as path
        separators), so the realistic alternate-form input we test in the
        route layer is the explicit YYYY-YYYY dash form."""
        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.get_late_accounting_date_rule',
            return_value=_hmrc_get_applied(),
        ) as mock_get:
            response = auth_client.get(
                '/api/hmrc/late-accounting-date-rule/2025-2026'
                '?nino=AA123456A&business_id=X1'
            )

        assert response.status_code == 200, response.get_data(as_text=True)
        # Route passed the URL-decoded tax year through to the client.
        args = mock_get.call_args.args
        assert args[2] == '2025-2026'

    def test_hmrc_4xx_does_not_corrupt_cache(
        self, auth_client, app, connected,
    ):
        seeded = _seed_cache(app, status='Applied')

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.get_late_accounting_date_rule',
            return_value=_hmrc_4xx(),
        ):
            response = auth_client.get(self._url())

        assert response.status_code == 422
        body = response.get_json()
        assert body['success'] is False
        assert body['validation_errors'][0]['field'] == '/taxYear'
        # Optional cache fallback is surfaced.
        assert body['cached']['status'] == 'Applied'
        assert body['cached']['stale'] is True

        # Cache itself unchanged (still 'Applied').
        from app.services import hmrc_ladr_cache as ladr_cache
        with app.app_context():
            cached = ladr_cache.get('X1', '2025-26')
        assert cached['status'] == seeded['status']

    def test_hmrc_5xx_surfaces_error(self, auth_client, app, connected):
        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.get_late_accounting_date_rule',
            return_value=_hmrc_5xx(),
        ):
            response = auth_client.get(self._url())

        assert response.status_code == 503


# ===========================================================================
# POST /late-accounting-date-rule/<tax_year>/disapply
# ===========================================================================

class TestDisapplyRoute:
    URL = '/api/hmrc/late-accounting-date-rule/2025-26/disapply'

    def test_missing_identifiers_returns_400(self, auth_client, connected):
        response = auth_client.post(self.URL, json={'nino': 'AA123456A'})
        assert response.status_code == 400
        response = auth_client.post(self.URL, json={'business_id': 'X1'})
        assert response.status_code == 400

    def test_successful_disapply_caches_disapplied(
        self, auth_client, app, connected,
    ):
        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.disapply_late_accounting_date_rule',
            return_value=_hmrc_204(),
        ) as mock_put:
            response = auth_client.post(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1'},
            )

        assert response.status_code == 200, response.get_data(as_text=True)
        body = response.get_json()
        assert body['success'] is True
        assert body['data']['status'] == 'Disapplied'
        assert body['data']['last_synced_at']

        # HMRC was called with the right args.
        args = mock_put.call_args.args
        assert args == ('AA123456A', 'X1', '2025-26')

        # Cache reflects new status.
        from app.services import hmrc_ladr_cache as ladr_cache
        with app.app_context():
            cached = ladr_cache.get('X1', '2025-26')
        assert cached['status'] == 'Disapplied'

    def test_hmrc_4xx_leaves_cache_unchanged(
        self, auth_client, app, connected,
    ):
        seeded = _seed_cache(app, status='Applied')

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.disapply_late_accounting_date_rule',
            return_value=_hmrc_4xx(),
        ):
            response = auth_client.post(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1'},
            )

        assert response.status_code == 422
        body = response.get_json()
        assert body['validation_errors'][0]['field'] == '/taxYear'

        # Cache unchanged.
        from app.services import hmrc_ladr_cache as ladr_cache
        with app.app_context():
            cached = ladr_cache.get('X1', '2025-26')
        assert cached['status'] == seeded['status'] == 'Applied'

    def test_hmrc_5xx_leaves_cache_unchanged(
        self, auth_client, app, connected,
    ):
        seeded = _seed_cache(app, status='Applied')

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.disapply_late_accounting_date_rule',
            return_value=_hmrc_5xx(),
        ):
            response = auth_client.post(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1'},
            )

        assert response.status_code == 503
        from app.services import hmrc_ladr_cache as ladr_cache
        with app.app_context():
            cached = ladr_cache.get('X1', '2025-26')
        assert cached['status'] == seeded['status']


# ===========================================================================
# DELETE /late-accounting-date-rule/<tax_year>/disapply
# ===========================================================================

class TestWithdrawRoute:
    URL = '/api/hmrc/late-accounting-date-rule/2025-26/disapply'

    def test_missing_identifiers_returns_400(
        self, auth_client, app, connected,
    ):
        response = auth_client.delete(self.URL, json={'nino': 'AA123456A'})
        assert response.status_code == 400

    def test_successful_withdraw_caches_applied(
        self, auth_client, app, connected,
    ):
        # Seed cache as Disapplied so we can see it flip back to Applied.
        _seed_cache(app, status='Disapplied')

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.withdraw_late_accounting_date_rule_disapplication',
            return_value=_hmrc_204(),
        ) as mock_delete:
            response = auth_client.delete(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1'},
            )

        assert response.status_code == 200, response.get_data(as_text=True)
        body = response.get_json()
        assert body['success'] is True
        assert body['data']['status'] == 'Applied'

        args = mock_delete.call_args.args
        assert args == ('AA123456A', 'X1', '2025-26')

        from app.services import hmrc_ladr_cache as ladr_cache
        with app.app_context():
            cached = ladr_cache.get('X1', '2025-26')
        assert cached['status'] == 'Applied'

    def test_hmrc_4xx_leaves_cache_unchanged(
        self, auth_client, app, connected,
    ):
        seeded = _seed_cache(app, status='Disapplied')

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.withdraw_late_accounting_date_rule_disapplication',
            return_value=_hmrc_4xx(),
        ):
            response = auth_client.delete(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1'},
            )

        assert response.status_code == 422
        from app.services import hmrc_ladr_cache as ladr_cache
        with app.app_context():
            cached = ladr_cache.get('X1', '2025-26')
        assert cached['status'] == seeded['status'] == 'Disapplied'

    def test_hmrc_5xx_leaves_cache_unchanged(
        self, auth_client, app, connected,
    ):
        seeded = _seed_cache(app, status='Disapplied')

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.withdraw_late_accounting_date_rule_disapplication',
            return_value=_hmrc_5xx(),
        ):
            response = auth_client.delete(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1'},
            )

        assert response.status_code == 503
        from app.services import hmrc_ladr_cache as ladr_cache
        with app.app_context():
            cached = ladr_cache.get('X1', '2025-26')
        assert cached['status'] == seeded['status']


# ===========================================================================
# cache helper unit tests
# ===========================================================================

class TestLadrCache:
    def test_get_returns_none_when_empty(self, app):
        from app.services import hmrc_ladr_cache as ladr_cache
        with app.app_context():
            assert ladr_cache.get('X1', '2025-26') is None

    def test_set_then_get_roundtrip(self, app):
        from app.services import hmrc_ladr_cache as ladr_cache
        with app.app_context():
            ladr_cache.set('X1', '2025-26', 'Applied',
                           hmrc_response={'foo': 'bar'})
            cached = ladr_cache.get('X1', '2025-26')
        assert cached['status'] == 'Applied'
        assert cached['hmrc_response'] == {'foo': 'bar'}
        assert cached['last_synced_at']

    def test_set_rejects_invalid_status(self, app):
        from app.services import hmrc_ladr_cache as ladr_cache
        with app.app_context():
            with pytest.raises(ValueError):
                ladr_cache.set('X1', '2025-26', 'Bogus')

    def test_clear_removes_entry(self, app):
        from app.services import hmrc_ladr_cache as ladr_cache
        with app.app_context():
            ladr_cache.set('X1', '2025-26', 'Applied')
            ladr_cache.clear('X1', '2025-26')
            assert ladr_cache.get('X1', '2025-26') is None

    def test_keys_isolated_per_business_and_tax_year(self, app):
        from app.services import hmrc_ladr_cache as ladr_cache
        with app.app_context():
            ladr_cache.set('X1', '2025-26', 'Applied')
            ladr_cache.set('X2', '2025-26', 'Disapplied')
            ladr_cache.set('X1', '2024-25', 'Disapplied')
            assert ladr_cache.get('X1', '2025-26')['status'] == 'Applied'
            assert ladr_cache.get('X2', '2025-26')['status'] == 'Disapplied'
            assert ladr_cache.get('X1', '2024-25')['status'] == 'Disapplied'

    def test_derive_status_disapplied_flag(self):
        from app.services import hmrc_ladr_cache as ladr_cache
        assert ladr_cache.derive_status_from_hmrc_data(
            {'lateAccountingDateRuleDisapplied': True}
        ) == 'Disapplied'

    def test_derive_status_applied_flag(self):
        from app.services import hmrc_ladr_cache as ladr_cache
        assert ladr_cache.derive_status_from_hmrc_data(
            {'lateAccountingDateRuleDisapplied': False}
        ) == 'Applied'

    def test_derive_status_disapplications_array(self):
        from app.services import hmrc_ladr_cache as ladr_cache
        assert ladr_cache.derive_status_from_hmrc_data(
            {'disapplications': [{'date': '2025-04-06'}]}
        ) == 'Disapplied'

    def test_derive_status_unknown_for_empty_dict(self):
        from app.services import hmrc_ladr_cache as ladr_cache
        assert ladr_cache.derive_status_from_hmrc_data({}) == 'Unknown'
        assert ladr_cache.derive_status_from_hmrc_data(None) == 'Unknown'

    def test_derive_status_explicit_string(self):
        from app.services import hmrc_ladr_cache as ladr_cache
        assert ladr_cache.derive_status_from_hmrc_data(
            {'status': 'Disapplied'}
        ) == 'Disapplied'
