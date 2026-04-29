"""UI tests for the HMRC Late Accounting Date Rule (LADR) panel.

Renders the /settings/hmrc page with the auth_client fixture and asserts
that the new panel + supporting JS / CSS are present and wired up the
way the JS controller expects.
"""

import os
import re


def _get_page(auth_client):
    response = auth_client.get('/settings/hmrc')
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    return response.get_data(as_text=True)


def _read_static(app, *parts):
    path = os.path.normpath(os.path.join(app.root_path, '..', 'static', *parts))
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


# ---------------------------------------------------------------------------
# panel structure
# ---------------------------------------------------------------------------

def test_ladr_card_present(auth_client):
    body = _get_page(auth_client)

    assert 'id="ladrCard"' in body
    assert 'Late Accounting Date Rule' in body
    assert 'settings-card' in body
    assert 'ladr-card' in body


def test_panel_renders_all_required_element_ids(auth_client):
    body = _get_page(auth_client)

    for el_id in (
        'ladrTaxYearSelect',
        'ladrSummary',
        'ladrStatusBadge',
        'ladrLastSynced',
        'ladrStaleBadge',
        'ladrResult',
        'ladrRefreshBtn',
        'ladrDisapplyBtn',
        'ladrWithdrawBtn',
    ):
        assert f'id="{el_id}"' in body, f'missing element {el_id}'


def test_tax_year_selector_offers_relevant_years(auth_client):
    body = _get_page(auth_client)

    select_idx = body.find('id="ladrTaxYearSelect"')
    assert select_idx != -1
    end = body.find('</select>', select_idx)
    snippet = body[select_idx:end]
    assert 'value="2024-25"' in snippet
    assert 'value="2025-26"' in snippet
    assert 'value="2026-27"' in snippet
    # 2025-26 is the default.
    assert 'value="2025-26" selected' in snippet


def test_initial_status_badge_is_unknown_variant(auth_client):
    """Pre-render state is Unknown until JS load() resolves."""
    body = _get_page(auth_client)

    idx = body.find('id="ladrStatusBadge"')
    assert idx != -1
    snippet = body[max(0, idx - 200):idx + 200]
    assert 'ladr-status-badge' in snippet
    assert 'ladr-status-unknown' in snippet
    assert '>Unknown<' in snippet


def test_action_buttons_hidden_initially_until_status_known(auth_client):
    """Disapply + Withdraw start with d-none + disabled. JS toggles
    visibility based on status. Refresh is always visible."""
    body = _get_page(auth_client)

    for btn_id in ('ladrDisapplyBtn', 'ladrWithdrawBtn'):
        idx = body.find(f'id="{btn_id}"')
        assert idx != -1
        snippet = body[max(0, idx - 250):idx + 50]
        # Find the actual <button ... id="..."> opening tag.
        btn_open_start = snippet.rfind('<button')
        btn_open_end = snippet.find('>', btn_open_start)
        open_tag = snippet[btn_open_start:btn_open_end + 1]
        assert 'd-none' in open_tag, f'{btn_id} must start hidden via d-none'
        assert ' disabled' in open_tag, f'{btn_id} must start disabled'

    # Refresh button is visible (no d-none).
    idx = body.find('id="ladrRefreshBtn"')
    assert idx != -1
    snippet = body[max(0, idx - 250):idx + 50]
    btn_open_start = snippet.rfind('<button')
    btn_open_end = snippet.find('>', btn_open_start)
    open_tag = snippet[btn_open_start:btn_open_end + 1]
    assert 'd-none' not in open_tag


def test_stale_badge_starts_hidden(auth_client):
    body = _get_page(auth_client)

    idx = body.find('id="ladrStaleBadge"')
    assert idx != -1
    snippet = body[max(0, idx - 200):idx + 100]
    span_open_start = snippet.rfind('<span')
    span_open_end = snippet.find('>', span_open_start)
    open_tag = snippet[span_open_start:span_open_end + 1]
    assert 'd-none' in open_tag


# ---------------------------------------------------------------------------
# helper text (plain English explanation)
# ---------------------------------------------------------------------------

def test_helper_text_explains_ladr_in_plain_english(auth_client):
    """The user must see a plain-English explanation since LADR is a
    niche rule that almost no sole trader will use."""
    body = _get_page(auth_client)

    # Locate the panel slice and collapse whitespace so phrases that
    # span template line-breaks still match.
    start = body.find('id="ladrCard"')
    assert start != -1
    end = body.find('<!-- Tabs for Obligations', start)
    panel = body[start:end]
    flat = re.sub(r'\s+', ' ', panel).lower()

    # Plain-English signal phrases.
    assert 'accounting period' in flat
    assert '5 april' in flat
    # Either "does not apply" or "no action is needed" should be present.
    assert 'does not apply' in flat or 'no action is needed' in flat


# ---------------------------------------------------------------------------
# CSS / JS wiring
# ---------------------------------------------------------------------------

def test_ladr_css_loaded(auth_client):
    body = _get_page(auth_client)
    assert 'css/hmrc-ladr.css' in body, (
        'hmrc-ladr.css not wired into extra_css block'
    )


def test_ladr_js_loaded(auth_client):
    body = _get_page(auth_client)
    assert 'js/hmrc-ladr.js' in body, (
        'hmrc-ladr.js not wired into extra_js block'
    )


def test_no_inline_styles_in_panel(auth_client):
    body = _get_page(auth_client)

    start = body.find('id="ladrCard"')
    assert start != -1
    end = body.find('<!-- Tabs for Obligations', start)
    assert end != -1
    panel_html = body[start:end]

    assert 'style=' not in panel_html, (
        'Inline styles found in LADR panel - move to '
        'static/css/hmrc-ladr.css'
    )


# ---------------------------------------------------------------------------
# JS module surface
# ---------------------------------------------------------------------------

def test_js_module_exposes_public_api(app):
    source = _read_static(app, 'js', 'hmrc-ladr.js')

    assert 'window.HMRCLateAccountingDateRule' in source
    for fn in ('load:', 'disapply:', 'withdraw:'):
        assert fn in source, f'{fn} missing from window.HMRCLateAccountingDateRule'


def test_js_module_targets_correct_endpoints(app):
    source = _read_static(app, 'js', 'hmrc-ladr.js')

    assert '/api/hmrc/late-accounting-date-rule/' in source
    assert '/disapply' in source

    for method in ("'GET'", "'POST'", "'DELETE'"):
        assert method in source, f'{method} not used by LADR JS module'


def test_js_module_handles_distinct_status_codes(app):
    source = _read_static(app, 'js', 'hmrc-ladr.js')

    for status in ('400', '404', '409', '422'):
        assert status in source, f'JS module does not branch on HTTP {status}'
    # 5xx must be handled distinctly from 4xx.
    assert '>= 500' in source or '>=500' in source, (
        'JS module does not have a separate 5xx handler'
    )


def test_js_module_confirms_before_mutating_actions(app):
    source = _read_static(app, 'js', 'hmrc-ladr.js')

    # Both disapply and withdraw must call confirm() before sending.
    confirm_calls = re.findall(r'window\.confirm\(', source)
    assert len(confirm_calls) >= 2, (
        'Both disapply() and withdraw() must prompt confirm() before sending.'
    )


def test_js_module_handles_stale_cache_response(app):
    """The route's GET returns ``stale: true`` from cache when not connected;
    the JS must read that flag (so the badge can show)."""
    source = _read_static(app, 'js', 'hmrc-ladr.js')

    assert 'stale' in source, (
        'JS module does not read the stale flag from cache responses.'
    )
    assert 'last_synced_at' in source, (
        'JS module does not read the last_synced_at timestamp.'
    )


# ---------------------------------------------------------------------------
# CSS file rules
# ---------------------------------------------------------------------------

def test_css_uses_only_bootstrap_variables(app):
    css = _read_static(app, 'css', 'hmrc-ladr.css')

    hex_matches = re.findall(r'#[0-9a-fA-F]{3,8}\b', css)
    assert not hex_matches, (
        f'Hardcoded hex colours found in hmrc-ladr.css: {hex_matches}'
    )
    assert '--bs-' in css, 'CSS does not use any --bs-* variables'


def test_css_has_no_important_overrides(app):
    css = _read_static(app, 'css', 'hmrc-ladr.css')
    assert '!important' not in css, (
        '!important is forbidden in hmrc-ladr.css'
    )


def test_css_provides_all_three_status_variants(app):
    css = _read_static(app, 'css', 'hmrc-ladr.css')

    for variant in (
        'ladr-status-applied',
        'ladr-status-disapplied',
        'ladr-status-unknown',
    ):
        assert variant in css, f'CSS missing status variant {variant}'


def test_css_touch_target_min_height(app):
    """Mobile rule: action buttons must be at least 44px tall."""
    css = _read_static(app, 'css', 'hmrc-ladr.css')

    assert 'ladr-action-btn' in css
    assert 'min-height: 44px' in css, (
        'Action buttons must declare min-height: 44px for touch targets.'
    )
