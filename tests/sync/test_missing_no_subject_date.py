"""Phase 1.2 regression test: --missing mode no longer filters by subject date.

Previously `download_missing_runsheets` parsed the email Subject with
    re.search(r'(\\d{1,2})(?:st|nd|rd|th)?\\s+(\\w+)\\s+(\\d{4})', subject)
and silently dropped any email whose subject lacked an English date pattern
(e.g. 'Warrington - Run Sheets', 'RUN SHEETS - WARRINGTON'). This test
asserts the new behaviour: every email returned by the Gmail search has its
attachments downloaded, regardless of subject.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _build_msg_metadata(subject: str) -> dict:
    """Build the shape returned by service.users().messages().get(format='metadata')."""
    return {
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': subject},
                {'name': 'Date', 'value': 'Mon, 27 Apr 2026 19:30:00 +0000'},
            ],
        },
    }


def test_missing_mode_downloads_email_with_no_date_in_subject(tmp_path):
    """A 'Warrington - Run Sheets' subject (no date) must NOT be skipped."""
    from scripts.production import download_runsheets_gmail as drg

    downloader = drg.GmailRunSheetDownloader(download_dir=tmp_path)

    # Three fake emails: one no-date subject, one with-date subject, one bare.
    subjects = [
        'Warrington - Run Sheets',
        'MONDAY 27th APRIL 2026',
        'RUN SHEETS - WARRINGTON',
    ]
    fake_emails = [{'id': f'msg-{i}'} for i in range(len(subjects))]

    # Patch the Gmail service tree to return our fake messages and metadata.
    service = MagicMock()
    messages = service.users.return_value.messages.return_value

    def _get(userId, id, format=None, metadataHeaders=None):
        idx = int(id.rsplit('-', 1)[1])
        return MagicMock(execute=MagicMock(return_value=_build_msg_metadata(subjects[idx])))

    messages.get.side_effect = _get
    downloader.service = service

    # Stub the methods that would otherwise hit Gmail or disk.
    download_calls: list[str] = []

    def _download_attachments(email_id: str):
        download_calls.append(email_id)
        return [f'{email_id}.pdf']

    with patch.object(downloader, 'authenticate', return_value=True), \
         patch.object(downloader, 'find_missing_runsheet_dates',
                      return_value=['27/04/2026']), \
         patch.object(downloader, 'search_run_sheet_emails',
                      return_value=fake_emails), \
         patch.object(downloader, 'download_attachments',
                      side_effect=_download_attachments), \
         patch.object(downloader, 'organize_pdf', side_effect=lambda p: p):
        downloader.download_missing_runsheets(days_back=14)

    # Every email must have been processed — no subject filtering.
    assert download_calls == ['msg-0', 'msg-1', 'msg-2'], (
        f'Expected all 3 emails downloaded, got {download_calls}'
    )


def test_missing_mode_no_subject_regex_in_source():
    """Belt-and-braces: the dropped regex must not reappear during a careless rebase."""
    import inspect
    from scripts.production import download_runsheets_gmail as drg

    src = inspect.getsource(drg.GmailRunSheetDownloader.download_missing_runsheets)
    # The old subject-date regex pattern should be gone.
    assert 'st|nd|rd|th' not in src, (
        'Subject-date regex (st|nd|rd|th) reintroduced in download_missing_runsheets'
    )
    assert 'JANUARY' not in src, (
        'Subject month-name map reintroduced in download_missing_runsheets'
    )
