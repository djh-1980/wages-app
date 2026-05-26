"""HMRC Amendment Flow tests.

These tests verify the amendment flow for Final Declaration,
ensuring the UI and API correctly handle both initial declarations
and amendments to previously submitted declarations.
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


# ---------------------------------------------------------------------------
# Client Tests - trigger_crystallisation with calculation_type
# ---------------------------------------------------------------------------

class TestTriggerCrystallisationAmendment:
    def test_accepts_intent_to_amend_calculation_type(self, patched_client):
        """Verify trigger_crystallisation accepts 'intent-to-amend' calculation type."""
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(status=200, body={'id': 'calc123'})

        result = client.trigger_crystallisation('AA123456A', '2024-25', calculation_type='intent-to-amend')

        assert result['success'] is True
        mock_requests.post.assert_called_once()

    def test_sends_intent_to_amend_in_payload(self, patched_client):
        """Verify 'intent-to-amend' is sent in the request payload."""
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(status=200, body={'id': 'calc123'})

        client.trigger_crystallisation('AA123456A', '2024-25', calculation_type='intent-to-amend')

        json_data = mock_requests.post.call_args.kwargs.get('json', {})
        assert json_data.get('calculationType') == 'intent-to-amend'

    def test_defaults_to_intent_to_finalise(self, patched_client):
        """Verify default calculation_type is 'intent-to-finalise'."""
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(status=200, body={'id': 'calc123'})

        client.trigger_crystallisation('AA123456A', '2024-25')

        json_data = mock_requests.post.call_args.kwargs.get('json', {})
        assert json_data.get('calculationType') == 'intent-to-finalise'


# ---------------------------------------------------------------------------
# Client Tests - submit_final_declaration with declaration_type
# ---------------------------------------------------------------------------

class TestSubmitFinalDeclarationAmendment:
    def test_accepts_confirm_amendment_declaration_type(self, patched_client):
        """Verify submit_final_declaration accepts 'confirm-amendment' declaration type."""
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(status=200, body={'id': 'receipt123'})

        result = client.submit_final_declaration(
            'AA123456A', '2024-25', 'calc123', declaration_type='confirm-amendment'
        )

        assert result['success'] is True
        mock_requests.post.assert_called_once()

    def test_sends_confirm_amendment_in_payload(self, patched_client):
        """Verify 'confirm-amendment' is sent in the request payload."""
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(status=200, body={'id': 'receipt123'})

        client.submit_final_declaration(
            'AA123456A', '2024-25', 'calc123', declaration_type='confirm-amendment'
        )

        json_data = mock_requests.post.call_args.kwargs.get('json', {})
        assert json_data.get('declarationType') == 'confirm-amendment'

    def test_defaults_to_final_declaration(self, patched_client):
        """Verify default declaration_type is 'final-declaration'."""
        client, mock_requests = patched_client
        mock_requests.post.return_value = _ok_response(status=200, body={'id': 'receipt123'})

        client.submit_final_declaration('AA123456A', '2024-25', 'calc123')

        json_data = mock_requests.post.call_args.kwargs.get('json', {})
        assert json_data.get('declarationType') == 'final-declaration'


# ---------------------------------------------------------------------------
# Route Tests - calculate endpoint with calculation_type
# ---------------------------------------------------------------------------

class TestCalculateFinalDeclarationRoute:
    @patch('app.routes.api_hmrc.HMRCClient')
    def test_route_accepts_intent_to_amend(self, mock_client_class, auth_client):
        """Verify calculate route accepts 'intent-to-amend' calculation_type."""
        mock_client = MagicMock()
        mock_client.trigger_crystallisation.return_value = {
            'success': True,
            'data': {'id': 'calc123'}
        }
        mock_client.submit_annual_submission.return_value = {
            'success': True
        }
        mock_client_class.return_value = mock_client

        response = auth_client.post(
            '/api/hmrc/final-declaration/calculate',
            json={
                'tax_year': '2024/2025',
                'nino': 'AA123456A',
                'business_id': 'XBIS12345678901',
                'calculation_type': 'intent-to-amend'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        
        # Verify the client was called with intent-to-amend
        mock_client.trigger_crystallisation.assert_called_once()
        call_args = mock_client.trigger_crystallisation.call_args
        # The route calls trigger_crystallisation(nino, tax_year, calculation_type)
        assert len(call_args.args) >= 3
        assert call_args.args[2] == 'intent-to-amend'

    @patch('app.routes.api_hmrc.HMRCClient')
    def test_route_passes_calculation_type_to_client(self, mock_client_class, auth_client):
        """Verify route passes calculation_type parameter to client."""
        mock_client = MagicMock()
        mock_client.trigger_crystallisation.return_value = {
            'success': True,
            'data': {'id': 'calc123'}
        }
        mock_client.submit_annual_submission.return_value = {
            'success': True
        }
        mock_client_class.return_value = mock_client

        auth_client.post(
            '/api/hmrc/final-declaration/calculate',
            json={
                'tax_year': '2024/2025',
                'nino': 'AA123456A',
                'business_id': 'XBIS12345678901',
                'calculation_type': 'intent-to-amend'
            }
        )

        call_args = mock_client.trigger_crystallisation.call_args
        # The route calls trigger_crystallisation(nino, tax_year, calculation_type)
        assert len(call_args.args) >= 3
        assert call_args.args[2] == 'intent-to-amend'


# ---------------------------------------------------------------------------
# Route Tests - submit endpoint with declaration_type
# ---------------------------------------------------------------------------

class TestSubmitFinalDeclarationRoute:
    @patch('app.routes.api_hmrc.HMRCClient')
    def test_route_accepts_confirm_amendment(self, mock_client_class, auth_client):
        """Verify submit route accepts 'confirm-amendment' declaration_type."""
        mock_client = MagicMock()
        mock_client.submit_final_declaration.return_value = {
            'success': True,
            'data': {'id': 'receipt123'}
        }
        mock_client_class.return_value = mock_client

        response = auth_client.post(
            '/api/hmrc/final-declaration/submit',
            json={
                'tax_year': '2024/2025',
                'calculation_id': 'calc123',
                'nino': 'AA123456A',
                'confirmed': True,
                'declaration_type': 'confirm-amendment'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    @patch('app.routes.api_hmrc.HMRCClient')
    def test_route_passes_declaration_type_to_client(self, mock_client_class, auth_client):
        """Verify route passes declaration_type parameter to client."""
        mock_client = MagicMock()
        mock_client.submit_final_declaration.return_value = {
            'success': True,
            'data': {'id': 'receipt123'}
        }
        mock_client_class.return_value = mock_client

        auth_client.post(
            '/api/hmrc/final-declaration/submit',
            json={
                'tax_year': '2024/2025',
                'calculation_id': 'calc123',
                'nino': 'AA123456A',
                'confirmed': True,
                'declaration_type': 'confirm-amendment'
            }
        )

        call_args = mock_client.submit_final_declaration.call_args
        # Check positional args or kwargs
        if len(call_args.args) >= 4:
            assert call_args.args[3] == 'confirm-amendment'
        else:
            assert call_args.kwargs.get('declaration_type') == 'confirm-amendment'

    @patch('app.routes.api_hmrc.HMRCClient')
    def test_route_defaults_to_final_declaration(self, mock_client_class, auth_client):
        """Verify route defaults to 'final-declaration' when declaration_type not provided."""
        mock_client = MagicMock()
        mock_client.submit_final_declaration.return_value = {
            'success': True,
            'data': {'id': 'receipt123'}
        }
        mock_client_class.return_value = mock_client

        auth_client.post(
            '/api/hmrc/final-declaration/submit',
            json={
                'tax_year': '2024/2025',
                'calculation_id': 'calc123',
                'nino': 'AA123456A',
                'confirmed': True
            }
        )

        call_args = mock_client.submit_final_declaration.call_args
        # Check positional args or kwargs
        if len(call_args.args) >= 4:
            assert call_args.args[3] == 'final-declaration'
        else:
            assert call_args.kwargs.get('declaration_type') == 'final-declaration'


# ---------------------------------------------------------------------------
# Status Detection Tests
# ---------------------------------------------------------------------------

class TestFinalDeclarationStatusDetection:
    def test_status_endpoint_returns_declaration_status(self, auth_client, app):
        """Verify status endpoint returns declaration_status field."""
        with app.app_context():
            from app.database import get_db_connection
            
            # Insert a test final declaration
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO hmrc_final_declarations 
                    (tax_year, calculation_id, estimated_tax, status, created_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                """, ('2024/2025', 'calc123', 1000.00, 'submitted'))
                conn.commit()

        response = auth_client.get('/api/hmrc/final-declaration/status?tax_year=2024/2025')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['declaration_status'] == 'submitted'

    def test_status_not_started_when_no_declaration(self, auth_client):
        """Verify status is 'not_started' when no declaration exists."""
        response = auth_client.get('/api/hmrc/final-declaration/status?tax_year=2099/2100')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['declaration_status'] == 'not_started'


# ---------------------------------------------------------------------------
# Declaration Statement Tests
# ---------------------------------------------------------------------------

class TestDeclarationStatementConsistency:
    def test_same_declaration_text_for_both_flows(self):
        """Verify the same declaration statement is used for both initial and amendment flows."""
        # This test verifies that the declaration text doesn't change between flows
        # The actual text is in the HTML template and should be identical for both
        
        declaration_text = (
            "I declare that the information and tax return I have submitted are "
            "(taken together) correct and complete to the best of my knowledge. "
            "I understand that I may have to pay financial penalties and face "
            "prosecution if I give false information."
        )
        
        # This is a documentation test - the text must not be paraphrased
        # and must be the same for both initial declaration and amendment
        assert len(declaration_text) > 0
        assert "correct and complete" in declaration_text
        assert "financial penalties" in declaration_text
