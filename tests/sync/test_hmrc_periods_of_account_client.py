"""HMRCClient Periods of Account endpoint tests.

These tests mock requests.* and the OAuth/fraud-header layers so we can
verify URL, HTTP method, headers and body that HMRCClient sends - without
ever touching the real sandbox.

Endpoint family (Business Details API v2.0):
    POST   /individuals/business/details/{nino}/{businessId}/periods-of-account
    GET    /individuals/business/details/{nino}/{businessId}/periods-of-account
    PUT    /individuals/business/details/{nino}/{businessId}/periods-of-account/{periodId}
    DELETE /individuals/business/details/{nino}/{businessId}/periods-of-account/{periodId}
"""

from unittest.mock import MagicMock, patch

import pytest


PERIOD_PAYLOAD = {
    'startDate': '2025-04-06',
    'endDate': '2026-04-05',
}


@pytest.fixture
def patched_client(app):
    """Yield an HMRCClient with auth + fraud headers + requests stubbed."""
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
        ), patch(
            'app.services.hmrc_client.requests'
        ) as mock_requests:
            yield client, mock_requests


def _ok_response(status=201, body=None):
    resp = MagicMock()
    resp.status_code = status
    resp.content = b'{}' if body is None else b'{"ok":true}'
    resp.json.return_value = body if body is not None else {}
    return resp


# ---------------------------------------------------------------------------
# create_period_of_account (POST)
# ---------------------------------------------------------------------------

class TestCreatePeriodOfAccount:
    def test_posts_to_correct_endpoint(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(
            status=201, body={'periodId': 'POA-123'}
        )

        result = client.create_period_of_account(
            'AA123456A', 'XAIS12345678901', PERIOD_PAYLOAD
        )

        assert result['success'] is True
        assert result['data'] == {'periodId': 'POA-123'}
        mock_requests.post.assert_called_once()
        url = mock_requests.post.call_args.args[0]
        assert url.endswith(
            '/individuals/business/details/AA123456A/'
            'XAIS12345678901/periods-of-account'
        )

    def test_sandbox_url_is_test_api(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response()

        assert client.environment == 'sandbox'
        client.create_period_of_account(
            'AA123456A', 'X1', PERIOD_PAYLOAD
        )

        url = mock_requests.post.call_args.args[0]
        assert url.startswith('https://test-api.service.hmrc.gov.uk/'), url

    def test_production_url_is_live_api(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response()

        # Flip into production mode without changing env vars.
        client.environment = 'production'
        client.base_url = 'https://api.service.hmrc.gov.uk'

        client.create_period_of_account(
            'AA123456A', 'X1', PERIOD_PAYLOAD
        )

        url = mock_requests.post.call_args.args[0]
        assert url.startswith('https://api.service.hmrc.gov.uk/'), url
        assert 'test-api' not in url

        # Production must NOT carry a Gov-Test-Scenario header.
        headers = mock_requests.post.call_args.kwargs['headers']
        assert 'Gov-Test-Scenario' not in headers

    def test_includes_fraud_prevention_headers(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response()

        client.create_period_of_account('AA123456A', 'X1', PERIOD_PAYLOAD)

        headers = mock_requests.post.call_args.kwargs['headers']
        assert headers.get('Gov-Client-Connection-Method') == 'WEB_APP_VIA_SERVER'

    def test_includes_oauth_bearer_token(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response()

        client.create_period_of_account('AA123456A', 'X1', PERIOD_PAYLOAD)

        headers = mock_requests.post.call_args.kwargs['headers']
        assert headers.get('Authorization') == 'Bearer fake-access-token'

    def test_uses_v2_accept_header(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response()

        client.create_period_of_account('AA123456A', 'X1', PERIOD_PAYLOAD)

        headers = mock_requests.post.call_args.kwargs['headers']
        # Business Details API is v2.0
        assert headers['Accept'] == 'application/vnd.hmrc.2.0+json'

    def test_sends_payload_as_json_body(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response()

        client.create_period_of_account('AA123456A', 'X1', PERIOD_PAYLOAD)

        sent_body = mock_requests.post.call_args.kwargs['json']
        assert sent_body == PERIOD_PAYLOAD

    def test_unauthenticated_returns_error_without_calling_requests(self, app):
        from app.services.hmrc_client import HMRCClient

        with app.test_request_context('/'):
            client = HMRCClient()
            with patch.object(
                client.auth_service, 'get_valid_access_token', return_value=None
            ), patch('app.services.hmrc_client.requests') as mock_requests:
                result = client.create_period_of_account(
                    'AA123456A', 'X1', PERIOD_PAYLOAD
                )

        assert result['success'] is False
        assert 'authenticated' in result['error'].lower()
        mock_requests.post.assert_not_called()

    def test_4xx_validation_error_surfaces_field_details(self, patched_client):
        client, mock_requests = patched_client
        body = {
            'message': 'Invalid request',
            'errors': [
                {
                    'path': '/startDate',
                    'message': 'Must be a valid ISO date',
                    'code': 'FORMAT_DATE',
                }
            ],
        }
        resp = MagicMock()
        resp.status_code = 422
        resp.content = b'{"errors":[]}'
        resp.json.return_value = body
        mock_requests.post.return_value = resp

        result = client.create_period_of_account(
            'AA123456A', 'X1', PERIOD_PAYLOAD
        )

        assert result['success'] is False
        assert result['status_code'] == 422
        assert result['validation_errors'][0]['field'] == '/startDate'
        assert result['validation_errors'][0]['code'] == 'FORMAT_DATE'

    def test_5xx_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 503
        resp.content = b'{}'
        resp.json.return_value = {'message': 'Service unavailable'}
        mock_requests.post.return_value = resp

        result = client.create_period_of_account(
            'AA123456A', 'X1', PERIOD_PAYLOAD
        )

        assert result['success'] is False
        assert result['status_code'] == 503

    def test_network_error_returns_error_envelope(self, patched_client):
        import requests as real_requests
        client, mock_requests = patched_client
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.post.side_effect = real_requests.exceptions.ConnectTimeout(
            'connection timed out'
        )

        result = client.create_period_of_account(
            'AA123456A', 'X1', PERIOD_PAYLOAD
        )

        assert result['success'] is False
        assert 'timed out' in result['error'].lower()


# ---------------------------------------------------------------------------
# list_periods_of_account (GET)
# ---------------------------------------------------------------------------

class TestListPeriodsOfAccount:
    def test_get_hits_correct_endpoint(self, patched_client):
        client, mock_requests = patched_client
        body = {
            'periodsOfAccount': [
                {
                    'periodId': 'POA-1',
                    'startDate': '2025-04-06',
                    'endDate': '2026-04-05',
                }
            ]
        }
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{}'
        resp.json.return_value = body
        mock_requests.get.return_value = resp

        result = client.list_periods_of_account(
            'AA123456A', 'XAIS12345678901'
        )

        assert result['success'] is True
        assert result['data'] == body
        url = mock_requests.get.call_args.args[0]
        assert url.endswith(
            '/individuals/business/details/AA123456A/'
            'XAIS12345678901/periods-of-account'
        )

    def test_includes_oauth_and_fraud_headers(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{}'
        resp.json.return_value = {}
        mock_requests.get.return_value = resp

        client.list_periods_of_account('AA123456A', 'X1')

        headers = mock_requests.get.call_args.kwargs['headers']
        assert headers['Authorization'] == 'Bearer fake-access-token'
        assert headers['Gov-Client-Connection-Method'] == 'WEB_APP_VIA_SERVER'
        assert headers['Accept'] == 'application/vnd.hmrc.2.0+json'

    def test_production_url_is_live_api(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{}'
        resp.json.return_value = {}
        mock_requests.get.return_value = resp

        client.environment = 'production'
        client.base_url = 'https://api.service.hmrc.gov.uk'
        client.list_periods_of_account('AA123456A', 'X1')

        url = mock_requests.get.call_args.args[0]
        assert url.startswith('https://api.service.hmrc.gov.uk/')
        headers = mock_requests.get.call_args.kwargs['headers']
        assert 'Gov-Test-Scenario' not in headers

    def test_404_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 404
        resp.content = b'{}'
        resp.json.return_value = {'message': 'Not found'}
        mock_requests.get.return_value = resp

        result = client.list_periods_of_account('AA123456A', 'X1')

        assert result['success'] is False
        assert result['status_code'] == 404

    def test_5xx_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 502
        resp.content = b'{}'
        resp.json.return_value = {'message': 'Bad gateway'}
        mock_requests.get.return_value = resp

        result = client.list_periods_of_account('AA123456A', 'X1')

        assert result['success'] is False
        assert result['status_code'] == 502

    def test_network_error_returns_error_envelope(self, patched_client):
        import requests as real_requests
        client, mock_requests = patched_client
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.get.side_effect = real_requests.exceptions.ReadTimeout(
            'read timed out'
        )

        result = client.list_periods_of_account('AA123456A', 'X1')

        assert result['success'] is False
        assert 'timed out' in result['error'].lower()

    def test_unauthenticated_returns_error_without_calling_requests(self, app):
        from app.services.hmrc_client import HMRCClient

        with app.test_request_context('/'):
            client = HMRCClient()
            with patch.object(
                client.auth_service, 'get_valid_access_token', return_value=None
            ), patch('app.services.hmrc_client.requests') as mock_requests:
                result = client.list_periods_of_account('AA123456A', 'X1')

        assert result['success'] is False
        assert 'authenticated' in result['error'].lower()
        mock_requests.get.assert_not_called()


# ---------------------------------------------------------------------------
# update_period_of_account (PUT)
# ---------------------------------------------------------------------------

class TestUpdatePeriodOfAccount:
    def test_put_includes_period_id_in_url(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{}'
        resp.json.return_value = {}
        mock_requests.put.return_value = resp

        result = client.update_period_of_account(
            'AA123456A', 'XAIS12345678901', 'POA-42',
            {'startDate': '2025-05-01', 'endDate': '2026-04-30'},
        )

        assert result['success'] is True
        url = mock_requests.put.call_args.args[0]
        assert url.endswith(
            '/individuals/business/details/AA123456A/'
            'XAIS12345678901/periods-of-account/POA-42'
        )

    def test_sends_payload_as_json_body(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{}'
        resp.json.return_value = {}
        mock_requests.put.return_value = resp

        new_payload = {'startDate': '2025-05-01', 'endDate': '2026-04-30'}
        client.update_period_of_account(
            'AA123456A', 'X1', 'POA-1', new_payload
        )

        sent_body = mock_requests.put.call_args.kwargs['json']
        assert sent_body == new_payload

    def test_includes_oauth_and_fraud_headers(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{}'
        resp.json.return_value = {}
        mock_requests.put.return_value = resp

        client.update_period_of_account(
            'AA123456A', 'X1', 'POA-1', PERIOD_PAYLOAD
        )

        headers = mock_requests.put.call_args.kwargs['headers']
        assert headers['Authorization'] == 'Bearer fake-access-token'
        assert headers['Gov-Client-Connection-Method'] == 'WEB_APP_VIA_SERVER'
        assert headers['Accept'] == 'application/vnd.hmrc.2.0+json'

    def test_production_url_is_live_api(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{}'
        resp.json.return_value = {}
        mock_requests.put.return_value = resp

        client.environment = 'production'
        client.base_url = 'https://api.service.hmrc.gov.uk'
        client.update_period_of_account(
            'AA123456A', 'X1', 'POA-1', PERIOD_PAYLOAD
        )

        url = mock_requests.put.call_args.args[0]
        assert url.startswith('https://api.service.hmrc.gov.uk/')
        headers = mock_requests.put.call_args.kwargs['headers']
        assert 'Gov-Test-Scenario' not in headers

    def test_4xx_validation_error_surfaces_field_details(self, patched_client):
        client, mock_requests = patched_client
        body = {
            'message': 'Invalid request',
            'errors': [
                {
                    'path': '/endDate',
                    'message': 'End date must be after start date',
                    'code': 'RULE_DATE_RANGE',
                }
            ],
        }
        resp = MagicMock()
        resp.status_code = 422
        resp.content = b'{"errors":[]}'
        resp.json.return_value = body
        mock_requests.put.return_value = resp

        result = client.update_period_of_account(
            'AA123456A', 'X1', 'POA-1', PERIOD_PAYLOAD
        )

        assert result['success'] is False
        assert result['status_code'] == 422
        assert result['validation_errors'][0]['field'] == '/endDate'
        assert result['validation_errors'][0]['code'] == 'RULE_DATE_RANGE'

    def test_5xx_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 500
        resp.content = b'{}'
        resp.json.return_value = {'message': 'Internal server error'}
        mock_requests.put.return_value = resp

        result = client.update_period_of_account(
            'AA123456A', 'X1', 'POA-1', PERIOD_PAYLOAD
        )

        assert result['success'] is False
        assert result['status_code'] == 500

    def test_network_error_returns_error_envelope(self, patched_client):
        import requests as real_requests
        client, mock_requests = patched_client
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.put.side_effect = real_requests.exceptions.ConnectTimeout(
            'connection timed out'
        )

        result = client.update_period_of_account(
            'AA123456A', 'X1', 'POA-1', PERIOD_PAYLOAD
        )

        assert result['success'] is False
        assert 'timed out' in result['error'].lower()

    def test_unauthenticated_returns_error_without_calling_requests(self, app):
        from app.services.hmrc_client import HMRCClient

        with app.test_request_context('/'):
            client = HMRCClient()
            with patch.object(
                client.auth_service, 'get_valid_access_token', return_value=None
            ), patch('app.services.hmrc_client.requests') as mock_requests:
                result = client.update_period_of_account(
                    'AA123456A', 'X1', 'POA-1', PERIOD_PAYLOAD
                )

        assert result['success'] is False
        assert 'authenticated' in result['error'].lower()
        mock_requests.put.assert_not_called()


# ---------------------------------------------------------------------------
# delete_period_of_account (DELETE)
# ---------------------------------------------------------------------------

class TestDeletePeriodOfAccount:
    def test_delete_hits_period_specific_endpoint(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 204
        resp.content = b''
        resp.json.return_value = {}
        mock_requests.delete.return_value = resp

        result = client.delete_period_of_account(
            'AA123456A', 'XAIS12345678901', 'POA-42'
        )

        assert result['success'] is True
        url = mock_requests.delete.call_args.args[0]
        assert url.endswith(
            '/individuals/business/details/AA123456A/'
            'XAIS12345678901/periods-of-account/POA-42'
        )

    def test_204_no_content_returns_empty_data_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 204
        resp.content = b''
        resp.json.return_value = {}
        mock_requests.delete.return_value = resp

        result = client.delete_period_of_account(
            'AA123456A', 'X1', 'POA-1'
        )

        assert result['success'] is True
        assert result['data'] == {}
        assert result['status_code'] == 204

    def test_includes_oauth_and_fraud_headers(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 204
        resp.content = b''
        resp.json.return_value = {}
        mock_requests.delete.return_value = resp

        client.delete_period_of_account('AA123456A', 'X1', 'POA-1')

        headers = mock_requests.delete.call_args.kwargs['headers']
        assert headers['Authorization'] == 'Bearer fake-access-token'
        assert headers['Gov-Client-Connection-Method'] == 'WEB_APP_VIA_SERVER'
        assert headers['Accept'] == 'application/vnd.hmrc.2.0+json'

    def test_sandbox_url_is_test_api(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 204
        resp.content = b''
        resp.json.return_value = {}
        mock_requests.delete.return_value = resp

        client.delete_period_of_account('AA123456A', 'X1', 'POA-1')

        url = mock_requests.delete.call_args.args[0]
        assert url.startswith('https://test-api.service.hmrc.gov.uk/')

    def test_production_url_is_live_api(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 204
        resp.content = b''
        resp.json.return_value = {}
        mock_requests.delete.return_value = resp

        client.environment = 'production'
        client.base_url = 'https://api.service.hmrc.gov.uk'
        client.delete_period_of_account('AA123456A', 'X1', 'POA-1')

        url = mock_requests.delete.call_args.args[0]
        assert url.startswith('https://api.service.hmrc.gov.uk/')
        headers = mock_requests.delete.call_args.kwargs['headers']
        assert 'Gov-Test-Scenario' not in headers

    def test_404_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 404
        resp.content = b'{}'
        resp.json.return_value = {'message': 'Not found'}
        mock_requests.delete.return_value = resp

        result = client.delete_period_of_account(
            'AA123456A', 'X1', 'POA-MISSING'
        )

        assert result['success'] is False
        assert result['status_code'] == 404

    def test_5xx_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 503
        resp.content = b'{}'
        resp.json.return_value = {'message': 'Service unavailable'}
        mock_requests.delete.return_value = resp

        result = client.delete_period_of_account(
            'AA123456A', 'X1', 'POA-1'
        )

        assert result['success'] is False
        assert result['status_code'] == 503

    def test_network_error_returns_error_envelope(self, patched_client):
        import requests as real_requests
        client, mock_requests = patched_client
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.delete.side_effect = real_requests.exceptions.ConnectionError(
            'connection refused'
        )

        result = client.delete_period_of_account(
            'AA123456A', 'X1', 'POA-1'
        )

        assert result['success'] is False
        assert 'connection' in result['error'].lower()

    def test_unauthenticated_returns_error_without_calling_requests(self, app):
        from app.services.hmrc_client import HMRCClient

        with app.test_request_context('/'):
            client = HMRCClient()
            with patch.object(
                client.auth_service, 'get_valid_access_token', return_value=None
            ), patch('app.services.hmrc_client.requests') as mock_requests:
                result = client.delete_period_of_account(
                    'AA123456A', 'X1', 'POA-1'
                )

        assert result['success'] is False
        assert 'authenticated' in result['error'].lower()
        mock_requests.delete.assert_not_called()
