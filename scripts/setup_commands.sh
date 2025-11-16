#!/bin/bash
# Container Setup Commands - Run these on the Proxmox container as root

echo "=== TVS Wages Container Setup ==="
echo

# Update system
echo "Step 1: Updating system..."
apt-get update && apt-get upgrade -y

# Install all required packages
echo "Step 2: Installing required packages..."
apt-get install -y \
    openssh-server \
    sudo \
    nano \
    curl \
    wget \
    git \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    sqlite3 \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev

# Create tvswages user
echo "Step 3: Creating tvswages user..."
useradd -m -s /bin/bash tvswages

# Set password
echo "Step 4: Setting password for tvswages..."
echo "Please enter password for tvswages user:"
passwd tvswages

# Add to sudo group
echo "Step 5: Adding tvswages to sudo group..."
usermod -aG sudo tvswages

# Create application directory
echo "Step 6: Creating application directory..."
mkdir -p /var/www/tvs-wages
chown tvswages:tvswages /var/www/tvs-wages

# Enable SSH service
echo "Step 7: Enabling SSH service..."
systemctl enable ssh
systemctl start ssh

echo
echo "=== Setup Complete! ==="
echo
echo "Next steps:"
echo "1. Switch to tvswages user: su - tvswages"
echo "2. Setup SSH key authentication"
echo "3. Exit and reconnect from your Mac"
