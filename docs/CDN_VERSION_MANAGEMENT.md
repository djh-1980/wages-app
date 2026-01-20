# Dependency Version Management System

## Overview

The TVS Wages application now includes automated version management for both **frontend (CDN)** and **backend (Python)** dependencies. Check for updates and apply them with a single click.

## Features

### 🌐 Frontend (CDN) Dependencies

#### ✅ Automated Version Checking
- Fetches latest versions from NPM registry and CDNJS APIs
- Compares current versions with latest available
- Displays update status for each library

#### ✅ One-Click Updates
- Update individual libraries or all at once
- Automatic backup and rollback on failure
- Safe update process with validation

#### ✅ Supported Libraries
- **Bootstrap** (CSS & JS)
- **Bootstrap Icons**
- **Chart.js**
- **jsPDF**
- **jsPDF-AutoTable**

### 🐍 Backend (Python) Dependencies

#### ✅ Automated Package Checking
- Fetches latest versions from PyPI
- Semantic version comparison
- Update type detection (major/minor/patch)

#### ✅ Smart Update Options
- **Patch Only** - Safest, bug fixes only
- **Minor** - New features, backward compatible
- **Individual** - Update specific packages
- Respects version operators (==, >=, etc.)

#### ✅ Safety Features
- Automatic backup of requirements.txt
- Version conflict detection
- Rollback on failure
- Clear upgrade path warnings

### ✅ Web Interface
- Clean UI in System Settings page
- Real-time status updates
- Last check timestamp tracking
- Summary statistics with color coding

## How to Use

### 🌐 Frontend (CDN) Dependencies

#### Via Web Interface

1. **Navigate to Settings**
   - Go to Settings → System
   - Scroll to "CDN Library Versions (Frontend)" section

2. **Check for Updates**
   - Click "Check for Updates" button
   - System will fetch latest versions from CDN APIs
   - Results displayed in table with status badges

3. **Update Libraries**
   - **Single Library**: Click "Update" button next to specific library
   - **All Libraries**: Click "Update All" button to update everything
   - Page refresh recommended after updates

#### Via Command Line

```bash
# Check for updates
python3 scripts/check_cdn_versions.py --check

# Update specific libraries
python3 scripts/check_cdn_versions.py --update bootstrap chartjs

# Update all libraries with available updates
python3 scripts/check_cdn_versions.py --update-all

# Get JSON output
python3 scripts/check_cdn_versions.py --check --json
```

### 🐍 Backend (Python) Dependencies

#### Via Web Interface

1. **Navigate to Settings**
   - Go to Settings → System
   - Scroll to "Python Dependencies (Backend)" section

2. **Check for Updates**
   - Click "Check for Updates" button
   - System will fetch latest versions from PyPI
   - Summary shows major/minor/patch breakdown

3. **Update Packages**
   - **Patch Only** (Safest): Bug fixes only, no breaking changes
   - **Minor**: New features + patches, backward compatible
   - **Individual**: Click "Update" next to specific package
   
4. **After Updating**
   - Run: `pip install -r requirements.txt`
   - Restart the application
   - Refresh the page

#### Via Command Line

```bash
# Check for updates
python3 scripts/check_python_deps.py --check

# Update only patch versions (safest)
python3 scripts/check_python_deps.py --update-patch

# Update minor and patch versions
python3 scripts/check_python_deps.py --update-minor

# Update specific packages
python3 scripts/check_python_deps.py --update Flask requests

# Update all packages (including major versions)
python3 scripts/check_python_deps.py --update-all

# Get package info
python3 scripts/check_python_deps.py --info Flask

# Get JSON output
python3 scripts/check_python_deps.py --check --json
```

## How It Works

### Version Detection
1. Reads `templates/base.html` to extract current CDN URLs
2. Uses regex patterns to parse version numbers
3. Stores current versions in memory

### Latest Version Fetching
- **NPM Libraries** (Bootstrap, Chart.js, Bootstrap Icons):
  - Queries: `https://registry.npmjs.org/{package}/latest`
  - Parses JSON response for version field

- **CDNJS Libraries** (jsPDF, jsPDF-AutoTable):
  - Queries: `https://api.cdnjs.com/libraries/{package}`
  - Parses JSON response for version field

### Update Process
1. Creates backup of `base.html` (`.html.bak`)
2. Uses regex to replace version numbers in CDN URLs
3. Writes updated content to `base.html`
4. On success: Removes backup
5. On failure: Restores from backup

### Version Comparison
- Semantic versioning comparison (e.g., 5.3.0 vs 5.3.3)
- Splits versions into parts and compares numerically
- Handles different version formats safely

## Configuration

### Version Check Storage
Results are stored in: `config/cdn_versions.json`

```json
{
  "last_check": "2026-01-20T22:30:00",
  "libraries": {
    "bootstrap": {
      "name": "Bootstrap",
      "current": "5.3.0",
      "latest": "5.3.3",
      "update_available": true
    }
  }
}
```

### Library Definitions
Located in: `scripts/check_cdn_versions.py`

```python
self.libraries = {
    'bootstrap': {
        'name': 'Bootstrap',
        'current_pattern': r'bootstrap@([\d.]+)/dist/css/bootstrap\.min\.css',
        'cdn_url': 'https://cdn.jsdelivr.net/npm/bootstrap@{version}/...',
        'api_url': 'https://registry.npmjs.org/bootstrap/latest',
        'version_key': 'version'
    }
}
```

## API Endpoints

### GET `/api/cdn/check`
Check for CDN library updates

**Response:**
```json
{
  "success": true,
  "libraries": {
    "bootstrap": {
      "name": "Bootstrap",
      "current": "5.3.0",
      "latest": "5.3.3",
      "update_available": true
    }
  }
}
```

### GET `/api/cdn/status`
Get last version check results

**Response:**
```json
{
  "success": true,
  "data": {
    "last_check": "2026-01-20T22:30:00",
    "libraries": { ... }
  }
}
```

### POST `/api/cdn/update`
Update specific libraries

**Request:**
```json
{
  "libraries": ["bootstrap", "chartjs"]
}
```

**Response:**
```json
{
  "success": true,
  "results": {
    "bootstrap": true,
    "chartjs": true
  },
  "message": "Updated 2 of 2 libraries"
}
```

### POST `/api/cdn/update-all`
Update all libraries with available updates

**Response:**
```json
{
  "success": true,
  "results": {
    "bootstrap": true,
    "chartjs": true
  },
  "message": "Updated 2 of 2 libraries"
}
```

## Automation Options

### Option 1: Cron Job (Weekly Check)
```bash
# Add to crontab
0 9 * * 1 cd /var/www/tvs-wages && python3 scripts/check_cdn_versions.py --check
```

### Option 2: Scheduled Task (Monthly Auto-Update)
```bash
# First Monday of each month at 2 AM
0 2 1-7 * 1 cd /var/www/tvs-wages && python3 scripts/check_cdn_versions.py --update-all
```

### Option 3: Manual Only
- Use web interface when needed
- Check before major releases
- Review updates before applying

## Safety Features

### Automatic Backup
- Creates `.html.bak` before any changes
- Restores automatically on failure
- Manual rollback available

### Version Validation
- Compares semantic versions correctly
- Handles malformed versions gracefully
- Skips invalid updates

### Error Handling
- Network timeout protection (10 seconds)
- API failure fallbacks
- Detailed error logging

### Rollback Process
If an update causes issues:

```bash
# Manual rollback
cd /Users/danielhanson/CascadeProjects/Wages-App/templates
cp base.html.bak base.html
```

## Troubleshooting

### Issue: "Failed to fetch latest version"
**Cause:** Network connectivity or API unavailable  
**Solution:** Check internet connection, try again later

### Issue: "Update failed"
**Cause:** File permissions or syntax error  
**Solution:** Check file permissions, review error logs

### Issue: "Page broken after update"
**Cause:** Incompatible library version  
**Solution:** Restore from backup, report issue

### Issue: "No updates shown"
**Cause:** Already up to date or cache issue  
**Solution:** Clear browser cache, check again

## Best Practices

### ✅ DO
- Check for updates monthly
- Test updates in development first
- Review changelog before updating
- Keep backups of working versions
- Update during low-traffic periods

### ❌ DON'T
- Auto-update in production without testing
- Update all libraries at once without review
- Skip reading release notes
- Update during peak usage hours
- Ignore breaking changes in major versions

## Current Library Versions

As of January 2026:

| Library | Current | Latest | Status |
|---------|---------|--------|--------|
| Bootstrap | 5.3.0 | 5.3.3 | ⚠️ Update Available |
| Bootstrap Icons | 1.10.0 | 1.11.3 | ⚠️ Update Available |
| Chart.js | 4.3.0 | 4.4.7 | ⚠️ Update Available |
| jsPDF | 2.5.1 | 2.5.2 | ⚠️ Update Available |
| jsPDF-AutoTable | 3.5.31 | 3.8.4 | ⚠️ Update Available |

## Benefits

### Security
- Patches for known vulnerabilities
- Security fixes in dependencies
- Reduced attack surface

### Performance
- Optimized code in newer versions
- Better browser compatibility
- Smaller file sizes

### Features
- New components and utilities
- Bug fixes and improvements
- Better mobile support

### Maintenance
- Easier debugging with latest versions
- Better documentation available
- Community support for current versions

## Future Enhancements

Potential improvements:

- [ ] Email notifications for critical updates
- [ ] Automatic testing after updates
- [ ] Changelog integration
- [ ] Dependency conflict detection
- [ ] Rollback history tracking
- [ ] Update scheduling
- [ ] Version pinning options

## Support

For issues or questions:
1. Check this documentation
2. Review error logs in browser console
3. Test in development environment first
4. Create backup before major updates

---

**Last Updated:** January 20, 2026  
**System Version:** 1.0.0  
**Maintainer:** TVS Wages Development Team
