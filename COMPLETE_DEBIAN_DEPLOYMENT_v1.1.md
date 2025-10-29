# 🚀 Complete Wages App v1.1 Deployment Guide - Debian 12

**Complete step-by-step guide to deploy the enterprise-grade Wages App v1.1 on a fresh Debian 12 container.**

## 📋 Prerequisites
- Fresh Debian 12 container (unprivileged recommended)
- Proxmox console access
- Your Mac with the v1.1 codebase
- Network connectivity

---

## 🔧 Part 1: Initial Container Setup

### Step 1.1: Access Container Console
1. **Open Proxmox web interface**
2. **Select your container**
3. **Click "Console"** (you'll be logged in as root)

### Step 1.2: Update System
```bash
apt update && apt upgrade -y
```

### Step 1.3: Install Essential Packages
```bash
apt install -y python3 python3-pip python3-venv git sqlite3 nginx supervisor curl nano htop
```

### Step 1.4: Set Root Password (for SSH access)
```bash
passwd root
# Enter a secure password when prompted
```

### Step 1.5: Configure SSH Access
```bash
# Edit SSH configuration
nano /etc/ssh/sshd_config

# Ensure these lines are set:
PermitRootLogin yes
PasswordAuthentication yes
PubkeyAuthentication yes

# Restart SSH service
systemctl restart ssh
systemctl enable ssh
```

### Step 1.6: Add Your SSH Key (Recommended)
```bash
# Create SSH directory
mkdir -p /root/.ssh
chmod 700 /root/.ssh

# Add your public key (replace with your actual key)
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDjrasdb1wfUnyJ18iXZqpOoSBzNbgO+8HAqAI3MucO69XUAvD6Vhg7K1gv5VxoPyjDoo+iLvagT/Gfmvw3ixOcO/vZ2UZ/fjPwA76cdaWhpg6aIdv2pcDv33AUM9ZN1kqx1YqiwgEwY2tvIm2hCDG0WIxtxHpe7wqouRTUfjIxgKRRxYNJ8usvVtPLdjf0SiXgWxj2FxtgKWcrWRgqLFdcUhVr0SsL17GR5sIxQdJ6RBaW1mRWwB67+vAmTwGWhKPPOe7BUjyBkTiF0qQeoWTHylph0ZEMHzUPGeV8yYIKtgVbp+DPLExURY0kHEvbQv71auDXh43Z+DeUe62kh62TCMebsFAnQA4R7NFo/+pRT4aur70vCYmD1xuNCPhuwgmDQZS3FugJGoLgG6tzBhzc6V1qT8T4S/56NTvxlUMdajCJT2JpC93efBvlJnyvRinaiOncjfJTu/s6CKPI+eJuHSQwl0L4IIq0bAsbUUSJUzSJ0b4tNwvYLtLNM7GnaZF7L3WtPtb7r8mIDKwYPL/AmCl8ywW3QRDna8AZObNxTIf4cUviUVyyxtn3VEVLHgdchcpdMg298yK+wLNaz4hu3tM9DHp1Z/p4VJ+jvaaO//2J9dRNjnWlblTa5nu6a5QbwqqbUQoH54b6CS8MpxLkdAukieWA/QCu4hFX110gMw== danielhanson@192.168.1.238" > /root/.ssh/authorized_keys

# Set correct permissions
chmod 600 /root/.ssh/authorized_keys
```

### Step 1.7: Create Application User
```bash
# Create dedicated user for the app
adduser --disabled-password --gecos "" wagesapp

# Set up SSH access for wagesapp user
mkdir -p /home/wagesapp/.ssh
chmod 700 /home/wagesapp/.ssh

# Copy SSH key to wagesapp user
cp /root/.ssh/authorized_keys /home/wagesapp/.ssh/authorized_keys
chmod 600 /home/wagesapp/.ssh/authorized_keys
chown -R wagesapp:wagesapp /home/wagesapp/.ssh

# Add wagesapp to sudo group (optional)
usermod -aG sudo wagesapp
```

---

## 📦 Part 2: Deploy Application Code

### Step 2.1: Test SSH Access (From Your Mac)
```bash
# Test root access
ssh root@192.168.1.202

# Test wagesapp user access
ssh wagesapp@192.168.1.202
```

### Step 2.2: Clone Application (as wagesapp user)
```bash
# SSH to server as wagesapp
ssh wagesapp@192.168.1.202

# Clone the v1.1 repository
git clone https://github.com/djh-1980/wages-app.git
cd wages-app

# Verify you have v1.1
git log --oneline -1
# Should show: "🎉 Release v1.1: Complete Enterprise Transformation"
```

### Step 2.3: Set Up Python Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install core dependencies
pip install -r requirements.txt

# Optional: Install Gmail sync features
pip install -r requirements-gmail.txt
```

### Step 2.4: Test Application Installation
```bash
# Test v1.1 imports
python3 -c "from app import create_app; print('✅ v1.1 imports successfully')"

# Test app creation
python3 -c "from app import create_app; app = create_app(); print('✅ App creation successful')"
```

---

## 📊 Part 3: Transfer Your Data

### Step 3.1: Copy Database (From Your Mac)
```bash
# Copy your existing database
scp /Users/danielhanson/CascadeProjects/Wages-App/data/payslips.db root@192.168.1.202:/home/wagesapp/wages-app/data/

# Fix ownership
ssh root@192.168.1.202 "chown wagesapp:wagesapp /home/wagesapp/wages-app/data/payslips.db"
```

### Step 3.2: Copy RunSheets Folder (Important!)
```bash
# Copy RunSheets directory with all PDFs
scp -r /Users/danielhanson/CascadeProjects/Wages-App/RunSheets root@192.168.1.202:/home/wagesapp/wages-app/

# Copy PaySlips directory
scp -r /Users/danielhanson/CascadeProjects/Wages-App/PaySlips root@192.168.1.202:/home/wagesapp/wages-app/

# Fix ownership and permissions for all data
ssh root@192.168.1.202 "chown -R wagesapp:wagesapp /home/wagesapp/wages-app/RunSheets /home/wagesapp/wages-app/PaySlips /home/wagesapp/wages-app/data"
ssh root@192.168.1.202 "chmod -R 755 /home/wagesapp/wages-app/data"
ssh root@192.168.1.202 "chmod 664 /home/wagesapp/wages-app/data/payslips.db"
```

### Step 3.3: Copy Gmail Credentials (Optional)
```bash
# If you have Gmail integration set up
scp /Users/danielhanson/CascadeProjects/Wages-App/credentials.json root@192.168.1.202:/home/wagesapp/wages-app/
scp /Users/danielhanson/CascadeProjects/Wages-App/token.json root@192.168.1.202:/home/wagesapp/wages-app/

# Fix ownership
ssh root@192.168.1.202 "chown wagesapp:wagesapp /home/wagesapp/wages-app/credentials.json /home/wagesapp/wages-app/token.json"
```

---

## 🧪 Part 4: Test the Application

### Step 4.1: Manual Test Run
```bash
# SSH as wagesapp user
ssh wagesapp@192.168.1.202
cd wages-app
source venv/bin/activate

# Start the application manually
python3 new_web_app.py
```

You should see:
```
================================================================================
WAGES APP - WEB INTERFACE (REFACTORED)
================================================================================

🌐 Starting web server...
📊 Open your browser to: http://localhost:5001
⏹️  Press Ctrl+C to stop

================================================================================

 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5001
 * Running on http://192.168.1.202:5001
```

### Step 4.2: Test Web Access
**From your Mac browser:**
```
http://192.168.1.202:5001
```

You should see the Wages App v1.1 dashboard!

**Press Ctrl+C to stop the test server.**

---

## 🔧 Part 5: Production Setup with Supervisor

### Step 5.1: Create Supervisor Configuration (as root)
```bash
# SSH as root
ssh root@192.168.1.202

# Create supervisor config
nano /etc/supervisor/conf.d/wagesapp.conf
```

**Add this content:**
```ini
[program:wagesapp]
command=/home/wagesapp/wages-app/venv/bin/python3 /home/wagesapp/wages-app/new_web_app.py
directory=/home/wagesapp/wages-app
user=wagesapp
autostart=true
autorestart=true
stderr_logfile=/var/log/wagesapp.err.log
stdout_logfile=/var/log/wagesapp.out.log
environment=PATH="/home/wagesapp/wages-app/venv/bin"
```

### Step 5.2: Start the Service
```bash
# Reload supervisor configuration
supervisorctl reread
supervisorctl update

# Start the application
supervisorctl start wagesapp

# Check status
supervisorctl status
```

---

## 🌐 Part 6: Nginx Reverse Proxy Setup

### Step 6.1: Configure Nginx (as root)
```bash
# Create nginx site configuration
nano /etc/nginx/sites-available/wagesapp
```

**Add this content:**
```nginx
server {
    listen 80;
    server_name 192.168.1.202;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeout for file uploads and processing
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
    
    # Increase max upload size for PDFs
    client_max_body_size 50M;
    
    # Optional: Serve static files directly (performance optimization)
    location /static/ {
        alias /home/wagesapp/wages-app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Step 6.2: Enable Site and Start Nginx
```bash
# Enable the site
ln -s /etc/nginx/sites-available/wagesapp /etc/nginx/sites-enabled/

# Remove default site (optional)
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
nginx -t

# Start and enable nginx
systemctl start nginx
systemctl enable nginx

# CRITICAL: Fix static file permissions for Nginx
chmod 755 /home/wagesapp
chmod 755 /home/wagesapp/wages-app
chmod -R 755 /home/wagesapp/wages-app/static/

# Reload nginx to apply changes
systemctl reload nginx
```

---

## 🔒 Part 7: Security and Firewall

### Step 7.1: Configure Firewall
```bash
# Install and configure UFW firewall
apt install -y ufw

# Allow SSH
ufw allow 22/tcp

# Allow HTTP
ufw allow 80/tcp

# Allow HTTPS (for future SSL)
ufw allow 443/tcp

# Enable firewall
ufw --force enable

# Check status
ufw status
```

### Step 7.2: Add Password Protection (Optional)
```bash
# Install apache2-utils for htpasswd
apt install -y apache2-utils

# Create password file
htpasswd -c /etc/nginx/.htpasswd yourusername
# Enter password when prompted

# Update nginx config to add authentication
nano /etc/nginx/sites-available/wagesapp
```

**Add these lines inside the `location /` block:**
```nginx
    auth_basic "Wages App Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
```

**Restart nginx:**
```bash
systemctl restart nginx
```

---

## ✅ Part 8: Final Testing and Access

### Step 8.1: Test Complete Setup
**From your Mac browser:**
```
http://192.168.1.202
```

You should see:
- ✅ **Wages App v1.1 Dashboard**
- ✅ **All data loaded** (payslips, runsheets)
- ✅ **All features working** (analytics, reports, etc.)

### Step 8.2: Test Key Features
1. **Dashboard** - Should show your data and analytics
2. **PaySlips** - Upload and view functionality
3. **RunSheets** - Management and optimization features
4. **Reports** - Advanced business intelligence
5. **Settings** - Configuration options
6. **Gmail Sync** - If configured

---

## 🛠️ Part 9: Management Commands

### Application Management
```bash
# Check application status
supervisorctl status wagesapp

# View logs
tail -f /var/log/wagesapp.out.log
tail -f /var/log/wagesapp.err.log

# Restart application
supervisorctl restart wagesapp

# Stop application
supervisorctl stop wagesapp

# Start application
supervisorctl start wagesapp
```

### System Management
```bash
# Check nginx status
systemctl status nginx

# Restart nginx
systemctl restart nginx

# Check system resources
htop

# Check disk space
df -h

# Check memory usage
free -h
```

### Update Application
```bash
# SSH as wagesapp user
ssh wagesapp@192.168.1.202
cd wages-app

# Pull latest changes
git pull origin main

# Update dependencies if needed
source venv/bin/activate
pip install -r requirements.txt

# Restart application
sudo supervisorctl restart wagesapp
```

---

## 📋 Part 10: Backup and Maintenance

### Database Backup
```bash
# SSH as wagesapp user to create backup script
ssh wagesapp@192.168.1.202
nano backup.sh
```

**Add this content:**
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/wagesapp/backups"
mkdir -p $BACKUP_DIR

# Backup database
cp /home/wagesapp/wages-app/data/payslips.db $BACKUP_DIR/payslips_$DATE.db

# Backup RunSheets
tar -czf $BACKUP_DIR/runsheets_$DATE.tar.gz -C /home/wagesapp/wages-app RunSheets

# Keep only last 30 days
find $BACKUP_DIR -name "payslips_*.db" -mtime +30 -delete
find $BACKUP_DIR -name "runsheets_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

**Make executable and set up cron:**
```bash
# Make script executable (as wagesapp user)
chmod +x backup.sh

# Exit back to your Mac, then SSH as root to set up cron
exit
```

**Then as root, set up the cron job:**
```bash
# SSH as root to set up cron job
ssh root@192.168.1.202

# Add to crontab for wagesapp user (daily at 2 AM)
crontab -e -u wagesapp
# Add this line in the editor:
0 2 * * * /home/wagesapp/backup.sh >> /var/log/backup.log 2>&1
```

---

## 🎯 Part 11: Troubleshooting

### Common Issues

**Application won't start:**
```bash
# Check logs
tail -50 /var/log/wagesapp.err.log

# Check if port is in use
netstat -tlnp | grep 5001

# Test manually
su - wagesapp
cd wages-app
source venv/bin/activate
python3 new_web_app.py
```

**Can't access from browser:**
```bash
# Check nginx status
systemctl status nginx

# Check nginx logs
tail -50 /var/log/nginx/error.log

# Test nginx config
nginx -t

# Check firewall
ufw status
```

**Database issues:**
```bash
# Check database file permissions
ls -la /home/wagesapp/wages-app/data/payslips.db

# Fix database permissions if needed
chown -R wagesapp:wagesapp /home/wagesapp/wages-app/data
chmod -R 755 /home/wagesapp/wages-app/data
chmod 664 /home/wagesapp/wages-app/data/payslips.db

# Test database connection
cd /home/wagesapp/wages-app
source venv/bin/activate
python3 -c "from app.database import get_db_connection; print('Database OK')"

# Check if database has data
sqlite3 data/payslips.db 'SELECT COUNT(*) FROM payslips;'
```

**Static files not loading (403 errors on CSS/JS):**
```bash
# Fix static file permissions for Nginx
chmod 755 /home/wagesapp
chmod 755 /home/wagesapp/wages-app
chmod -R 755 /home/wagesapp/wages-app/static/

# Reload nginx
systemctl reload nginx

# Test static file access
curl -I http://localhost/static/runsheets.js
```

**Upload issues:**
```bash
# Check directory permissions
ls -la /home/wagesapp/wages-app/PaySlips/
ls -la /home/wagesapp/wages-app/RunSheets/

# Fix permissions if needed
chown -R wagesapp:wagesapp /home/wagesapp/wages-app/PaySlips/
chown -R wagesapp:wagesapp /home/wagesapp/wages-app/RunSheets/
```

---

## 🎉 Deployment Complete!

### What You Now Have:
- ✅ **Enterprise-grade Wages App v1.1** running on Debian 12
- ✅ **Professional web server** with Nginx reverse proxy
- ✅ **Automatic startup** with Supervisor process management
- ✅ **Security** with firewall and optional password protection
- ✅ **All features** including RunSheets, PaySlips, Analytics, Reports
- ✅ **Gmail integration** (if configured)
- ✅ **Automated backups** and maintenance
- ✅ **SSH access** for management
- ✅ **Production-ready** infrastructure

### Access Your Application:
**Main URL:** `http://192.168.1.202`
**SSH Access:** `ssh wagesapp@192.168.1.202`
**Management:** Use supervisor and nginx commands

### Next Steps:
1. **Set up SSL/HTTPS** with Let's Encrypt (optional)
2. **Configure domain name** instead of IP (optional)
3. **Set up monitoring** and alerting (optional)
4. **Regular maintenance** and updates

**Your Wages App v1.1 is now fully deployed and production-ready!** 🚀
