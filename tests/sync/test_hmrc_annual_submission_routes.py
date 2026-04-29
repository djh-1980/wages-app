"""HMRCClient Annual Summary endpoint tests + new Annual Submission route tests.

Covers:
- ``HMRCClient.get_annual_summary`` and ``update_annual_summary`` (no
  prior tests existed despite the methods being on the client since
  earlier phases). HTTP layer mocked.
- The new clean RESTful route family at ``/api/hmrc/annual-submission/<tax_year>``
  added in Phase 2.4. Two-phase write contract:
    1. PUT calls HMRC client first.
    2. Local cache (settings table key=hmrc_annual_last_<biz>_<ty>) only
       updates after HMRC confirms success.
    3. HMRC failures must NOT corrupt the cache.
"""

from unittest.mock import MagicMock, patch

import pytest


PAYLOAD_PATH = 'app.routes.api_hmrc'


# ===========================================================================
# fixtures
# ===========================================================================

@pytest.fixture
def patched_client(app):
    """HMRCClient with auth + fraud headers + requests stubbed out."""
    from app.services.hmrc_client import HMRCClient

    with app.test_request_context('/'):
        client = HMRCClient()
        with patch.object(
            client.auth_service,
            'get_valid_access_token',
            return_value='fake-access-token',
        ), patch(
            'app.services.hmrc_fraud_headers.build_fraud_prevention_headers',
            return_value={'Gov-Client-Connection-Method': 'WEB_APP_VIA_SERVER'},
        ), patch('app.services.hmrc_client.requests') as mock_requests:
            yield client, mock_requests


def _ok_response(status=200, body=None):
    resp = MagicMock()
    resp.status_code = status
    resp.content = b'{}' if body is None else b'{"ok":true}'
    resp.json.return_value = body if body is not None else {}
    return resp


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

def _hmrc_get_ok(annual_data=None):
    return {
        'success': True,
        'data': annual_data or {
            'allowances': {'annualInvestmentAllowance': 0},
            'adjustments': {'averagingAdjustment': 0},
        },
        'status_code': 200,
    }


def _hmrc_put_ok():
    return {'success': True, 'data': {}, 'status_code': 204}


def _hmrc_404():
    return {'success': False, 'error': 'Not found', 'status_code': 404}


def _hmrc_4xx():
    return {
        'success': False,
        'error': 'Validation failed',
        'status_code': 422,
        'validation_errors': [
            {'field': '/allowances/annualInvestmentAllowance',
             'message': 'Must be non-negative',
             'code': 'RULE_INVALID_AMOUNT'}
        ],
    }


def _hmrc_5xx():
    return {'success': False, 'error': 'Service unavailable', 'status_code': 503}


def _sample_annual_data():
    """Realistic Daniel-shape payload: cash basis, mostly zero."""
    return {
        'adjustments': {
            'averagingAdjustment': 0,
            'includedNonTaxableProfits': 0,
        },
        'allowances': {
            'annualInvestmentAllowance': 0,
            'capitalAllowanceMainPool': 0,
            'zeroEmissionsCarAllowance': 0,
        },
        'nonFinancials': {
            'businessDetailsChangedRecently': False,
        },
    }


# ===========================================================================
# HMRCClient: get_annual_summary
# ===========================================================================

class TestGetAnnualSummary:
    def test_get_hits_correct_endpoint(self, patched_client):
        client, mock_requests = patched_client
        body = _sample_annual_data()
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{}'
        resp.json.return_value = body
        mock_requests.get.return_value = resp

        result = client.get_annual_summary(
            'AA123456A', 'XAIS12345678901', '2025-26',
        )

        assert result['success'] is True
        assert result['data'] == body
        url = mock_requests.get.call_args.args[0]
        assert url.endswith(
            '/individuals/business/self-employment/AA123456A/'
            'XAIS12345678901/annual/2025-26'
        )

    def test_includes_oauth_and_fraud_headers(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response(status=200, body={})

        client.get_annual_summary('AA123456A', 'X1', '2025-26')

        headers = mock_requests.get.call_args.kwargs['headers']
        assert headers['Authorization'] == 'Bearer fake-access-token'
        assert headers['Gov-Client-Connection-Method'] == 'WEB_APP_VIA_SERVER'

    def test_sandbox_url_is_test_api(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response(status=200, body={})

        assert client.environment == 'sandbox'
        client.get_annual_summary('AA123456A', 'X1', '2025-26')

        url = mock_requests.get.call_args.args[0]
        assert url.startswith('https://test-api.service.hmrc.gov.uk/')

    def test_production_url_is_live_api(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response(status=200, body={})

        client.environment = 'production'
        client.base_url = 'https://api.service.hmrc.gov.uk'
        client.get_annual_summary('AA123456A', 'X1', '2025-26')

        url = mock_requests.get.call_args.args[0]
        assert url.startswith('https://api.service.hmrc.gov.uk/')
        headers = mock_requests.get.call_args.kwargs['headers']
        assert 'Gov-Test-Scenario' not in headers

    def test_404_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 404
        resp.content = b'{}'
        resp.json.return_value = {'message': 'No annual summary on file'}
        mock_requests.get.return_value = resp

        result = client.get_annual_summary('AA123456A', 'X1', '2025-26')

        assert result['success'] is False
        assert result['status_code'] == 404

    def test_5xx_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 503
        resp.content = b'{}'
        resp.json.return_value = {'message': 'Service unavailable'}
        mock_requests.get.return_value = resp

        result = client.get_annual_summary('AA123456A', 'X1', '2025-26')

        assert result['success'] is False
        assert result['status_code'] == 503

    def test_unauthenticated_short_circuits(self, app):
        from app.services.hmrc_client import HMRCClient
        with app.test_request_context('/'):
            client = HMRCClient()
            with patch.object(
                client.auth_service,
                'get_valid_access_token',
                return_value=None,
            ), patch('app.services.hmrc_client.requests') as mock_requests:
                result = client.get_annual_summary('AA123456A', 'X1', '2025-26')
        assert result['success'] is False
        mock_requests.get.assert_not_called()


# ===========================================================================
# HMRCClient: update_annual_summary
# ===========================================================================

class TestUpdateAnnualSummary:
    def test_put_hits_correct_endpoint(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 204
        resp.content = b''
        resp.json.return_value = {}
        mock_requests.put.return_value = resp

        result = client.update_annual_summary(
            'AA123456A', 'XAIS12345678901', '2025-26', _sample_annual_data(),
        )

        assert result['success'] is True
        url = mock_requests.put.call_args.args[0]
        assert url.endswith(
            '/individuals/business/self-employment/AA123456A/'
            'XAIS12345678901/annual/2025-26'
        )

    def test_put_forwards_payload_verbatim(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.put.return_value = _ok_response(status=204, body={})
        payload = _sample_annual_data()

        client.update_annual_summary('AA123456A', 'X1', '2025-26', payload)

        sent = mock_requests.put.call_args.kwargs['json']
        assert sent == payload

    def test_4xx_validation_errors_surface(self, patched_client):
        client, mock_requests = patched_client
        body = {
            'message': 'Invalid request',
            'errors': [
                {
                    'path': '/allowances/annualInvestmentAllowance',
                    'message': 'Must be non-negative',
                    'code': 'RULE_INVALID_AMOUNT',
                }
            ],
        }
        resp = MagicMock()
        resp.status_code = 422
        resp.content = b'{"errors":[]}'
        resp.json.return_value = body
        mock_requests.put.return_value = resp

        result = client.update_annual_summary(
            'AA123456A', 'X1', '2025-26', _sample_annual_data(),
        )

        assert result['success'] is False
        assert result['status_code'] == 422
        assert (
            result['validation_errors'][0]['field']
            == '/allowances/annualInvestmentAllowance'
        )

    def test_5xx_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 503
        resp.content = b'{}'
        resp.json.return_value = {'message': 'Service unavailable'}
        mock_requests.put.return_value = resp

        result = client.update_annual_summary(
            'AA123456A', 'X1', '2025-26', _sample_annual_data(),
        )

        assert result['success'] is False
        assert result['status_code'] == 503

    def test_network_timeout_returns_error_envelope(self, patched_client):
        import requests as real_requests
        client, mock_requests = patched_client
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.put.side_effect = real_requests.exceptions.ReadTimeout(
            'read timed out',
        )

        result = client.update_annual_summary(
            'AA123456A', 'X1', '2025-26', _sample_annual_data(),
        )

        assert result['success'] is False
        assert 'timed out' in result['error'].lower()

    def test_unauthenticated_short_circuits(self, app):
        from app.services.hmrc_client import HMRCClient
        with app.test_request_context('/'):
            client = HMRCClient()
            with patch.object(
                client.auth_service,
                'get_valid_access_token',
                return_value=None,
            ), patch('app.services.hmrc_client.requests') as mock_requests:
                result = client.update_annual_summary(
                    'AA123456A', 'X1', '2025-26', _sample_annual_data(),
                )
        assert result['success'] is False
        mock_requests.put.assert_not_called()


# ===========================================================================
# Routes - auth + connection guards
# ===========================================================================

class TestRouteAuthAndConnection:
    GET_URL = '/api/hmrc/annual-submission/2025-26?nino=AA123456A&business_id=X1'
    PUT_URL = '/api/hmrc/annual-submission/2025-26'
    DRAFT_URL = '/api/hmrc/annual-submission/2025-26/draft'

    def test_unauthenticated_get_blocked(self, client):
        response = client.get(self.GET_URL, follow_redirects=False)
        assert response.status_code in (302, 401)

    def test_unauthenticated_put_blocked(self, client):
        response = client.put(
            self.PUT_URL,
            json={'nino': 'AA123456A', 'business_id': 'X1',
                  'annual_data': _sample_annual_data()},
            follow_redirects=False,
        )
        assert response.status_code in (302, 401)

    def test_unauthenticated_draft_post_blocked(self, client):
        response = client.post(
            self.DRAFT_URL,
            json={'business_id': 'X1', 'annual_data': {}},
            follow_redirects=False,
        )
        assert response.status_code in (302, 401)

    def test_unauthenticated_draft_delete_blocked(self, client):
        response = client.delete(
            self.DRAFT_URL,
            json={'business_id': 'X1'},
            follow_redirects=False,
        )
        assert response.status_code in (302, 401)

    def test_put_without_hmrc_connection_returns_400(
        self, auth_client, disconnected,
    ):
        response = auth_client.put(
            self.PUT_URL,
            json={'nino': 'AA123456A', 'business_id': 'X1',
                  'annual_data': _sample_annual_data()},
        )
        assert response.status_code == 400
        body = response.get_json()
        assert 'connected' in body['error'].lower()


# ===========================================================================
# GET /annual-submission/<tax_year>
# ===========================================================================

class TestGetRoute:
    def _url(self, tax_year='2025-26', nino='AA123456A', business_id='X1'):
        return (
            f'/api/hmrc/annual-submission/{tax_year}'
            f'?nino={nino}&business_id={business_id}'
        )

    def test_400_when_identifiers_missing(self, auth_client, connected):
        response = auth_client.get('/api/hmrc/annual-submission/2025-26')
        assert response.status_code == 400

    def test_connected_fresh_fetch_returns_hmrc_data(
        self, auth_client, app, connected,
    ):
        sample = _sample_annual_data()
        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.get_annual_summary',
            return_value=_hmrc_get_ok(sample),
        ) as mock_get:
            response = auth_client.get(self._url())

        assert response.status_code == 200, response.get_data(as_text=True)
        body = response.get_json()
        assert body['success'] is True
        assert body['data']['hmrc_data'] == sample
        assert body['data']['stale'] is False
        assert body['data']['source'] == 'hmrc'

        args = mock_get.call_args.args
        assert args == ('AA123456A', 'X1', '2025-26')

    def test_connected_404_surfaces_as_success_with_no_data(
        self, auth_client, connected,
    ):
        """HMRC 404 = no annual submission yet; UI should be allowed to
        start a fresh one rather than seeing an error."""
        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.get_annual_summary',
            return_value=_hmrc_404(),
        ):
            response = auth_client.get(self._url())

        assert response.status_code == 200
        body = response.get_json()
        assert body['success'] is True
        assert body['data']['hmrc_data'] is None
        assert body['data']['source'] == 'hmrc'

    def test_connected_4xx_other_surfaces_error_with_cache_payload(
        self, auth_client, app, connected,
    ):
        # Seed a draft so the route can return it alongside the error.
        from app.services import hmrc_annual_submission_cache as ac
        with app.app_context():
            ac.set_draft('X1', '2025-26', _sample_annual_data())

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.get_annual_summary',
            return_value=_hmrc_4xx(),
        ):
            response = auth_client.get(self._url())

        assert response.status_code == 422
        body = response.get_json()
        assert body['success'] is False
        assert body['validation_errors'][0]['field'].startswith('/allowances')
        # Draft surfaced alongside error.
        assert body['draft']['annual_data'] == _sample_annual_data()

    def test_disconnected_serves_cache_with_stale_flag(
        self, auth_client, app, disconnected,
    ):
        from app.services import hmrc_annual_submission_cache as ac
        sample = _sample_annual_data()
        with app.app_context():
            ac.set_last_submitted('X1', '2025-26', sample)
            ac.set_draft('X1', '2025-26', sample)

        response = auth_client.get(self._url())

        assert response.status_code == 200
        body = response.get_json()
        assert body['data']['stale'] is True
        assert body['data']['source'] == 'cache'
        assert body['data']['last_submitted']['annual_data'] == sample
        assert body['data']['draft']['annual_data'] == sample


# ===========================================================================
# PUT /annual-submission/<tax_year>
# ===========================================================================

class TestSubmitRoute:
    URL = '/api/hmrc/annual-submission/2025-26'

    def test_missing_identifiers_returns_400(self, auth_client, connected):
        response = auth_client.put(
            self.URL,
            json={'annual_data': _sample_annual_data()},
        )
        assert response.status_code == 400

    def test_missing_annual_data_returns_400(self, auth_client, connected):
        response = auth_client.put(
            self.URL,
            json={'nino': 'AA123456A', 'business_id': 'X1'},
        )
        assert response.status_code == 400

    def test_empty_annual_data_returns_400(self, auth_client, connected):
        response = auth_client.put(
            self.URL,
            json={'nino': 'AA123456A', 'business_id': 'X1', 'annual_data': {}},
        )
        assert response.status_code == 400

    def test_successful_put_records_last_submitted_and_clears_draft(
        self, auth_client, app, connected,
    ):
        # Seed a draft so we can verify it gets cleared on success.
        from app.services import hmrc_annual_submission_cache as ac
        with app.app_context():
            ac.set_draft('X1', '2025-26', {'allowances': {'foo': 1}})

        payload = _sample_annual_data()
        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.update_annual_summary',
            return_value=_hmrc_put_ok(),
        ) as mock_put:
            response = auth_client.put(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1',
                      'annual_data': payload},
            )

        assert response.status_code == 200, response.get_data(as_text=True)
        body = response.get_json()
        assert body['success'] is True
        assert body['data']['submitted_at']
        assert body['data']['annual_data'] == payload

        args = mock_put.call_args.args
        assert args == ('AA123456A', 'X1', '2025-26', payload)

        # Cache reflects the submission, draft cleared.
        with app.app_context():
            last = ac.get_last_submitted('X1', '2025-26')
            draft = ac.get_draft('X1', '2025-26')
        assert last is not None
        assert last['annual_data'] == payload
        assert draft is None

    def test_hmrc_4xx_leaves_cache_unchanged(
        self, auth_client, app, connected,
    ):
        from app.services import hmrc_annual_submission_cache as ac
        seeded_payload = {'allowances': {'seed': 1}}
        with app.app_context():
            ac.set_draft('X1', '2025-26', seeded_payload)
        # No prior last_submitted on file.

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.update_annual_summary',
            return_value=_hmrc_4xx(),
        ):
            response = auth_client.put(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1',
                      'annual_data': _sample_annual_data()},
            )

        assert response.status_code == 422
        body = response.get_json()
        assert body['validation_errors'][0]['field'].startswith('/allowances')

        # Critical: no last_submitted recorded; draft preserved.
        with app.app_context():
            assert ac.get_last_submitted('X1', '2025-26') is None
            draft = ac.get_draft('X1', '2025-26')
        assert draft['annual_data'] == seeded_payload

    def test_hmrc_5xx_leaves_cache_unchanged(self, auth_client, app, connected):
        from app.services import hmrc_annual_submission_cache as ac

        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.update_annual_summary',
            return_value=_hmrc_5xx(),
        ):
            response = auth_client.put(
                self.URL,
                json={'nino': 'AA123456A', 'business_id': 'X1',
                      'annual_data': _sample_annual_data()},
            )

        assert response.status_code == 503
        with app.app_context():
            assert ac.get_last_submitted('X1', '2025-26') is None


# ===========================================================================
# POST/DELETE /annual-submission/<tax_year>/draft
# ===========================================================================

class TestDraftRoutes:
    URL = '/api/hmrc/annual-submission/2025-26/draft'

    def test_save_draft_without_business_id_returns_400(self, auth_client):
        response = auth_client.post(
            self.URL, json={'annual_data': _sample_annual_data()},
        )
        assert response.status_code == 400

    def test_save_draft_with_invalid_annual_data_returns_400(self, auth_client):
        response = auth_client.post(
            self.URL, json={'business_id': 'X1', 'annual_data': 'not-a-dict'},
        )
        assert response.status_code == 400

    def test_save_draft_persists_locally_without_calling_hmrc(
        self, auth_client, app,
    ):
        payload = _sample_annual_data()
        with patch(
            f'{PAYLOAD_PATH}.HMRCClient.update_annual_summary',
        ) as mock_put:
            response = auth_client.post(
                self.URL,
                json={'business_id': 'X1', 'annual_data': payload},
            )

        assert response.status_code == 200
        mock_put.assert_not_called()

        from app.services import hmrc_annual_submission_cache as ac
        with app.app_context():
            draft = ac.get_draft('X1', '2025-26')
        assert draft['annual_data'] == payload

    def test_delete_draft_clears_cache(self, auth_client, app):
        from app.services import hmrc_annual_submission_cache as ac
        with app.app_context():
            ac.set_draft('X1', '2025-26', _sample_annual_data())

        response = auth_client.delete(
            self.URL, json={'business_id': 'X1'},
        )

        assert response.status_code == 200
        with app.app_context():
            assert ac.get_draft('X1', '2025-26') is None

    def test_delete_draft_no_business_id_returns_400(self, auth_client):
        response = auth_client.delete(self.URL, json={})
        assert response.status_code == 400


# ===========================================================================
# Cache helper unit tests
# ===========================================================================

class TestAnnualSubmissionCache:
    def test_get_draft_returns_none_when_empty(self, app):
        from app.services import hmrc_annual_submission_cache as ac
        with app.app_context():
            assert ac.get_draft('X1', '2025-26') is None

    def test_set_then_get_draft(self, app):
        from app.services import hmrc_annual_submission_cache as ac
        payload = _sample_annual_data()
        with app.app_context():
            ac.set_draft('X1', '2025-26', payload)
            draft = ac.get_draft('X1', '2025-26')
        assert draft['annual_data'] == payload
        assert draft['updated_at']

    def test_set_draft_rejects_non_dict(self, app):
        from app.services import hmrc_annual_submission_cache as ac
        with app.app_context():
            with pytest.raises(ValueError):
                ac.set_draft('X1', '2025-26', 'oops')

    def test_clear_draft_removes_entry(self, app):
        from app.services import hmrc_annual_submission_cache as ac
        with app.app_context():
            ac.set_draft('X1', '2025-26', {'a': 1})
            ac.clear_draft('X1', '2025-26')
            assert ac.get_draft('X1', '2025-26') is None

    def test_set_then_get_last_submitted(self, app):
        from app.services import hmrc_annual_submission_cache as ac
        payload = _sample_annual_data()
        with app.app_context():
            ac.set_last_submitted('X1', '2025-26', payload,
                                  hmrc_response={'echoed': True})
            last = ac.get_last_submitted('X1', '2025-26')
        assert last['annual_data'] == payload
        assert last['hmrc_response'] == {'echoed': True}
        assert last['submitted_at']

    def test_keys_isolated_per_business_and_tax_year(self, app):
        from app.services import hmrc_annual_submission_cache as ac
        with app.app_context():
            ac.set_draft('X1', '2025-26', {'a': 1})
            ac.set_draft('X2', '2025-26', {'b': 2})
            ac.set_draft('X1', '2024-25', {'c': 3})
            assert ac.get_draft('X1', '2025-26')['annual_data'] == {'a': 1}
            assert ac.get_draft('X2', '2025-26')['annual_data'] == {'b': 2}
            assert ac.get_draft('X1', '2024-25')['annual_data'] == {'c': 3}

    def test_drafts_and_last_submitted_keys_dont_collide(self, app):
        """A draft and a last-submitted record for the same business+ty
        must coexist without overwriting each other."""
        from app.services import hmrc_annual_submission_cache as ac
        with app.app_context():
            ac.set_draft('X1', '2025-26', {'draft': True})
            ac.set_last_submitted('X1', '2025-26', {'submitted': True})
            assert ac.get_draft('X1', '2025-26')['annual_data'] == {'draft': True}
            assert (
                ac.get_last_submitted('X1', '2025-26')['annual_data']
                == {'submitted': True}
            )
