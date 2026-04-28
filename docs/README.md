# TVS Wages Application

A comprehensive Flask-based web application for managing driver wages, runsheets, payslips, expenses, and HMRC MTD (Making Tax Digital) compliance for TVS delivery operations.

---

## What is tvstcms?

tvstcms (TVS Content Management System) is a full-featured wages and compliance management system that:
- Automatically syncs runsheets and payslips from Gmail
- Processes and parses PDF documents using advanced table extraction
- Tracks daily jobs, mileage, fuel costs, and expenses
- Generates comprehensive reports for tax compliance
- Integrates with HMRC MTD API for digital tax submissions
- Provides a modern, mobile-responsive web interface

---

## Requirements

- **Python:** 3.14+
- **Operating System:** macOS, Linux, or Windows
- **Database:** SQLite (included)
- **External Services:** Gmail API (optional, for auto-sync)

### Python Dependencies

All dependencies are pinned in `requirements.txt`:
- Flask 3.1.3 (web framework)
- pdfplumber 0.11.9 (PDF parsing)
- camelot-py 1.0.9 (table extraction)
- pandas 3.0.0 (data processing)
- reportlab 4.4.9 (PDF generation)
- See `requirements.txt` for complete list (70 packages)

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Wages-App
```

### 2. Create Virtual Environment

```bash
python3.14 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and configure the following:

```bash
# Flask Configuration
SECRET_KEY=<generate-with-command-below>
FLASK_ENV=development  # or 'production'

# Database
DATABASE_PATH=data/database/payslips.db

# Gmail API (optional - for auto-sync)
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=token.json

# HMRC MTD API (optional - for tax submissions)
HMRC_CLIENT_ID=<your-hmrc-client-id>
HMRC_CLIENT_SECRET=<your-hmrc-client-secret>
HMRC_SERVER_TOKEN=<your-hmrc-server-token>
HMRC_REDIRECT_URI=http://localhost:5001/api/hmrc/callback

# Application Settings
LOG_LEVEL=DEBUG  # or 'INFO' for production
```

### 5. Generate SECRET_KEY

**IMPORTANT:** Generate a secure secret key:

```bash
python -c 'import secrets; print(secrets.token_hex(32))'
```

Copy the output and paste it as your `SECRET_KEY` in `.env`.

### 6. Initialize Database

The database will be created automatically on first run. To manually initialize:

```bash
python create_admin_user.py
```

This creates an admin user with credentials:
- Username: `admin`
- Password: (you'll be prompted to set)

---

## Running Locally

### Development Mode

```bash
source venv/bin/activate
python new_web_app.py
```

The application will start on `http://localhost:5001`

### Production Mode

```bash
export FLASK_ENV=production
source venv/bin/activate
python new_web_app.py
```

Or use the provided shell script:

```bash
./start_web.sh
```

---

## Deploying to Proxmox LXC Container

### Prerequisites

- Proxmox VE server
- Debian 12 LXC container
- SSH access to the container

### Deployment Steps

1. **Prepare the container:**

```bash
# SSH into your Proxmox LXC container
ssh user@your-lxc-container

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.14 and dependencies
sudo apt install python3.14 python3.14-venv python3-pip git libmagic1 -y
```

2. **Clone and setup the application:**

```bash
# Clone repository
git clone <repository-url> /opt/wages-app
cd /opt/wages-app

# Create virtual environment
python3.14 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

3. **Configure environment:**

```bash
# Copy and edit .env file
cp .env.example .env
nano .env

# Set production values:
# FLASK_ENV=production
# LOG_LEVEL=INFO
# DATABASE_PATH=/opt/wages-app/data/database/payslips.db
```

4. **Create systemd service:**

Create `/etc/systemd/system/wages-app.service`:

```ini
[Unit]
Description=TVS Wages Application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/wages-app
Environment="PATH=/opt/wages-app/venv/bin"
ExecStart=/opt/wages-app/venv/bin/python /opt/wages-app/new_web_app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

5. **Enable and start service:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable wages-app
sudo systemctl start wages-app
sudo systemctl status wages-app
```

6. **Configure reverse proxy (Nginx):**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

7. **Use deployment script (alternative):**

```bash
# Use the provided deployment script
./deploy_to_debian.sh
```

---

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for sessions | `a1b2c3d4...` (64 chars) |
| `FLASK_ENV` | Environment mode | `development` or `production` |
| `DATABASE_PATH` | Path to SQLite database | `data/database/payslips.db` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `GMAIL_CREDENTIALS_PATH` | Gmail API credentials file | `credentials.json` |
| `GMAIL_TOKEN_PATH` | Gmail API token file | `token.json` |
| `HMRC_CLIENT_ID` | HMRC MTD client ID | None |
| `HMRC_CLIENT_SECRET` | HMRC MTD client secret | None |
| `HMRC_SERVER_TOKEN` | HMRC MTD server token | None |
| `HMRC_REDIRECT_URI` | HMRC OAuth callback URL | `http://localhost:5001/api/hmrc/callback` |

### Gmail API Setup (Optional)

To enable automatic Gmail sync:

1. Create a Google Cloud Project
2. Enable Gmail API
3. Create OAuth 2.0 credentials
4. Download `credentials.json` to project root
5. Run the app and authenticate when prompted
6. `token.json` will be created automatically

### HMRC MTD API Setup (Optional)

To enable HMRC tax submissions:

1. Register for HMRC MTD API sandbox/production
2. Create an application in HMRC Developer Hub
3. Obtain Client ID, Client Secret, and Server Token
4. Add credentials to `.env` file
5. Configure redirect URI in HMRC Developer Hub

---

## Directory Structure

```
Wages-App/
├── app/                      # Core application code
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration classes
│   ├── database.py          # Database initialization
│   ├── middleware.py        # Request/response middleware
│   ├── models/              # Database models
│   ├── routes/              # API and page routes
│   ├── services/            # Business logic services
│   └── utils/               # Utility functions
├── data/                     # Application data (gitignored)
│   ├── database/            # SQLite database files
│   ├── documents/           # Runsheets and payslips
│   ├── exports/             # CSV exports
│   ├── processing/          # File processing queue
│   └── uploads/             # File uploads
├── static/                   # Web assets
│   ├── css/                 # Stylesheets
│   ├── js/                  # JavaScript files
│   └── images/              # Images and icons
├── templates/                # Jinja2 HTML templates
├── scripts/                  # Utility scripts
│   ├── production/          # Production scripts
│   ├── testing/             # Test scripts
│   └── utilities/           # Helper scripts
├── docs/                     # Documentation
├── logs/                     # Application logs (gitignored)
├── .env                      # Environment variables (gitignored)
├── .env.example             # Environment template
├── .gitignore               # Git ignore rules
├── .windsurfrules           # AI coding rules
├── requirements.txt         # Python dependencies
├── create_admin_user.py     # Admin user creation script
├── new_web_app.py           # Main application entry point
├── README.md                # This file
└── SECURITY_AUDIT.md        # Security documentation
```

---

## Features

### Core Functionality
- **Runsheet Management:** Import, parse, and track daily delivery jobs
- **Payslip Processing:** Extract job items and earnings from PDF payslips
- **Expense Tracking:** Record and categorize business expenses
- **Mileage Logging:** Track daily mileage and fuel costs
- **Attendance Records:** Monitor work days and patterns

### Advanced Features
- **Gmail Integration:** Automatic sync of runsheets and payslips
- **PDF Parsing:** Advanced table extraction using camelot-py
- **HMRC MTD Integration:** Digital tax submissions
- **Recurring Payments:** Smart template matching for expenses
- **Route Planning:** Optimize delivery routes
- **Comprehensive Reports:** Weekly summaries, tax year reports, analytics

### User Interface
- Modern, responsive design
- Mobile-optimized
- Real-time updates
- Dark mode support
- Accessible (WCAG compliant)

---

## Security

### Implemented Security Measures

- ✅ **SQL Injection Protection:** Parameterized queries throughout
- ✅ **Session Security:** Session fixation prevention
- ✅ **Password Policy:** 12+ characters with complexity requirements
- ✅ **Security Headers:** CSP, HSTS, X-Frame-Options, etc.
- ✅ **Input Validation:** NINO, tax year, and user input validation
- ✅ **Logging:** Secure logging (no sensitive data logged)
- ✅ **Dependency Management:** All packages pinned, vulnerabilities fixed

See `SECURITY_AUDIT.md` for complete security documentation.

---

## Documentation

- **`SECURITY_AUDIT.md`** - Complete security audit and fixes
- **`DEPENDENCY_RESOLUTION.md`** - Dependency conflict resolution
- **`docs/`** - Additional guides and documentation
- **`.windsurfrules`** - AI coding standards for this project

---

## Support

For issues, questions, or contributions, please contact the development team.

---

## License

Proprietary - TVS Internal Use Only

---

*Last Updated: March 31, 2026*
