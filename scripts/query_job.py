#!/usr/bin/env python3
"""Quick script to query job details."""

import sqlite3
import json
from pathlib import Path

db_path = Path('data/database/payslips.db')

if not db_path.exists():
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

job_number = '4206986'

# Query job_items table
print(f"\n{'='*80}")
print(f"JOB DETAILS FOR JOB NUMBER: {job_number}")
print(f"{'='*80}\n")

cursor.execute("""
    SELECT 
        j.*,
        p.tax_year,
        p.week_number,
        p.pay_date,
        p.net_payment
    FROM job_items j
    LEFT JOIN payslips p ON j.payslip_id = p.id
    WHERE j.job_number = ?
""", (job_number,))

job_in_payslip = cursor.fetchone()

if job_in_payslip:
    print("📄 FOUND IN PAYSLIPS:")
    print(f"   Job Number: {job_in_payslip['job_number']}")
    print(f"   Client: {job_in_payslip['client']}")
    print(f"   Location: {job_in_payslip['location']}")
    print(f"   Postcode: {job_in_payslip['postcode'] if 'postcode' in job_in_payslip.keys() else 'N/A'}")
    print(f"   Job Type: {job_in_payslip['job_type']}")
    print(f"   Date: {job_in_payslip['date']}")
    print(f"   Time: {job_in_payslip['time']}")
    print(f"   Units: {job_in_payslip['units']}")
    print(f"   Rate: £{job_in_payslip['rate']}")
    print(f"   Amount: £{job_in_payslip['amount']}")
    print(f"   Agency: {job_in_payslip['agency']}")
    print(f"   Tax Year: {job_in_payslip['tax_year']}")
    print(f"   Week Number: {job_in_payslip['week_number']}")
    print(f"   Pay Date: {job_in_payslip['pay_date']}")
    print(f"   Description: {job_in_payslip['description'][:100]}...")
else:
    print("❌ NOT FOUND IN PAYSLIPS")

print()

# Query run_sheet_jobs table
cursor.execute("""
    SELECT *
    FROM run_sheet_jobs
    WHERE job_number = ?
""", (job_number,))

job_in_runsheet = cursor.fetchone()

if job_in_runsheet:
    print("📋 FOUND IN RUNSHEETS:")
    print(f"   Job Number: {job_in_runsheet['job_number']}")
    print(f"   Customer: {job_in_runsheet['customer_name']}")
    print(f"   Address: {job_in_runsheet['address']}")
    print(f"   Postcode: {job_in_runsheet['postcode']}")
    print(f"   Job Type: {job_in_runsheet['job_type']}")
else:
    print("❌ NOT FOUND IN RUNSHEETS")

print(f"\n{'='*80}")

# Check if it's a discrepancy
if job_in_payslip and not job_in_runsheet:
    print("\n⚠️  DISCREPANCY: This job is in payslips but MISSING from runsheets!")
elif not job_in_payslip and job_in_runsheet:
    print("\n⚠️  DISCREPANCY: This job is in runsheets but MISSING from payslips!")
elif job_in_payslip and job_in_runsheet:
    print("\n✅ MATCHED: This job exists in both payslips and runsheets")
else:
    print("\n❓ NOT FOUND: This job doesn't exist in either payslips or runsheets")

print()

conn.close()
