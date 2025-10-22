# Changelog

All notable changes to the Wages App will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0] - 2025-10-22

### Added
- Clean, organized file structure with dedicated directories
- `STRUCTURE.md` - Comprehensive project structure guide
- `CHANGELOG.md` - Version history tracking
- `VERSION` file for version tracking
- `.gitkeep` files to preserve empty directories in git
- Error handling for empty database scenarios
- Validation for API endpoints
- Professional directory layout (scripts/, docs/, data/, output/)

### Changed
- **File Organization**:
  - Moved all Python scripts to `scripts/` directory
  - Moved all documentation to `docs/` directory
  - Moved database to `data/` directory
  - Moved generated files to `output/` directory
- Updated all file paths and references across the codebase
- Updated `README.md` with new structure and quick start guide
- Updated `.gitignore` for new directory layout
- Improved job description parsing logic in `extract_payslips.py`

### Fixed
- Removed redundant `datetime` import in `web_app.py`
- Added error handling for empty database in `quick_stats.py`
- Fixed division by zero errors in `generate_report.py`
- Added validation check in `web_app.py` `api_payslip_detail()` endpoint
- Improved multi-line job description parsing to avoid false matches

### Technical Details
- All scripts now use relative paths (`data/`, `output/`)
- Database path: `data/payslips.db`
- Generated reports: `output/`
- All Python files verified to compile without errors
- Maintained backward compatibility with existing workflows

### Features
- PDF payslip data extraction from SASER Limited payslips
- SQLite database storage with comprehensive schema
- Interactive CLI query tool with multiple analysis options
- Web dashboard with Bootstrap UI and Chart.js visualizations
- CSV export functionality for all data types
- Comprehensive text report generation
- Quick statistics overview
- Client and job type breakdown analysis
- Missing payslip detection
- Database backup functionality
- PDF upload and processing via web interface

---

## Pre-1.0 Development

Prior to v1.0, the project was in active development with the following milestones:

- Initial PDF extraction implementation
- Database schema design
- Web dashboard creation
- Query tools development
- Documentation creation
- Testing and refinement

---

**Note**: This is the first official production-ready release of the Wages App.
