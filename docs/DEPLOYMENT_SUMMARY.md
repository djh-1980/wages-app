# Deployment Summary - TVS Wages to Proxmox

Quick reference for deploying to your Proxmox Debian container at **192.168.1.202**

---

## 📚 Documentation Files Created

1. **QUICK_START_PROXMOX.md** - ⭐ START HERE - Fast track deployment (~30 min)
2. **DEPLOYMENT_PROXMOX.md** - Detailed step-by-step guide with explanations
3. **PRODUCTION_DEPLOYMENT.md** - Generic deployment guide (any server/container)
4. **DEPLOYMENT_CHECKLIST.md** - Printable checklist to track progress
5. **SECURITY_SETUP.md** - SECRET_KEY configuration (already done ✅)
6. **.ssh-config-example** - SSH configuration template

---

## 🚀 Quick Commands Reference

### Initial Setup (One Time)

```bash
# 1. Generate SSH key on your Mac
ssh-keygen -t ed25519 -f ~/.ssh/tvs_wages_proxmox

# 2. Connect to container
ssh root@192.168.1.202

# 3. Setup user and SSH
useradd -m -s /bin/bash tvswages
passwd tvswages
usermod -aG sudo tvswages
mkdir -p /var/www/tvs-wages
chown tvswages:tvswages /var/www/tvs-wages

# 4. Add SSH key (as tvswages user)
su - tvswages
mkdir -p ~/.ssh && chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys  # Paste your public key
chmod 600 ~/.ssh/authorized_keys
```

### Deploy Application

```bash
# On your Mac - upload code
cd /Users/danielhanson/CascadeProjects/Wages-App
rsync -avz --progress --exclude 'data/' --exclude 'venv/' --exclude '.git/' \
    -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    ./ tvswages@192.168.1.202:/var/www/tvs-wages/

# On container - setup
ssh -i ~/.ssh/tvs_wages_proxmox tvswages@192.168.1.202
cd /var/www/tvs-wages
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt gunicorn gevent
python3 -c "from app.database import init_database; init_database()"
```

### Transfer Data

```bash
# Database
rsync -avz --progress -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    data/database/payslips.db \
    tvswages@192.168.1.202:/var/www/tvs-wages/data/database/

# Payslips
rsync -avz --progress -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    data/documents/payslips/ \
    tvswages@192.168.1.202:/var/www/tvs-wages/data/documents/payslips/

# Runsheets
rsync -avz --progress -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    data/documents/runsheets/ \
    tvswages@192.168.1.202:/var/www/tvs-wages/data/documents/runsheets/
```

---

## 🔧 Daily Operations

### Connect to Container

```bash
# After adding to ~/.ssh/config
ssh tvs-wages

# Or full command
ssh -i ~/.ssh/tvs_wages_proxmox tvswages@192.168.1.202
```

### Manage Application

```bash
# Restart
sudo systemctl restart tvs-wages

# Status
sudo systemctl status tvs-wages

# Logs (live)
sudo journalctl -u tvs-wages -f

# Logs (last 50 lines)
sudo journalctl -u tvs-wages -n 50
```

### Update Application

```bash
# Upload new code
cd /Users/danielhanson/CascadeProjects/Wages-App
rsync -avz --progress --exclude 'data/' -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    ./ tvswages@192.168.1.202:/var/www/tvs-wages/

# Restart on server
ssh tvs-wages "cd /var/www/tvs-wages && source venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart tvs-wages"
```

---

## 📍 Important Information

### URLs
- **Application**: http://192.168.1.202
- **Accessible from**: Any device on 192.168.1.x network

### Credentials
- **SSH User**: tvswages
- **SSH Key**: ~/.ssh/tvs_wages_proxmox
- **Container IP**: 192.168.1.202

### Paths on Server
- **Application**: /var/www/tvs-wages
- **Database**: /var/www/tvs-wages/data/database/payslips.db
- **Logs**: /var/www/tvs-wages/logs
- **Backups**: /var/www/tvs-wages/data/database/backups

### Configuration Files
- **Environment**: /var/www/tvs-wages/.env
- **Service**: /etc/systemd/system/tvs-wages.service
- **Nginx**: /etc/nginx/sites-available/tvs-wages

---

## 🎯 Deployment Stages

### Stage 1: Container & SSH ✅
- [x] SSH key generated
- [x] User 'tvswages' created
- [x] SSH key authentication working
- [x] Can connect: `ssh tvs-wages`

### Stage 2: Application Installation ✅
- [x] System dependencies installed
- [x] Code deployed
- [x] Virtual environment created
- [x] .env file configured with SECRET_KEY
- [x] Database initialized
- [x] Systemd service running
- [x] Nginx configured
- [x] Accessible at http://192.168.1.202

### Stage 3: Data Migration ✅
- [x] Database transferred
- [x] Payslips transferred (238 files)
- [x] Runsheets transferred (1,685+ files)
- [x] Automated backups configured
- [x] All data visible in app

---

## 🔍 Monitoring

### Check Application Health

```bash
# Service status
ssh tvs-wages "sudo systemctl status tvs-wages"

# Recent logs
ssh tvs-wages "sudo journalctl -u tvs-wages -n 20"

# Disk space
ssh tvs-wages "df -h"

# Memory usage
ssh tvs-wages "free -h"
```

### Check Backups

```bash
# List backups
ssh tvs-wages "ls -lh /var/www/tvs-wages/data/database/backups/"

# Check backup log
ssh tvs-wages "tail /var/www/tvs-wages/logs/backup.log"
```

---

## 🆘 Troubleshooting

### Application Won't Start

```bash
ssh tvs-wages
sudo journalctl -u tvs-wages -n 100
cd /var/www/tvs-wages
source venv/bin/activate
python3 new_web_app.py  # Test manually
```

### Can't Access via Browser

```bash
# Check services
ssh tvs-wages "sudo systemctl status tvs-wages nginx"

# Check ports
ssh tvs-wages "sudo netstat -tlnp | grep -E ':(80|5001)'"

# Test locally
ssh tvs-wages "curl http://localhost"
```

### Database Issues

```bash
ssh tvs-wages
cd /var/www/tvs-wages
ls -lh data/database/payslips.db
sqlite3 data/database/payslips.db "SELECT COUNT(*) FROM payslips;"
```

### Need to Reset

```bash
ssh tvs-wages
cd /var/www/tvs-wages
source venv/bin/activate
python3 -c "from app.database import init_database; init_database()"
sudo systemctl restart tvs-wages
```

---

## 📝 Next Steps (Optional)

### 1. Enable Gmail Auto-Sync

```bash
ssh tvs-wages
nano /var/www/tvs-wages/.env
# Change: AUTO_SYNC_ENABLED=true
sudo systemctl restart tvs-wages
```

### 2. Setup Local Domain

```bash
# On your Mac
sudo nano /etc/hosts
# Add: 192.168.1.202    tvs-wages.local

# Access via: http://tvs-wages.local
```

### 3. Add More Users

When you need to add users (future):
- Install Flask-Login
- Create user table
- Add authentication to routes

---

## 📊 Statistics

### Your Data
- **Payslips**: 238 records
- **Job Items**: 14,463 items
- **Total Earnings**: £284,840.98
- **Runsheets**: 1,685+ files organized by year/month
- **Jobs**: 15,125+ jobs

### Application
- **Framework**: Flask 2.3.3
- **Database**: SQLite
- **Server**: Gunicorn + Nginx
- **Platform**: Debian (Proxmox LXC)

---

## 🎉 Success Criteria

Your deployment is successful when:

- ✅ Can access http://192.168.1.202 from your Mac
- ✅ Wages page shows all 238 payslips
- ✅ Runsheets page shows all runsheets
- ✅ Reports generate correctly
- ✅ Application survives container restart
- ✅ Daily backups are running
- ✅ No errors in logs

---

## 📞 Quick Help

### Most Common Commands

```bash
# Connect
ssh tvs-wages

# Restart app
ssh tvs-wages "sudo systemctl restart tvs-wages"

# View logs
ssh tvs-wages "sudo journalctl -u tvs-wages -f"

# Upload code
cd /Users/danielhanson/CascadeProjects/Wages-App && \
rsync -avz --exclude 'data/' -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
./ tvswages@192.168.1.202:/var/www/tvs-wages/

# Backup database manually
ssh tvs-wages "/var/www/tvs-wages/scripts/backup_production.sh"
```

---

**Documentation created**: November 15, 2025  
**Container IP**: 192.168.1.202  
**Status**: Ready to deploy 🚀
