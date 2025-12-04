# Project Structure Guide

This document explains the organized file structure of the Wages App.

## Directory Layout

```
Wages-App/
├── data/                   # Database and data files
│   ├── .gitkeep           # Preserves directory in git
│   └── payslips.db        # SQLite database (generated)
│
├── data/output/                 # Generated reports and exports
│   ├── .gitkeep           # Preserves directory in git
│   ├── *.csv              # CSV exports (generated)
│   └── payslip_report.txt # Text report (generated)
│
├── scripts/                # Python utility scripts
│   ├── extract_payslips.py  # Extract data from PDFs
│   ├── query_payslips.py    # Interactive query tool
│   ├── generate_report.py   # Generate text reports
│   ├── export_to_csv.py     # Export data to CSV
│   └── quick_stats.py       # Quick statistics display
│
├── docs/                   # Documentation
│   ├── START_HERE.txt
│   ├── USAGE_GUIDE.md
│   ├── WEB_APP_GUIDE.md
│   ├── PROJECT_SUMMARY.md
│   └── DEBIAN_DEPLOYMENT_GUIDE.md
│
├── templates/              # Flask HTML templates
│   └── index.html
│
├── static/                 # Static web assets
│   └── (CSS, JS, images)
│
├── data/payslips/               # PDF payslip files (organized by year)
│   ├── 2021/
│   ├── 2022/
│   ├── 2023/
│   ├── 2024/
│   └── 2025/
│
├── Backups/                # Database backups
│
├── web_app.py             # Flask web application (main)
├── wages.py               # CLI menu interface (main)
├── start_web.sh           # Shell script to start web app
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
└── README.md             # Main documentation

```

## Key Files

### Main Entry Points
- **`wages.py`** - Main CLI menu interface for all tools
- **`web_app.py`** - Web dashboard (Flask application)
- **`start_web.sh`** - Quick start script for web interface

### Scripts Directory
All utility scripts are in `scripts/`:
- Run with: `python3 scripts/<script_name>.py`
- All scripts use relative paths to find `data/` and `data/output/`

### Data Flow
1. **Input**: PDFs go in `data/payslips/YYYY/`
2. **Processing**: Run `scripts/extract_payslips.py`
3. **Storage**: Data saved to `data/payslips.db`
4. **Output**: Reports/exports saved to `data/output/`

## Quick Commands

```bash
# Start main menu
python3 wages.py

# Start web dashboard
python3 web_app.py
# or
./start_web.sh

# Extract PDFs
python3 scripts/extract_payslips.py

# Query database
python3 scripts/query_payslips.py

# Generate report
python3 scripts/generate_report.py

# Export to CSV
python3 scripts/export_to_csv.py

# Quick stats
python3 scripts/quick_stats.py
```

## Benefits of This Structure

1. **Organized** - Clear separation of concerns
2. **Clean Root** - Main directory not cluttered
3. **Git-Friendly** - Easy to track what's generated vs source
4. **Scalable** - Easy to add new scripts or documentation
5. **Professional** - Standard project layout

## Notes

- `data/` and `data/output/` directories contain generated files (gitignored)
- `.gitkeep` files preserve empty directories in git
- All scripts automatically use the correct paths
- Documentation is centralized in `docs/`
