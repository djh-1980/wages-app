"""HMRCClient Late Accounting Date Rule (LADR) endpoint tests.

Mocks ``requests.*`` and the OAuth/fraud-header layers so we can verify
URL, HTTP method, headers and tax-year normalisation that HMRCClient
sends - without ever touching the real sandbox.

Endpoint family (Business Details API v2.0):
    GET    /individuals/business/details/{nino}/{businessId}/{taxYear}/late-accounting-date-rule
    PUT    /individuals/business/details/{nino}/{businessId}/{taxYear}/late-accounting-date-rule/disapply
    DELETE /individuals/business/details/{nino}/{businessId}/{taxYear}/late-accounting-date-rule/disapply
"""

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

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


def _ok_response(status=200, body=None):
    resp = MagicMock()
    resp.status_code = status
    resp.content = b'{}' if body is None else b'{"ok":true}'
    resp.json.return_value = body if body is not None else {}
    return resp


# ---------------------------------------------------------------------------
# tax-year normalisation
# ---------------------------------------------------------------------------

class TestTaxYearNormalisation:
    """Internal helper used by all 3 LADR methods."""

    def test_passthrough_yyyy_yy(self):
        from app.services.hmrc_client import HMRCClient
        assert HMRCClient._normalise_tax_year('2025-26') == '2025-26'

    def test_collapses_yyyy_slash_yyyy(self):
        from app.services.hmrc_client import HMRCClient
        assert HMRCClient._normalise_tax_year('2025/2026') == '2025-26'

    def test_collapses_yyyy_dash_yyyy(self):
        from app.services.hmrc_client import HMRCClient
        assert HMRCClient._normalise_tax_year('2025-2026') == '2025-26'

    def test_returns_unchanged_for_garbage(self):
        from app.services.hmrc_client import HMRCClient
        assert HMRCClient._normalise_tax_year(None) is None
        assert HMRCClient._normalise_tax_year('') == ''


# ---------------------------------------------------------------------------
# get_late_accounting_date_rule (GET)
# ---------------------------------------------------------------------------

class TestGetLateAccountingDateRule:
    def test_get_hits_correct_endpoint(self, patched_client):
        client, mock_requests = patched_client
        body = {'lateAccountingDateRule': 'applied'}
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{}'
        resp.json.return_value = body
        mock_requests.get.return_value = resp

        result = client.get_late_accounting_date_rule(
            'AA123456A', 'XAIS12345678901', '2025-26',
        )

        assert result['success'] is True
        assert result['data'] == body
        url = mock_requests.get.call_args.args[0]
        assert url.endswith(
            '/individuals/business/details/AA123456A/XAIS12345678901/'
            '2025-26/late-accounting-date-rule'
        )

    def test_normalises_slash_tax_year(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response()

        client.get_late_accounting_date_rule('AA123456A', 'X1', '2025/2026')

        url = mock_requests.get.call_args.args[0]
        assert '/2025-26/late-accounting-date-rule' in url

    def test_normalises_yyyy_yyyy_dash_form(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response()

        client.get_late_accounting_date_rule('AA123456A', 'X1', '2025-2026')

        url = mock_requests.get.call_args.args[0]
        assert '/2025-26/late-accounting-date-rule' in url

    def test_includes_oauth_and_fraud_headers(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response()

        client.get_late_accounting_date_rule('AA123456A', 'X1', '2025-26')

        headers = mock_requests.get.call_args.kwargs['headers']
        assert headers['Authorization'] == 'Bearer fake-access-token'
        assert headers['Gov-Client-Connection-Method'] == 'WEB_APP_VIA_SERVER'
        assert headers['Accept'] == 'application/vnd.hmrc.2.0+json'

    def test_sandbox_url_is_test_api(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response()

        assert client.environment == 'sandbox'
        client.get_late_accounting_date_rule('AA123456A', 'X1', '2025-26')

        url = mock_requests.get.call_args.args[0]
        assert url.startswith('https://test-api.service.hmrc.gov.uk/')

    def test_production_url_is_live_api(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response()

        client.environment = 'production'
        client.base_url = 'https://api.service.hmrc.gov.uk'
        client.get_late_accounting_date_rule('AA123456A', 'X1', '2025-26')

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

        result = client.get_late_accounting_date_rule(
            'AA123456A', 'X1', '2025-26',
        )

        assert result['success'] is False
        assert result['status_code'] == 404

    def test_5xx_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 502
        resp.content = b'{}'
        resp.json.return_value = {'message': 'Bad gateway'}
        mock_requests.get.return_value = resp

        result = client.get_late_accounting_date_rule(
            'AA123456A', 'X1', '2025-26',
        )

        assert result['success'] is False
        assert result['status_code'] == 502

    def test_network_error_returns_error_envelope(self, patched_client):
        import requests as real_requests
        client, mock_requests = patched_client
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.get.side_effect = real_requests.exceptions.ReadTimeout(
            'read timed out'
        )

        result = client.get_late_accounting_date_rule(
            'AA123456A', 'X1', '2025-26',
        )

        assert result['success'] is False
        assert 'timed out' in result['error'].lower()

    def test_unauthenticated_returns_error_without_calling_requests(self, app):
        from app.services.hmrc_client import HMRCClient

        with app.test_request_context('/'):
            client = HMRCClient()
            with patch.object(
                client.auth_service,
                'get_valid_access_token',
                return_value=None,
            ), patch('app.services.hmrc_client.requests') as mock_requests:
                result = client.get_late_accounting_date_rule(
                    'AA123456A', 'X1', '2025-26',
                )

        assert result['success'] is False
        assert 'authenticated' in result['error'].lower()
        mock_requests.get.assert_not_called()


# ---------------------------------------------------------------------------
# disapply_late_accounting_date_rule (PUT)
# ---------------------------------------------------------------------------

class TestDisapplyLateAccountingDateRule:
    def test_put_hits_disapply_endpoint(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 204
        resp.content = b''
        resp.json.return_value = {}
        mock_requests.put.return_value = resp

        result = client.disapply_late_accounting_date_rule(
            'AA123456A', 'XAIS12345678901', '2025-26',
        )

        assert result['success'] is True
        url = mock_requests.put.call_args.args[0]
        assert url.endswith(
            '/individuals/business/details/AA123456A/XAIS12345678901/'
            '2025-26/late-accounting-date-rule/disapply'
        )

    def test_put_sends_empty_body(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.put.return_value = _ok_response(status=204)

        client.disapply_late_accounting_date_rule('AA123456A', 'X1', '2025-26')

        # HMRC's PUT for disapply takes no body. We send an empty dict so
        # the request still includes a JSON content-type header.
        sent_body = mock_requests.put.call_args.kwargs['json']
        assert sent_body == {}

    def test_normalises_slash_tax_year(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.put.return_value = _ok_response(status=204)

        client.disapply_late_accounting_date_rule(
            'AA123456A', 'X1', '2025/2026',
        )

        url = mock_requests.put.call_args.args[0]
        assert '/2025-26/late-accounting-date-rule/disapply' in url

    def test_includes_oauth_and_fraud_headers(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.put.return_value = _ok_response(status=204)

        client.disapply_late_accounting_date_rule(
            'AA123456A', 'X1', '2025-26',
        )

        headers = mock_requests.put.call_args.kwargs['headers']
        assert headers['Authorization'] == 'Bearer fake-access-token'
        assert headers['Gov-Client-Connection-Method'] == 'WEB_APP_VIA_SERVER'
        assert headers['Accept'] == 'application/vnd.hmrc.2.0+json'

    def test_sandbox_url_is_test_api(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.put.return_value = _ok_response(status=204)

        client.disapply_late_accounting_date_rule(
            'AA123456A', 'X1', '2025-26',
        )

        url = mock_requests.put.call_args.args[0]
        assert url.startswith('https://test-api.service.hmrc.gov.uk/')

    def test_production_url_is_live_api(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.put.return_value = _ok_response(status=204)

        client.environment = 'production'
        client.base_url = 'https://api.service.hmrc.gov.uk'
        client.disapply_late_accounting_date_rule(
            'AA123456A', 'X1', '2025-26',
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
                    'path': '/taxYear',
                    'message': 'Tax year out of range',
                    'code': 'RULE_TAX_YEAR_NOT_SUPPORTED',
                }
            ],
        }
        resp = MagicMock()
        resp.status_code = 422
        resp.content = b'{"errors":[]}'
        resp.json.return_value = body
        mock_requests.put.return_value = resp

        result = client.disapply_late_accounting_date_rule(
            'AA123456A', 'X1', '2025-26',
        )

        assert result['success'] is False
        assert result['status_code'] == 422
        assert result['validation_errors'][0]['field'] == '/taxYear'
        assert (
            result['validation_errors'][0]['code']
            == 'RULE_TAX_YEAR_NOT_SUPPORTED'
        )

    def test_5xx_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 503
        resp.content = b'{}'
        resp.json.return_value = {'message': 'Service unavailable'}
        mock_requests.put.return_value = resp

        result = client.disapply_late_accounting_date_rule(
            'AA123456A', 'X1', '2025-26',
        )

        assert result['success'] is False
        assert result['status_code'] == 503

    def test_network_error_returns_error_envelope(self, patched_client):
        import requests as real_requests
        client, mock_requests = patched_client
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.put.side_effect = real_requests.exceptions.ConnectTimeout(
            'connection timed out'
        )

        result = client.disapply_late_accounting_date_rule(
            'AA123456A', 'X1', '2025-26',
        )

        assert result['success'] is False
        assert 'timed out' in result['error'].lower()

    def test_unauthenticated_returns_error_without_calling_requests(self, app):
        from app.services.hmrc_client import HMRCClient

        with app.test_request_context('/'):
            client = HMRCClient()
            with patch.object(
                client.auth_service,
                'get_valid_access_token',
                return_value=None,
            ), patch('app.services.hmrc_client.requests') as mock_requests:
                result = client.disapply_late_accounting_date_rule(
                    'AA123456A', 'X1', '2025-26',
                )

        assert result['success'] is False
        assert 'authenticated' in result['error'].lower()
        mock_requests.put.assert_not_called()


# ---------------------------------------------------------------------------
# withdraw_late_accounting_date_rule_disapplication (DELETE)
# ---------------------------------------------------------------------------

class TestWithdrawLateAccountingDateRuleDisapplication:
    def test_delete_hits_disapply_endpoint(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 204
        resp.content = b''
        resp.json.return_value = {}
        mock_requests.delete.return_value = resp

        result = client.withdraw_late_accounting_date_rule_disapplication(
            'AA123456A', 'XAIS12345678901', '2025-26',
        )

        assert result['success'] is True
        url = mock_requests.delete.call_args.args[0]
        assert url.endswith(
            '/individuals/business/details/AA123456A/XAIS12345678901/'
            '2025-26/late-accounting-date-rule/disapply'
        )

    def test_204_no_content_returns_empty_data(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 204
        resp.content = b''
        resp.json.return_value = {}
        mock_requests.delete.return_value = resp

        result = client.withdraw_late_accounting_date_rule_disapplication(
            'AA123456A', 'X1', '2025-26',
        )

        assert result['success'] is True
        assert result['data'] == {}
        assert result['status_code'] == 204

    def test_normalises_slash_tax_year(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.delete.return_value = _ok_response(status=204)

        client.withdraw_late_accounting_date_rule_disapplication(
            'AA123456A', 'X1', '2025/2026',
        )

        url = mock_requests.delete.call_args.args[0]
        assert '/2025-26/late-accounting-date-rule/disapply' in url

    def test_includes_oauth_and_fraud_headers(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.delete.return_value = _ok_response(status=204)

        client.withdraw_late_accounting_date_rule_disapplication(
            'AA123456A', 'X1', '2025-26',
        )

        headers = mock_requests.delete.call_args.kwargs['headers']
        assert headers['Authorization'] == 'Bearer fake-access-token'
        assert headers['Gov-Client-Connection-Method'] == 'WEB_APP_VIA_SERVER'
        assert headers['Accept'] == 'application/vnd.hmrc.2.0+json'

    def test_production_url_is_live_api(self, patched_client):
        client, mock_requests = patched_client
        mock_requests.delete.return_value = _ok_response(status=204)

        client.environment = 'production'
        client.base_url = 'https://api.service.hmrc.gov.uk'
        client.withdraw_late_accounting_date_rule_disapplication(
            'AA123456A', 'X1', '2025-26',
        )

        url = mock_requests.delete.call_args.args[0]
        assert url.startswith('https://api.service.hmrc.gov.uk/')
        headers = mock_requests.delete.call_args.kwargs['headers']
        assert 'Gov-Test-Scenario' not in headers

    def test_404_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 404
        resp.content = b'{}'
        resp.json.return_value = {'message': 'No disapplication on record'}
        mock_requests.delete.return_value = resp

        result = client.withdraw_late_accounting_date_rule_disapplication(
            'AA123456A', 'X1', '2025-26',
        )

        assert result['success'] is False
        assert result['status_code'] == 404

    def test_5xx_returns_error_envelope(self, patched_client):
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 500
        resp.content = b'{}'
        resp.json.return_value = {'message': 'Internal server error'}
        mock_requests.delete.return_value = resp

        result = client.withdraw_late_accounting_date_rule_disapplication(
            'AA123456A', 'X1', '2025-26',
        )

        assert result['success'] is False
        assert result['status_code'] == 500

    def test_network_error_returns_error_envelope(self, patched_client):
        import requests as real_requests
        client, mock_requests = patched_client
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.delete.side_effect = (
            real_requests.exceptions.ConnectionError('connection refused')
        )

        result = client.withdraw_late_accounting_date_rule_disapplication(
            'AA123456A', 'X1', '2025-26',
        )

        assert result['success'] is False
        assert 'connection' in result['error'].lower()

    def test_unauthenticated_returns_error_without_calling_requests(self, app):
        from app.services.hmrc_client import HMRCClient

        with app.test_request_context('/'):
            client = HMRCClient()
            with patch.object(
                client.auth_service,
                'get_valid_access_token',
                return_value=None,
            ), patch('app.services.hmrc_client.requests') as mock_requests:
                result = client.withdraw_late_accounting_date_rule_disapplication(
                    'AA123456A', 'X1', '2025-26',
                )

        assert result['success'] is False
        assert 'authenticated' in result['error'].lower()
        mock_requests.delete.assert_not_called()
