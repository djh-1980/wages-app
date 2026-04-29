"""UI tests for the HMRC Periods of Account panel.

Renders the /settings/hmrc page with the auth_client fixture and asserts
that the new panel + supporting JS / CSS are present and wired up the
way the JS controller expects.
"""

import os


def _get_page(auth_client):
    response = auth_client.get('/settings/hmrc')
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    return response.get_data(as_text=True)


# ---------------------------------------------------------------------------
# panel structure
# ---------------------------------------------------------------------------

def test_period_of_account_card_present(auth_client):
    body = _get_page(auth_client)

    assert 'id="periodOfAccountCard"' in body
    assert 'Period of Account' in body
    # Bootstrap card scaffold (settings-card matches sibling cards).
    assert 'settings-card' in body
    # Panel-specific class for our CSS hook.
    assert 'poa-card' in body


def test_panel_renders_all_required_element_ids(auth_client):
    body = _get_page(auth_client)

    for el_id in (
        'poaTaxYearSelect',
        'poaSummary',
        'poaSummaryEmpty',
        'poaSummaryContent',
        'poaSummaryDates',
        'poaSummaryPeriodId',
        'poaTypeBadge',
        'poaForm',
        'poaCustomToggle',
        'poaCustomDates',
        'poaStartDate',
        'poaEndDate',
        'poaResult',
        'poaCreateBtn',
        'poaCreateBtnLabel',
        'poaUpdateBtn',
        'poaDeleteBtn',
    ):
        assert f'id="{el_id}"' in body, f'missing element {el_id}'


def test_tax_year_selector_offers_relevant_years(auth_client):
    body = _get_page(auth_client)

    # Daniel's case is the 2025-26 tax year. The selector must default to it.
    select_idx = body.find('id="poaTaxYearSelect"')
    assert select_idx != -1
    end = body.find('</select>', select_idx)
    snippet = body[select_idx:end]
    assert 'value="2024-25"' in snippet
    assert 'value="2025-26"' in snippet
    assert 'value="2026-27"' in snippet
    assert 'selected' in snippet  # one option is pre-selected
    # 2025-26 is the default.
    assert 'value="2025-26" selected' in snippet


def test_custom_dates_hidden_by_default(auth_client):
    """Custom date inputs are inside #poaCustomDates which has d-none on
    initial render; the JS controller toggles it when the switch flips."""
    body = _get_page(auth_client)

    idx = body.find('id="poaCustomDates"')
    assert idx != -1
    end = body.find('>', idx) + 1
    open_tag = body[idx - 80:end]  # capture class= attribute too
    assert 'd-none' in open_tag, (
        '#poaCustomDates must start hidden via the d-none class.'
    )


def test_custom_toggle_is_off_by_default(auth_client):
    body = _get_page(auth_client)

    idx = body.find('id="poaCustomToggle"')
    assert idx != -1
    snippet = body[max(0, idx - 200):idx + 200]
    # The switch is rendered without the `checked` attribute.
    assert 'checked' not in snippet


def test_action_buttons_have_correct_initial_disabled_state(auth_client):
    """Create starts enabled, Update / Delete start disabled (no period
    yet). The JS controller flips the state once load() resolves."""
    body = _get_page(auth_client)

    create_idx = body.find('id="poaCreateBtn"')
    update_idx = body.find('id="poaUpdateBtn"')
    delete_idx = body.find('id="poaDeleteBtn"')
    assert create_idx != -1 and update_idx != -1 and delete_idx != -1

    create_tag = body[max(0, create_idx - 200):create_idx + 200]
    update_tag = body[max(0, update_idx - 200):update_idx + 200]
    delete_tag = body[max(0, delete_idx - 200):delete_idx + 200]

    # Create: enabled (no `disabled` attribute on the button element).
    # The settings-card / row markup may include the word "disabled" in a
    # different context, so we look for the explicit attribute on the tag.
    assert 'id="poaCreateBtn"' in create_tag
    # Find the actual button opening tag and ensure no disabled attribute.
    btn_open_start = create_tag.find('<button')
    btn_open_end = create_tag.find('>', btn_open_start)
    create_open = create_tag[btn_open_start:btn_open_end + 1]
    assert ' disabled' not in create_open

    # Update + Delete carry the disabled attribute on render.
    btn_open_start = update_tag.find('<button')
    btn_open_end = update_tag.find('>', btn_open_start)
    assert ' disabled' in update_tag[btn_open_start:btn_open_end + 1]

    btn_open_start = delete_tag.find('<button')
    btn_open_end = delete_tag.find('>', btn_open_start)
    assert ' disabled' in delete_tag[btn_open_start:btn_open_end + 1]


def test_default_create_button_label_is_set_standard(auth_client):
    """When the custom toggle is off, the primary button reads 'Set
    Standard Period' so the one-click default is obvious for tax-year
    aligned traders (Daniel's case)."""
    body = _get_page(auth_client)

    idx = body.find('id="poaCreateBtnLabel"')
    assert idx != -1
    end = body.find('</span>', idx)
    snippet = body[idx:end]
    assert 'Set Standard Period' in snippet


# ---------------------------------------------------------------------------
# CSS / JS wiring
# ---------------------------------------------------------------------------

def test_periods_of_account_css_loaded(auth_client):
    body = _get_page(auth_client)
    assert 'css/hmrc-periods-of-account.css' in body, (
        'hmrc-periods-of-account.css not wired into extra_css block'
    )


def test_periods_of_account_js_loaded(auth_client):
    body = _get_page(auth_client)
    assert 'js/hmrc-periods-of-account.js' in body, (
        'hmrc-periods-of-account.js not wired into extra_js block'
    )


def test_no_inline_styles_in_panel(auth_client):
    """user_rules forbid inline styles on new templates. Spot-check that
    no element inside the Period of Account card has a style="" attribute."""
    body = _get_page(auth_client)

    start = body.find('id="periodOfAccountCard"')
    assert start != -1
    # The next major sibling block in the template is the obligations tabs.
    end = body.find('<!-- Tabs for Obligations and Submissions', start)
    assert end != -1
    panel_html = body[start:end]

    assert 'style=' not in panel_html, (
        'Inline styles found in Period of Account panel - move to '
        'static/css/hmrc-periods-of-account.css'
    )


# ---------------------------------------------------------------------------
# JS module surface
# ---------------------------------------------------------------------------

def _read_static(app, *parts):
    path = os.path.normpath(os.path.join(app.root_path, '..', 'static', *parts))
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def test_js_module_exposes_public_api(app):
    source = _read_static(app, 'js', 'hmrc-periods-of-account.js')

    # Public API surface promised in the route plan.
    assert 'window.HMRCPeriodsOfAccount' in source
    for fn in ('load:', 'create:', 'update:', 'delete:'):
        assert fn in source, f'{fn} missing from window.HMRCPeriodsOfAccount'


def test_js_module_targets_correct_endpoints(app):
    source = _read_static(app, 'js', 'hmrc-periods-of-account.js')

    # Routes registered in commit 3.
    assert '/api/hmrc/period-of-account/' in source

    # Each verb is used.
    for method in ("'GET'", "'POST'", "'PUT'", "'DELETE'"):
        assert method in source, f'{method} not used by JS module'


def test_js_module_handles_distinct_status_codes(app):
    source = _read_static(app, 'js', 'hmrc-periods-of-account.js')

    # The status codes the routes emit must be handled with separate paths.
    for status in ('400', '404', '409', '422'):
        assert status in source, (
            f'JS module does not branch on HTTP {status}'
        )
    # 5xx must be handled distinctly from 4xx.
    assert '>= 500' in source or '>=500' in source, (
        'JS module does not have a separate 5xx handler'
    )


def test_js_module_confirms_before_delete(app):
    source = _read_static(app, 'js', 'hmrc-periods-of-account.js')

    # Delete must prompt the user before sending.
    assert 'confirm(' in source


# ---------------------------------------------------------------------------
# CSS file rules
# ---------------------------------------------------------------------------

def test_css_uses_only_bootstrap_variables(app):
    """The user rules require Bootstrap CSS variables, no hardcoded hex."""
    css = _read_static(app, 'css', 'hmrc-periods-of-account.css')

    # No literal hex colour values.
    import re
    hex_matches = re.findall(r'#[0-9a-fA-F]{3,8}\b', css)
    assert not hex_matches, (
        f'Hardcoded hex colours found in hmrc-periods-of-account.css: '
        f'{hex_matches}'
    )

    # Must reference Bootstrap variables.
    assert '--bs-' in css, 'CSS does not use any --bs-* variables'


def test_css_has_no_important_overrides(app):
    css = _read_static(app, 'css', 'hmrc-periods-of-account.css')
    assert '!important' not in css, (
        '!important is forbidden in hmrc-periods-of-account.css'
    )
