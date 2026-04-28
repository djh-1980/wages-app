"""HMRC compliance tests for the Software Approvals checklist.

These tests cover the two Phase-1 quick-wins from
HMRC_PRODUCTION_CHECKLIST_GAP_AUDIT.md:

  1. Final Declaration Statement on the HMRC settings page must show the
     verbatim wording from the MTD IT End to End Service Guide and the
     Submit button must be disabled until the user ticks the agreement
     checkbox (checklist item EOY9).
  2. UK / foreign property is out of scope for this submission, so the
     property tab must be hidden and the property API routes must 404
     unless explicitly re-enabled via HMRC_PROPERTY_ENABLED.
"""

import re

import pytest


# -- Final Declaration Statement (EOY7 + EOY9) -----------------------------

# Verbatim wording from the MTD IT End to End Service Guide (Individuals).
# Do NOT paraphrase any of these strings.
FINAL_DECL_PARAGRAPHS = (
    'Before you submit your final declaration to HMRC you should ensure '
    'that the information you are providing is correct and complete. '
    'A person who knowingly or recklessly makes a false statement, or '
    'submits a false document, in connection with their tax affairs may '
    'be liable to financial penalties and/or prosecution.',
    'I declare that the information I have provided is correct and '
    'complete to the best of my knowledge and belief.',
    'By submitting this declaration you are confirming that the '
    'information given is true and complete. Any false statement may '
    'result in prosecution.',
)

CHECKBOX_LABEL = 'I have read and agreed to the declaration above'


def test_final_declaration_requires_agreement(auth_client):
    """The HMRC settings page must:
      * render the verbatim Final Declaration Statement,
      * show a checkbox the user must tick,
      * keep the Submit button disabled until they do.
    """
    response = auth_client.get('/settings/hmrc')
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    body = response.get_data(as_text=True)

    # The full declaration paragraphs must appear byte-for-byte.
    for para in FINAL_DECL_PARAGRAPHS:
        assert para in body, f'Missing verbatim declaration paragraph: {para!r}'

    # The labelled section heading must be present.
    assert 'Final Declaration Statement' in body
    assert 'id="finalDeclarationStatement"' in body

    # Agreement checkbox with the prescribed label.
    assert 'id="declarationCheckbox"' in body
    assert CHECKBOX_LABEL in body

    # Submit button must be disabled in the rendered HTML.
    submit_btn_match = re.search(
        r'<button[^>]*id="submitDeclBtn"[^>]*>',
        body,
    )
    assert submit_btn_match, 'submitDeclBtn not found in rendered page'
    assert 'disabled' in submit_btn_match.group(0), (
        'submitDeclBtn must be rendered with the `disabled` attribute so the '
        'user cannot submit the Final Declaration before ticking the agreement '
        'checkbox.'
    )


# -- Property tab + routes feature flag (audit Section 6.5) ----------------

def test_property_tab_hidden_when_disabled(auth_client, app):
    """With HMRC_PROPERTY_ENABLED = False (the default), the HMRC settings
    page must not advertise UK Property at all."""
    assert app.config.get('HMRC_PROPERTY_ENABLED') is False, (
        'Default config must keep HMRC_PROPERTY_ENABLED off; this is what we '
        'told HMRC on the Software Approvals form.'
    )
    response = auth_client.get('/settings/hmrc')
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    # The nav-pill anchor and the tab-pane are both gated.
    assert 'data-bs-target="#property"' not in body, (
        'Property nav-pill leaked into the page despite the feature flag.'
    )
    assert 'id="property"' not in body, (
        'Property tab pane leaked into the page despite the feature flag.'
    )
    # Belt-and-braces: no UK Property heading either.
    assert 'UK Property Business' not in body


def test_property_routes_404_when_disabled(auth_client, app):
    """Both property API routes must return 404 with the flag off."""
    assert app.config.get('HMRC_PROPERTY_ENABLED') is False

    obligations_resp = auth_client.get(
        '/api/hmrc/property/obligations?nino=AA123456A'
    )
    assert obligations_resp.status_code == 404, (
        f'Expected 404 with property disabled, got '
        f'{obligations_resp.status_code}: {obligations_resp.get_data(as_text=True)[:200]}'
    )

    submit_resp = auth_client.post(
        '/api/hmrc/property/submit',
        json={
            'nino': 'AA123456A',
            'tax_year': '2024-25',
            'from_date': '2024-04-06',
            'to_date': '2024-07-05',
        },
    )
    assert submit_resp.status_code == 404, (
        f'Expected 404 with property disabled, got '
        f'{submit_resp.status_code}: {submit_resp.get_data(as_text=True)[:200]}'
    )


def test_property_routes_reachable_when_flag_enabled(auth_client, app):
    """Sanity check: flipping the flag on at runtime makes the routes
    addressable again (they will then fall through to NINO validation /
    HMRC client errors, but they must not 404)."""
    app.config['HMRC_PROPERTY_ENABLED'] = True
    try:
        response = auth_client.get(
            '/api/hmrc/property/obligations?nino=AA123456A'
        )
        # Anything except 404 is acceptable — the route is reachable.
        # (In sandbox without auth it will surface a JSON error from
        # HMRCClient, status 200 with success=false.)
        assert response.status_code != 404
    finally:
        app.config['HMRC_PROPERTY_ENABLED'] = False

