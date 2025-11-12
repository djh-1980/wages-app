# TVS Wages Application - Production Ready

## 🚀 Quick Start

### Installation
```bash
pip install -r requirements.txt
python3 new_web_app.py
```

### Access
Open browser to: http://localhost:5001

## 📁 Directory Structure

```
├── app/                    # Core application code
├── data/                   # Application data (excluded from git)
├── static/                 # Web assets (CSS, JS, images)
├── templates/              # HTML templates
├── scripts/
│   ├── production/         # Core processing scripts
│   ├── analysis/           # Data analysis tools
│   ├── deployment/         # Deployment scripts
│   └── utilities/          # Utility scripts
├── config/                 # Configuration files
├── logs/                   # Application logs
└── docs/                   # Documentation
```

## 🔧 Production Scripts

### Core Processing (`scripts/production/`)
- `download_runsheets_gmail.py` - Gmail sync
- `extract_payslips.py` - Payslip processing
- `import_run_sheets.py` - Runsheet processing
- `export_to_csv.py` - Data export
- `generate_report.py` - Report generation

### Analysis Tools (`scripts/analysis/`)
- `analyze_missing_runsheets.py` - Missing data analysis
- `discrepancy_report.py` - Data validation
- `validate_data.py` - Data integrity checks

### Deployment (`scripts/deployment/`)
- `setup_live_server.sh` - Production server setup
- `auto_sync.py` - Automated sync configuration

## 📊 Features

- **Web Interface** - Modern responsive UI
- **Gmail Integration** - Automatic file sync
- **Real-time Processing** - Immediate file processing
- **Data Analysis** - Comprehensive reporting
- **Mobile Optimized** - Works on all devices

## 🔒 Security

- Data directory excluded from git
- Secure Gmail API integration
- Input validation and sanitization

## 📖 Documentation

See `docs/` folder for detailed guides:
- Gmail API setup
- Deployment instructions
- Usage guides
