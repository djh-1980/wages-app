"""UI tests for the HMRC cumulative submission panel.

Renders the /settings/hmrc page with the auth_client fixture and asserts
that the cumulative panel + supporting JS / CSS are present and wired up
the way the controller expects.
"""

import pytest


def _get_page(auth_client):
    response = auth_client.get('/settings/hmrc')
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    return response.get_data(as_text=True)


# ---------------------------------------------------------------------------
# panel structure
# ---------------------------------------------------------------------------

def test_cumulative_panel_present_in_obligations_tab(auth_client):
    """The panel container ships with the page so the JS controller has
    something to populate when the user clicks Submit on an obligation."""
    body = _get_page(auth_client)

    # Panel is in the obligations tab, hidden by default via d-none.
    assert 'id="cumulativePanel"' in body
    assert 'cumulative-panel' in body
    assert 'd-none' in body  # hidden until openCumulativePanel() runs

    # All the slots the controller writes into.
    for el_id in (
        'cumulativePanelPeriod',
        'cumulativeStartDate',
        'cumulativeEndDate',
        'cumulativeLoading',
        'cumulativeContent',
        'cumulativeTurnover',
        'cumulativeOther',
        'cumulativeExpenseBody',
        'cumulativeBreakdownBody',
        'cumulativeConfirmCheckbox',
        'cumulativeSubmitBtn',
        'cumulativeResult',
        'cumulativePanelClose',
        'cumulativePanelCancel',
    ):
        assert f'id="{el_id}"' in body, f'missing element {el_id}'


def test_panel_explains_cumulative_semantics(auth_client):
    """The user must see a clear note that this is a CUMULATIVE submission
    (running total), not a per-period submission."""
    body = _get_page(auth_client)

    assert 'Cumulative Submissions' in body
    assert 'running total' in body.lower()
    # Must explain the Q2 = Q1 + Q2 etc. semantics, in user-friendly terms.
    assert 'Q1' in body and 'Q2' in body and 'Q3' in body and 'Q4' in body


def test_breakdown_table_has_per_quarter_columns(auth_client):
    """The breakdown table needs Quarter / Window / Turnover / Expenses
    columns so the user can see what each quarter contributed."""
    body = _get_page(auth_client)

    # Heading + the four table headers.
    assert 'Quarterly Breakdown' in body
    assert '>Quarter<' in body
    assert '>Window<' in body
    assert '>Turnover<' in body
    assert '>Expenses<' in body


# ---------------------------------------------------------------------------
# confirm-checkbox / submit-button gating
# ---------------------------------------------------------------------------

def test_submit_button_starts_disabled(auth_client):
    body = _get_page(auth_client)

    # Locate the cumulativeSubmitBtn and verify the disabled attribute is
    # present at render time.
    idx = body.find('id="cumulativeSubmitBtn"')
    assert idx != -1
    # Look at the surrounding 200 chars of the opening tag.
    snippet = body[max(0, idx - 200):idx + 200]
    assert 'disabled' in snippet


def test_confirm_checkbox_is_present_and_unchecked(auth_client):
    body = _get_page(auth_client)

    idx = body.find('id="cumulativeConfirmCheckbox"')
    assert idx != -1
    snippet = body[max(0, idx - 100):idx + 200]
    # Checkbox is rendered without the `checked` attribute.
    assert 'checked' not in snippet
    # Label spells out the confirmation.
    assert 'I confirm these cumulative totals are correct' in body


# ---------------------------------------------------------------------------
# JS / CSS wiring
# ---------------------------------------------------------------------------

def test_cumulative_js_and_css_loaded(auth_client):
    body = _get_page(auth_client)

    assert 'js/hmrc-cumulative.js' in body, 'cumulative JS not wired in'
    assert 'css/hmrc-cumulative.css' in body, 'cumulative CSS not wired in'
    # Loaded BEFORE settings-hmrc.js so submitPeriod() can call into it.
    cumulative_idx = body.find('js/hmrc-cumulative.js')
    settings_idx = body.find('js/settings-hmrc.js')
    assert cumulative_idx != -1 and settings_idx != -1
    assert cumulative_idx < settings_idx, (
        'hmrc-cumulative.js must load before settings-hmrc.js so the '
        'submitPeriod() handler can find window.HMRCCumulative.'
    )


def test_settings_hmrc_js_uses_cumulative_panel(app):
    """settings-hmrc.js must hand off to window.HMRCCumulative.open()
    instead of redirecting to /expenses for per-period submission."""
    import os
    js_path = os.path.join(app.root_path, '..', 'static', 'js', 'settings-hmrc.js')
    js_path = os.path.normpath(js_path)
    with open(js_path, 'r', encoding='utf-8') as f:
        source = f.read()

    assert 'window.HMRCCumulative' in source, (
        'submitPeriod() must call into the cumulative panel module.'
    )
    assert 'HMRCCumulative.open' in source


def test_cumulative_js_module_exposes_open_api(app):
    import os
    js_path = os.path.join(
        app.root_path, '..', 'static', 'js', 'hmrc-cumulative.js'
    )
    js_path = os.path.normpath(js_path)
    with open(js_path, 'r', encoding='utf-8') as f:
        source = f.read()

    # Public API surface used by settings-hmrc.js.
    assert 'window.HMRCCumulative' in source
    assert 'open: openCumulativePanel' in source

    # Posts to the new cumulative endpoint.
    assert '/api/hmrc/period/cumulative/' in source

    # Handles 409 / 422 / 5xx + receipt id explicitly.
    assert 'res.status === 409' in source
    assert 'res.status === 422' in source
    assert 'res.status >= 500' in source
    assert 'Receipt ID' in source


# ---------------------------------------------------------------------------
# legacy / migration safety
# ---------------------------------------------------------------------------

def test_legacy_expenses_modal_still_present(app):
    """We must NOT delete the legacy expenses.js modal - it's the
    fallback when the cumulative module fails to load. (The user
    explicitly asked for migration safety in commit 4.)"""
    import os
    js_path = os.path.join(app.root_path, '..', 'static', 'js', 'expenses.js')
    js_path = os.path.normpath(js_path)
    with open(js_path, 'r', encoding='utf-8') as f:
        source = f.read()

    # Legacy submission code still in place.
    assert "/api/hmrc/period/submit" in source


def test_no_inline_styles_in_cumulative_panel(auth_client):
    """The .windsurfrules forbid inline styles on new templates. Spot-check
    that none of the new cumulative-* elements grew a style="" attribute."""
    body = _get_page(auth_client)

    # Only check the slice between the panel open and close tags.
    start = body.find('id="cumulativePanel"')
    assert start != -1
    end = body.find('<!-- Submissions Tab', start)
    assert end != -1
    panel_html = body[start:end]

    # Allow style="..." nowhere inside the panel.
    assert 'style=' not in panel_html, (
        'Inline styles found in cumulative panel - move to '
        'static/css/hmrc-cumulative.css'
    )
