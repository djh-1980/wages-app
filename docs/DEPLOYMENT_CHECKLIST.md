# Production Deployment Checklist

Quick reference checklist for deploying TVS Wages App to production.

---

## 📋 Stage 1: Container & SSH Setup

### Server Setup
- [ ] Container/VPS created and running
- [ ] Ubuntu 22.04 LTS installed
- [ ] System updated: `apt-get update && apt-get upgrade -y`

### SSH Configuration
- [ ] SSH server installed: `apt-get install openssh-server`
- [ ] SSH service started: `service ssh start`
- [ ] SSH enabled on boot: `systemctl enable ssh`

### User Setup
- [ ] User 'tvswages' created: `useradd -m -s /bin/bash tvswages`
- [ ] Password set: `passwd tvswages`
- [ ] Added to sudo: `usermod -aG sudo tvswages`
- [ ] App directory created: `mkdir -p /var/www/tvs-wages`
- [ ] Ownership set: `chown tvswages:tvswages /var/www/tvs-wages`

### SSH Key Authentication
- [ ] SSH key pair generated locally: `ssh-keygen -t ed25519`
- [ ] `.ssh` directory created on server: `mkdir -p ~/.ssh && chmod 700 ~/.ssh`
- [ ] `authorized_keys` created: `touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys`
- [ ] Public key added to `authorized_keys`
- [ ] SSH config updated locally (`~/.ssh/config`)
- [ ] SSH connection tested: `ssh tvs-wages-prod`

### SSH Security
- [ ] Password authentication disabled in `/etc/ssh/sshd_config`
- [ ] Root login disabled
- [ ] SSH restarted: `systemctl restart ssh`

---

## 📋 Stage 2: Application Installation

### System Dependencies
- [ ] Python 3 installed: `apt-get install python3 python3-pip python3-venv`
- [ ] Nginx installed: `apt-get install nginx`
- [ ] Supervisor installed: `apt-get install supervisor`
- [ ] SQLite installed: `apt-get install sqlite3`
- [ ] Git installed: `apt-get install git`
- [ ] Build tools installed: `apt-get install build-essential`

### Application Deployment
- [ ] Connected to server: `ssh tvs-wages-prod`
- [ ] Navigated to app directory: `cd /var/www/tvs-wages`
- [ ] Code deployed (git clone or rsync)
- [ ] Virtual environment created: `python3 -m venv venv`
- [ ] Virtual environment activated: `source venv/bin/activate`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Gunicorn installed: `pip install gunicorn gevent`

### Configuration
- [ ] `.env` file created with SECRET_KEY
- [ ] `FLASK_ENV=production` set
- [ ] Database path configured
- [ ] Log directory configured
- [ ] Feature flags set

### Directory Structure
- [ ] `data/database` created
- [ ] `data/database/backups` created
- [ ] `data/documents/payslips` created
- [ ] `data/documents/runsheets` created
- [ ] `data/exports/csv` created
- [ ] `data/exports/summaries` created
- [ ] `data/reports` created
- [ ] `data/processing/queue` created
- [ ] `data/processing/temp` created
- [ ] `data/processing/failed` created
- [ ] `data/uploads/payslips` created
- [ ] `data/uploads/runsheets` created
- [ ] `logs` directory created
- [ ] Permissions set: `chmod 755 data logs`

### Database
- [ ] Database initialized: `python3 -c "from app.database import init_database; init_database()"`
- [ ] Database file exists: `ls -lh data/database/payslips.db`

### Application Testing
- [ ] Manual test successful: `python3 new_web_app.py`
- [ ] Application starts without errors
- [ ] Ctrl+C stops cleanly

### Systemd Service
- [ ] Service file created: `/etc/systemd/system/tvs-wages.service`
- [ ] Service configured with correct paths
- [ ] Systemd reloaded: `systemctl daemon-reload`
- [ ] Service enabled: `systemctl enable tvs-wages`
- [ ] Service started: `systemctl start tvs-wages`
- [ ] Service status checked: `systemctl status tvs-wages`
- [ ] Service running without errors

### Nginx Configuration
- [ ] Nginx config created: `/etc/nginx/sites-available/tvs-wages`
- [ ] Server name/IP configured
- [ ] Proxy settings configured
- [ ] Static files path configured
- [ ] Symbolic link created: `ln -s /etc/nginx/sites-available/tvs-wages /etc/nginx/sites-enabled/`
- [ ] Nginx config tested: `nginx -t`
- [ ] Nginx restarted: `systemctl restart nginx`
- [ ] Nginx enabled: `systemctl enable nginx`

### Firewall
- [ ] UFW installed: `apt-get install ufw`
- [ ] SSH allowed: `ufw allow 22/tcp`
- [ ] HTTP allowed: `ufw allow 80/tcp`
- [ ] HTTPS allowed: `ufw allow 443/tcp`
- [ ] Firewall enabled: `ufw enable`
- [ ] Status verified: `ufw status`

### Verification
- [ ] Application accessible via browser: `http://your-server-ip`
- [ ] Home page loads
- [ ] All navigation links work
- [ ] No console errors (F12)

---

## 📋 Stage 3: Data Migration

### Local Preparation
- [ ] Local data backed up: `tar -czf data-backup-$(date +%Y%m%d).tar.gz data/`
- [ ] Migration archive created: `tar -czf data-migration.tar.gz data/`

### Database Transfer
- [ ] Database copied to server via scp/rsync
- [ ] Database file exists on server
- [ ] Database readable: `sqlite3 payslips.db "SELECT COUNT(*) FROM payslips;"`

### Documents Transfer
- [ ] Payslips transferred: `rsync data/documents/payslips/`
- [ ] Runsheets transferred: `rsync data/documents/runsheets/`
- [ ] File counts verified on server

### Gmail Credentials (Optional)
- [ ] `credentials.json` transferred
- [ ] `token.json` transferred
- [ ] Files in correct location

### Permissions
- [ ] All files owned by tvswages: `chown -R tvswages:tvswages /var/www/tvs-wages`
- [ ] Directory permissions: `find data -type d -exec chmod 755 {} \;`
- [ ] File permissions: `find data -type f -exec chmod 644 {} \;`
- [ ] Database writable: `chmod 644 data/database/payslips.db`

### Application Restart
- [ ] Service restarted: `systemctl restart tvs-wages`
- [ ] Status checked: `systemctl status tvs-wages`
- [ ] Logs checked: `journalctl -u tvs-wages -f`
- [ ] No errors in logs

### Data Verification
- [ ] Wages page shows payslip data
- [ ] Correct number of payslips displayed
- [ ] Runsheets page shows runsheet data
- [ ] Correct number of runsheets displayed
- [ ] Reports generate correctly
- [ ] All data accessible

### Backup Configuration
- [ ] Backup script created: `scripts/backup_production.sh`
- [ ] Script executable: `chmod +x scripts/backup_production.sh`
- [ ] Cron job configured: `crontab -e`
- [ ] Backup tested manually
- [ ] Backup log file created

### Auto-Sync (Optional)
- [ ] Gmail credentials verified
- [ ] `AUTO_SYNC_ENABLED=true` in .env
- [ ] Service restarted
- [ ] Sync working in logs

---

## 📋 Post-Deployment

### Final Verification
- [ ] Application accessible: `http://your-server-ip`
- [ ] All pages load correctly
- [ ] All features working
- [ ] Data displays correctly
- [ ] Reports generate
- [ ] No errors in browser console
- [ ] No errors in application logs

### Monitoring Setup
- [ ] Know how to check status: `systemctl status tvs-wages`
- [ ] Know how to view logs: `journalctl -u tvs-wages -f`
- [ ] Know how to restart: `systemctl restart tvs-wages`
- [ ] Nginx logs location known: `/var/log/nginx/`

### Documentation
- [ ] Server IP/domain documented
- [ ] SSH connection command saved
- [ ] Admin credentials stored securely
- [ ] Backup location documented

### Optional Enhancements
- [ ] SSL certificate installed (Certbot)
- [ ] HTTPS configured
- [ ] Domain name configured
- [ ] Monitoring/alerting setup
- [ ] Log rotation configured

---

## 🚨 Emergency Contacts

### Quick Commands
```bash
# Connect to server
ssh tvs-wages-prod

# Restart application
sudo systemctl restart tvs-wages

# View logs
sudo journalctl -u tvs-wages -f

# Check status
sudo systemctl status tvs-wages

# Manual backup
/var/www/tvs-wages/scripts/backup_production.sh
```

### Important Paths
- Application: `/var/www/tvs-wages`
- Database: `/var/www/tvs-wages/data/database/payslips.db`
- Logs: `/var/www/tvs-wages/logs`
- Backups: `/var/www/tvs-wages/data/database/backups`

---

## ✅ Deployment Status

**Stage 1 Complete:** _____ (Date)  
**Stage 2 Complete:** _____ (Date)  
**Stage 3 Complete:** _____ (Date)  

**Production URL:** ___________________  
**Deployed By:** ___________________  
**Deployment Date:** ___________________  

---

**🎉 All stages complete = Production ready!**
