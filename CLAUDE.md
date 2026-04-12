# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TVS TCMS — a Flask web application for managing driver wages, runsheets, payslips, expenses, and HMRC Making Tax Digital (MTD) compliance. Python 3.14, Flask 3.x, SQLite database. Version 3.0.0.

## Common Commands

```bash
# Run development server (port 5001)
./venv/bin/python3 -m flask --app app run --host=0.0.0.0 --port=5001

# Or use the convenience script
./start_web.sh

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest test_q1_submission.py
pytest test_final_declaration.py

# Create admin user
python scripts/create_admin_user.py

# Direct database access
sqlite3 data/database/payslips.db
```

## Architecture

**App factory pattern** in `app/__init__.py` using `create_app()`. Flask Blueprints for route organization.

### Request flow
Browser → Flask routing (`app/routes/`) → `@login_required` auth check → CSRF/rate limiting → Business logic (`app/services/`) → Database ops (`app/models/`) → JSON or HTML response

### Key directories
- `app/routes/` — One Blueprint per file (29 route files). Largest: `api_data.py`, `api_reports.py`, `api_hmrc.py`
- `app/services/` — Business logic. Key: `hmrc_client.py` (HMRC API), `periodic_sync.py` (Gmail auto-sync), `runsheet_service.py` (PDF parsing), `payslip_service.py`
- `app/models/` — SQLite ORM layer (13 model files). Uses `get_db_connection()` context manager
- `app/utils/` — Helpers for dates, validation, encryption, timezone, PDF generation
- `templates/` — Jinja2 templates (Bootstrap 5.3)
- `static/js/`, `static/css/` — Frontend assets
- `migrations/` — SQL migration files, auto-run on startup via `app/services/migration_runner.py`
- `data/database/payslips.db` — Main SQLite database (gitignored)

### Entry point
`new_web_app.py` is a legacy entry point. The actual app factory is `app/__init__.py` and the server runs via `flask --app app run`.

### Major integrations
- **HMRC MTD** — OAuth 2.0 flow in `app/services/hmrc_auth.py`, API client in `app/services/hmrc_client.py`, routes in `app/routes/api_hmrc.py`
- **Gmail sync** — Auto-syncs runsheets/payslips from Gmail. Service in `app/services/periodic_sync.py`
- **PDF processing** — pdfplumber for text extraction, camelot-py for table extraction (critical for multi-driver runsheets). pypdf pinned to 3.17.4 for camelot-py compatibility
- **Google Maps** — Route optimization in `app/routes/api_route_planning.py`

## Code Conventions (from .windsurfrules)

### Style
- PEP8, 4-space indent, single quotes, 120 char line max
- Imports ordered: stdlib → third-party → local, alphabetical within groups
- `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE_CASE` constants

### API responses
```python
# Success
{'success': True, 'data': {...}}
# Error
{'success': False, 'error': 'message'}
```

### Database access — always parameterized queries
```python
with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM table WHERE id = ?", (id,))
```
**Never** use f-strings or concatenation in SQL.

### Route pattern
Every route must have: docstring, try/except block, `@login_required` on protected endpoints. Log errors with `logger.error()`, never `print()`.

### Logging
```python
import logging
logger = logging.getLogger(__name__)
```
Logs go to `logs/app.log`, `logs/error.log`, `logs/hmrc.log`.

### UI standards
- Bootstrap 5.3, Bootstrap Icons only (`bi-*`)
- Mobile-first: all columns need `col-12` base, min 44px touch targets
- Dark mode via `data-bs-theme`, CSS variables (`--bs-*`) not hardcoded hex
- No inline styles, use CSS classes. Main stylesheet: `static/css/unified-styles.css`
- Show success/error notifications via existing `showNotification()` pattern
- Loading states (spinner + disabled) on all async buttons

### Config
- Environment variables in `.env` (see `.env.example`)
- Config classes in `app/config.py` (Dev/Prod/Test)
- Feature flags in `app/config.py` via `FeatureFlags` class
