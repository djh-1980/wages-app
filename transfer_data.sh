#!/bin/bash
# Transfer data to production server

set -e

echo "=================================="
echo "TVS Wages App - Data Transfer"
echo "=================================="
echo ""

# Configuration
SERVER_IP="192.168.4.202"
SERVER_USER="admin"
APP_DIR="/opt/tvstcms"
LOCAL_DIR="/Users/danielhanson/CascadeProjects/Wages-App"

echo "Target: $SERVER_USER@$SERVER_IP:$APP_DIR"
echo ""

# Step 1: Transfer database
echo "Step 1: Transferring database..."
if [ -f "$LOCAL_DIR/data/database/payslips.db" ]; then
    rsync -avz --progress \
        $LOCAL_DIR/data/database/payslips.db \
        $SERVER_USER@$SERVER_IP:$APP_DIR/data/database/
    echo "✓ Database transferred"
else
    echo "⚠ No database found at $LOCAL_DIR/data/database/payslips.db"
fi
echo ""

# Step 2: Transfer payslips
echo "Step 2: Transferring payslips..."
if [ -d "$LOCAL_DIR/data/documents/payslips" ]; then
    PAYSLIP_COUNT=$(find $LOCAL_DIR/data/documents/payslips -type f -name "*.pdf" | wc -l)
    echo "Found $PAYSLIP_COUNT payslip files"
    
    rsync -avz --progress \
        $LOCAL_DIR/data/documents/payslips/ \
        $SERVER_USER@$SERVER_IP:$APP_DIR/data/documents/payslips/
    echo "✓ Payslips transferred"
else
    echo "⚠ No payslips directory found"
fi
echo ""

# Step 3: Transfer runsheets
echo "Step 3: Transferring runsheets..."
if [ -d "$LOCAL_DIR/data/documents/runsheets" ]; then
    RUNSHEET_COUNT=$(find $LOCAL_DIR/data/documents/runsheets -type f -name "*.pdf" | wc -l)
    echo "Found $RUNSHEET_COUNT runsheet files"
    
    rsync -avz --progress \
        $LOCAL_DIR/data/documents/runsheets/ \
        $SERVER_USER@$SERVER_IP:$APP_DIR/data/documents/runsheets/
    echo "✓ Runsheets transferred"
else
    echo "⚠ No runsheets directory found"
fi
echo ""

# Step 4: Transfer Gmail credentials (if they exist)
echo "Step 4: Transferring Gmail credentials..."
if [ -f "$LOCAL_DIR/credentials.json" ]; then
    scp $LOCAL_DIR/credentials.json $SERVER_USER@$SERVER_IP:$APP_DIR/
    echo "✓ credentials.json transferred"
else
    echo "⚠ No credentials.json found"
fi

if [ -f "$LOCAL_DIR/token.json" ]; then
    scp $LOCAL_DIR/token.json $SERVER_USER@$SERVER_IP:$APP_DIR/
    echo "✓ token.json transferred"
else
    echo "⚠ No token.json found"
fi
echo ""

# Step 5: Set permissions on server
echo "Step 5: Setting permissions on server..."
ssh $SERVER_USER@$SERVER_IP << ENDSSH
cd $APP_DIR
sudo chown -R $SERVER_USER:$SERVER_USER data/
chmod 755 data
chmod 644 data/database/payslips.db 2>/dev/null || true
find data -type d -exec chmod 755 {} \;
find data -type f -exec chmod 644 {} \;
echo "✓ Permissions set"
ENDSSH
echo ""

# Step 6: Restart application
echo "Step 6: Restarting application..."
ssh $SERVER_USER@$SERVER_IP "sudo systemctl restart tvs-wages"
echo "✓ Application restarted"
echo ""

# Step 7: Verify data
echo "Step 7: Verifying data on server..."
ssh $SERVER_USER@$SERVER_IP << ENDSSH
cd $APP_DIR

echo "Database:"
if [ -f data/database/payslips.db ]; then
    DB_SIZE=\$(du -h data/database/payslips.db | cut -f1)
    echo "  ✓ payslips.db (\$DB_SIZE)"
    
    # Count records
    PAYSLIP_COUNT=\$(sqlite3 data/database/payslips.db "SELECT COUNT(*) FROM payslips;" 2>/dev/null || echo "0")
    JOB_COUNT=\$(sqlite3 data/database/payslips.db "SELECT COUNT(*) FROM run_sheet_jobs;" 2>/dev/null || echo "0")
    echo "  - Payslips: \$PAYSLIP_COUNT"
    echo "  - Jobs: \$JOB_COUNT"
else
    echo "  ✗ Database not found"
fi

echo ""
echo "Documents:"
PAYSLIP_FILES=\$(find data/documents/payslips -type f -name "*.pdf" 2>/dev/null | wc -l)
RUNSHEET_FILES=\$(find data/documents/runsheets -type f -name "*.pdf" 2>/dev/null | wc -l)
echo "  - Payslips: \$PAYSLIP_FILES PDFs"
echo "  - Runsheets: \$RUNSHEET_FILES PDFs"
ENDSSH
echo ""

echo "=================================="
echo "✓ Data Transfer Complete!"
echo "=================================="
echo ""
echo "Access your application at:"
echo "  http://$SERVER_IP"
echo ""
echo "Check application logs:"
echo "  ssh $SERVER_USER@$SERVER_IP 'sudo journalctl -u tvs-wages -f'"
echo ""
