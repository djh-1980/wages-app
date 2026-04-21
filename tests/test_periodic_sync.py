"""Unit tests for ``app.services.periodic_sync.PeriodicSyncService``.

This module exercises the state machine, short-circuit logic and helpers on
the sync service. Every subprocess call, database read and scheduler hook
is mocked: tests are deterministic, self-contained, and run in well under
a second each.

Background: every week has shipped a new sync regression (download
tracking, path resolution, exit codes, regex parsing). These tests lock
down the working behaviour.
"""

import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from subprocess import CompletedProcess

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_datetime(fixed_now):
    """Build a ``datetime`` subclass whose ``.now()`` returns ``fixed_now``.

    We subclass the real ``datetime`` so that arithmetic with ``timedelta``
    and other ``datetime`` instances keeps working inside the module under
    test.
    """

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    return FakeDatetime


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sync_service(monkeypatch):
    """Fresh ``PeriodicSyncService`` with external hooks neutralised."""
    # Prevent _load_config from touching the real settings DB.
    from app.services import periodic_sync as ps_mod

    monkeypatch.setattr(
        ps_mod.PeriodicSyncService, '_load_config', lambda self: None
    )
    service = ps_mod.PeriodicSyncService()
    # The ``is_running`` flag gates _estimate_next_sync() and some helpers.
    service.is_running = True
    yield service
    service.is_running = False


@pytest.fixture
def freeze_now(monkeypatch):
    """Factory: freeze ``datetime.now()`` inside periodic_sync to a value."""

    def _freeze(fixed_now):
        from app.services import periodic_sync as ps_mod
        monkeypatch.setattr(ps_mod, 'datetime', _make_fake_datetime(fixed_now))
        return fixed_now

    return _freeze


@pytest.fixture
def mock_latest_runsheet(monkeypatch):
    """Factory: mock ``get_latest_runsheet_date()`` inside periodic_sync."""

    def _mock(date_str):
        monkeypatch.setattr(
            'app.services.periodic_sync.get_latest_runsheet_date',
            lambda: date_str,
        )

    return _mock


@pytest.fixture
def mock_latest_payslip_week(monkeypatch):
    """Factory: mock ``get_latest_payslip_week()`` inside periodic_sync."""

    def _mock(week_str):
        monkeypatch.setattr(
            'app.services.periodic_sync.get_latest_payslip_week',
            lambda: week_str,
        )

    return _mock


@pytest.fixture
def silent_schedule(monkeypatch):
    """No-op out the ``schedule`` library so tests don't touch the scheduler."""
    import app.services.periodic_sync as ps_mod

    class _Fake:
        def clear(self, *a, **kw):
            pass

        def every(self, *a, **kw):
            return self

        def day(self, *a, **kw):
            return self

        def at(self, *a, **kw):
            return self

        def do(self, *a, **kw):
            return self

        def run_pending(self, *a, **kw):
            pass

    monkeypatch.setattr(ps_mod, 'schedule', _Fake())


# ---------------------------------------------------------------------------
# Pause / resume state machine
# ---------------------------------------------------------------------------

class TestPauseResume:
    def test_pause_indefinitely_sets_flags(self, sync_service):
        sync_service.pause_sync()
        assert sync_service.is_paused is True
        assert sync_service.pause_until is None
        assert sync_service.current_state == 'paused'

    def test_pause_with_duration_sets_future_timestamp(
        self, sync_service, freeze_now
    ):
        freeze_now(datetime(2026, 4, 21, 12, 0))
        sync_service.pause_sync(duration_minutes=30)
        assert sync_service.is_paused is True
        assert sync_service.pause_until == datetime(2026, 4, 21, 12, 30)

    def test_resume_clears_pause_state(self, sync_service, silent_schedule):
        sync_service.is_paused = True
        sync_service.pause_until = datetime(2030, 1, 1)
        sync_service.current_state = 'paused'

        assert sync_service.resume_sync() is True
        assert sync_service.is_paused is False
        assert sync_service.pause_until is None
        assert sync_service.current_state == 'idle'


# ---------------------------------------------------------------------------
# sync_latest() early-return guards
# ---------------------------------------------------------------------------

class TestSyncLatestGuards:
    def test_paused_indefinitely_returns_early(self, sync_service):
        sync_service.is_paused = True
        sync_service.pause_until = None
        # Must return without touching state beyond what pause set.
        sync_service.sync_latest()
        # Still paused, did not flip to 'running'.
        assert sync_service.current_state != 'running'

    def test_paused_until_future_returns_early(self, sync_service, freeze_now):
        freeze_now(datetime(2026, 4, 21, 12, 0))
        sync_service.is_paused = True
        sync_service.pause_until = datetime(2026, 4, 21, 13, 0)

        sync_service.sync_latest()

        # Still paused, still has pause_until.
        assert sync_service.is_paused is True
        assert sync_service.pause_until == datetime(2026, 4, 21, 13, 0)

    def test_already_running_returns_early(self, sync_service):
        sync_service.current_state = 'running'
        # Call must return without flipping current_state off, so the
        # concurrent instance keeps the lock.
        sync_service.sync_latest()
        assert sync_service.current_state == 'running'

    def test_paused_until_past_auto_resumes(
        self, sync_service, freeze_now, silent_schedule, mock_latest_runsheet
    ):
        """An expired pause window triggers resume_sync() before running."""
        freeze_now(datetime(2026, 4, 21, 12, 0))
        sync_service.is_paused = True
        sync_service.pause_until = datetime(2026, 4, 21, 11, 0)  # past

        # Pre-populate the "have tomorrow" short-circuit so sync_latest exits
        # cleanly right after auto-resuming.
        mock_latest_runsheet('22/04/2026')

        sync_service.sync_latest()

        assert sync_service.is_paused is False
        assert sync_service.pause_until is None


# ---------------------------------------------------------------------------
# Tomorrow's-runsheet short circuit
# ---------------------------------------------------------------------------

class TestTomorrowShortCircuit:
    """When latest runsheet is tomorrow or later, sync must short-circuit."""

    @pytest.mark.parametrize('latest', ['22/04/2026', '22-04-2026', '23/04/2026'])
    def test_have_tomorrow_stops_sync(
        self, sync_service, freeze_now, silent_schedule,
        mock_latest_runsheet, latest,
    ):
        freeze_now(datetime(2026, 4, 21, 19, 0))
        mock_latest_runsheet(latest)

        sync_service.sync_latest()

        # Should have early-exited before any download attempt, so no errors
        # accumulated and runsheet_completed_today was not flipped by the
        # download path.
        assert sync_service.last_error is None

    def test_latest_before_tomorrow_does_not_short_circuit(
        self, sync_service, freeze_now, silent_schedule,
        mock_latest_runsheet, monkeypatch,
    ):
        freeze_now(datetime(2026, 4, 21, 19, 0))
        mock_latest_runsheet('20/04/2026')

        # Stub out the subprocess calls so the sync can proceed without
        # actually running any scripts.
        def fake_run(*args, **kwargs):
            return CompletedProcess(args=args[0], returncode=0, stdout='', stderr='')

        monkeypatch.setattr('subprocess.run', fake_run)
        monkeypatch.setattr('time.sleep', lambda *_: None)

        # Also stub the disk walk so we don't scan real filesystem.
        monkeypatch.setattr(
            sync_service, '_get_unprocessed_runsheets', lambda: []
        )

        sync_service.sync_latest()

        # current_state advanced past the short-circuit (either 'running'
        # still at end of try, or already transitioned - the key point is
        # it did NOT early-return).
        assert sync_service.current_state != 'idle'

    def test_no_runsheets_in_db_does_not_short_circuit(
        self, sync_service, freeze_now, silent_schedule,
        mock_latest_runsheet, monkeypatch,
    ):
        freeze_now(datetime(2026, 4, 21, 19, 0))
        mock_latest_runsheet(None)

        def fake_run(*args, **kwargs):
            return CompletedProcess(args=args[0], returncode=0, stdout='', stderr='')

        monkeypatch.setattr('subprocess.run', fake_run)
        monkeypatch.setattr('time.sleep', lambda *_: None)
        monkeypatch.setattr(
            sync_service, '_get_unprocessed_runsheets', lambda: []
        )

        sync_service.sync_latest()

        # Did not short-circuit (state changed from idle).
        assert sync_service.current_state != 'idle'


# ---------------------------------------------------------------------------
# New-day / new-week tracking resets
# ---------------------------------------------------------------------------

class TestDailyResets:
    def test_new_day_resets_runsheet_completed_today(
        self, sync_service, freeze_now, silent_schedule, mock_latest_runsheet
    ):
        freeze_now(datetime(2026, 4, 21, 19, 0))
        mock_latest_runsheet('22/04/2026')  # short-circuit after reset

        sync_service.last_check_date = '2026-04-20'  # yesterday
        sync_service.runsheet_completed_today = True
        sync_service.sync_started_today = True
        sync_service.last_runsheet_date_processed = '20/04/2026'

        sync_service.sync_latest()

        assert sync_service.last_check_date == '2026-04-21'
        assert sync_service.runsheet_completed_today is False
        assert sync_service.sync_started_today is False
        assert sync_service.last_runsheet_date_processed is None

    def test_same_day_does_not_reset_tracking(
        self, sync_service, freeze_now, silent_schedule, mock_latest_runsheet
    ):
        freeze_now(datetime(2026, 4, 21, 19, 0))
        mock_latest_runsheet('22/04/2026')  # short-circuit

        sync_service.last_check_date = '2026-04-21'  # same day
        sync_service.runsheet_completed_today = True

        sync_service.sync_latest()

        # runsheet_completed_today should remain True.
        assert sync_service.runsheet_completed_today is True

    def test_tuesday_new_payslip_week_resets_flag(
        self, sync_service, freeze_now, silent_schedule,
        mock_latest_runsheet, mock_latest_payslip_week,
    ):
        # 2026-04-21 is a Tuesday.
        assert datetime(2026, 4, 21).weekday() == 1
        freeze_now(datetime(2026, 4, 21, 19, 0))
        mock_latest_runsheet('22/04/2026')  # short-circuit
        mock_latest_payslip_week('Week 16, 2026')

        sync_service.last_payslip_week_processed = 'Week 15, 2026'
        sync_service.payslip_completed_this_week = True

        sync_service.sync_latest()

        assert sync_service.payslip_completed_this_week is False


# ---------------------------------------------------------------------------
# Import-output regex parsing
# ---------------------------------------------------------------------------

# The sync loop uses this regex to extract a job count from the importer's
# stdout. Re-declaring it here keeps the test focused on the contract.
_IMPORT_JOB_COUNT_RE = re.compile(
    r'[Ii]mported (\d+) jobs|✓ Imported (\d+)|imported (\d+)'
)


class TestImportJobCountRegex:
    @pytest.mark.parametrize(
        'output, expected',
        [
            ('Imported 5 jobs from DH_21-04-2026.pdf', 5),
            ('✓ Imported 3', 3),
            ('imported 7', 7),
        ],
    )
    def test_matches_known_formats(self, output, expected):
        match = _IMPORT_JOB_COUNT_RE.search(output)
        assert match is not None, f'Regex did not match: {output!r}'
        groups = [g for g in match.groups() if g is not None]
        assert int(groups[0]) == expected

    def test_no_match_on_unrelated_output(self):
        assert _IMPORT_JOB_COUNT_RE.search('nothing interesting here') is None


# ---------------------------------------------------------------------------
# _get_unprocessed_runsheets()
# ---------------------------------------------------------------------------

class TestGetUnprocessedRunsheets:
    def test_missing_dir_returns_empty(self, sync_service, monkeypatch, tmp_path):
        from app import config as config_mod

        missing = tmp_path / 'does_not_exist'
        monkeypatch.setattr(config_mod.Config, 'RUNSHEETS_DIR', str(missing))

        assert sync_service._get_unprocessed_runsheets() == []

    def test_returns_pdfs_not_in_db(
        self, sync_service, monkeypatch, tmp_path
    ):
        from app import config as config_mod
        from app.services import periodic_sync as ps_mod

        # Build a fake runsheets tree with three PDFs; two real DH_* files
        # and one macOS resource fork that must be ignored.
        year_dir = tmp_path / '2026' / '04-April'
        year_dir.mkdir(parents=True)
        (year_dir / 'DH_21-04-2026.pdf').write_bytes(b'%PDF-fake')
        (year_dir / 'DH_22-04-2026.pdf').write_bytes(b'%PDF-fake')
        (year_dir / '._DH_22-04-2026.pdf').write_bytes(b'resource fork')

        monkeypatch.setattr(config_mod.Config, 'RUNSHEETS_DIR', str(tmp_path))

        # Point the sync service's DB lookup at an in-memory DB seeded with
        # just one imported file.
        db_path = tmp_path / 'test.db'
        conn = sqlite3.connect(db_path)
        conn.execute(
            'CREATE TABLE run_sheet_jobs (source_file TEXT)'
        )
        conn.execute(
            'INSERT INTO run_sheet_jobs (source_file) VALUES (?)',
            ('DH_21-04-2026.pdf',),
        )
        conn.commit()
        conn.close()

        monkeypatch.setattr(ps_mod, 'DB_PATH', str(db_path))

        unprocessed = sync_service._get_unprocessed_runsheets()

        names = sorted(f.name for f in unprocessed)
        assert names == ['DH_22-04-2026.pdf']
        # Resource fork file must not leak through.
        assert not any(n.startswith('._') for n in names)

    def test_db_error_returns_empty_list(
        self, sync_service, monkeypatch, tmp_path
    ):
        from app import config as config_mod
        from app.services import periodic_sync as ps_mod

        (tmp_path / 'DH_21-04-2026.pdf').write_bytes(b'%PDF')
        monkeypatch.setattr(config_mod.Config, 'RUNSHEETS_DIR', str(tmp_path))

        # Point DB_PATH at a directory (not a file) to force sqlite3 errors.
        bad_db = tmp_path / 'not_a_real_db_dir'
        bad_db.mkdir()
        monkeypatch.setattr(ps_mod, 'DB_PATH', str(bad_db))

        # Should swallow the exception and return [].
        assert sync_service._get_unprocessed_runsheets() == []
