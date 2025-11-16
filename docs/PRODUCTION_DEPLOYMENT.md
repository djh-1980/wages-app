# Production Deployment Guide - Staged Approach

Complete guide for deploying TVS Wages App to a production container/server in stages.

---

## Stage 1: Container Setup with SSH & User

### 1.1 Create Container/Server

**Option A: Docker Container**
```bash
# Pull Ubuntu image
docker pull ubuntu:22.04

# Create container with SSH
docker run -d \
  --name tvs-wages-prod \
  -p 2222:22 \
  -p 5001:5001 \
  --restart unless-stopped \
  ubuntu:22.04 \
  sleep infinity
```

**Option B: VPS/Cloud Server**
- Use your preferred provider (DigitalOcean, Linode, AWS, etc.)
- Choose Ubuntu 22.04 LTS
- Minimum specs: 1GB RAM, 1 CPU, 20GB storage

### 1.2 Initial Container/Server Access

```bash
# For Docker container
docker exec -it tvs-wages-prod bash

# For VPS
ssh root@your-server-ip
```

### 1.3 Install SSH Server (Docker only)

```bash
# Update system
apt-get update && apt-get upgrade -y

# Install SSH server
apt-get install -y openssh-server sudo nano curl wget git

# Start SSH service
service ssh start

# Enable SSH to start on boot
systemctl enable ssh
```

### 1.4 Create Application User

```bash
# Create user 'tvswages' with home directory
useradd -m -s /bin/bash tvswages

# Set password (you'll be prompted)
passwd tvswages

# Add user to sudo group
usermod -aG sudo tvswages

# Create application directory
mkdir -p /var/www/tvs-wages
chown tvswages:tvswages /var/www/tvs-wages
```

### 1.5 Setup SSH Key Authentication

**On your local machine:**
```bash
# Generate SSH key pair (if you don't have one)
ssh-keygen -t ed25519 -C "tvs-wages-production" -f ~/.ssh/tvs_wages_prod

# This creates:
# - ~/.ssh/tvs_wages_prod (private key - keep secret!)
# - ~/.ssh/tvs_wages_prod.pub (public key)
```

**On the server:**
```bash
# Switch to tvswages user
su - tvswages

# Create .ssh directory
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Create authorized_keys file
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Add your public key (paste the content of tvs_wages_prod.pub)
nano ~/.ssh/authorized_keys
# Paste your public key, save and exit (Ctrl+X, Y, Enter)
```

**Back on your local machine:**
```bash
# Test SSH connection
# For Docker container:
ssh -i ~/.ssh/tvs_wages_prod -p 2222 tvswages@localhost

# For VPS:
ssh -i ~/.ssh/tvs_wages_prod tvswages@your-server-ip

# Create SSH config for easy access
nano ~/.ssh/config
```

Add this to your SSH config:
```
Host tvs-wages-prod
    HostName your-server-ip  # or localhost for Docker
    Port 22                   # or 2222 for Docker
    User tvswages
    IdentityFile ~/.ssh/tvs_wages_prod
    IdentitiesOnly yes
```

Now you can connect with:
```bash
ssh tvs-wages-prod
```

### 1.6 Secure SSH Configuration

**On the server (as root or with sudo):**
```bash
# Edit SSH config
sudo nano /etc/ssh/sshd_config
```

Update these settings:
```
# Disable password authentication (use keys only)
PasswordAuthentication no
PubkeyAuthentication yes

# Disable root login
PermitRootLogin no

# Only allow specific user
AllowUsers tvswages
```

Restart SSH:
```bash
sudo systemctl restart ssh
```

### ✅ Stage 1 Complete Checklist
- [ ] Container/server created and running
- [ ] SSH server installed and configured
- [ ] User 'tvswages' created with sudo access
- [ ] SSH key pair generated
- [ ] Public key added to server
- [ ] SSH key authentication working
- [ ] SSH config file updated for easy access
- [ ] Password authentication disabled
- [ ] Can connect: `ssh tvs-wages-prod`

---

## Stage 2: Install Application on Container

### 2.1 Connect to Server

```bash
ssh tvs-wages-prod
```

### 2.2 Install System Dependencies

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python and required packages
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    supervisor \
    sqlite3 \
    git

# Install build dependencies for Python packages
sudo apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev
```

### 2.3 Clone Application Repository

```bash
# Navigate to application directory
cd /var/www/tvs-wages

# Clone your repository
git clone https://github.com/yourusername/wages-app.git .

# Or if using SSH
git clone git@github.com:yourusername/wages-app.git .
```

**Alternative: Manual Upload**
```bash
# On your local machine
rsync -avz -e "ssh -i ~/.ssh/tvs_wages_prod" \
    --exclude 'data/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.git/' \
    /Users/danielhanson/CascadeProjects/Wages-App/ \
    tvswages@your-server-ip:/var/www/tvs-wages/
```

### 2.4 Create Python Virtual Environment

```bash
cd /var/www/tvs-wages

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 2.5 Install Python Dependencies

```bash
# Install application dependencies
pip install -r requirements.txt

# Install production server (gunicorn)
pip install gunicorn gevent
```

### 2.6 Setup Environment Configuration

```bash
# Create .env file
nano .env
```

Add your production configuration:
```bash
# Flask Configuration
SECRET_KEY=99cd2927171ddd2572fb9d52779939dde003e9bb3a63a8954e1e14bc463ba346
FLASK_ENV=production

# Database Configuration
DATABASE_PATH=/var/www/tvs-wages/data/database/payslips.db
BACKUP_DIR=/var/www/tvs-wages/data/database/backups
BACKUP_RETENTION_DAYS=30

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/www/tvs-wages/logs

# Auto-sync (disable initially until Gmail configured)
AUTO_SYNC_ENABLED=false

# Feature Flags
FEATURE_ADVANCED_ANALYTICS=true
FEATURE_ROUTE_OPTIMIZATION=true
FEATURE_PREDICTIVE_ANALYTICS=true
FEATURE_DATA_VALIDATION=true
FEATURE_INTELLIGENT_SYNC=false
```

### 2.7 Create Required Directories

```bash
# Create data directories
mkdir -p data/database
mkdir -p data/database/backups
mkdir -p data/documents/payslips
mkdir -p data/documents/runsheets
mkdir -p data/exports/csv
mkdir -p data/exports/summaries
mkdir -p data/reports
mkdir -p data/processing/queue
mkdir -p data/processing/temp
mkdir -p data/processing/failed
mkdir -p data/uploads/payslips
mkdir -p data/uploads/runsheets

# Create logs directory
mkdir -p logs

# Set permissions
chmod 755 data
chmod 755 logs
```

### 2.8 Initialize Database

```bash
# Activate virtual environment if not already
source venv/bin/activate

# Initialize database
python3 -c "from app.database import init_database; init_database()"

# Verify database created
ls -lh data/database/
```

### 2.9 Test Application

```bash
# Test the application starts
python3 new_web_app.py

# Should see:
# ================================================================================
# WAGES APP - WEB INTERFACE (REFACTORED)
# ================================================================================
# 
# 🌐 Starting web server...
# 📊 Open your browser to: http://localhost:5001

# Press Ctrl+C to stop
```

### 2.10 Create Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/tvs-wages.service
```

Add this configuration:
```ini
[Unit]
Description=TVS Wages Application
After=network.target

[Service]
Type=notify
User=tvswages
Group=tvswages
WorkingDirectory=/var/www/tvs-wages
Environment="PATH=/var/www/tvs-wages/venv/bin"
ExecStart=/var/www/tvs-wages/venv/bin/gunicorn \
    --bind 127.0.0.1:5001 \
    --workers 2 \
    --worker-class gevent \
    --timeout 300 \
    --access-logfile /var/www/tvs-wages/logs/access.log \
    --error-logfile /var/www/tvs-wages/logs/error.log \
    --log-level info \
    new_web_app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable tvs-wages

# Start service
sudo systemctl start tvs-wages

# Check status
sudo systemctl status tvs-wages

# View logs
sudo journalctl -u tvs-wages -f
```

### 2.11 Configure Nginx Reverse Proxy

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/tvs-wages
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Change this to your domain or IP

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running requests
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location /static {
        alias /var/www/tvs-wages/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Logs
    access_log /var/log/nginx/tvs-wages-access.log;
    error_log /var/log/nginx/tvs-wages-error.log;
}
```

Enable the site:
```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/tvs-wages /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Enable Nginx to start on boot
sudo systemctl enable nginx
```

### 2.12 Configure Firewall (Optional but Recommended)

```bash
# Install UFW if not installed
sudo apt-get install -y ufw

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS (for future SSL)
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### ✅ Stage 2 Complete Checklist
- [ ] System dependencies installed
- [ ] Application code deployed
- [ ] Python virtual environment created
- [ ] Dependencies installed
- [ ] .env file configured with SECRET_KEY
- [ ] Required directories created
- [ ] Database initialized
- [ ] Application tested manually
- [ ] Systemd service created and running
- [ ] Nginx configured and running
- [ ] Firewall configured
- [ ] Can access app via browser: http://your-server-ip

---

## Stage 3: Migrate Data to Server

### 3.1 Prepare Data for Migration

**On your local machine:**

```bash
# Navigate to your project
cd /Users/danielhanson/CascadeProjects/Wages-App

# Create backup of current data
tar -czf data-backup-$(date +%Y%m%d).tar.gz data/

# Create a clean export (exclude temp files)
tar -czf data-migration.tar.gz \
    --exclude='data/processing/temp/*' \
    --exclude='data/processing/queue/*' \
    --exclude='*.log' \
    data/
```

### 3.2 Transfer Database

```bash
# Copy database file
scp -i ~/.ssh/tvs_wages_prod \
    data/database/payslips.db \
    tvswages@your-server-ip:/var/www/tvs-wages/data/database/

# Or using rsync for resume capability
rsync -avz --progress -e "ssh -i ~/.ssh/tvs_wages_prod" \
    data/database/payslips.db \
    tvswages@your-server-ip:/var/www/tvs-wages/data/database/
```

### 3.3 Transfer Documents (Payslips & Runsheets)

```bash
# Transfer payslips
rsync -avz --progress -e "ssh -i ~/.ssh/tvs_wages_prod" \
    data/documents/payslips/ \
    tvswages@your-server-ip:/var/www/tvs-wages/data/documents/payslips/

# Transfer runsheets
rsync -avz --progress -e "ssh -i ~/.ssh/tvs_wages_prod" \
    data/documents/runsheets/ \
    tvswages@your-server-ip:/var/www/tvs-wages/data/documents/runsheets/
```

### 3.4 Transfer Gmail Credentials (If Using)

```bash
# Transfer credentials.json
scp -i ~/.ssh/tvs_wages_prod \
    credentials.json \
    tvswages@your-server-ip:/var/www/tvs-wages/

# Transfer token.json
scp -i ~/.ssh/tvs_wages_prod \
    token.json \
    tvswages@your-server-ip:/var/www/tvs-wages/
```

### 3.5 Verify Data on Server

**On the server:**

```bash
ssh tvs-wages-prod

cd /var/www/tvs-wages

# Check database
ls -lh data/database/payslips.db
sqlite3 data/database/payslips.db "SELECT COUNT(*) FROM payslips;"

# Check documents
find data/documents/payslips -type f -name "*.pdf" | wc -l
find data/documents/runsheets -type f -name "*.pdf" | wc -l

# Check permissions
ls -la data/
```

### 3.6 Set Correct Permissions

```bash
# Ensure tvswages user owns all files
sudo chown -R tvswages:tvswages /var/www/tvs-wages

# Set directory permissions
find /var/www/tvs-wages/data -type d -exec chmod 755 {} \;

# Set file permissions
find /var/www/tvs-wages/data -type f -exec chmod 644 {} \;

# Make database writable
chmod 644 /var/www/tvs-wages/data/database/payslips.db
```

### 3.7 Restart Application

```bash
# Restart the service to pick up new data
sudo systemctl restart tvs-wages

# Check status
sudo systemctl status tvs-wages

# Watch logs for any errors
sudo journalctl -u tvs-wages -f
```

### 3.8 Verify Application with Data

**In your browser:**
1. Navigate to `http://your-server-ip`
2. Check Wages page - should show your payslip data
3. Check Runsheets page - should show your runsheet data
4. Check Reports page - should generate reports
5. Test all functionality

### 3.9 Setup Automated Backups

```bash
# Create backup script
nano /var/www/tvs-wages/scripts/backup_production.sh
```

Add this script:
```bash
#!/bin/bash
# Production backup script

BACKUP_DIR="/var/www/tvs-wages/data/database/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="/var/www/tvs-wages/data/database/payslips.db"

# Create backup
sqlite3 $DB_PATH ".backup '$BACKUP_DIR/payslips_$DATE.db'"

# Compress backup
gzip "$BACKUP_DIR/payslips_$DATE.db"

# Delete backups older than 30 days
find $BACKUP_DIR -name "*.db.gz" -mtime +30 -delete

echo "Backup completed: payslips_$DATE.db.gz"
```

Make it executable:
```bash
chmod +x /var/www/tvs-wages/scripts/backup_production.sh
```

Setup cron job:
```bash
# Edit crontab
crontab -e
```

Add this line (backup daily at 2 AM):
```
0 2 * * * /var/www/tvs-wages/scripts/backup_production.sh >> /var/www/tvs-wages/logs/backup.log 2>&1
```

### 3.10 Enable Gmail Auto-Sync (Optional)

**On the server:**

```bash
# Update .env file
nano /var/www/tvs-wages/.env
```

Change:
```
AUTO_SYNC_ENABLED=true
```

Restart application:
```bash
sudo systemctl restart tvs-wages
```

### ✅ Stage 3 Complete Checklist
- [ ] Local data backed up
- [ ] Database transferred to server
- [ ] Payslips transferred to server
- [ ] Runsheets transferred to server
- [ ] Gmail credentials transferred (if using)
- [ ] File permissions set correctly
- [ ] Application restarted
- [ ] Data verified in web interface
- [ ] All pages working correctly
- [ ] Automated backups configured
- [ ] Gmail auto-sync enabled (optional)

---

## Post-Deployment

### Monitoring

```bash
# Check application status
sudo systemctl status tvs-wages

# View application logs
sudo journalctl -u tvs-wages -f

# View Nginx logs
sudo tail -f /var/log/nginx/tvs-wages-access.log
sudo tail -f /var/log/nginx/tvs-wages-error.log

# Check disk space
df -h

# Check memory usage
free -h
```

### Maintenance Commands

```bash
# Restart application
sudo systemctl restart tvs-wages

# Stop application
sudo systemctl stop tvs-wages

# Start application
sudo systemctl start tvs-wages

# View service status
sudo systemctl status tvs-wages

# Manual backup
/var/www/tvs-wages/scripts/backup_production.sh

# Update application
cd /var/www/tvs-wages
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart tvs-wages
```

### SSL/HTTPS Setup (Recommended)

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
# Test renewal
sudo certbot renew --dry-run
```

---

## Troubleshooting

### Application Won't Start

```bash
# Check logs
sudo journalctl -u tvs-wages -n 50

# Check if port is in use
sudo netstat -tlnp | grep 5001

# Test manually
cd /var/www/tvs-wages
source venv/bin/activate
python3 new_web_app.py
```

### Database Errors

```bash
# Check database file exists
ls -lh /var/www/tvs-wages/data/database/payslips.db

# Check permissions
ls -la /var/www/tvs-wages/data/database/

# Test database
sqlite3 /var/www/tvs-wages/data/database/payslips.db "SELECT COUNT(*) FROM payslips;"
```

### Nginx Errors

```bash
# Test Nginx config
sudo nginx -t

# Check Nginx status
sudo systemctl status nginx

# View Nginx error log
sudo tail -f /var/log/nginx/error.log
```

---

## Quick Reference

### Important Paths
- Application: `/var/www/tvs-wages`
- Virtual Environment: `/var/www/tvs-wages/venv`
- Database: `/var/www/tvs-wages/data/database/payslips.db`
- Logs: `/var/www/tvs-wages/logs`
- Nginx Config: `/etc/nginx/sites-available/tvs-wages`
- Service File: `/etc/systemd/system/tvs-wages.service`

### Important Commands
```bash
# Connect to server
ssh tvs-wages-prod

# Restart app
sudo systemctl restart tvs-wages

# View logs
sudo journalctl -u tvs-wages -f

# Update app
cd /var/www/tvs-wages && git pull && sudo systemctl restart tvs-wages
```

---

**🎉 Deployment Complete!**

Your TVS Wages application is now running in production with:
- ✅ Secure SSH access with key authentication
- ✅ Dedicated application user
- ✅ Python virtual environment
- ✅ Systemd service for auto-restart
- ✅ Nginx reverse proxy
- ✅ All data migrated
- ✅ Automated backups
- ✅ Production-ready configuration
