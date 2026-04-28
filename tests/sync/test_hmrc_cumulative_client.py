"""HMRCClient cumulative endpoint tests.

These tests mock requests.* and the OAuth/fraud-header layers so we can
verify the URL, HTTP method, headers, and body that HMRCClient sends -
without ever touching the real sandbox.
"""

from unittest.mock import MagicMock, patch

import pytest


CUMULATIVE_PAYLOAD = {
    'periodDates': {
        'periodStartDate': '2025-04-06',
        'periodEndDate': '2025-10-05',
    },
    'periodIncome': {'turnover': 3000.00, 'other': 0},
    'periodExpenses': {'travelCosts': 50.00, 'adminCosts': 75.00},
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
# submit_cumulative_period
# ---------------------------------------------------------------------------

class TestSubmitCumulativePeriod:
    def test_posts_to_cumulative_endpoint_with_taxyear_in_url(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(status=201)

        result = client.submit_cumulative_period(
            'AA123456A', 'XAIS12345678901', '2025-26', CUMULATIVE_PAYLOAD
        )

        assert result['success'] is True
        mock_requests.post.assert_called_once()
        url = mock_requests.post.call_args.args[0]
        assert url.endswith(
            '/individuals/business/self-employment/AA123456A/'
            'XAIS12345678901/period/cumulative/2025-26'
        )

    def test_normalises_slash_tax_year_to_yyyy_yy(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response()

        client.submit_cumulative_period(
            'AA123456A', 'X1', '2025/2026', CUMULATIVE_PAYLOAD
        )

        url = mock_requests.post.call_args.args[0]
        assert url.endswith('/period/cumulative/2025-26')

    def test_sandbox_url_is_test_api(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response()

        # Sandbox is the default in conftest (HMRC_ENVIRONMENT='sandbox').
        assert client.environment == 'sandbox'
        client.submit_cumulative_period(
            'AA123456A', 'X1', '2025-26', CUMULATIVE_PAYLOAD
        )

        url = mock_requests.post.call_args.args[0]
        assert url.startswith('https://test-api.service.hmrc.gov.uk/'), url

    def test_production_url_is_live_api(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response()

        # Flip the client into production mode without changing env vars.
        client.environment = 'production'
        client.base_url = 'https://api.service.hmrc.gov.uk'

        client.submit_cumulative_period(
            'AA123456A', 'X1', '2025-26', CUMULATIVE_PAYLOAD
        )

        url = mock_requests.post.call_args.args[0]
        assert url.startswith('https://api.service.hmrc.gov.uk/'), url
        # Must NOT leak the test sandbox into production calls.
        assert 'test-api' not in url

        # Production must NOT carry a Gov-Test-Scenario header.
        headers = mock_requests.post.call_args.kwargs['headers']
        assert 'Gov-Test-Scenario' not in headers

    def test_normalises_yyyy_yyyy_dash_form(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response()

        client.submit_cumulative_period(
            'AA123456A', 'X1', '2025-2026', CUMULATIVE_PAYLOAD
        )

        url = mock_requests.post.call_args.args[0]
        assert url.endswith('/period/cumulative/2025-26')

    def test_includes_fraud_prevention_headers(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response()

        client.submit_cumulative_period(
            'AA123456A', 'X1', '2025-26', CUMULATIVE_PAYLOAD
        )

        headers = mock_requests.post.call_args.kwargs['headers']
        # Fraud prevention header injected by build_fraud_prevention_headers
        assert headers.get('Gov-Client-Connection-Method') == 'WEB_APP_VIA_SERVER'

    def test_includes_oauth_bearer_token(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response()

        client.submit_cumulative_period(
            'AA123456A', 'X1', '2025-26', CUMULATIVE_PAYLOAD
        )

        headers = mock_requests.post.call_args.kwargs['headers']
        assert headers.get('Authorization') == 'Bearer fake-access-token'

    def test_uses_v5_accept_header(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response()

        client.submit_cumulative_period(
            'AA123456A', 'X1', '2025-26', CUMULATIVE_PAYLOAD
        )

        headers = mock_requests.post.call_args.kwargs['headers']
        assert headers['Accept'] == 'application/vnd.hmrc.5.0+json'

    def test_sends_payload_as_json_body(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response()

        client.submit_cumulative_period(
            'AA123456A', 'X1', '2025-26', CUMULATIVE_PAYLOAD
        )

        sent_body = mock_requests.post.call_args.kwargs['json']
        assert sent_body == CUMULATIVE_PAYLOAD

    def test_unauthenticated_returns_error_without_calling_requests(self, app):
        from app.services.hmrc_client import HMRCClient

        with app.test_request_context('/'):
            client = HMRCClient()
            with patch.object(
                client.auth_service, 'get_valid_access_token', return_value=None
            ), patch('app.services.hmrc_client.requests') as mock_requests:
                result = client.submit_cumulative_period(
                    'AA123456A', 'X1', '2025-26', CUMULATIVE_PAYLOAD
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
                    'path': '/periodIncome/turnover',
                    'message': 'Must be non-negative',
                    'code': 'FORMAT_VALUE',
                }
            ],
        }
        resp = MagicMock()
        resp.status_code = 422
        resp.content = b'{"errors":[]}'
        resp.json.return_value = body
        mock_requests.post.return_value = resp

        result = client.submit_cumulative_period(
            'AA123456A', 'X1', '2025-26', CUMULATIVE_PAYLOAD
        )

        assert result['success'] is False
        assert result['status_code'] == 422
        assert result['validation_errors'][0]['field'] == '/periodIncome/turnover'

    def test_5xx_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 503
        resp.content = b'{}'
        resp.json.return_value = {'message': 'Service unavailable'}
        mock_requests.post.return_value = resp

        result = client.submit_cumulative_period(
            'AA123456A', 'X1', '2025-26', CUMULATIVE_PAYLOAD
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

        result = client.submit_cumulative_period(
            'AA123456A', 'X1', '2025-26', CUMULATIVE_PAYLOAD
        )

        assert result['success'] is False
        assert 'timed out' in result['error'].lower()


# ---------------------------------------------------------------------------
# get_cumulative_period
# ---------------------------------------------------------------------------

class TestGetCumulativePeriod:
    def test_get_hits_cumulative_endpoint(self, patched_client):
        client, mock_requests = patched_client
        body = {
            'periodDates': {
                'periodStartDate': '2025-04-06',
                'periodEndDate': '2025-10-05',
            },
            'periodIncome': {'turnover': 3000.0, 'other': 0},
            'periodExpenses': {'adminCosts': 75.0},
        }
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{}'
        resp.json.return_value = body
        mock_requests.get.return_value = resp

        result = client.get_cumulative_period(
            'AA123456A', 'XAIS12345678901', '2025-26'
        )

        assert result['success'] is True
        assert result['data'] == body
        url = mock_requests.get.call_args.args[0]
        assert url.endswith(
            '/individuals/business/self-employment/AA123456A/'
            'XAIS12345678901/period/cumulative/2025-26'
        )

    def test_get_normalises_tax_year(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{}'
        resp.json.return_value = {}
        mock_requests.get.return_value = resp

        client.get_cumulative_period('AA123456A', 'X1', '2025/2026')

        url = mock_requests.get.call_args.args[0]
        assert url.endswith('/period/cumulative/2025-26')

    def test_get_404_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 404
        resp.content = b'{}'
        resp.json.return_value = {'message': 'Not found'}
        mock_requests.get.return_value = resp

        result = client.get_cumulative_period('AA123456A', 'X1', '2025-26')

        assert result['success'] is False
        assert result['status_code'] == 404
