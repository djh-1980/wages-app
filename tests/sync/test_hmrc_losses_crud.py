"""HMRCClient Individual Losses CRUD endpoint tests.

These tests verify the new losses retrieve, update, and delete endpoints,
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
# get_loss
# ---------------------------------------------------------------------------

class TestGetLoss:
    def test_gets_loss_endpoint_with_loss_id(self, patched_client):
        """Verify GET request to correct endpoint with loss_id in path."""
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response(body={
            'lossId': 'AAZZ1234567890a',
            'lossAmount': 1000.00
        })

        result = client.get_loss('AA123456A', 'AAZZ1234567890a')

        assert result['success'] is True
        mock_requests.get.assert_called_once()
        url = mock_requests.get.call_args.args[0]
        assert url.endswith('/individuals/losses/AA123456A/brought-forward-losses/AAZZ1234567890a')

    def test_handles_success_response(self, patched_client):
        """Verify successful response is parsed correctly."""
        client, mock_requests = patched_client
        mock_data = {
            'lossId': 'AAZZ1234567890a',
            'taxYearBroughtForwardFrom': '2023-24',
            'typeOfLoss': 'self-employment',
            'businessId': 'XBIS12345678901',
            'lossAmount': 1000.00,
            'lastModified': '2024-01-15T10:30:00Z'
        }
        mock_requests.get.return_value = _ok_response(body=mock_data)

        result = client.get_loss('AA123456A', 'AAZZ1234567890a')

        assert result['success'] is True
        assert result['data'] == mock_data

    def test_handles_404_error(self, patched_client):
        """Verify 404 error is handled gracefully."""
        client, mock_requests = patched_client
        mock_requests.get.return_value = _error_response(status=404)

        result = client.get_loss('AA123456A', 'INVALID_ID')

        assert result['success'] is False
        assert 'error' in result

    def test_uses_losses_api_version_6(self, patched_client):
        """Verify Accept header uses Individual Losses API v6.0."""
        client, mock_requests = patched_client
        mock_requests.get.return_value = _ok_response(body={'lossId': 'test'})

        client.get_loss('AA123456A', 'AAZZ1234567890a')

        headers = mock_requests.get.call_args.kwargs.get('headers', {})
        assert 'Accept' in headers
        assert 'vnd.hmrc.6.0+json' in headers['Accept']


# ---------------------------------------------------------------------------
# update_loss
# ---------------------------------------------------------------------------

class TestUpdateLoss:
    def test_puts_to_change_amount_endpoint(self, patched_client):
        """Verify PUT request to correct change-loss-amount endpoint."""
        client, mock_requests = patched_client
        mock_requests.put.return_value = _ok_response(status=200)

        result = client.update_loss('AA123456A', 'AAZZ1234567890a', 1500.00)

        assert result['success'] is True
        mock_requests.put.assert_called_once()
        url = mock_requests.put.call_args.args[0]
        assert url.endswith(
            '/individuals/losses/AA123456A/brought-forward-losses/AAZZ1234567890a/change-loss-amount'
        )

    def test_includes_loss_amount_in_payload(self, patched_client):
        """Verify lossAmount is included in request payload."""
        client, mock_requests = patched_client
        mock_requests.put.return_value = _ok_response(status=200)

        client.update_loss('AA123456A', 'AAZZ1234567890a', 1500.00)

        json_data = mock_requests.put.call_args.kwargs.get('json', {})
        assert 'lossAmount' in json_data
        assert json_data['lossAmount'] == 1500.00

    def test_converts_amount_to_float(self, patched_client):
        """Verify amount is converted to float."""
        client, mock_requests = patched_client
        mock_requests.put.return_value = _ok_response(status=200)

        client.update_loss('AA123456A', 'AAZZ1234567890a', '1500.50')

        json_data = mock_requests.put.call_args.kwargs.get('json', {})
        assert isinstance(json_data['lossAmount'], float)
        assert json_data['lossAmount'] == 1500.50

    def test_handles_success_response(self, patched_client):
        """Verify successful update response."""
        client, mock_requests = patched_client
        mock_requests.put.return_value = _ok_response(status=200, body={'status': 'updated'})

        result = client.update_loss('AA123456A', 'AAZZ1234567890a', 1500.00)

        assert result['success'] is True
        assert result['data']['status'] == 'updated'

    def test_handles_validation_error(self, patched_client):
        """Verify validation error is handled gracefully."""
        client, mock_requests = patched_client
        mock_requests.put.return_value = _error_response(
            status=400,
            body={'error': 'Invalid loss amount'}
        )

        result = client.update_loss('AA123456A', 'AAZZ1234567890a', -1000.00)

        assert result['success'] is False
        assert 'error' in result

    def test_uses_losses_api_version_6(self, patched_client):
        """Verify Accept header uses Individual Losses API v6.0."""
        client, mock_requests = patched_client
        mock_requests.put.return_value = _ok_response(status=200)

        client.update_loss('AA123456A', 'AAZZ1234567890a', 1500.00)

        headers = mock_requests.put.call_args.kwargs.get('headers', {})
        assert 'Accept' in headers
        assert 'vnd.hmrc.6.0+json' in headers['Accept']


# ---------------------------------------------------------------------------
# delete_loss
# ---------------------------------------------------------------------------

class TestDeleteLoss:
    def test_deletes_from_correct_endpoint(self, patched_client):
        """Verify DELETE request to correct endpoint with loss_id."""
        client, mock_requests = patched_client
        mock_requests.delete.return_value = _ok_response(status=204)

        result = client.delete_loss('AA123456A', 'AAZZ1234567890a')

        assert result['success'] is True
        mock_requests.delete.assert_called_once()
        url = mock_requests.delete.call_args.args[0]
        assert url.endswith('/individuals/losses/AA123456A/brought-forward-losses/AAZZ1234567890a')

    def test_handles_204_no_content(self, patched_client):
        """Verify 204 No Content response is handled as success."""
        client, mock_requests = patched_client
        resp = MagicMock()
        resp.status_code = 204
        resp.content = b''
        resp.json.return_value = {}
        mock_requests.delete.return_value = resp

        result = client.delete_loss('AA123456A', 'AAZZ1234567890a')

        assert result['success'] is True

    def test_handles_404_error(self, patched_client):
        """Verify 404 error when loss doesn't exist."""
        client, mock_requests = patched_client
        mock_requests.delete.return_value = _error_response(status=404)

        result = client.delete_loss('AA123456A', 'INVALID_ID')

        assert result['success'] is False
        assert 'error' in result

    def test_uses_losses_api_version_6(self, patched_client):
        """Verify Accept header uses Individual Losses API v6.0."""
        client, mock_requests = patched_client
        mock_requests.delete.return_value = _ok_response(status=204)

        client.delete_loss('AA123456A', 'AAZZ1234567890a')

        headers = mock_requests.delete.call_args.kwargs.get('headers', {})
        assert 'Accept' in headers
        assert 'vnd.hmrc.6.0+json' in headers['Accept']


# ---------------------------------------------------------------------------
# Flask API Route Tests
# ---------------------------------------------------------------------------

class TestGetLossRoute:
    def test_get_route_requires_nino(self, auth_client):
        """Verify get route returns 400 without NINO."""
        response = auth_client.get('/api/hmrc/losses/AAZZ1234567890a')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'NINO' in data['error']

    def test_get_route_validates_nino_format(self, auth_client):
        """Verify get route validates NINO format."""
        response = auth_client.get('/api/hmrc/losses/AAZZ1234567890a?nino=INVALID')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    @patch('app.routes.api_hmrc.HMRCClient')
    def test_get_route_returns_success(self, mock_client_class, auth_client):
        """Verify get route returns successful response."""
        mock_client = MagicMock()
        mock_client.get_loss.return_value = {
            'success': True,
            'data': {'lossId': 'AAZZ1234567890a', 'lossAmount': 1000.00}
        }
        mock_client_class.return_value = mock_client

        response = auth_client.get('/api/hmrc/losses/AAZZ1234567890a?nino=AA123456A')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    @patch('app.routes.api_hmrc.HMRCClient')
    def test_get_route_handles_client_error(self, mock_client_class, auth_client):
        """Verify get route handles client errors."""
        mock_client = MagicMock()
        mock_client.get_loss.return_value = {
            'success': False,
            'error': 'Loss not found'
        }
        mock_client_class.return_value = mock_client

        response = auth_client.get('/api/hmrc/losses/INVALID?nino=AA123456A')
        data = response.get_json()
        assert data['success'] is False


class TestUpdateLossRoute:
    def test_update_route_requires_nino(self, auth_client):
        """Verify update route returns 400 without NINO."""
        response = auth_client.put(
            '/api/hmrc/losses/AAZZ1234567890a',
            json={'loss_amount': 1500.00}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'nino' in data['error']

    def test_update_route_requires_loss_amount(self, auth_client):
        """Verify update route returns 400 without loss_amount."""
        response = auth_client.put(
            '/api/hmrc/losses/AAZZ1234567890a',
            json={'nino': 'AA123456A'}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'loss_amount' in data['error']

    def test_update_route_validates_nino_format(self, auth_client):
        """Verify update route validates NINO format."""
        response = auth_client.put(
            '/api/hmrc/losses/AAZZ1234567890a',
            json={'nino': 'INVALID', 'loss_amount': 1500.00}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_update_route_validates_positive_amount(self, auth_client):
        """Verify update route rejects negative or zero amounts."""
        response = auth_client.put(
            '/api/hmrc/losses/AAZZ1234567890a',
            json={'nino': 'AA123456A', 'loss_amount': -100.00}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'greater than 0' in data['error']

    @patch('app.routes.api_hmrc.HMRCClient')
    def test_update_route_returns_success(self, mock_client_class, auth_client):
        """Verify update route returns successful response."""
        mock_client = MagicMock()
        mock_client.update_loss.return_value = {
            'success': True,
            'data': {'status': 'updated'}
        }
        mock_client_class.return_value = mock_client

        response = auth_client.put(
            '/api/hmrc/losses/AAZZ1234567890a',
            json={'nino': 'AA123456A', 'loss_amount': 1500.00}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    @patch('app.routes.api_hmrc.HMRCClient')
    def test_update_route_handles_client_error(self, mock_client_class, auth_client):
        """Verify update route handles client errors."""
        mock_client = MagicMock()
        mock_client.update_loss.return_value = {
            'success': False,
            'error': 'Invalid amount'
        }
        mock_client_class.return_value = mock_client

        response = auth_client.put(
            '/api/hmrc/losses/AAZZ1234567890a',
            json={'nino': 'AA123456A', 'loss_amount': 1500.00}
        )
        data = response.get_json()
        assert data['success'] is False


class TestDeleteLossRoute:
    def test_delete_route_requires_nino(self, auth_client):
        """Verify delete route returns 400 without NINO."""
        response = auth_client.delete('/api/hmrc/losses/AAZZ1234567890a')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'NINO' in data['error']

    def test_delete_route_validates_nino_format(self, auth_client):
        """Verify delete route validates NINO format."""
        response = auth_client.delete('/api/hmrc/losses/AAZZ1234567890a?nino=INVALID')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    @patch('app.routes.api_hmrc.HMRCClient')
    def test_delete_route_returns_success(self, mock_client_class, auth_client):
        """Verify delete route returns successful response."""
        mock_client = MagicMock()
        mock_client.delete_loss.return_value = {
            'success': True,
            'data': {}
        }
        mock_client_class.return_value = mock_client

        response = auth_client.delete('/api/hmrc/losses/AAZZ1234567890a?nino=AA123456A')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    @patch('app.routes.api_hmrc.HMRCClient')
    def test_delete_route_handles_client_error(self, mock_client_class, auth_client):
        """Verify delete route handles client errors."""
        mock_client = MagicMock()
        mock_client.delete_loss.return_value = {
            'success': False,
            'error': 'Loss not found'
        }
        mock_client_class.return_value = mock_client

        response = auth_client.delete('/api/hmrc/losses/INVALID?nino=AA123456A')
        data = response.get_json()
        assert data['success'] is False
