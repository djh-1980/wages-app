"""Phase 1.1 regression test: manual upload copies the PDF to NAS canonical path.

Previously `process_single_runsheet` called two scripts that no longer exist
(`scripts/organize_uploaded_runsheets.py`, `scripts/sync_runsheets_with_payslips.py`).
Their non-zero exit codes were swallowed and the uploaded PDF stayed in
`data/processing/manual/...` forever, never reaching `<Config.RUNSHEETS_DIR>`.

This test asserts the post-import copy now happens.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def fake_pdf(tmp_path):
    """Create a tiny dummy file that pretends to be the uploaded PDF."""
    pdf = tmp_path / 'manual' / 'DH_27-04-2026_20260427_120000.pdf'
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b'%PDF-1.4\n%fake pdf bytes\n')
    return pdf


@pytest.fixture
def fake_runsheets_dir(tmp_path):
    """A throwaway directory standing in for the NAS mount."""
    target = tmp_path / 'runsheets_nas'
    target.mkdir(parents=True, exist_ok=True)
    return target


def _stub_db_connection(date_value: str | None = '27/04/2026'):
    """Return a context-managed mock DB connection that yields a row with `date`."""
    cursor = MagicMock()
    cursor.rowcount = 1
    cursor.fetchone.return_value = (date_value,) if date_value is not None else None
    cursor.execute.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    return conn


def test_successful_import_copies_to_nas_canonical_path(fake_pdf, fake_runsheets_dir):
    from app.routes import api_upload

    completed = MagicMock()
    completed.returncode = 0
    completed.stdout = '✓ Successfully imported 5 jobs'
    completed.stderr = ''

    with patch.object(api_upload.subprocess, 'run', return_value=completed) as run_mock, \
         patch.object(api_upload, 'get_db_connection', return_value=_stub_db_connection('27/04/2026')), \
         patch('app.config.Config.RUNSHEETS_DIR', str(fake_runsheets_dir)):
        result = api_upload.process_single_runsheet(str(fake_pdf))

    assert result['success'] is True, result
    # Subprocess called import_run_sheets.py once.
    run_mock.assert_called_once()
    args = run_mock.call_args.args[0]
    assert 'scripts/production/import_run_sheets.py' in args
    assert '--file' in args

    # Canonical file present at the expected path.
    expected = fake_runsheets_dir / '2026' / '04-April' / 'DH_27-04-2026.pdf'
    assert expected.exists(), (
        f'Expected canonical PDF at {expected}, got runsheets_dir={list(fake_runsheets_dir.rglob("*"))}'
    )
    assert expected.read_bytes() == fake_pdf.read_bytes()
    assert 'Copied to NAS' in result['output']


def test_skips_copy_when_canonical_already_exists(fake_pdf, fake_runsheets_dir):
    from app.routes import api_upload

    # Pre-create the canonical file with different content; it must not be overwritten.
    canonical = fake_runsheets_dir / '2026' / '04-April' / 'DH_27-04-2026.pdf'
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_bytes(b'%PDF-1.4\n%existing canonical pdf')

    completed = MagicMock()
    completed.returncode = 0
    completed.stdout = ''
    completed.stderr = ''

    with patch.object(api_upload.subprocess, 'run', return_value=completed), \
         patch.object(api_upload, 'get_db_connection', return_value=_stub_db_connection('27/04/2026')), \
         patch('app.config.Config.RUNSHEETS_DIR', str(fake_runsheets_dir)):
        result = api_upload.process_single_runsheet(str(fake_pdf))

    assert result['success'] is True
    # Existing file untouched.
    assert canonical.read_bytes() == b'%PDF-1.4\n%existing canonical pdf'
    assert 'already exists' in result['output']


def test_no_db_date_means_no_copy_but_still_success(fake_pdf, fake_runsheets_dir):
    """If we can't find a date in DB (edge case), report success but log a warning."""
    from app.routes import api_upload

    completed = MagicMock()
    completed.returncode = 0
    completed.stdout = ''
    completed.stderr = ''

    with patch.object(api_upload.subprocess, 'run', return_value=completed), \
         patch.object(api_upload, 'get_db_connection', return_value=_stub_db_connection(None)), \
         patch('app.config.Config.RUNSHEETS_DIR', str(fake_runsheets_dir)):
        result = api_upload.process_single_runsheet(str(fake_pdf))

    assert result['success'] is True
    assert list(fake_runsheets_dir.rglob('*.pdf')) == []
    assert 'No runsheet date found' in result['output']


def test_failed_import_returns_error_no_copy(fake_pdf, fake_runsheets_dir):
    from app.routes import api_upload

    completed = MagicMock()
    completed.returncode = 1
    completed.stdout = ''
    completed.stderr = 'parser failed'

    with patch.object(api_upload.subprocess, 'run', return_value=completed), \
         patch.object(api_upload, 'get_db_connection', return_value=_stub_db_connection('27/04/2026')), \
         patch('app.config.Config.RUNSHEETS_DIR', str(fake_runsheets_dir)):
        result = api_upload.process_single_runsheet(str(fake_pdf))

    assert result['success'] is False
    assert result['error'] == 'parser failed'
    # No canonical file should have been created.
    assert list(fake_runsheets_dir.rglob('*.pdf')) == []
