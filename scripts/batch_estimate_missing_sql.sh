#!/bin/bash
# Batch estimate mileage for all missing dates using route optimization API

API_URL="http://localhost:5000/api/route-planning/optimize"
DB_PATH="data/database/payslips.db"

echo "============================================================"
echo "BATCH MILEAGE ESTIMATION - ALL MISSING DATES"
echo "============================================================"
echo ""

# Get all missing dates
echo "📊 Finding dates with missing mileage..."
MISSING_DATES=$(sqlite3 "$DB_PATH" "SELECT DISTINCT r.date FROM run_sheet_jobs r LEFT JOIN runsheet_daily_data m ON r.date = m.date WHERE m.mileage IS NULL AND r.status != 'deleted' GROUP BY r.date ORDER BY r.date")

if [ -z "$MISSING_DATES" ]; then
    echo "✓ No missing mileage found!"
    exit 0
fi

TOTAL=$(echo "$MISSING_DATES" | wc -l | tr -d ' ')
echo "✓ Found $TOTAL dates with missing mileage"
echo ""

SUCCESS=0
FAILED=0
COUNTER=0

# Process each date
while IFS= read -r DATE; do
    COUNTER=$((COUNTER + 1))
    
    # Get job count for this date
    JOB_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM run_sheet_jobs WHERE date = '$DATE' AND status != 'deleted'")
    
    echo "[$COUNTER/$TOTAL] $DATE ($JOB_COUNT jobs)..."
    
    # Call route optimization API
    RESPONSE=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "{\"date\": \"$DATE\", \"include_depot\": true}" \
        --max-time 30)
    
    # Check if successful
    if echo "$RESPONSE" | grep -q '"success":true'; then
        # Extract distance
        DISTANCE=$(echo "$RESPONSE" | grep -o '"total_distance_miles":[0-9.]*' | cut -d':' -f2)
        
        if [ ! -z "$DISTANCE" ]; then
            # Round up
            ROUNDED=$(echo "$DISTANCE" | awk '{print int($1) + ($1 > int($1))}')
            
            # Extract route data
            ROUTE_DATA=$(echo "$RESPONSE" | jq -c '{total_distance_miles, total_duration_minutes, total_jobs, route}')
            
            # Save to database
            sqlite3 "$DB_PATH" "INSERT INTO runsheet_daily_data (date, mileage, route_data, updated_at) VALUES ('$DATE', $ROUNDED, '$ROUTE_DATA', CURRENT_TIMESTAMP) ON CONFLICT(date) DO UPDATE SET mileage = excluded.mileage, route_data = excluded.route_data, updated_at = CURRENT_TIMESTAMP"
            
            echo "  ✓ Saved: $ROUNDED miles (from $DISTANCE)"
            SUCCESS=$((SUCCESS + 1))
        else
            echo "  ✗ Failed to extract distance"
            FAILED=$((FAILED + 1))
        fi
    else
        echo "  ✗ API error or timeout"
        FAILED=$((FAILED + 1))
    fi
    
    # Small delay
    sleep 0.5
    
done <<< "$MISSING_DATES"

echo ""
echo "============================================================"
echo "BATCH ESTIMATION COMPLETE"
echo "============================================================"
echo "✓ Success: $SUCCESS dates"
echo "✗ Failed:  $FAILED dates"
echo "📊 Total:   $TOTAL dates"
echo "============================================================"
