# One-shot scripts archived 20 April 2026

These scripts were originally in `scripts/` at the repository root.
They are one-time migrations or data-cleanup tools that have already
been executed against production data and are not run on a regular
schedule. Archived here to keep `scripts/` focused on active tooling
while preserving the history for reference.

- `add_current_year_home_office.py` — seeds the annual home-office
  simplified-expense for the current tax year.
- `batch_estimate_all_missing_mileage.py` — bulk-fill missing mileage
  from route-planning optimisation.
- `batch_estimate_missing_sql.sh` — SQL shortcut for the above.
- `batch_optimize_mileage.py` — earlier variant of the mileage
  estimator.
- `list_expenses_no_description.py` / `list_expenses_no_notes.py` —
  audit helpers for expense description/notes gaps.
- `organize_uploaded_runsheets.py` — one-off runsheet folder reorg.
- `remove_mobile_xfer.py` — retired mobile-transfer cleanup.
- `seed_expense_categories.py` — superseded by
  `init_database()` which now seeds default categories.
- `setup_home_office_annual.py` / `setup_home_office_templates.py` —
  one-off setup for the recurring home-office template system.

If any of these is needed again, copy it back to `scripts/` rather
than running from here.
