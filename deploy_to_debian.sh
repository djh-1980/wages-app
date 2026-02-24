#!/bin/bash
# Quick deployment script for Debian container at 192.168.4.202
# User: admin

set -e  # Exit on error

echo "=================================="
echo "TVS Wages App - Debian Deployment"
echo "=================================="
echo ""

# Configuration
SERVER_IP="192.168.4.202"
SERVER_USER="admin"
APP_DIR="/opt/tvstcms"
LOCAL_DIR="/Users/danielhanson/CascadeProjects/Wages-App"

echo "Target: $SERVER_USER@$SERVER_IP"
echo "App Directory: $APP_DIR"
echo ""

# Step 1: Test SSH connection
echo "Step 1: Testing SSH connection..."
if ssh -o ConnectTimeout=5 $SERVER_USER@$SERVER_IP "echo 'SSH connection successful'"; then
    echo "✓ SSH connection working"
else
    echo "✗ SSH connection failed"
    echo "Please ensure:"
    echo "  1. Debian container is running"
    echo "  2. SSH server is installed: sudo apt-get install openssh-server"
    echo "  3. SSH service is running: sudo systemctl start ssh"
    echo "  4. You can connect: ssh $SERVER_USER@$SERVER_IP"
    exit 1
fi
echo ""

# Step 2: Install system dependencies
echo "Step 2: Installing system dependencies on server..."
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
sudo apt-get update
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
    python3-dev \
    rsync
echo "✓ System dependencies installed"
ENDSSH
echo ""

# Step 3: Create application directory
echo "Step 3: Creating application directory..."
ssh $SERVER_USER@$SERVER_IP "sudo mkdir -p $APP_DIR && sudo chown $SERVER_USER:$SERVER_USER $APP_DIR"
echo "✓ Application directory created"
echo ""

# Step 4: Transfer application files
echo "Step 4: Transferring application files..."
echo "This may take a few minutes..."
rsync -avz --progress \
    --exclude 'data/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.git/' \
    --exclude 'venv/' \
    --exclude '*.log' \
    --exclude '.DS_Store' \
    $LOCAL_DIR/ \
    $SERVER_USER@$SERVER_IP:$APP_DIR/
echo "✓ Application files transferred"
echo ""

# Step 5: Setup Python environment and install dependencies
echo "Step 5: Setting up Python environment..."
ssh $SERVER_USER@$SERVER_IP << ENDSSH
cd $APP_DIR

# Create virtual environment
python3 -m venv venv

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn gevent

echo "✓ Python environment setup complete"
ENDSSH
echo ""

# Step 6: Create required directories
echo "Step 6: Creating required directories..."
ssh $SERVER_USER@$SERVER_IP << ENDSSH
cd $APP_DIR

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
mkdir -p logs

# Set permissions
chmod 755 data logs

echo "✓ Directories created"
ENDSSH
echo ""

# Step 7: Create .env file
echo "Step 7: Creating .env configuration..."
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
cat > /opt/tvstcms/.env << 'EOF'
# Flask Configuration
SECRET_KEY=99cd2927171ddd2572fb9d52779939dde003e9bb3a63a8954e1e14bc463ba346
FLASK_ENV=production

# Database Configuration
DATABASE_PATH=/opt/tvstcms/data/database/payslips.db
BACKUP_DIR=/opt/tvstcms/data/database/backups
BACKUP_RETENTION_DAYS=30

# Logging
LOG_LEVEL=INFO
LOG_DIR=/opt/tvstcms/logs

# Auto-sync (disable initially)
AUTO_SYNC_ENABLED=false

# Feature Flags
FEATURE_ADVANCED_ANALYTICS=true
FEATURE_ROUTE_OPTIMIZATION=true
FEATURE_PREDICTIVE_ANALYTICS=true
FEATURE_DATA_VALIDATION=true
FEATURE_INTELLIGENT_SYNC=false
EOF
echo "✓ .env file created"
ENDSSH
echo ""

# Step 8: Initialize database
echo "Step 8: Initializing database..."
ssh $SERVER_USER@$SERVER_IP << ENDSSH
cd $APP_DIR
source venv/bin/activate
python3 -c "from app.database import init_database; init_database()"
echo "✓ Database initialized"
ENDSSH
echo ""

# Step 9: Create systemd service
echo "Step 9: Creating systemd service..."
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
sudo tee /etc/systemd/system/tvs-wages.service > /dev/null << 'EOF'
[Unit]
Description=TVS Wages Application
After=network.target

[Service]
Type=notify
User=admin
Group=admin
WorkingDirectory=/opt/tvstcms
Environment="PATH=/opt/tvstcms/venv/bin"
ExecStart=/opt/tvstcms/venv/bin/gunicorn \
    --bind 127.0.0.1:5001 \
    --workers 2 \
    --worker-class gevent \
    --timeout 300 \
    --access-logfile /opt/tvstcms/logs/access.log \
    --error-logfile /opt/tvstcms/logs/error.log \
    --log-level info \
    new_web_app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable tvs-wages
sudo systemctl start tvs-wages
echo "✓ Systemd service created and started"
ENDSSH
echo ""

# Step 10: Configure Nginx
echo "Step 10: Configuring Nginx..."
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
sudo tee /etc/nginx/sites-available/tvs-wages > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location /static {
        alias /opt/tvstcms/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    access_log /var/log/nginx/tvs-wages-access.log;
    error_log /var/log/nginx/tvs-wages-error.log;
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/tvs-wages /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

echo "✓ Nginx configured and started"
ENDSSH
echo ""

# Step 11: Check service status
echo "Step 11: Checking service status..."
ssh $SERVER_USER@$SERVER_IP << ENDSSH
echo "Application Status:"
sudo systemctl status tvs-wages --no-pager | head -15

echo ""
echo "Nginx Status:"
sudo systemctl status nginx --no-pager | head -10
ENDSSH
echo ""

echo "=================================="
echo "✓ Deployment Complete!"
echo "=================================="
echo ""
echo "Your application is now running at:"
echo "  http://$SERVER_IP"
echo ""
echo "Useful commands:"
echo "  - View logs: ssh $SERVER_USER@$SERVER_IP 'sudo journalctl -u tvs-wages -f'"
echo "  - Restart app: ssh $SERVER_USER@$SERVER_IP 'sudo systemctl restart tvs-wages'"
echo "  - Check status: ssh $SERVER_USER@$SERVER_IP 'sudo systemctl status tvs-wages'"
echo ""
echo "Next steps:"
echo "  1. Open http://$SERVER_IP in your browser"
echo "  2. Transfer your data using: ./transfer_data.sh"
echo "  3. Configure Gmail credentials if needed"
echo ""
