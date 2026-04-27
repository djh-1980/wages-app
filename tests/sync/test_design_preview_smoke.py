"""Smoke test: /design-preview is publicly accessible and renders the
expected scaffolding (theme buttons, switcher script, mobile toggle)."""

from __future__ import annotations


def test_design_preview_is_public_no_auth_required(client):
    response = client.get('/design-preview')
    assert response.status_code == 200, response.status_code
    body = response.get_data(as_text=True)

    # Page scaffold
    assert 'theme-stylesheet' in body
    assert 'data-theme="a"' in body
    assert 'data-theme="b"' in body
    assert 'data-theme="c"' in body
    assert 'data-theme="d"' in body
    assert 'Toggle mobile view' in body

    # Theme stylesheet URLs are emitted by url_for
    assert 'theme-a.css' in body
    assert 'theme-b.css' in body
    assert 'theme-c.css' in body
    assert 'theme-d.css' in body

    # Sample widgets present
    assert 'Run Sheets' in body                   # page header
    assert 'Confirm Delete' in body               # fake modal
    assert 'Chart · weekly pay trend' in body     # chart placeholder
