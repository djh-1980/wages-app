#!/usr/bin/env python3
"""
Import mileage data from CSV file.
Supports various CSV formats and updates the runsheet_daily_data table.
"""

import csv
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
import argparse

# Add parent directory to path to import database utilities
sys.path.append(str(Path(__file__).parent.parent))
from app.database import get_db_connection, DB_PATH

def parse_date(date_str):
    """Parse date string in various formats."""
    date_formats = [
        '%A, %d %B %Y',  # Tuesday, 5 April 2022
        '%d/%m/%Y',      # DD/MM/YYYY
        '%Y-%m-%d',      # YYYY-MM-DD
        '%m/%d/%Y',      # MM/DD/YYYY
        '%d-%m-%Y',      # DD-MM-YYYY
        '%Y/%m/%d',      # YYYY/MM/DD
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime('%d/%m/%Y')  # Convert to DD/MM/YYYY format
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date: {date_str}")

def import_mileage_csv(csv_file, date_column='date', mileage_column='mileage', fuel_cost_column=None, dry_run=False):
    """Import mileage data from CSV file."""
    
    if not Path(csv_file).exists():
        print(f"❌ Error: CSV file not found: {csv_file}")
        return False
    
    print(f"📁 Reading CSV file: {csv_file}")
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            # Try to detect delimiter
            sample = f.read(1024)
            f.seek(0)
            
            delimiter = ','
            if ';' in sample and sample.count(';') > sample.count(','):
                delimiter = ';'
            elif '\t' in sample:
                delimiter = '\t'
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            # Clean up column names (strip whitespace and BOM)
            cleaned_fieldnames = [col.strip().lstrip('\ufeff') for col in reader.fieldnames]
            fieldname_mapping = {col.strip().lstrip('\ufeff'): col for col in reader.fieldnames}
            
            # Check if required columns exist
            if date_column not in cleaned_fieldnames:
                print(f"❌ Error: Date column '{date_column}' not found in CSV")
                print(f"Available columns: {', '.join(reader.fieldnames)}")
                return False
            
            if mileage_column not in cleaned_fieldnames:
                print(f"❌ Error: Mileage column '{mileage_column}' not found in CSV")
                print(f"Available columns: {', '.join(cleaned_fieldnames)}")
                return False
            
            print(f"✓ Found columns: {', '.join(cleaned_fieldnames)}")
            print(f"✓ Using date column: '{date_column}'")
            print(f"✓ Using mileage column: '{mileage_column}'")
            
            if fuel_cost_column and fuel_cost_column in cleaned_fieldnames:
                print(f"✓ Using fuel cost column: '{fuel_cost_column}'")
            elif fuel_cost_column:
                print(f"⚠️  Fuel cost column '{fuel_cost_column}' not found, skipping fuel costs")
                fuel_cost_column = None
            
            records = []
            errors = []
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is header
                try:
                    # Parse date (use original column name with whitespace)
                    date_str = row[fieldname_mapping[date_column]].strip()
                    if not date_str:
                        continue  # Skip empty dates
                    
                    parsed_date = parse_date(date_str)
                    
                    # Parse mileage (use original column name with whitespace)
                    mileage_str = row[fieldname_mapping[mileage_column]].strip()
                    if not mileage_str:
                        continue  # Skip empty mileage
                    
                    mileage = float(mileage_str)
                    
                    # Parse fuel cost if available
                    fuel_cost = None
                    if fuel_cost_column and row[fieldname_mapping[fuel_cost_column]].strip():
                        fuel_cost = float(row[fieldname_mapping[fuel_cost_column]].strip())
                    
                    records.append({
                        'date': parsed_date,
                        'mileage': mileage,
                        'fuel_cost': fuel_cost,
                        'row_num': row_num
                    })
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {e}")
            
            print(f"\n📊 Processing Results:")
            print(f"✓ Valid records: {len(records)}")
            if errors:
                print(f"⚠️  Errors: {len(errors)}")
                for error in errors[:5]:  # Show first 5 errors
                    print(f"   {error}")
                if len(errors) > 5:
                    print(f"   ... and {len(errors) - 5} more errors")
            
            if not records:
                print("❌ No valid records found to import")
                return False
            
            if dry_run:
                print(f"\n🔍 DRY RUN - Would import {len(records)} records:")
                for record in records[:5]:  # Show first 5 records
                    fuel_info = f", Fuel: £{record['fuel_cost']:.2f}" if record['fuel_cost'] is not None else ""
                    print(f"   {record['date']}: {record['mileage']} miles{fuel_info}")
                if len(records) > 5:
                    print(f"   ... and {len(records) - 5} more records")
                return True
            
            # Import to database
            print(f"\n💾 Importing to database...")
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                imported = 0
                updated = 0
                
                for record in records:
                    try:
                        # Check if record already exists
                        cursor.execute(
                            "SELECT mileage, fuel_cost FROM runsheet_daily_data WHERE date = ?",
                            (record['date'],)
                        )
                        existing = cursor.fetchone()
                        
                        if existing:
                            # Update existing record
                            cursor.execute("""
                                UPDATE runsheet_daily_data 
                                SET mileage = COALESCE(?, mileage),
                                    fuel_cost = COALESCE(?, fuel_cost),
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE date = ?
                            """, (record['mileage'], record['fuel_cost'], record['date']))
                            updated += 1
                        else:
                            # Insert new record
                            cursor.execute("""
                                INSERT INTO runsheet_daily_data (date, mileage, fuel_cost, updated_at)
                                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                            """, (record['date'], record['mileage'], record['fuel_cost']))
                            imported += 1
                            
                    except Exception as e:
                        errors.append(f"Database error for {record['date']}: {e}")
                
                conn.commit()
            
            print(f"\n✅ Import Complete!")
            print(f"📈 New records: {imported}")
            print(f"🔄 Updated records: {updated}")
            
            if errors:
                print(f"⚠️  Final errors: {len(errors)}")
                for error in errors:
                    print(f"   {error}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Import mileage data from CSV file')
    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument('--date-column', default='date', help='Name of date column (default: date)')
    parser.add_argument('--mileage-column', default='mileage', help='Name of mileage column (default: mileage)')
    parser.add_argument('--fuel-cost-column', help='Name of fuel cost column (optional)')
    parser.add_argument('--dry-run', action='store_true', help='Preview import without making changes')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MILEAGE CSV IMPORTER")
    print("=" * 60)
    
    success = import_mileage_csv(
        csv_file=args.csv_file,
        date_column=args.date_column,
        mileage_column=args.mileage_column,
        fuel_cost_column=args.fuel_cost_column,
        dry_run=args.dry_run
    )
    
    if success:
        print("\n🎉 Import completed successfully!")
    else:
        print("\n💥 Import failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
