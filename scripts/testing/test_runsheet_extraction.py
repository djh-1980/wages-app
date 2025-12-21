#!/usr/bin/env python3
"""
Standalone Runsheet Extraction Testing Tool

Test and perfect runsheet parsing logic without affecting the main system.
Allows iterative testing, comparison, and quality scoring.
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.production.import_run_sheets import RunSheetImporter


class RunSheetTester:
    """Test harness for runsheet extraction."""
    
    def __init__(self):
        self.results = []
        self.test_db = "data/testing/test_runsheets.db"
        
        # Ensure test directory exists
        Path("data/testing").mkdir(parents=True, exist_ok=True)
        
    def test_single_file(self, pdf_path: str, show_details: bool = True):
        """Test extraction on a single PDF file."""
        print(f"\n{'='*80}")
        print(f"Testing: {Path(pdf_path).name}")
        print(f"{'='*80}\n")
        
        # Create importer with test database
        importer = RunSheetImporter(db_path=self.test_db)
        
        try:
            # Parse the PDF
            jobs = importer.parse_pdf_run_sheet(pdf_path)
            
            print(f"✓ Extracted {len(jobs)} jobs\n")
            
            if show_details:
                for i, job in enumerate(jobs, 1):
                    self._display_job(i, job)
            
            # Calculate quality scores
            scores = [self._calculate_quality(job) for job in jobs]
            avg_score = sum(scores) / len(scores) if scores else 0
            
            print(f"\n{'='*80}")
            print(f"QUALITY SUMMARY")
            print(f"{'='*80}")
            print(f"Average Quality Score: {avg_score:.1f}/100")
            print(f"High Quality (80+): {sum(1 for s in scores if s >= 80)} jobs")
            print(f"Medium Quality (50-79): {sum(1 for s in scores if 50 <= s < 80)} jobs")
            print(f"Low Quality (<50): {sum(1 for s in scores if s < 50)} jobs")
            print(f"{'='*80}\n")
            
            # Store results
            result = {
                'file': Path(pdf_path).name,
                'timestamp': datetime.now().isoformat(),
                'job_count': len(jobs),
                'avg_quality': avg_score,
                'jobs': jobs
            }
            self.results.append(result)
            
            return jobs
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _display_job(self, index: int, job: dict):
        """Display a single job in a readable format."""
        print(f"Job #{index}: {job.get('job_number', 'UNKNOWN')}")
        print(f"  Customer:  {job.get('customer', 'N/A')}")
        print(f"  Activity:  {job.get('activity', 'N/A')}")
        print(f"  Address:   {job.get('job_address', 'N/A')}")
        print(f"  Postcode:  {job.get('postcode', 'N/A')}")
        
        # Show quality score
        score = self._calculate_quality(job)
        quality = "HIGH" if score >= 80 else "MEDIUM" if score >= 50 else "LOW"
        print(f"  Quality:   {score}/100 ({quality})")
        print()
    
    def _calculate_quality(self, job: dict) -> int:
        """Calculate quality score for a job (0-100)."""
        score = 0
        
        # Has job number (required)
        if job.get('job_number'):
            score += 20
        
        # Has customer
        if job.get('customer') and len(job.get('customer', '')) > 3:
            score += 20
        
        # Has activity
        if job.get('activity'):
            score += 15
        
        # Has address
        if job.get('job_address') and len(job.get('job_address', '')) > 10:
            score += 20
            
            # Bonus for street indicators
            address = job.get('job_address', '').upper()
            if any(word in address for word in ['ROAD', 'STREET', 'AVENUE', 'LANE', 'DRIVE']):
                score += 5
        
        # Has postcode
        if job.get('postcode'):
            score += 15
            
            # Bonus for properly formatted postcode
            import re
            if re.match(r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s\d[A-Z]{2}$', job.get('postcode', '')):
                score += 5
        
        return min(score, 100)
    
    def compare_extractions(self, pdf_path: str, before_jobs: list, after_jobs: list):
        """Compare two extraction results to see improvements."""
        print(f"\n{'='*80}")
        print(f"COMPARISON: {Path(pdf_path).name}")
        print(f"{'='*80}\n")
        
        print(f"Before: {len(before_jobs)} jobs")
        print(f"After:  {len(after_jobs)} jobs")
        print()
        
        # Compare quality scores
        before_scores = [self._calculate_quality(job) for job in before_jobs]
        after_scores = [self._calculate_quality(job) for job in after_jobs]
        
        before_avg = sum(before_scores) / len(before_scores) if before_scores else 0
        after_avg = sum(after_scores) / len(after_scores) if after_scores else 0
        
        print(f"Average Quality:")
        print(f"  Before: {before_avg:.1f}/100")
        print(f"  After:  {after_avg:.1f}/100")
        print(f"  Change: {after_avg - before_avg:+.1f}")
        print()
        
        # Show specific improvements
        print("Quality Distribution:")
        print(f"  High (80+):   {sum(1 for s in before_scores if s >= 80)} → {sum(1 for s in after_scores if s >= 80)}")
        print(f"  Medium (50-79): {sum(1 for s in before_scores if 50 <= s < 80)} → {sum(1 for s in after_scores if 50 <= s < 80)}")
        print(f"  Low (<50):    {sum(1 for s in before_scores if s < 50)} → {sum(1 for s in after_scores if s < 50)}")
        print()
    
    def save_results(self, output_file: str = "data/testing/extraction_results.json"):
        """Save test results to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"✓ Results saved to {output_file}")
    
    def test_directory(self, directory: str, limit: int = 5):
        """Test multiple files from a directory."""
        pdf_files = list(Path(directory).glob("*.pdf"))[:limit]
        
        print(f"\nTesting {len(pdf_files)} files from {directory}\n")
        
        for pdf_file in pdf_files:
            self.test_single_file(str(pdf_file), show_details=False)
        
        # Overall summary
        if self.results:
            avg_quality = sum(r['avg_quality'] for r in self.results) / len(self.results)
            total_jobs = sum(r['job_count'] for r in self.results)
            
            print(f"\n{'='*80}")
            print(f"OVERALL SUMMARY")
            print(f"{'='*80}")
            print(f"Files tested: {len(self.results)}")
            print(f"Total jobs extracted: {total_jobs}")
            print(f"Average quality: {avg_quality:.1f}/100")
            print(f"{'='*80}\n")


def main():
    """Main test interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test runsheet extraction')
    parser.add_argument('path', help='Path to PDF file or directory')
    parser.add_argument('--details', '-d', action='store_true', help='Show detailed job information')
    parser.add_argument('--limit', '-l', type=int, default=5, help='Limit number of files to test (for directories)')
    parser.add_argument('--save', '-s', action='store_true', help='Save results to JSON')
    
    args = parser.parse_args()
    
    tester = RunSheetTester()
    
    path = Path(args.path)
    
    if path.is_file():
        # Test single file
        tester.test_single_file(str(path), show_details=args.details)
    elif path.is_dir():
        # Test directory
        tester.test_directory(str(path), limit=args.limit)
    else:
        print(f"Error: {path} is not a valid file or directory")
        return 1
    
    if args.save:
        tester.save_results()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
