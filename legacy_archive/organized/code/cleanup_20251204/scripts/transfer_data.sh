#!/bin/bash
# Data transfer script for TVS Wages deployment

cd /Users/danielhanson/CascadeProjects/Wages-App

echo "=== Transferring Database ==="
rsync -avz --progress \
    -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    data/database/payslips.db \
    tvswages@192.168.1.202:/var/www/tvs-wages/data/database/

echo ""
echo "=== Transferring Payslips (238 files) ==="
rsync -avz --progress \
    -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    data/documents/payslips/ \
    tvswages@192.168.1.202:/var/www/tvs-wages/data/documents/payslips/

echo ""
echo "=== Transferring Runsheets (1,685+ files - this will take a while) ==="
rsync -avz --progress \
    -e "ssh -i ~/.ssh/tvs_wages_proxmox" \
    data/documents/runsheets/ \
    tvswages@192.168.1.202:/var/www/tvs-wages/data/documents/runsheets/

echo ""
echo "=== Transfer Complete! ==="
echo "Gmail credentials already transferred ✓"
