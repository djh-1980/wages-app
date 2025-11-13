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

## 📊 Part 3: Complete Data and Database Setup

### Step 3.1: Create Data Directory Structure
```bash
# SSH as wagesapp user
ssh wagesapp@192.168.1.202
cd wages-app

# Create the complete data directory structure
mkdir -p data/database/backups
mkdir -p data/documents/payslips
mkdir -p data/documents/runsheets
mkdir -p data/exports/csv
mkdir -p data/exports/summaries
mkdir -p data/processing/queue
mkdir -p data/processing/temp
mkdir -p data/processing/failed
mkdir -p data/processing/manual
mkdir -p data/reports
mkdir -p data/uploads/payslips
mkdir -p data/uploads/runsheets

# Create .gitkeep files to preserve empty directories
touch data/documents/payslips/.gitkeep
touch data/documents/runsheets/.gitkeep
touch data/uploads/payslips/.gitkeep
touch data/uploads/runsheets/.gitkeep
touch data/processing/queue/.gitkeep
touch data/processing/temp/.gitkeep
touch data/processing/failed/.gitkeep
touch data/processing/manual/.gitkeep

# Exit back to your Mac for data transfer
exit
```

### Step 3.2: Transfer Main Database (From Your Mac)
```bash
# Copy the main SQLite database (contains all payslip and job data)
scp /Users/danielhanson/CascadeProjects/Wages-App/data/database/payslips.db root@192.168.1.202:/home/wagesapp/wages-app/data/database/

# Fix ownership and permissions
ssh root@192.168.1.202 "chown wagesapp:wagesapp /home/wagesapp/wages-app/data/database/payslips.db"
ssh root@192.168.1.202 "chmod 664 /home/wagesapp/wages-app/data/database/payslips.db"
```

### Step 3.3: Transfer Organized Runsheet PDFs
```bash
# Copy the organized runsheets directory (1,685+ PDFs organized by year/month)
scp -r /Users/danielhanson/CascadeProjects/Wages-App/data/runsheets/ root@192.168.1.202:/home/wagesapp/wages-app/data/

# Fix ownership and permissions
ssh root@192.168.1.202 "chown -R wagesapp:wagesapp /home/wagesapp/wages-app/data/runsheets"
ssh root@192.168.1.202 "chmod -R 755 /home/wagesapp/wages-app/data/runsheets"
```

### Step 3.4: Transfer Document Archives (If Available)
```bash
# Copy organized payslip PDFs if they exist
if [ -d "/Users/danielhanson/CascadeProjects/Wages-App/data/documents/payslips" ]; then
    scp -r /Users/danielhanson/CascadeProjects/Wages-App/data/documents/payslips/ root@192.168.1.202:/home/wagesapp/wages-app/data/documents/
    ssh root@192.168.1.202 "chown -R wagesapp:wagesapp /home/wagesapp/wages-app/data/documents/payslips"
fi

# Copy organized runsheet PDFs if they exist in documents folder
if [ -d "/Users/danielhanson/CascadeProjects/Wages-App/data/documents/runsheets" ]; then
    scp -r /Users/danielhanson/CascadeProjects/Wages-App/data/documents/runsheets/ root@192.168.1.202:/home/wagesapp/wages-app/data/documents/
    ssh root@192.168.1.202 "chown -R wagesapp:wagesapp /home/wagesapp/wages-app/data/documents/runsheets"
fi
```

### Step 3.5: Transfer Export Files and Reports
```bash
# Copy existing export files
if [ -d "/Users/danielhanson/CascadeProjects/Wages-App/data/exports" ]; then
    scp -r /Users/danielhanson/CascadeProjects/Wages-App/data/exports/ root@192.168.1.202:/home/wagesapp/wages-app/data/
    ssh root@192.168.1.202 "chown -R wagesapp:wagesapp /home/wagesapp/wages-app/data/exports"
fi

# Copy existing reports
if [ -d "/Users/danielhanson/CascadeProjects/Wages-App/data/reports" ]; then
    scp -r /Users/danielhanson/CascadeProjects/Wages-App/data/reports/ root@192.168.1.202:/home/wagesapp/wages-app/data/
    ssh root@192.168.1.202 "chown -R wagesapp:wagesapp /home/wagesapp/wages-app/data/reports"
fi
```

### Step 3.6: Transfer Legacy Data (If Needed)
```bash
# Copy legacy RunSheets folder if it still exists
if [ -d "/Users/danielhanson/CascadeProjects/Wages-App/RunSheets" ]; then
    echo "⚠️  Legacy RunSheets folder found - copying for backup"
    scp -r /Users/danielhanson/CascadeProjects/Wages-App/RunSheets root@192.168.1.202:/home/wagesapp/wages-app/legacy_RunSheets
    ssh root@192.168.1.202 "chown -R wagesapp:wagesapp /home/wagesapp/wages-app/legacy_RunSheets"
fi

# Copy legacy PaySlips folder if it still exists
if [ -d "/Users/danielhanson/CascadeProjects/Wages-App/PaySlips" ]; then
    echo "⚠️  Legacy PaySlips folder found - copying for backup"
    scp -r /Users/danielhanson/CascadeProjects/Wages-App/PaySlips root@192.168.1.202:/home/wagesapp/wages-app/legacy_PaySlips
    ssh root@192.168.1.202 "chown -R wagesapp:wagesapp /home/wagesapp/wages-app/legacy_PaySlips"
fi
```

### Step 3.7: Transfer Configuration Files
```bash
# Copy runsheet configuration if it exists
if [ -f "/Users/danielhanson/CascadeProjects/Wages-App/data/new_runsheets.json" ]; then
    scp /Users/danielhanson/CascadeProjects/Wages-App/data/new_runsheets.json root@192.168.1.202:/home/wagesapp/wages-app/data/
    ssh root@192.168.1.202 "chown wagesapp:wagesapp /home/wagesapp/wages-app/data/new_runsheets.json"
fi

# Copy data documentation
if [ -f "/Users/danielhanson/CascadeProjects/Wages-App/data/README.md" ]; then
    scp /Users/danielhanson/CascadeProjects/Wages-App/data/README.md root@192.168.1.202:/home/wagesapp/wages-app/data/
    ssh root@192.168.1.202 "chown wagesapp:wagesapp /home/wagesapp/wages-app/data/README.md"
fi
```

### Step 3.8: Transfer Gmail Credentials (Optional)
```bash
# If you have Gmail integration set up
if [ -f "/Users/danielhanson/CascadeProjects/Wages-App/credentials.json" ]; then
    scp /Users/danielhanson/CascadeProjects/Wages-App/credentials.json root@192.168.1.202:/home/wagesapp/wages-app/
    ssh root@192.168.1.202 "chown wagesapp:wagesapp /home/wagesapp/wages-app/credentials.json"
    ssh root@192.168.1.202 "chmod 600 /home/wagesapp/wages-app/credentials.json"
fi

if [ -f "/Users/danielhanson/CascadeProjects/Wages-App/token.json" ]; then
    scp /Users/danielhanson/CascadeProjects/Wages-App/token.json root@192.168.1.202:/home/wagesapp/wages-app/
    ssh root@192.168.1.202 "chown wagesapp:wagesapp /home/wagesapp/wages-app/token.json"
    ssh root@192.168.1.202 "chmod 600 /home/wagesapp/wages-app/token.json"
fi
```

### Step 3.9: Verify Data Transfer and Database Integrity
```bash
# SSH as wagesapp user to verify everything
ssh wagesapp@192.168.1.202
cd wages-app

# Check database file
ls -la data/database/payslips.db

# Verify database has data
sqlite3 data/database/payslips.db "SELECT COUNT(*) as payslip_count FROM payslips;"
sqlite3 data/database/payslips.db "SELECT COUNT(*) as job_items_count FROM job_items;"
sqlite3 data/database/payslips.db "SELECT SUM(total_earnings) as total_earnings FROM payslips;"

# Check runsheets directory structure
find data/runsheets -name "*.pdf" | wc -l
echo "Runsheets organized by year:"
ls -la data/runsheets/

# Check directory permissions
ls -la data/

# Test database connection with the app
source venv/bin/activate
python3 -c "from app.database import get_db_connection; conn = get_db_connection(); print('✅ Database connection successful'); conn.close()"

exit
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
    server_name 192.168.1.202 tvs.daniel-hanson.co.uk;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Handle Cloudflare Tunnel headers
    real_ip_header CF-Connecting-IP;
    set_real_ip_from 0.0.0.0/0;
    
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Cloudflare Tunnel specific headers
        proxy_set_header CF-Connecting-IP $http_cf_connecting_ip;
        proxy_set_header CF-Ray $http_cf_ray;
        proxy_set_header CF-Visitor $http_cf_visitor;
        
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

## 🌐 Part 6.5: Cloudflare Tunnel Configuration

### Step 6.5.1: Update Cloudflare Tunnel on Your Management Device
**On the device where cloudflared is already running:**

```bash
# Edit your tunnel configuration
sudo nano /etc/cloudflared/config.yml
```

**Add or update the TVS Wages App service:**
```yaml
tunnel: your-tunnel-id
credentials-file: /etc/cloudflared/your-tunnel-id.json

ingress:
  # TVS Wages App
  - hostname: tvs.daniel-hanson.co.uk
    service: http://192.168.1.202:80
    originRequest:
      httpHostHeader: tvs.daniel-hanson.co.uk
      connectTimeout: 30s
      tlsTimeout: 30s
      tcpKeepAlive: 30s
      keepAliveTimeout: 90s
      keepAliveConnections: 100
  
  # Your other services (if any)
  # - hostname: other.daniel-hanson.co.uk
  #   service: http://other-ip:port
  
  # Catch-all rule (must be last)
  - service: http_status:404
```

### Step 6.5.2: Restart Cloudflare Tunnel
```bash
# Restart the tunnel service
sudo systemctl restart cloudflared

# Check status
sudo systemctl status cloudflared

# View logs if needed
sudo journalctl -u cloudflared -f
```

### Step 6.5.3: Verify DNS Configuration
**In Cloudflare Dashboard:**
1. **Go to DNS settings** for `daniel-hanson.co.uk`
2. **Verify CNAME record** exists:
   - **Name**: `tvs`
   - **Target**: `your-tunnel-id.cfargotunnel.com`
   - **Proxy status**: Proxied (orange cloud)

### Step 6.5.4: Test Cloudflare Tunnel Access
**From any internet-connected device:**
```bash
# Test DNS resolution
nslookup tvs.daniel-hanson.co.uk

# Test HTTP access
curl -I https://tvs.daniel-hanson.co.uk
```

**Expected result:**
- DNS should resolve to Cloudflare IPs
- HTTP should return 200 OK or redirect to HTTPS
- HTTPS should show your TVS Wages App

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

**Local Network Access (from your Mac browser):**
```
http://192.168.1.202
```

**Internet Access (from anywhere via Cloudflare Tunnel):**
```
https://tvs.daniel-hanson.co.uk
```

You should see:
- ✅ **Wages App v1.1 Dashboard**
- ✅ **All data loaded** (238 payslips, 14,477+ job items, 1,824+ runsheets)
- ✅ **All features working** (analytics, reports, etc.)
- ✅ **Secure HTTPS access** via Cloudflare
- ✅ **Fast global CDN** performance

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

### Complete Database and Data Backup
```bash
# SSH as wagesapp user to create comprehensive backup script
ssh wagesapp@192.168.1.202
nano backup.sh
```

**Add this enhanced backup content:**
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/wagesapp/backups"
APP_DIR="/home/wagesapp/wages-app"

# Create backup directory structure
mkdir -p $BACKUP_DIR/database
mkdir -p $BACKUP_DIR/documents
mkdir -p $BACKUP_DIR/exports
mkdir -p $BACKUP_DIR/reports

echo "Starting comprehensive backup: $DATE"

# Backup main database with integrity check
echo "Backing up main database..."
sqlite3 $APP_DIR/data/database/payslips.db "PRAGMA integrity_check;" > $BACKUP_DIR/database/integrity_check_$DATE.log
cp $APP_DIR/data/database/payslips.db $BACKUP_DIR/database/payslips_$DATE.db

# Backup organized runsheets (compressed)
echo "Backing up organized runsheets..."
if [ -d "$APP_DIR/data/runsheets" ]; then
    tar -czf $BACKUP_DIR/documents/runsheets_organized_$DATE.tar.gz -C $APP_DIR/data runsheets
fi

# Backup document archives if they exist
echo "Backing up document archives..."
if [ -d "$APP_DIR/data/documents/payslips" ] && [ "$(ls -A $APP_DIR/data/documents/payslips)" ]; then
    tar -czf $BACKUP_DIR/documents/payslips_archive_$DATE.tar.gz -C $APP_DIR/data/documents payslips
fi

if [ -d "$APP_DIR/data/documents/runsheets" ] && [ "$(ls -A $APP_DIR/data/documents/runsheets)" ]; then
    tar -czf $BACKUP_DIR/documents/runsheets_archive_$DATE.tar.gz -C $APP_DIR/data/documents runsheets
fi

# Backup exports and reports
echo "Backing up exports and reports..."
if [ -d "$APP_DIR/data/exports" ] && [ "$(ls -A $APP_DIR/data/exports)" ]; then
    tar -czf $BACKUP_DIR/exports/exports_$DATE.tar.gz -C $APP_DIR/data exports
fi

if [ -d "$APP_DIR/data/reports" ] && [ "$(ls -A $APP_DIR/data/reports)" ]; then
    tar -czf $BACKUP_DIR/reports/reports_$DATE.tar.gz -C $APP_DIR/data reports
fi

# Backup configuration files
echo "Backing up configuration files..."
cp $APP_DIR/data/new_runsheets.json $BACKUP_DIR/new_runsheets_$DATE.json 2>/dev/null || true
cp $APP_DIR/data/README.md $BACKUP_DIR/README_$DATE.md 2>/dev/null || true

# Create backup summary
echo "Creating backup summary..."
cat > $BACKUP_DIR/backup_summary_$DATE.txt << EOF
Backup Summary - $DATE
========================

Database:
- Main database: $(ls -lh $BACKUP_DIR/database/payslips_$DATE.db | awk '{print $5}')
- Integrity check: $(cat $BACKUP_DIR/database/integrity_check_$DATE.log)

Documents:
$(ls -lh $BACKUP_DIR/documents/ | grep $DATE || echo "No document backups created")

Exports:
$(ls -lh $BACKUP_DIR/exports/ | grep $DATE || echo "No export backups created")

Reports:
$(ls -lh $BACKUP_DIR/reports/ | grep $DATE || echo "No report backups created")

Total backup size: $(du -sh $BACKUP_DIR | awk '{print $1}')
EOF

# Cleanup old backups (keep last 30 days)
echo "Cleaning up old backups..."
find $BACKUP_DIR -name "*_*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*_*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*_*.json" -mtime +30 -delete
find $BACKUP_DIR -name "*_*.md" -mtime +30 -delete
find $BACKUP_DIR -name "*_*.txt" -mtime +30 -delete
find $BACKUP_DIR -name "*_*.log" -mtime +30 -delete

echo "Backup completed successfully: $DATE"
echo "Summary saved to: $BACKUP_DIR/backup_summary_$DATE.txt"
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
ls -la /home/wagesapp/wages-app/data/database/payslips.db

# Fix database permissions if needed
chown -R wagesapp:wagesapp /home/wagesapp/wages-app/data
chmod -R 755 /home/wagesapp/wages-app/data
chmod 664 /home/wagesapp/wages-app/data/database/payslips.db

# Test database connection
cd /home/wagesapp/wages-app
source venv/bin/activate
python3 -c "from app.database import get_db_connection; print('Database OK')"

# Check if database has data
sqlite3 data/database/payslips.db 'SELECT COUNT(*) FROM payslips;'
sqlite3 data/database/payslips.db 'SELECT COUNT(*) FROM job_items;'
sqlite3 data/database/payslips.db 'SELECT SUM(total_earnings) FROM payslips;'

# Check database integrity
sqlite3 data/database/payslips.db 'PRAGMA integrity_check;'

# Check database schema
sqlite3 data/database/payslips.db '.schema'
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

**Upload and file processing issues:**
```bash
# Check upload directory permissions
ls -la /home/wagesapp/wages-app/data/uploads/
ls -la /home/wagesapp/wages-app/data/processing/

# Check document storage permissions
ls -la /home/wagesapp/wages-app/data/documents/
ls -la /home/wagesapp/wages-app/data/runsheets/

# Fix permissions if needed
chown -R wagesapp:wagesapp /home/wagesapp/wages-app/data/uploads/
chown -R wagesapp:wagesapp /home/wagesapp/wages-app/data/processing/
chown -R wagesapp:wagesapp /home/wagesapp/wages-app/data/documents/
chown -R wagesapp:wagesapp /home/wagesapp/wages-app/data/runsheets/

# Check processing queue
ls -la /home/wagesapp/wages-app/data/processing/queue/
ls -la /home/wagesapp/wages-app/data/processing/failed/

# Clear stuck processing files if needed
rm -f /home/wagesapp/wages-app/data/processing/temp/*
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
- ✅ **Secure global access** via Cloudflare Tunnel
- ✅ **HTTPS encryption** and DDoS protection
- ✅ **Fast CDN delivery** worldwide

### Access Your Application:
**Public URL:** `https://tvs.daniel-hanson.co.uk` (secure, global access)
**Local URL:** `http://192.168.1.202` (local network only)
**SSH Access:** `ssh wagesapp@192.168.1.202`
**Management:** Use supervisor and nginx commands

### Next Steps:
1. **Set up SSL/HTTPS** with Let's Encrypt (optional)
2. **Configure domain name** instead of IP (optional)
3. **Set up monitoring** and alerting (optional)
4. **Regular maintenance** and updates

**Your Wages App v1.1 is now fully deployed and production-ready!** 🚀
