#!/usr/bin/env python3
"""
Parsing Improvement Tracker
Tracks progress on improving runsheet parsing for customers with missing activities.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import json

class ParsingTracker:
    def __init__(self, db_path: str = "data/database/payslips.db"):
        self.db_path = Path(db_path)
        self.init_tracking_table()
    
    def init_tracking_table(self):
        """Initialize the parsing improvement tracking table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parsing_improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                jobs_missing_activity INTEGER NOT NULL,
                priority TEXT NOT NULL, -- high, medium, low
                status TEXT NOT NULL, -- pending, in_progress, completed, skipped
                parser_function TEXT, -- name of the parser function created
                improvement_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Parsing improvements tracking table initialized")
    
    def analyze_missing_activities(self) -> List[Dict]:
        """Analyze customers with missing activities and return prioritized list."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get customers with missing activities
        cursor.execute("""
            SELECT customer, COUNT(*) as missing_count
            FROM run_sheet_jobs 
            WHERE (customer IS NOT NULL AND customer != '') 
            AND (activity IS NULL OR activity = '')
            GROUP BY customer
            ORDER BY missing_count DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        # Prioritize based on count and customer type
        prioritized = []
        for customer, count in results:
            priority = self._determine_priority(customer, count)
            prioritized.append({
                'customer': customer,
                'missing_count': count,
                'priority': priority,
                'status': 'pending'
            })
        
        return prioritized
    
    def _determine_priority(self, customer: str, count: int) -> str:
        """Determine priority based on customer name and missing count."""
        customer_upper = customer.upper()
        
        # Skip "DO NOT INVOICE" customers (likely intentional)
        if 'DO NOT INVOICE' in customer_upper or 'NO INV' in customer_upper:
            return 'low'
        
        # High priority: Many missing jobs and common customers
        if count >= 20:
            return 'high'
        elif count >= 10:
            return 'medium'
        else:
            return 'low'
    
    def populate_tracking_table(self):
        """Populate the tracking table with current missing activity analysis."""
        customers = self.analyze_missing_activities()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute("DELETE FROM parsing_improvements")
        
        # Insert new analysis
        for customer_data in customers:
            cursor.execute("""
                INSERT INTO parsing_improvements 
                (customer_name, jobs_missing_activity, priority, status, improvement_notes)
                VALUES (?, ?, ?, ?, ?)
            """, (
                customer_data['customer'],
                customer_data['missing_count'],
                customer_data['priority'],
                customer_data['status'],
                f"Identified {customer_data['missing_count']} jobs missing activity"
            ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Populated tracking table with {len(customers)} customers")
        return customers
    
    def get_improvement_status(self) -> Dict:
        """Get current improvement status and statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_customers,
                SUM(jobs_missing_activity) as total_missing_jobs,
                SUM(CASE WHEN status = 'completed' THEN jobs_missing_activity ELSE 0 END) as jobs_fixed,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as customers_fixed,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as customers_in_progress,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as customers_pending
            FROM parsing_improvements
        """)
        
        stats = cursor.fetchone()
        
        # Priority breakdown
        cursor.execute("""
            SELECT priority, COUNT(*) as count, SUM(jobs_missing_activity) as jobs
            FROM parsing_improvements
            GROUP BY priority
            ORDER BY 
                CASE priority 
                    WHEN 'high' THEN 1 
                    WHEN 'medium' THEN 2 
                    WHEN 'low' THEN 3 
                END
        """)
        
        priority_breakdown = cursor.fetchall()
        
        # Recent progress
        cursor.execute("""
            SELECT customer_name, status, jobs_missing_activity, updated_at
            FROM parsing_improvements
            WHERE status IN ('completed', 'in_progress')
            ORDER BY updated_at DESC
            LIMIT 10
        """)
        
        recent_progress = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_customers': stats[0],
            'total_missing_jobs': stats[1],
            'jobs_fixed': stats[2],
            'customers_fixed': stats[3],
            'customers_in_progress': stats[4],
            'customers_pending': stats[5],
            'priority_breakdown': priority_breakdown,
            'recent_progress': recent_progress,
            'completion_percentage': (stats[2] / stats[1] * 100) if stats[1] > 0 else 0
        }
    
    def update_customer_status(self, customer_name: str, status: str, 
                             parser_function: str = None, notes: str = None):
        """Update the status of a customer's parsing improvement."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        update_fields = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]
        
        if parser_function:
            update_fields.append("parser_function = ?")
            params.append(parser_function)
        
        if notes:
            update_fields.append("improvement_notes = ?")
            params.append(notes)
        
        if status == 'completed':
            update_fields.append("completed_at = CURRENT_TIMESTAMP")
        
        params.append(customer_name)
        
        cursor.execute(f"""
            UPDATE parsing_improvements 
            SET {', '.join(update_fields)}
            WHERE customer_name = ?
        """, params)
        
        conn.commit()
        conn.close()
        
        print(f"✅ Updated {customer_name} status to {status}")
    
    def get_next_priority_customers(self, limit: int = 5) -> List[Dict]:
        """Get the next highest priority customers to work on."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT customer_name, jobs_missing_activity, priority, status, improvement_notes
            FROM parsing_improvements
            WHERE status = 'pending' AND priority = 'high'
            ORDER BY jobs_missing_activity DESC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'customer': row[0],
                'missing_jobs': row[1],
                'priority': row[2],
                'status': row[3],
                'notes': row[4]
            }
            for row in results
        ]
    
    def generate_report(self) -> str:
        """Generate a comprehensive progress report."""
        status = self.get_improvement_status()
        next_customers = self.get_next_priority_customers()
        
        report = f"""
# 📊 Parsing Improvement Progress Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🎯 Overall Progress
- **Total Customers**: {status['total_customers']}
- **Total Missing Jobs**: {status['total_missing_jobs']}
- **Jobs Fixed**: {status['jobs_fixed']} ({status['completion_percentage']:.1f}%)
- **Customers Fixed**: {status['customers_fixed']}
- **In Progress**: {status['customers_in_progress']}
- **Pending**: {status['customers_pending']}

## 📈 Priority Breakdown
"""
        
        for priority, count, jobs in status['priority_breakdown']:
            report += f"- **{priority.title()}**: {count} customers ({jobs} jobs)\n"
        
        report += f"""
## 🚀 Next Priority Customers (Top {len(next_customers)})
"""
        
        for i, customer in enumerate(next_customers, 1):
            report += f"{i}. **{customer['customer'][:50]}...** - {customer['missing_jobs']} jobs\n"
        
        if status['recent_progress']:
            report += "\n## 📋 Recent Progress\n"
            for customer, status_val, jobs, updated in status['recent_progress'][:5]:
                report += f"- {customer[:40]}... - {status_val} ({jobs} jobs)\n"
        
        return report

def main():
    """Main function to run parsing improvement analysis."""
    print("🔍 Parsing Improvement Tracker")
    print("=" * 50)
    
    tracker = ParsingTracker()
    
    # Populate with current data
    print("\n1. Analyzing missing activities...")
    customers = tracker.populate_tracking_table()
    
    # Generate report
    print("\n2. Generating progress report...")
    report = tracker.generate_report()
    print(report)
    
    # Save report to file
    report_file = Path("parsing_improvement_report.md")
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n✅ Report saved to {report_file}")
    
    # Show next steps
    next_customers = tracker.get_next_priority_customers(3)
    if next_customers:
        print(f"\n🎯 Next 3 customers to work on:")
        for i, customer in enumerate(next_customers, 1):
            print(f"  {i}. {customer['customer'][:60]} - {customer['missing_jobs']} jobs")

if __name__ == "__main__":
    main()
