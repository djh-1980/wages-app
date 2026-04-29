"""UI tests for the HMRC Annual Submission panel.

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

def test_annual_submission_card_present(auth_client):
    body = _get_page(auth_client)

    assert 'id="annCard"' in body
    assert 'Annual Submission' in body
    assert 'settings-card' in body
    assert 'ann-card' in body


def test_panel_renders_all_required_element_ids(auth_client):
    body = _get_page(auth_client)

    for el_id in (
        'annTaxYearSelect',
        'annHelperText',
        'annLastSubmittedTimestamp',
        'annDraftBadge',
        'annDraftAge',
        'annForm',
        'annAccordion',
        'annAllowancesToggle',
        'annAllowancesBody',
        'annAdjustmentsToggle',
        'annAdjustmentsBody',
        'annNonFinancialsToggle',
        'annNonFinancialsBody',
        'annResult',
        'annSaveDraftBtn',
        'annDiscardDraftBtn',
        'annSubmitBtn',
    ):
        assert f'id="{el_id}"' in body, f'missing element {el_id}'


def test_tax_year_selector_offers_relevant_years(auth_client):
    body = _get_page(auth_client)

    select_idx = body.find('id="annTaxYearSelect"')
    assert select_idx != -1
    end = body.find('</select>', select_idx)
    snippet = body[select_idx:end]
    assert 'value="2024-25"' in snippet
    assert 'value="2025-26"' in snippet
    assert 'value="2026-27"' in snippet
    assert 'value="2025-26" selected' in snippet


# ---------------------------------------------------------------------------
# accordion sections
# ---------------------------------------------------------------------------

ALLOWANCE_FIELDS = (
    'annualInvestmentAllowance',
    'capitalAllowanceMainPool',
    'capitalAllowanceSpecialRatePool',
    'zeroEmissionGoodsVehicleAllowance',
    'businessPremisesRenovationAllowance',
    'enhancedCapitalAllowance',
    'allowanceOnSales',
)

ADJUSTMENT_FIELDS = (
    'includedNonTaxableProfits',
    'basisAdjustment',
    'overlapReliefUsed',
    'accountingAdjustment',
    'averagingAdjustment',
    'outstandingBusinessIncome',
    'balancingChargeBpra',
    'balancingChargeOther',
    'goodsAndServicesOwnUse',
)


def _input_open_tag(body, input_id):
    """Return the opening <input ...> tag for the given id, or None."""
    idx = body.find(f'id="{input_id}"')
    if idx == -1:
        return None
    open_start = body.rfind('<input', 0, idx)
    if open_start == -1:
        return None
    open_end = body.find('>', open_start)
    return body[open_start:open_end + 1]


def test_all_seven_allowance_inputs_present_with_correct_attrs(auth_client):
    body = _get_page(auth_client)

    for field in ALLOWANCE_FIELDS:
        # ID is camelCase prefixed: annAnnualInvestmentAllowance etc.
        input_id = f'ann{field[0].upper()}{field[1:]}'
        tag = _input_open_tag(body, input_id)
        assert tag is not None, f'allowance input {input_id} missing'
        assert 'type="number"' in tag
        assert 'step="0.01"' in tag
        assert 'min="0"' in tag
        assert 'value="0"' in tag
        assert f'data-field="{field}"' in tag
        assert 'data-section="allowances"' in tag


def test_all_nine_adjustment_inputs_present_with_correct_attrs(auth_client):
    body = _get_page(auth_client)

    for field in ADJUSTMENT_FIELDS:
        input_id = f'ann{field[0].upper()}{field[1:]}'
        tag = _input_open_tag(body, input_id)
        assert tag is not None, f'adjustment input {input_id} missing'
        assert 'type="number"' in tag
        assert 'step="0.01"' in tag
        assert 'min="0"' in tag
        assert 'value="0"' in tag
        assert f'data-field="{field}"' in tag
        assert 'data-section="adjustments"' in tag


def test_non_financials_section_has_checkbox_and_dropdown(auth_client):
    body = _get_page(auth_client)

    # Checkbox: businessDetailsChangedRecently
    cb_tag = _input_open_tag(body, 'annBusinessDetailsChangedRecently')
    assert cb_tag is not None
    assert 'type="checkbox"' in cb_tag
    assert 'data-section="nonFinancials"' in cb_tag
    assert 'data-field="businessDetailsChangedRecently"' in cb_tag

    # Dropdown: class4NicsExemptionReason
    sel_idx = body.find('id="annClass4NicsExemptionReason"')
    assert sel_idx != -1
    end = body.find('</select>', sel_idx)
    snippet = body[sel_idx:end]
    assert 'data-section="nonFinancials"' in snippet
    assert 'data-field="class4NicsExemptionReason"' in snippet
    # The HMRC-defined exemption codes.
    for code in (
        'non-resident', 'trustee', 'diver', 'ITTOIA-2005',
        'over-state-pension-age', 'under-16',
    ):
        assert f'value="{code}"' in snippet, f'missing exemption option {code}'


def test_three_accordion_sections_are_collapsible(auth_client):
    """Each section must use Bootstrap's data-bs-toggle="collapse" so the
    user can expand/collapse from the keyboard."""
    body = _get_page(auth_client)

    for toggle_id, target_id in (
        ('annAllowancesToggle', '#annAllowancesBody'),
        ('annAdjustmentsToggle', '#annAdjustmentsBody'),
        ('annNonFinancialsToggle', '#annNonFinancialsBody'),
    ):
        idx = body.find(f'id="{toggle_id}"')
        assert idx != -1, f'{toggle_id} missing'
        snippet = body[max(0, idx - 400):idx + 100]
        assert 'data-bs-toggle="collapse"' in snippet
        assert f'data-bs-target="{target_id}"' in snippet


# ---------------------------------------------------------------------------
# helper text
# ---------------------------------------------------------------------------

def test_helper_text_explains_annual_submission(auth_client):
    body = _get_page(auth_client)

    start = body.find('id="annHelperText"')
    assert start != -1
    end = body.find('</p>', start)
    text = re.sub(r'\s+', ' ', body[start:end]).lower()

    # Required signal phrases per spec.
    assert 'cash basis' in text
    assert 'mandatory' in text


# ---------------------------------------------------------------------------
# action buttons
# ---------------------------------------------------------------------------

def test_save_draft_button_present(auth_client):
    body = _get_page(auth_client)
    assert 'id="annSaveDraftBtn"' in body
    # Button should reference 'Save Draft'.
    idx = body.find('id="annSaveDraftBtn"')
    snippet = body[max(0, idx - 200):idx + 200]
    assert 'Save Draft' in snippet


def test_discard_draft_button_starts_hidden(auth_client):
    """Discard Draft only shows once a draft exists; JS toggles d-none."""
    body = _get_page(auth_client)

    idx = body.find('id="annDiscardDraftBtn"')
    assert idx != -1
    snippet = body[max(0, idx - 250):idx + 100]
    btn_open_start = snippet.rfind('<button')
    btn_open_end = snippet.find('>', btn_open_start)
    open_tag = snippet[btn_open_start:btn_open_end + 1]
    assert 'd-none' in open_tag


def test_submit_button_present(auth_client):
    body = _get_page(auth_client)
    assert 'id="annSubmitBtn"' in body
    idx = body.find('id="annSubmitBtn"')
    snippet = body[max(0, idx - 200):idx + 200]
    assert 'Submit to HMRC' in snippet


def test_draft_badge_starts_hidden(auth_client):
    body = _get_page(auth_client)

    idx = body.find('id="annDraftBadge"')
    assert idx != -1
    snippet = body[max(0, idx - 200):idx + 100]
    span_open_start = snippet.rfind('<span')
    span_open_end = snippet.find('>', span_open_start)
    open_tag = snippet[span_open_start:span_open_end + 1]
    assert 'd-none' in open_tag


# ---------------------------------------------------------------------------
# CSS / JS wiring
# ---------------------------------------------------------------------------

def test_annual_submission_css_loaded(auth_client):
    body = _get_page(auth_client)
    assert 'css/hmrc-annual-submission.css' in body, (
        'hmrc-annual-submission.css not wired into extra_css block'
    )


def test_annual_submission_js_loaded(auth_client):
    body = _get_page(auth_client)
    assert 'js/hmrc-annual-submission.js' in body, (
        'hmrc-annual-submission.js not wired into extra_js block'
    )


def test_no_inline_styles_in_panel(auth_client):
    body = _get_page(auth_client)

    start = body.find('id="annCard"')
    assert start != -1
    end = body.find('<!-- Tabs for Obligations', start)
    assert end != -1
    panel_html = body[start:end]

    assert 'style=' not in panel_html, (
        'Inline styles found in Annual Submission panel - move to '
        'static/css/hmrc-annual-submission.css'
    )


# ---------------------------------------------------------------------------
# JS module surface
# ---------------------------------------------------------------------------

def test_js_module_exposes_public_api(app):
    source = _read_static(app, 'js', 'hmrc-annual-submission.js')

    assert 'window.HMRCAnnualSubmission' in source
    for fn in ('load:', 'saveDraft:', 'discardDraft:', 'submit:'):
        assert fn in source, f'{fn} missing from window.HMRCAnnualSubmission'


def test_js_module_targets_correct_endpoints(app):
    source = _read_static(app, 'js', 'hmrc-annual-submission.js')

    assert '/api/hmrc/annual-submission/' in source
    assert '/draft' in source

    for method in ("'GET'", "'POST'", "'PUT'", "'DELETE'"):
        assert method in source


def test_js_module_handles_distinct_status_codes(app):
    source = _read_static(app, 'js', 'hmrc-annual-submission.js')

    for status in ('400', '404', '409', '422'):
        assert status in source, f'JS module does not branch on HTTP {status}'
    assert '>= 500' in source or '>=500' in source


def test_js_module_confirms_before_submit(app):
    source = _read_static(app, 'js', 'hmrc-annual-submission.js')
    # submit() must call confirm() before sending. discardDraft() also
    # calls confirm() so we expect at least 2 confirm() invocations.
    assert source.count('window.confirm(') >= 2


def test_js_module_builds_nested_payload(app):
    source = _read_static(app, 'js', 'hmrc-annual-submission.js')
    # collectFormData must build {allowances, adjustments, nonFinancials}.
    assert 'allowances' in source
    assert 'adjustments' in source
    assert 'nonFinancials' in source


# ---------------------------------------------------------------------------
# CSS file rules
# ---------------------------------------------------------------------------

def test_css_uses_only_bootstrap_variables(app):
    css = _read_static(app, 'css', 'hmrc-annual-submission.css')

    hex_matches = re.findall(r'#[0-9a-fA-F]{3,8}\b', css)
    assert not hex_matches, (
        f'Hardcoded hex colours found in hmrc-annual-submission.css: {hex_matches}'
    )
    assert '--bs-' in css, 'CSS does not use any --bs-* variables'


def test_css_has_no_important_overrides(app):
    css = _read_static(app, 'css', 'hmrc-annual-submission.css')
    assert '!important' not in css, (
        '!important is forbidden in hmrc-annual-submission.css'
    )


def test_css_touch_target_min_height(app):
    css = _read_static(app, 'css', 'hmrc-annual-submission.css')
    assert 'ann-action-btn' in css
    assert 'min-height: 44px' in css
