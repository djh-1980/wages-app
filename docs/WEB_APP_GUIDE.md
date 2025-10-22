# Web App Guide - Wages Dashboard

## 🌐 Beautiful Bootstrap Web Interface

Your payslip data now has a modern, responsive web interface with interactive charts and real-time search!

## Quick Start

### 1. Install Flask (if not already installed)
```bash
pip install Flask
```

### 2. Start the Web Server
```bash
python3 web_app.py
```

### 3. Open Your Browser
Navigate to: **http://localhost:5000**

That's it! 🎉

## Features

### 📊 Dashboard
- **Summary Cards** - Total earnings, averages, best week at a glance
- **Interactive Chart** - Weekly earnings trend (last 26 weeks)
- **Current Tax Year Stats** - Real-time statistics for current year
- **Top Clients** - Quick view of your top 5 clients

### 📄 Payslips Tab
- View all payslips in a sortable table
- Filter by tax year
- Click "View" to see detailed breakdown
- See job count for each week

### 👔 Clients Tab
- **Bar Chart** - Visual breakdown of top 10 clients
- **Table** - Detailed client statistics
- Shows total earnings and average per job

### 🔨 Job Types Tab
- **Doughnut Chart** - Visual distribution of job types
- **Table** - Complete job type analysis
- See which jobs you do most often

### 🔍 Search Tab
- Real-time search as you type
- Search by client name, location, or description
- Instant results with full details

## Screenshots

### Dashboard View
- Clean, modern interface with gradient cards
- Interactive Chart.js charts
- Responsive design works on mobile/tablet/desktop

### Key Metrics Displayed
- 💰 Total Earnings (all time)
- 📊 Average Weekly Earnings
- 💼 Total Jobs Completed
- 🏆 Best Week Ever

## Technical Details

### Built With
- **Backend**: Flask (Python web framework)
- **Frontend**: Bootstrap 5 (responsive CSS framework)
- **Charts**: Chart.js (interactive charts)
- **Icons**: Bootstrap Icons
- **Database**: SQLite (your existing payslips.db)

### API Endpoints
The web app provides a REST API:

- `GET /api/summary` - Overall statistics
- `GET /api/weekly_trend` - Weekly earnings data
- `GET /api/clients` - Client breakdown
- `GET /api/job_types` - Job type analysis
- `GET /api/payslips` - All payslips
- `GET /api/payslip/<id>` - Specific payslip detail
- `GET /api/search?q=<query>` - Search jobs
- `GET /api/monthly_breakdown` - Monthly stats
- `GET /api/tax_years` - Available tax years

### Customization

#### Change Port
Edit `web_app.py`, line at bottom:
```python
app.run(debug=True, host='0.0.0.0', port=5000)  # Change 5000 to your port
```

#### Modify Colors
Edit `templates/index.html`, CSS section at top to change color scheme.

#### Add More Charts
Use Chart.js documentation: https://www.chartjs.org/

## Tips

### Keep Server Running
The web server needs to stay running. Open a terminal and leave it running:
```bash
python3 web_app.py
```

### Access from Other Devices
If you want to access from phone/tablet on same network:
1. Find your computer's IP address
2. Open browser on other device
3. Go to: `http://YOUR_IP:5000`

### Production Use
For production deployment, use a proper WSGI server:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 web_app:app
```

## Troubleshooting

### Port Already in Use
If port 5000 is taken:
```bash
python3 web_app.py
# Edit the file to use a different port (e.g., 5001)
```

### Database Not Found
Make sure `payslips.db` exists:
```bash
python3 extract_payslips.py
```

### Charts Not Loading
- Check browser console for errors (F12)
- Ensure internet connection (CDN resources)
- Try refreshing the page

### Slow Performance
- Database is queried in real-time
- For large datasets, consider adding indexes
- Charts limited to reasonable data points

## Keyboard Shortcuts

- **Tab** - Navigate between tabs
- **Ctrl+F** - Browser search (works in tables)
- **Esc** - Close modal dialogs

## Mobile Friendly

The interface is fully responsive:
- Works on phones, tablets, and desktops
- Touch-friendly buttons and controls
- Optimized charts for small screens

## Security Notes

⚠️ **Important**: This is designed for local use only!

- Runs on localhost by default
- No authentication built-in
- Don't expose to public internet without adding security
- Your financial data is sensitive!

For secure remote access, consider:
- VPN to your home network
- SSH tunnel
- Add authentication middleware
- Use HTTPS

## What's Next?

Possible enhancements:
- Export charts as images
- Email reports
- Dark mode toggle
- More chart types (pie, scatter, etc.)
- Filtering by date ranges
- Comparison views (year over year)
- Budget tracking
- Expense integration

## Summary

You now have a beautiful, modern web interface to:
- ✅ View all your earnings data visually
- ✅ Interact with charts and graphs
- ✅ Search and filter your jobs
- ✅ Analyze trends and patterns
- ✅ Access from any device on your network

Enjoy your new dashboard! 🚀
