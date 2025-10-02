# Wages App - Debian Deployment Guide

Complete guide to deploy the Wages App on a fresh Debian server.

## Prerequisites
- Fresh Debian installation
- Root access
- Network connectivity

---

## Step 1: Initial Server Setup

### 1.1 Update System
```bash
apt update
apt upgrade -y
```

### 1.2 Install Required Packages
```bash
apt install -y python3 python3-pip python3-venv git sqlite3 nginx supervisor
```

### 1.3 Create Application User (Optional but Recommended)
```bash
# Create a dedicated user for the app
adduser --disabled-password --gecos "" wagesapp

# Switch to the new user
su - wagesapp
```

---

## Step 2: Clone and Setup Application

### 2.1 Clone from GitHub
```bash
# If you created wagesapp user, you're already in /home/wagesapp
# Otherwise, choose a directory like /opt/wages-app

git clone https://github.com/djh-1980/wages-app.git
cd wages-app
```

### 2.2 Create Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2.3 Install Python Dependencies
```bash
pip install --upgrade pip
pip install flask PyPDF2
```

---

## Step 3: Transfer Your Data

### 3.1 Copy Database from Mac to Debian Server

**On your Mac:**
```bash
# Replace SERVER_IP with your Debian server's IP address
scp /Users/danielhanson/CascadeProjects/Wages-App/payslips.db root@SERVER_IP:/home/wagesapp/wages-app/
```

### 3.2 Copy PaySlips Folder (Optional - if you want PDFs on server)
```bash
# On your Mac
scp -r /Users/danielhanson/CascadeProjects/Wages-App/PaySlips root@SERVER_IP:/home/wagesapp/wages-app/
```

**On Debian server (if you created wagesapp user):**
```bash
# Fix ownership
chown -R wagesapp:wagesapp /home/wagesapp/wages-app
```

---

## Step 4: Configure Application for Production

### 4.1 Create Production Startup Script

**On Debian server:**
```bash
cd /home/wagesapp/wages-app
nano start_production.sh
```

**Add this content:**
```bash
#!/bin/bash
cd /home/wagesapp/wages-app
source venv/bin/activate
python3 web_app.py
```

**Make it executable:**
```bash
chmod +x start_production.sh
```

### 4.2 Update web_app.py for Production

Edit the last line of `web_app.py`:
```bash
nano web_app.py
```

Change the last line from:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

To:
```python
app.run(debug=False, host='127.0.0.1', port=5001)
```

---

## Step 5: Setup Supervisor (Auto-start & Keep Running)

### 5.1 Create Supervisor Configuration

**As root:**
```bash
nano /etc/supervisor/conf.d/wagesapp.conf
```

**Add this content:**
```ini
[program:wagesapp]
command=/home/wagesapp/wages-app/venv/bin/python3 /home/wagesapp/wages-app/web_app.py
directory=/home/wagesapp/wages-app
user=wagesapp
autostart=true
autorestart=true
stderr_logfile=/var/log/wagesapp.err.log
stdout_logfile=/var/log/wagesapp.out.log
environment=PATH="/home/wagesapp/wages-app/venv/bin"
```

### 5.2 Start the Application
```bash
supervisorctl reread
supervisorctl update
supervisorctl start wagesapp
supervisorctl status
```

---

## Step 6: Setup Nginx (Web Server)

### 6.1 Create Nginx Configuration

```bash
nano /etc/nginx/sites-available/wagesapp
```

**Add this content:**
```nginx
server {
    listen 80;
    server_name YOUR_SERVER_IP;  # Replace with your server's IP or domain

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeout for file uploads
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
    
    # Increase max upload size for PDFs
    client_max_body_size 50M;
}
```

### 6.2 Enable Site and Restart Nginx
```bash
ln -s /etc/nginx/sites-available/wagesapp /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

---

## Step 7: Setup Firewall (Optional but Recommended)

```bash
apt install -y ufw
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS (for future SSL)
ufw enable
```

---

## Step 8: Access Your Application

Open a web browser and go to:
```
http://YOUR_SERVER_IP
```

You should see your Wages App dashboard!

---

## Step 9: Add Password Protection (Recommended)

### 9.1 Install Apache Utils
```bash
apt install -y apache2-utils
```

### 9.2 Create Password File
```bash
htpasswd -c /etc/nginx/.htpasswd yourusername
# Enter password when prompted
```

### 9.3 Update Nginx Configuration
```bash
nano /etc/nginx/sites-available/wagesapp
```

**Add these lines inside the `location /` block:**
```nginx
    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
```

### 9.4 Restart Nginx
```bash
systemctl restart nginx
```

Now you'll need to enter username/password to access the app!

---

## Maintenance Commands

### Check Application Status
```bash
supervisorctl status wagesapp
```

### View Logs
```bash
tail -f /var/log/wagesapp.out.log
tail -f /var/log/wagesapp.err.log
```

### Restart Application
```bash
supervisorctl restart wagesapp
```

### Stop Application
```bash
supervisorctl stop wagesapp
```

### Update Application (when you push changes to GitHub)
```bash
su - wagesapp
cd wages-app
git pull
supervisorctl restart wagesapp
```

---

## Troubleshooting

### Application won't start
```bash
# Check logs
tail -50 /var/log/wagesapp.err.log

# Check if port is in use
netstat -tlnp | grep 5001

# Manually test
su - wagesapp
cd wages-app
source venv/bin/activate
python3 web_app.py
```

### Can't access from browser
```bash
# Check nginx status
systemctl status nginx

# Check nginx error logs
tail -50 /var/log/nginx/error.log

# Test nginx config
nginx -t
```

### Upload not working
```bash
# Check permissions
ls -la /home/wagesapp/wages-app/PaySlips/
chown -R wagesapp:wagesapp /home/wagesapp/wages-app/PaySlips/
```

---

## Security Recommendations

1. **Change SSH port** from 22 to something else
2. **Disable root SSH login** - use wagesapp user
3. **Setup SSL/HTTPS** with Let's Encrypt (free)
4. **Regular backups** of payslips.db
5. **Keep system updated**: `apt update && apt upgrade`

---

## Backup Your Data

### Backup Database
```bash
# On Debian server
cp /home/wagesapp/wages-app/payslips.db /home/wagesapp/payslips.db.backup

# Copy to your Mac
scp root@SERVER_IP:/home/wagesapp/payslips.db.backup ~/Desktop/
```

### Automated Daily Backup (Optional)
```bash
# Create backup script
nano /home/wagesapp/backup.sh
```

**Add:**
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
cp /home/wagesapp/wages-app/payslips.db /home/wagesapp/backups/payslips_$DATE.db
# Keep only last 30 days
find /home/wagesapp/backups/ -name "payslips_*.db" -mtime +30 -delete
```

**Setup cron:**
```bash
chmod +x /home/wagesapp/backup.sh
mkdir -p /home/wagesapp/backups
crontab -e -u wagesapp
```

**Add this line:**
```
0 2 * * * /home/wagesapp/backup.sh
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start app | `supervisorctl start wagesapp` |
| Stop app | `supervisorctl stop wagesapp` |
| Restart app | `supervisorctl restart wagesapp` |
| View logs | `tail -f /var/log/wagesapp.out.log` |
| Update code | `cd wages-app && git pull && supervisorctl restart wagesapp` |
| Restart nginx | `systemctl restart nginx` |

---

## Done! 🎉

Your Wages App is now running on your Debian server!

Access it at: **http://YOUR_SERVER_IP**

For any issues, check the logs or contact support.
