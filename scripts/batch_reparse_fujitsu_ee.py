#!/usr/bin/env python3
"""
Batch Re-parse Fujitsu EE Jobs
Safely re-parses all Fujitsu EE jobs using the enhanced update_parsing_only script.
Preserves status and pay data while improving addresses and activities.
"""

import subprocess
import sys
from pathlib import Path
import time

def batch_reparse_fujitsu_ee():
    """Batch re-parse all Fujitsu EE jobs."""
    
    # Read the job list
    job_file = Path('/tmp/fujitsu_ee_jobs.txt')
    if not job_file.exists():
        print("❌ Job list file not found. Run the job collection script first.")
        return False
    
    jobs = []
    with open(job_file, 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) >= 3:
                job_number, date, customer = parts[0], parts[1], parts[2]
                jobs.append((job_number, date, customer))
    
    print(f"🔧 Starting batch re-parse of {len(jobs)} Fujitsu EE jobs...")
    print(f"⚠️  This will preserve all status and pay data")
    print()
    
    # Counters
    total_jobs = len(jobs)
    processed = 0
    improved = 0
    errors = 0
    
    # Process each job
    for i, (job_number, date, customer) in enumerate(jobs, 1):
        print(f"[{i}/{total_jobs}] Processing {job_number} ({date}) - {customer[:30]}...")
        
        try:
            # Run the update_parsing_only script
            result = subprocess.run([
                'python3', 'scripts/update_parsing_only.py',
                '--job-number', job_number,
                '--date', date
            ], capture_output=True, text=True, cwd='/Users/danielhanson/CascadeProjects/Wages-App')
            
            if result.returncode == 0:
                processed += 1
                # Check if improvements were made
                if "Applying changes:" in result.stdout:
                    improved += 1
                    print(f"  ✅ Improved")
                else:
                    print(f"  ✅ No changes needed")
            else:
                errors += 1
                print(f"  ❌ Error: {result.stderr.strip()}")
                
        except Exception as e:
            errors += 1
            print(f"  ❌ Exception: {e}")
        
        # Small delay to avoid overwhelming the system
        if i % 10 == 0:
            time.sleep(0.5)
            print(f"  📊 Progress: {processed}/{total_jobs} processed, {improved} improved, {errors} errors")
            print()
    
    # Final summary
    print(f"\n🎉 Batch re-parsing completed!")
    print(f"📊 Results:")
    print(f"  Total jobs: {total_jobs}")
    print(f"  Successfully processed: {processed}")
    print(f"  Jobs improved: {improved}")
    print(f"  Errors: {errors}")
    print(f"  Success rate: {(processed/total_jobs*100):.1f}%")
    print(f"  Improvement rate: {(improved/processed*100):.1f}%" if processed > 0 else "  Improvement rate: 0%")
    
    return errors == 0

if __name__ == "__main__":
    success = batch_reparse_fujitsu_ee()
    sys.exit(0 if success else 1)
