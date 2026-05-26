"""HMRCClient BSAS endpoint tests.

These tests verify the new BSAS list and submit adjustments endpoints,
covering both the HMRCClient methods and the Flask API routes.
"""

from unittest.mock import MagicMock, patch

import pytest


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
    """Create a mock successful response."""
    resp = MagicMock()
    resp.status_code = status
    resp.content = b'{}' if body is None else b'{"ok":true}'
    resp.json.return_value = body if body is not None else {}
    return resp


def _error_response(status=404, body=None):
    """Create a mock error response."""
    resp = MagicMock()
    resp.status_code = status
    resp.content = b'{"error":"Not found"}' if body is None else b'{"error":"test error"}'
    resp.json.return_value = body if body is not None else {'error': 'Not found'}
    return resp


# ---------------------------------------------------------------------------
# list_bsas_summaries
# ---------------------------------------------------------------------------

class TestListBsasSummaries:
    def test_gets_list_endpoint_with_nino(self, patched_client):
        """Verify GET request to correct endpoint with NINO in path."""
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response(body={'summaries': []})

        result = client.list_bsas_summaries('AA123456A', '2024-25', 'self-employment')

        assert result['success'] is True
        mock_requests.get.assert_called_once()
        url = mock_requests.get.call_args.args[0]
        assert url.endswith('/individuals/self-assessment/adjustable-summary/AA123456A')

    def test_includes_tax_year_query_param(self, patched_client):
        """Verify tax year is passed as query parameter."""
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response(body={'summaries': []})

        client.list_bsas_summaries('AA123456A', '2024-25', 'self-employment')

        params = mock_requests.get.call_args.kwargs.get('params', {})
        assert 'taxYear' in params
        assert params['taxYear'] == '2024-25'

    def test_includes_type_of_business_query_param(self, patched_client):
        """Verify typeOfBusiness is passed as query parameter."""
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response(body={'summaries': []})

        client.list_bsas_summaries('AA123456A', '2024-25', 'uk-property')

        params = mock_requests.get.call_args.kwargs.get('params', {})
        assert params['typeOfBusiness'] == 'uk-property'

    def test_normalises_slash_tax_year(self, patched_client):
        """Verify tax year with slash is normalized to YYYY-YY format."""
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response(body={'summaries': []})

        client.list_bsas_summaries('AA123456A', '2024/2025', 'self-employment')

        params = mock_requests.get.call_args.kwargs.get('params', {})
        assert params['taxYear'] == '2024-25'

    def test_handles_success_response(self, patched_client):
        """Verify successful response is parsed correctly."""
        client, mock_requests = patched_client
        mock_data = {
            'summaries': [
                {'calculationId': 'calc123', 'status': 'valid', 'typeOfBusiness': 'self-employment'}
            ]
        }
        mock_requests.get.return_value = _ok_response(body=mock_data)

        result = client.list_bsas_summaries('AA123456A', '2024-25')

        assert result['success'] is True
        assert result['data'] == mock_data

    def test_handles_404_error(self, patched_client):
        """Verify 404 error is handled gracefully."""
        client, mock_requests = patched_client
        mock_requests.get.return_value = _error_response(status=404)

        result = client.list_bsas_summaries('AA123456A', '2024-25')

        assert result['success'] is False
        assert 'error' in result

    def test_uses_bsas_api_version_7(self, patched_client):
        """Verify Accept header uses BSAS API v7.0."""
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response(body={'summaries': []})

        client.list_bsas_summaries('AA123456A', '2024-25')

        headers = mock_requests.get.call_args.kwargs.get('headers', {})
        assert 'Accept' in headers
        assert 'vnd.hmrc.7.0+json' in headers['Accept']


# ---------------------------------------------------------------------------
# submit_bsas_adjustments
# ---------------------------------------------------------------------------

class TestSubmitBsasAdjustments:
    def test_posts_to_adjust_endpoint(self, patched_client):
        """Verify POST request to correct adjustment endpoint."""
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(status=201)

        adjustments = {
            'income': {'turnover': 1000.00},
            'expenses': {'costOfGoods': 200.00}
        }
        result = client.submit_bsas_adjustments('AA123456A', 'calc123', adjustments)

        assert result['success'] is True
        mock_requests.post.assert_called_once()
        url = mock_requests.post.call_args.args[0]
        assert url.endswith(
            '/individuals/self-assessment/adjustable-summary/AA123456A/'
            'self-employment/calc123/adjust'
        )

    def test_filters_zero_income_values(self, patched_client):
        """Verify zero income values are filtered out."""
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(status=201)

        adjustments = {
            'income': {'turnover': 1000.00, 'other': 0},
            'expenses': {}
        }
        client.submit_bsas_adjustments('AA123456A', 'calc123', adjustments)

        json_data = mock_requests.post.call_args.kwargs.get('json', {})
        assert 'income' in json_data
        assert 'turnover' in json_data['income']
        assert 'other' not in json_data['income']

    def test_filters_zero_expense_values(self, patched_client):
        """Verify zero expense values are filtered out."""
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(status=201)

        adjustments = {
            'income': {},
            'expenses': {'costOfGoods': 200.00, 'adminCosts': 0, 'travelCosts': 50.00}
        }
        client.submit_bsas_adjustments('AA123456A', 'calc123', adjustments)

        json_data = mock_requests.post.call_args.kwargs.get('json', {})
        assert 'expenses' in json_data
        assert 'costOfGoods' in json_data['expenses']
        assert 'travelCosts' in json_data['expenses']
        assert 'adminCosts' not in json_data['expenses']

    def test_omits_empty_income_section(self, patched_client):
        """Verify empty income section is omitted entirely."""
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(status=201)

        adjustments = {
            'income': {'turnover': 0, 'other': 0},
            'expenses': {'costOfGoods': 200.00}
        }
        client.submit_bsas_adjustments('AA123456A', 'calc123', adjustments)

        json_data = mock_requests.post.call_args.kwargs.get('json', {})
        assert 'income' not in json_data
        assert 'expenses' in json_data

    def test_omits_empty_expenses_section(self, patched_client):
        """Verify empty expenses section is omitted entirely."""
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(status=201)

        adjustments = {
            'income': {'turnover': 1000.00},
            'expenses': {'costOfGoods': 0, 'adminCosts': 0}
        }
        client.submit_bsas_adjustments('AA123456A', 'calc123', adjustments)

        json_data = mock_requests.post.call_args.kwargs.get('json', {})
        assert 'income' in json_data
        assert 'expenses' not in json_data

    def test_handles_success_response(self, patched_client):
        """Verify successful submission response."""
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(status=201, body={'status': 'submitted'})

        adjustments = {'income': {'turnover': 1000.00}}
        result = client.submit_bsas_adjustments('AA123456A', 'calc123', adjustments)

        assert result['success'] is True
        assert result['data']['status'] == 'submitted'

    def test_handles_validation_error(self, patched_client):
        """Verify validation error is handled gracefully."""
        client, mock_requests = patched_client
        mock_requests.post.return_value = _error_response(
            status=400,
            body={'error': 'Invalid adjustment values'}
        )

        adjustments = {'income': {'turnover': -1000.00}}
        result = client.submit_bsas_adjustments('AA123456A', 'calc123', adjustments)

        assert result['success'] is False
        assert 'error' in result

    def test_uses_bsas_api_version_7(self, patched_client):
        """Verify Accept header uses BSAS API v7.0."""
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(status=201)

        adjustments = {'income': {'turnover': 1000.00}}
        client.submit_bsas_adjustments('AA123456A', 'calc123', adjustments)

        headers = mock_requests.post.call_args.kwargs.get('headers', {})
        assert 'Accept' in headers
        assert 'vnd.hmrc.7.0+json' in headers['Accept']


# ---------------------------------------------------------------------------
# Flask API Route Tests
# ---------------------------------------------------------------------------

class TestBsasListRoute:
    def test_list_route_requires_nino(self, auth_client):
        """Verify list route returns 400 without NINO."""
        response = auth_client.get('/api/hmrc/bsas/list/2024-25')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'NINO' in data['error']

    def test_list_route_validates_nino_format(self, auth_client):
        """Verify list route validates NINO format."""
        response = auth_client.get('/api/hmrc/bsas/list/2024-25?nino=INVALID')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    @patch('app.routes.api_hmrc.HMRCClient')
    def test_list_route_returns_success(self, mock_client_class, auth_client):
        """Verify list route returns successful response."""
        mock_client = MagicMock()
        mock_client.list_bsas_summaries.return_value = {
            'success': True,
            'data': {'summaries': []}
        }
        mock_client_class.return_value = mock_client

        response = auth_client.get('/api/hmrc/bsas/list/2024-25?nino=AA123456A')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    @patch('app.routes.api_hmrc.HMRCClient')
    def test_list_route_handles_client_error(self, mock_client_class, auth_client):
        """Verify list route handles client errors."""
        mock_client = MagicMock()
        mock_client.list_bsas_summaries.return_value = {
            'success': False,
            'error': 'HMRC API error'
        }
        mock_client_class.return_value = mock_client

        response = auth_client.get('/api/hmrc/bsas/list/2024-25?nino=AA123456A')
        data = response.get_json()
        assert data['success'] is False


class TestBsasAdjustRoute:
    def test_adjust_route_requires_nino(self, auth_client):
        """Verify adjust route returns 400 without NINO."""
        response = auth_client.post(
            '/api/hmrc/bsas/calc123/adjust',
            json={'adjustments': {}}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'nino' in data['error']

    def test_adjust_route_requires_adjustments(self, auth_client):
        """Verify adjust route returns 400 without adjustments."""
        response = auth_client.post(
            '/api/hmrc/bsas/calc123/adjust',
            json={'nino': 'AA123456A'}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'adjustments' in data['error']

    def test_adjust_route_validates_nino_format(self, auth_client):
        """Verify adjust route validates NINO format."""
        response = auth_client.post(
            '/api/hmrc/bsas/calc123/adjust',
            json={'nino': 'INVALID', 'adjustments': {}}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    @patch('app.routes.api_hmrc.HMRCClient')
    def test_adjust_route_returns_success(self, mock_client_class, auth_client):
        """Verify adjust route returns successful response."""
        mock_client = MagicMock()
        mock_client.submit_bsas_adjustments.return_value = {
            'success': True,
            'data': {'status': 'submitted'}
        }
        mock_client_class.return_value = mock_client

        response = auth_client.post(
            '/api/hmrc/bsas/calc123/adjust',
            json={
                'nino': 'AA123456A',
                'adjustments': {'income': {'turnover': 1000.00}}
            }
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    @patch('app.routes.api_hmrc.HMRCClient')
    def test_adjust_route_handles_client_error(self, mock_client_class, auth_client):
        """Verify adjust route handles client errors."""
        mock_client = MagicMock()
        mock_client.submit_bsas_adjustments.return_value = {
            'success': False,
            'error': 'Invalid adjustments'
        }
        mock_client_class.return_value = mock_client

        response = auth_client.post(
            '/api/hmrc/bsas/calc123/adjust',
            json={
                'nino': 'AA123456A',
                'adjustments': {'income': {'turnover': -1000.00}}
            }
        )
        data = response.get_json()
        assert data['success'] is False
