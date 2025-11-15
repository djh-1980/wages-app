# TVS Wages - Proxmox Debian Container Deployment

Deployment guide for your Proxmox Debian container at **192.168.1.202**

---

## Your Setup

- **Container Type**: Proxmox Debian LXC
- **IP Address**: 192.168.1.202
- **Network**: Local network (192.168.1.x)

---

## Stage 1: Container & SSH Setup

### 1.1 Connect to Container

```bash
# From your local machine
ssh root@192.168.1.202
```

If you get a connection refused, SSH might not be installed yet.

### 1.2 Install SSH Server (if needed)

```bash
# Update system first
apt-get update && apt-get upgrade -y

# Install SSH server
apt-get install -y openssh-server sudo nano curl wget git

# Start SSH service
systemctl start ssh
systemctl enable ssh

# Check SSH is running
systemctl status ssh
```

### 1.3 Create Application User

```bash
# Create user 'tvswages'
useradd -m -s /bin/bash tvswages

# Set password
passwd tvswages
# Enter a secure password when prompted

# Add to sudo group
usermod -aG sudo tvswages

# Create application directory
mkdir -p /var/www/tvs-wages
chown tvswages:tvswages /var/www/tvs-wages
```

### 1.4 Setup SSH Key Authentication

**On your Mac:**

```bash
# Generate SSH key pair
ssh-keygen -t ed25519 -C "tvs-wages-proxmox" -f ~/.ssh/tvs_wages_proxmox

# Copy public key to container
ssh-copy-id -i ~/.ssh/tvs_wages_proxmox.pub tvswages@192.168.1.202

# Test connection
ssh -i ~/.ssh/tvs_wages_proxmox tvswages@192.168.1.202
```

**Alternative manual method:**

```bash
# On your Mac - copy the public key
cat ~/.ssh/tvs_wages_proxmox.pub

# On the container (as tvswages user)
su - tvswages
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys
# Paste your public key, save (Ctrl+X, Y, Enter)
chmod 600 ~/.ssh/authorized_keys
```

### 1.5 Configure SSH for Easy Access

**On your Mac:**

```bash
# Edit SSH config
nano ~/.ssh/config
```

Add this configuration:

```
Host tvs-wages
    HostName 192.168.1.202
    Port 22
    User tvswages
    IdentityFile ~/.ssh/tvs_wages_proxmox
    IdentitiesOnly yes
```

Now you can connect with just:

```bash
ssh tvs-wages
```

### 1.6 Secure SSH (Optional but Recommended)

**On the container (as root or with sudo):**

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

### ✅ Stage 1 Complete

Test your connection:

```bash
# From your Mac
ssh tvs-wages

# Should connect without password
```

---

## Stage 2: Install Application

### 2.1 Connect to Container

```bash
ssh tvs-wages
```

### 2.2 Install System Dependencies

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python and dependencies
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    sqlite3 \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev

# Verify Python version
python3 --version
# Should be Python 3.9 or higher
```

### 2.3 Upload Application Code

**Option A: Using rsync (Recommended)**

From your Mac:

```bash
cd /Users/danielhanson/CascadeProjects/Wages-App

# Sync code to container
rsync -avz --progress \
    --exclude 'data/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.git/' \
    --exclude 'venv/' \
    --exclude '.DS_Store' \
    --exclude '*.log' \
    -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    ./ \
    tvswages@192.168.1.202:/var/www/tvs-wages/
```

**Option B: Using Git**

On the container:

```bash
cd /var/www/tvs-wages
git clone https://github.com/yourusername/wages-app.git .
```

### 2.4 Setup Python Virtual Environment

```bash
cd /var/www/tvs-wages

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install production server
pip install gunicorn gevent
```

### 2.5 Create .env File

```bash
cd /var/www/tvs-wages
nano .env
```

Add this configuration:

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

# Auto-sync (disable initially)
AUTO_SYNC_ENABLED=false

# Feature Flags
FEATURE_ADVANCED_ANALYTICS=true
FEATURE_ROUTE_OPTIMIZATION=true
FEATURE_PREDICTIVE_ANALYTICS=true
FEATURE_DATA_VALIDATION=true
FEATURE_INTELLIGENT_SYNC=false
```

Save and exit (Ctrl+X, Y, Enter)

### 2.6 Create Directory Structure

```bash
cd /var/www/tvs-wages

# Create all required directories
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
mkdir -p logs

# Set permissions
chmod 755 data logs
```

### 2.7 Initialize Database

```bash
cd /var/www/tvs-wages
source venv/bin/activate

# Initialize database
python3 -c "from app.database import init_database; init_database()"

# Verify database created
ls -lh data/database/payslips.db
```

### 2.8 Test Application

```bash
# Test run
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

### 2.9 Create Systemd Service

```bash
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

# Enable service
sudo systemctl enable tvs-wages

# Start service
sudo systemctl start tvs-wages

# Check status
sudo systemctl status tvs-wages

# Should show "active (running)"
```

### 2.10 Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/tvs-wages
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name 192.168.1.202;

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

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Should show "syntax is ok" and "test is successful"

# Restart Nginx
sudo systemctl restart nginx

# Enable Nginx to start on boot
sudo systemctl enable nginx
```

### 2.11 Configure Firewall (Optional)

```bash
# Install UFW if not installed
sudo apt-get install -y ufw

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS (for future)
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### 2.12 Test Access

**From your Mac, open browser:**

```
http://192.168.1.202
```

You should see the TVS Wages application!

### ✅ Stage 2 Complete

Application is now running and accessible at: **http://192.168.1.202**

---

## Stage 3: Migrate Data

### 3.1 Transfer Database

**From your Mac:**

```bash
cd /Users/danielhanson/CascadeProjects/Wages-App

# Copy database
scp -i ~/.ssh/tvs_wages_proxmox \
    data/database/payslips.db \
    tvswages@192.168.1.202:/var/www/tvs-wages/data/database/

# Or using rsync (better for large files)
rsync -avz --progress \
    -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    data/database/payslips.db \
    tvswages@192.168.1.202:/var/www/tvs-wages/data/database/
```

### 3.2 Transfer Payslips

```bash
# This will take a while - 238 PDFs
rsync -avz --progress \
    -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    data/documents/payslips/ \
    tvswages@192.168.1.202:/var/www/tvs-wages/data/documents/payslips/
```

### 3.3 Transfer Runsheets

```bash
# This will take longer - 1,685+ PDFs
rsync -avz --progress \
    -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    data/documents/runsheets/ \
    tvswages@192.168.1.202:/var/www/tvs-wages/data/documents/runsheets/
```

### 3.4 Transfer Gmail Credentials (Optional)

```bash
# Only if you want Gmail sync on the server
scp -i ~/.ssh/tvs_wages_proxmox \
    credentials.json \
    tvswages@192.168.1.202:/var/www/tvs-wages/

scp -i ~/.ssh/tvs_wages_proxmox \
    token.json \
    tvswages@192.168.1.202:/var/www/tvs-wages/
```

### 3.5 Verify Data on Server

**On the container:**

```bash
ssh tvs-wages

cd /var/www/tvs-wages

# Check database
ls -lh data/database/payslips.db
sqlite3 data/database/payslips.db "SELECT COUNT(*) FROM payslips;"

# Check payslips
find data/documents/payslips -type f -name "*.pdf" | wc -l

# Check runsheets
find data/documents/runsheets -type f -name "*.pdf" | wc -l
```

### 3.6 Set Permissions

```bash
# Ensure correct ownership
sudo chown -R tvswages:tvswages /var/www/tvs-wages

# Set directory permissions
find /var/www/tvs-wages/data -type d -exec chmod 755 {} \;

# Set file permissions
find /var/www/tvs-wages/data -type f -exec chmod 644 {} \;
```

### 3.7 Restart Application

```bash
# Restart service
sudo systemctl restart tvs-wages

# Check status
sudo systemctl status tvs-wages

# Watch logs
sudo journalctl -u tvs-wages -f
# Press Ctrl+C to stop watching
```

### 3.8 Verify in Browser

**Open browser to:** http://192.168.1.202

- Check Wages page - should show all payslips
- Check Runsheets page - should show all runsheets
- Check Reports page - should generate reports
- Test all functionality

### 3.9 Setup Automated Backups

**On the container:**

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

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Create backup
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/payslips_$DATE.db'"

# Compress backup
gzip "$BACKUP_DIR/payslips_$DATE.db"

# Delete backups older than 30 days
find "$BACKUP_DIR" -name "*.db.gz" -mtime +30 -delete

echo "$(date): Backup completed - payslips_$DATE.db.gz"
```

Make it executable:

```bash
chmod +x /var/www/tvs-wages/scripts/backup_production.sh

# Test it
/var/www/tvs-wages/scripts/backup_production.sh
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

### ✅ Stage 3 Complete

All data is now on the server and application is fully functional!

---

## Quick Reference

### Connection

```bash
# SSH to container
ssh tvs-wages

# Or full command
ssh -i ~/.ssh/tvs_wages_proxmox tvswages@192.168.1.202
```

### Application Management

```bash
# Restart application
sudo systemctl restart tvs-wages

# Stop application
sudo systemctl stop tvs-wages

# Start application
sudo systemctl start tvs-wages

# Check status
sudo systemctl status tvs-wages

# View logs
sudo journalctl -u tvs-wages -f

# View last 50 lines
sudo journalctl -u tvs-wages -n 50
```

### File Transfer

```bash
# Upload file
scp -i ~/.ssh/tvs_wages_proxmox \
    local-file.txt \
    tvswages@192.168.1.202:/var/www/tvs-wages/

# Download file
scp -i ~/.ssh/tvs_wages_proxmox \
    tvswages@192.168.1.202:/var/www/tvs-wages/remote-file.txt \
    ./

# Sync directory
rsync -avz --progress \
    -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    local-dir/ \
    tvswages@192.168.1.202:/var/www/tvs-wages/remote-dir/
```

### Using the Quick Deploy Script

```bash
# From your Mac
cd /Users/danielhanson/CascadeProjects/Wages-App

# Update SSH config in the script
export SSH_KEY="$HOME/.ssh/tvs_wages_proxmox"
export SSH_HOST="tvs-wages"

# Run deployment
./scripts/deployment/quick_deploy.sh --code
```

### Important Paths

- **Application**: `/var/www/tvs-wages`
- **Database**: `/var/www/tvs-wages/data/database/payslips.db`
- **Logs**: `/var/www/tvs-wages/logs`
- **Backups**: `/var/www/tvs-wages/data/database/backups`
- **Nginx Config**: `/etc/nginx/sites-available/tvs-wages`
- **Service File**: `/etc/systemd/system/tvs-wages.service`

### Access URLs

- **Application**: http://192.168.1.202
- **From local network**: Any device on 192.168.1.x network can access

---

## Next Steps (Optional)

### 1. Setup Domain Name

If you have a local DNS server or want to use a domain:

```bash
# Edit /etc/hosts on your Mac
sudo nano /etc/hosts

# Add this line
192.168.1.202    tvs-wages.local

# Now you can access via
http://tvs-wages.local
```

### 2. Enable Gmail Auto-Sync

```bash
# On the container
nano /var/www/tvs-wages/.env

# Change to
AUTO_SYNC_ENABLED=true

# Restart
sudo systemctl restart tvs-wages
```

### 3. Monitor Resources

```bash
# Check disk space
df -h

# Check memory
free -h

# Check CPU
top

# Check container resources in Proxmox web interface
```

---

## Troubleshooting

### Can't Connect via SSH

```bash
# Check if container is running in Proxmox
# Check if SSH service is running
ssh root@192.168.1.202
systemctl status ssh
```

### Application Won't Start

```bash
# Check logs
sudo journalctl -u tvs-wages -n 100

# Test manually
cd /var/www/tvs-wages
source venv/bin/activate
python3 new_web_app.py
```

### Can't Access via Browser

```bash
# Check if Nginx is running
sudo systemctl status nginx

# Check if application is running
sudo systemctl status tvs-wages

# Check if port 80 is open
sudo netstat -tlnp | grep :80

# Test locally on container
curl http://localhost
```

---

**🎉 Your TVS Wages app is now running on Proxmox at 192.168.1.202!**
