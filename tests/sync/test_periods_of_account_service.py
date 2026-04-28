"""Unit tests for app.services.periods_of_account_service.

These tests do not call HMRC; they only exercise the local service
against an isolated test database.
"""

import pytest


def test_create_standard_period_for_tax_year(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        record = svc.create_standard_period('2025-26')

    assert record['tax_year'] == '2025-26'
    assert record['period_start_date'] == '2025-04-06'
    assert record['period_end_date'] == '2026-04-05'
    assert record['period_type'] == 'standard'
    assert record['deleted_at'] is None


def test_default_period_is_6_april_to_5_april(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        start, end = svc.standard_period_dates('2024-25')

    assert start == '2024-04-06'
    assert end == '2025-04-05'


def test_create_standard_period_is_idempotent(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        a = svc.create_standard_period('2025-26')
        b = svc.create_standard_period('2025-26')

    assert a['id'] == b['id']


def test_create_custom_period(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        record = svc.create_custom_period(
            '2025-26',
            start_date='2025-04-01',
            end_date='2026-03-31',
            business_id='XAIS123',
        )

    assert record['tax_year'] == '2025-26'
    assert record['period_start_date'] == '2025-04-01'
    assert record['period_end_date'] == '2026-03-31'
    assert record['period_type'] == 'non-standard'
    assert record['business_id'] == 'XAIS123'


def test_create_custom_period_marked_standard_when_dates_match(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        record = svc.create_custom_period(
            '2025-26',
            start_date='2025-04-06',
            end_date='2026-04-05',
        )

    assert record['period_type'] == 'standard'


def test_create_custom_period_accepts_ddmmyyyy(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        record = svc.create_custom_period(
            '2025-26',
            start_date='06/04/2025',
            end_date='05/04/2026',
        )

    assert record['period_start_date'] == '2025-04-06'
    assert record['period_end_date'] == '2026-04-05'


def test_create_custom_period_rejects_duplicate_active(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        svc.create_standard_period('2025-26')
        with pytest.raises(ValueError):
            svc.create_custom_period(
                '2025-26',
                start_date='2025-04-01',
                end_date='2026-03-31',
            )


def test_get_for_tax_year_returns_active_period(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        created = svc.create_standard_period('2025-26')
        fetched = svc.get_for_tax_year('2025-26')

    assert fetched is not None
    assert fetched['id'] == created['id']


def test_get_for_tax_year_ignores_deleted(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        svc.create_standard_period('2025-26')
        assert svc.delete_period('2025-26') is True
        assert svc.get_for_tax_year('2025-26') is None


def test_get_for_tax_year_returns_none_when_absent(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        assert svc.get_for_tax_year('2099-00') is None


def test_update_period_dates(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        svc.create_standard_period('2025-26')
        updated = svc.update_period(
            '2025-26',
            start_date='2025-05-01',
            end_date='2026-04-30',
            period_type='non-standard',
        )

    assert updated['period_start_date'] == '2025-05-01'
    assert updated['period_end_date'] == '2026-04-30'
    assert updated['period_type'] == 'non-standard'


def test_update_period_preserves_unspecified_fields(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        original = svc.create_standard_period('2025-26', business_id='XAIS1')
        updated = svc.update_period('2025-26', period_id='POA-9')

    assert updated['business_id'] == original['business_id']
    assert updated['period_start_date'] == original['period_start_date']
    assert updated['period_end_date'] == original['period_end_date']
    assert updated['period_id'] == 'POA-9'


def test_update_period_raises_when_missing(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        with pytest.raises(ValueError):
            svc.update_period('2099-00', start_date='2099-04-06')


def test_soft_delete_period(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        svc.create_standard_period('2025-26')
        assert svc.delete_period('2025-26') is True
        # second call is a no-op (no active period left)
        assert svc.delete_period('2025-26') is False

        # Deleted row is still in the table for audit / list_periods.
        all_rows = svc.list_periods(include_deleted=True)
        assert any(
            r['tax_year'] == '2025-26' and r['deleted_at'] is not None
            for r in all_rows
        )


def test_period_dates_validation_start_before_end(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        with pytest.raises(ValueError):
            svc.create_custom_period(
                '2025-26',
                start_date='2026-04-05',
                end_date='2025-04-06',
            )
        with pytest.raises(ValueError):
            svc.create_custom_period(
                '2025-26',
                start_date='2025-04-06',
                end_date='2025-04-06',  # equal -> invalid
            )


def test_period_dates_validation_rejects_garbage(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        with pytest.raises(ValueError):
            svc.create_custom_period(
                '2025-26',
                start_date='not-a-date',
                end_date='2026-04-05',
            )


def test_update_period_rejects_inverted_dates(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        svc.create_standard_period('2025-26')
        with pytest.raises(ValueError):
            svc.update_period(
                '2025-26',
                start_date='2026-04-06',
                end_date='2025-04-05',
            )


def test_list_periods_active_only_by_default(app):
    from app.services import periods_of_account_service as svc

    with app.app_context():
        svc.create_standard_period('2024-25')
        svc.create_standard_period('2025-26')
        svc.delete_period('2024-25')

        active = svc.list_periods()
        assert {r['tax_year'] for r in active} == {'2025-26'}

        all_rows = svc.list_periods(include_deleted=True)
        assert {r['tax_year'] for r in all_rows} == {'2024-25', '2025-26'}
