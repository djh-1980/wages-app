# Quick Start - Proxmox Deployment

Fast track deployment to your Proxmox container at **192.168.1.202**

---

## Prerequisites

- ✅ Proxmox Debian container running at 192.168.1.202
- ✅ Root access to container
- ✅ Your Mac can ping 192.168.1.202

---

## Step 1: Generate SSH Key (2 minutes)

On your Mac:

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "tvs-wages-proxmox" -f ~/.ssh/tvs_wages_proxmox

# Press Enter for no passphrase (or add one for extra security)
```

---

## Step 2: Setup Container (5 minutes)

**Access container through Proxmox web interface:**

1. Open Proxmox web interface in browser (usually https://proxmox-ip:8006)
2. Navigate to your container (192.168.1.202)
3. Click **"Console"** button
4. Login as **root** with your root password

**Run these commands in the Proxmox console:**

```bash
# Update system
apt-get update && apt-get upgrade -y

# Install essentials
apt-get install -y openssh-server sudo nano curl wget git python3 python3-pip python3-venv nginx sqlite3 build-essential libssl-dev libffi-dev python3-dev

# Create user
useradd -m -s /bin/bash tvswages

# Set password
passwd tvswages
# Enter password: tvswages123 (or your choice)

# Add to sudo
usermod -aG sudo tvswages

# Create app directory
mkdir -p /var/www/tvs-wages
chown tvswages:tvswages /var/www/tvs-wages

# Enable and start SSH
systemctl enable ssh
systemctl start ssh

# Switch to tvswages user
su - tvswages

# Setup SSH key
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys
# Paste your public key from: cat ~/.ssh/tvs_wages_proxmox.pub (on your Mac)
# Save: Ctrl+X, Y, Enter
chmod 600 ~/.ssh/authorized_keys

# Exit back to root
exit

# Exit console
exit
```

**Now test SSH from your Mac:**

```bash
ssh -i ~/.ssh/tvs_wages_proxmox tvswages@192.168.1.202
# Should connect without password!
```

---

## Step 3: Configure SSH on Mac (1 minute)

On your Mac:

```bash
# Add to SSH config
nano ~/.ssh/config
```

Add this:

```
Host tvs-wages
    HostName 192.168.1.202
    Port 22
    User tvswages
    IdentityFile ~/.ssh/tvs_wages_proxmox
```

Save and test:

```bash
ssh tvs-wages
# Should connect without password!
```

---

## Step 4: Deploy Application (5 minutes)

On your Mac:

```bash
cd /Users/danielhanson/CascadeProjects/Wages-App

# Upload code
rsync -avz --progress \
    --exclude 'data/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.git/' \
    --exclude 'venv/' \
    --exclude '.DS_Store' \
    -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    ./ \
    tvswages@192.168.1.202:/var/www/tvs-wages/
```

On the container:

```bash
ssh tvs-wages

cd /var/www/tvs-wages

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn gevent

# Create .env file
nano .env
```

Paste this:

```
SECRET_KEY=99cd2927171ddd2572fb9d52779939dde003e9bb3a63a8954e1e14bc463ba346
FLASK_ENV=production
DATABASE_PATH=/var/www/tvs-wages/data/database/payslips.db
LOG_DIR=/var/www/tvs-wages/logs
AUTO_SYNC_ENABLED=false
```

Save and continue:

```bash
# Create directories
mkdir -p data/database data/database/backups data/documents/payslips data/documents/runsheets
mkdir -p data/exports/csv data/exports/summaries data/reports
mkdir -p data/processing/queue data/processing/temp data/processing/failed
mkdir -p data/uploads/payslips data/uploads/runsheets logs

# Initialize database
python3 -c "from app.database import init_database; init_database()"

# Test app
python3 new_web_app.py
# Should start! Press Ctrl+C to stop
```

---

## Step 5: Setup Service (3 minutes)

```bash
# Create service file
sudo nano /etc/systemd/system/tvs-wages.service
```

Paste this:

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
ExecStart=/var/www/tvs-wages/venv/bin/gunicorn --bind 127.0.0.1:5001 --workers 2 --worker-class gevent --timeout 300 --access-logfile /var/www/tvs-wages/logs/access.log --error-logfile /var/www/tvs-wages/logs/error.log --log-level info new_web_app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save and enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tvs-wages
sudo systemctl start tvs-wages
sudo systemctl status tvs-wages
# Should show "active (running)"
```

---

## Step 6: Setup Nginx (2 minutes)

```bash
sudo nano /etc/nginx/sites-available/tvs-wages
```

Paste this:

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
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location /static {
        alias /var/www/tvs-wages/static;
        expires 30d;
    }
}
```

Save and enable:

```bash
sudo ln -s /etc/nginx/sites-available/tvs-wages /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## Step 7: Test! (1 minute)

Open browser on your Mac:

```
http://192.168.1.202
```

**You should see the TVS Wages app!** 🎉

---

## Step 8: Transfer Your Data (10-30 minutes)

On your Mac:

```bash
cd /Users/danielhanson/CascadeProjects/Wages-App

# Transfer database
rsync -avz --progress \
    -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    data/database/payslips.db \
    tvswages@192.168.1.202:/var/www/tvs-wages/data/database/

# Transfer payslips (238 files)
rsync -avz --progress \
    -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    data/documents/payslips/ \
    tvswages@192.168.1.202:/var/www/tvs-wages/data/documents/payslips/

# Transfer runsheets (1,685+ files - this will take longer)
rsync -avz --progress \
    -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    data/documents/runsheets/ \
    tvswages@192.168.1.202:/var/www/tvs-wages/data/documents/runsheets/

# Transfer Gmail credentials (optional)
scp -i ~/.ssh/tvs_wages_proxmox credentials.json tvswages@192.168.1.202:/var/www/tvs-wages/
scp -i ~/.ssh/tvs_wages_proxmox token.json tvswages@192.168.1.202:/var/www/tvs-wages/
```

Restart application:

```bash
ssh tvs-wages
sudo systemctl restart tvs-wages
```

Refresh browser - you should now see all your data!

---

## Step 9: Setup Automated Backups (2 minutes)

```bash
ssh tvs-wages

# Create backup script
nano /var/www/tvs-wages/scripts/backup_production.sh
```

Paste this:

```bash
#!/bin/bash
BACKUP_DIR="/var/www/tvs-wages/data/database/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="/var/www/tvs-wages/data/database/payslips.db"
mkdir -p "$BACKUP_DIR"
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/payslips_$DATE.db'"
gzip "$BACKUP_DIR/payslips_$DATE.db"
find "$BACKUP_DIR" -name "*.db.gz" -mtime +30 -delete
echo "$(date): Backup completed - payslips_$DATE.db.gz"
```

Make executable and test:

```bash
chmod +x /var/www/tvs-wages/scripts/backup_production.sh
/var/www/tvs-wages/scripts/backup_production.sh
```

Setup daily backup:

```bash
crontab -e
```

Add this line:

```
0 2 * * * /var/www/tvs-wages/scripts/backup_production.sh >> /var/www/tvs-wages/logs/backup.log 2>&1
```

---

## ✅ Done!

Your TVS Wages app is now:

- ✅ Running on Proxmox at 192.168.1.202
- ✅ Accessible from any device on your network
- ✅ Auto-starts on container reboot
- ✅ Backed up daily at 2 AM
- ✅ All your data migrated

---

## Daily Usage

### Access the App

```
http://192.168.1.202
```

### SSH to Container

```bash
ssh tvs-wages
```

### View Logs

```bash
ssh tvs-wages
sudo journalctl -u tvs-wages -f
```

### Restart App

```bash
ssh tvs-wages
sudo systemctl restart tvs-wages
```

### Update App

```bash
# On your Mac
cd /Users/danielhanson/CascadeProjects/Wages-App
rsync -avz --progress --exclude 'data/' -e "ssh -i ~/.ssh/tvs_wages_proxmox" ./ tvswages@192.168.1.202:/var/www/tvs-wages/

# On container
ssh tvs-wages
cd /var/www/tvs-wages
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart tvs-wages
```

---

## Troubleshooting

### App won't start

```bash
ssh tvs-wages
sudo journalctl -u tvs-wages -n 50
```

### Can't access via browser

```bash
ssh tvs-wages
sudo systemctl status tvs-wages
sudo systemctl status nginx
```

### Need to rebuild

```bash
ssh tvs-wages
cd /var/www/tvs-wages
source venv/bin/activate
python3 -c "from app.database import init_database; init_database()"
sudo systemctl restart tvs-wages
```

---

**Total Setup Time: ~30 minutes + data transfer time**

**🎉 Enjoy your production TVS Wages app!**
