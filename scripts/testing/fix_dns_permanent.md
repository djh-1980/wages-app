# Fix DNS Permanently on Live Server

## Problem
`/etc/resolv.conf` gets overwritten on reboot, breaking GitHub access.

## Permanent Solutions

### Option 1: Make resolv.conf Immutable (Quick Fix)
```bash
# Add Google DNS
sudo nano /etc/resolv.conf
# Add these lines:
nameserver 8.8.8.8
nameserver 8.8.4.4

# Make it immutable (can't be changed even by system)
sudo chattr +i /etc/resolv.conf

# To undo later if needed:
# sudo chattr -i /etc/resolv.conf
```

### Option 2: Configure NetworkManager (Ubuntu/Debian)
```bash
# Edit NetworkManager config
sudo nano /etc/NetworkManager/NetworkManager.conf

# Add this section:
[main]
dns=none

# Restart NetworkManager
sudo systemctl restart NetworkManager

# Now edit resolv.conf
sudo nano /etc/resolv.conf
# Add:
nameserver 8.8.8.8
nameserver 8.8.4.4
```

### Option 3: Use systemd-resolved (Modern Systems)
```bash
# Edit resolved config
sudo nano /etc/systemd/resolved.conf

# Add these lines:
[Resolve]
DNS=8.8.8.8 8.8.4.4
FallbackDNS=1.1.1.1 1.0.0.1

# Restart service
sudo systemctl restart systemd-resolved

# Link resolv.conf
sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf
```

### Option 4: Use resolvconf (If installed)
```bash
# Edit base file
sudo nano /etc/resolvconf/resolv.conf.d/base

# Add:
nameserver 8.8.8.8
nameserver 8.8.4.4

# Update
sudo resolvconf -u
```

## Test DNS After Fix
```bash
# Test resolution
nslookup github.com
ping -c 3 github.com

# If working, try git
cd /var/www/tvs-wages
git pull origin main
```

## If DNS Still Won't Work - Alternative Approach

### Just copy the files directly via your hosting control panel:

**Files to update on live server:**

1. `scripts/sync_master.py`
2. `scripts/production/download_runsheets_gmail.py`
3. `scripts/production/import_run_sheets.py`
4. `scripts/production/extract_payslips.py`
5. `scripts/production/validate_addresses.py`
6. `app/utils/sync_logger.py`

Upload each file individually from your local machine to the same path on the live server.
