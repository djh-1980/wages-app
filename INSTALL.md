# TVS Wages Application - Installation Guide

## Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Application
```bash
python3 new_web_app.py
```

### 3. Access Application
Open your browser to: http://localhost:5001

## Dependencies Included

- **Flask** - Web framework
- **PyPDF2** - PDF text extraction
- **ReportLab + Pillow** - PDF report generation
- **Google APIs** - Gmail integration for automatic sync
- **Schedule + Watchdog** - Background processing and file monitoring

## Gmail Setup (Optional)

If you want automatic Gmail sync:
1. Follow the Gmail API setup guide in `docs/GMAIL_SETUP.md`
2. Place `credentials.json` in the root directory
3. Run the first sync to authenticate

## File Structure

- `app/` - Application code
- `data/` - All data files (payslips, runsheets, uploads)
- `static/` - Web assets (CSS, JS, images)
- `templates/` - HTML templates
- `scripts/` - Processing scripts
- `logs/` - Application logs

## Need Help?

Check the documentation in the `docs/` folder for detailed guides.
