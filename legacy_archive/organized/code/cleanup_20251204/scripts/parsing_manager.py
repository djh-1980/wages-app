#!/usr/bin/env python3
"""
Parsing Manager - Command line tool for managing parsing improvements
Usage: python parsing_manager.py [command] [args]
"""

import sys
import argparse
from parsing_improvement_tracker import ParsingTracker

def show_status(tracker):
    """Show current parsing improvement status."""
    status = tracker.get_improvement_status()
    
    print("📊 PARSING IMPROVEMENT STATUS")
    print("=" * 50)
    print(f"Total Customers: {status['total_customers']}")
    print(f"Total Missing Jobs: {status['total_missing_jobs']}")
    print(f"Progress: {status['jobs_fixed']}/{status['total_missing_jobs']} jobs fixed ({status['completion_percentage']:.1f}%)")
    print(f"Status: {status['customers_fixed']} completed, {status['customers_in_progress']} in progress, {status['customers_pending']} pending")
    
    print(f"\n📈 Priority Breakdown:")
    for priority, count, jobs in status['priority_breakdown']:
        print(f"  {priority.title()}: {count} customers ({jobs} jobs)")

def show_next(tracker, limit=5):
    """Show next customers to work on."""
    customers = tracker.get_next_priority_customers(limit)
    
    print(f"🎯 NEXT {len(customers)} HIGH PRIORITY CUSTOMERS")
    print("=" * 50)
    
    for i, customer in enumerate(customers, 1):
        print(f"{i}. {customer['customer'][:60]}")
        print(f"   Missing jobs: {customer['missing_jobs']}")
        print(f"   Priority: {customer['priority']}")
        print()

def start_customer(tracker, customer_name):
    """Mark a customer as in progress."""
    tracker.update_customer_status(customer_name, 'in_progress', 
                                 notes=f"Started working on parser for {customer_name}")
    print(f"✅ Marked '{customer_name}' as IN PROGRESS")

def complete_customer(tracker, customer_name, parser_function, notes=None):
    """Mark a customer as completed."""
    if not notes:
        notes = f"Created parser function: {parser_function}"
    
    tracker.update_customer_status(customer_name, 'completed', 
                                 parser_function=parser_function, notes=notes)
    print(f"✅ Marked '{customer_name}' as COMPLETED")
    print(f"   Parser function: {parser_function}")

def skip_customer(tracker, customer_name, reason):
    """Mark a customer as skipped."""
    tracker.update_customer_status(customer_name, 'skipped', 
                                 notes=f"Skipped: {reason}")
    print(f"⏭️  Marked '{customer_name}' as SKIPPED")
    print(f"   Reason: {reason}")

def list_customers(tracker, status_filter=None):
    """List customers with optional status filter."""
    import sqlite3
    
    conn = sqlite3.connect(tracker.db_path)
    cursor = conn.cursor()
    
    query = """
        SELECT customer_name, jobs_missing_activity, priority, status, parser_function
        FROM parsing_improvements
    """
    params = []
    
    if status_filter:
        query += " WHERE status = ?"
        params.append(status_filter)
    
    query += " ORDER BY jobs_missing_activity DESC"
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    
    print(f"📋 CUSTOMERS" + (f" ({status_filter.upper()})" if status_filter else ""))
    print("=" * 50)
    
    for customer, jobs, priority, status, parser in results:
        status_icon = {"pending": "⏳", "in_progress": "🔄", "completed": "✅", "skipped": "⏭️"}.get(status, "❓")
        print(f"{status_icon} {customer[:50]}")
        print(f"   Jobs: {jobs}, Priority: {priority}, Status: {status}")
        if parser:
            print(f"   Parser: {parser}")
        print()

def main():
    parser = argparse.ArgumentParser(description="Parsing Improvement Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show current status')
    
    # Next command
    next_parser = subparsers.add_parser('next', help='Show next customers to work on')
    next_parser.add_argument('--limit', type=int, default=5, help='Number of customers to show')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Mark customer as in progress')
    start_parser.add_argument('customer', help='Customer name (partial match)')
    
    # Complete command
    complete_parser = subparsers.add_parser('complete', help='Mark customer as completed')
    complete_parser.add_argument('customer', help='Customer name (partial match)')
    complete_parser.add_argument('parser', help='Parser function name')
    complete_parser.add_argument('--notes', help='Additional notes')
    
    # Skip command
    skip_parser = subparsers.add_parser('skip', help='Mark customer as skipped')
    skip_parser.add_argument('customer', help='Customer name (partial match)')
    skip_parser.add_argument('reason', help='Reason for skipping')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List customers')
    list_parser.add_argument('--status', choices=['pending', 'in_progress', 'completed', 'skipped'], 
                           help='Filter by status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    tracker = ParsingTracker()
    
    if args.command == 'status':
        show_status(tracker)
    
    elif args.command == 'next':
        show_next(tracker, args.limit)
    
    elif args.command == 'start':
        # Find customer by partial match
        import sqlite3
        conn = sqlite3.connect(tracker.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT customer_name FROM parsing_improvements WHERE customer_name LIKE ?", 
                      (f"%{args.customer}%",))
        matches = cursor.fetchall()
        conn.close()
        
        if len(matches) == 1:
            start_customer(tracker, matches[0][0])
        elif len(matches) == 0:
            print(f"❌ No customer found matching '{args.customer}'")
        else:
            print(f"❌ Multiple customers found matching '{args.customer}':")
            for match in matches:
                print(f"   - {match[0]}")
    
    elif args.command == 'complete':
        # Find customer by partial match
        import sqlite3
        conn = sqlite3.connect(tracker.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT customer_name FROM parsing_improvements WHERE customer_name LIKE ?", 
                      (f"%{args.customer}%",))
        matches = cursor.fetchall()
        conn.close()
        
        if len(matches) == 1:
            complete_customer(tracker, matches[0][0], args.parser, args.notes)
        elif len(matches) == 0:
            print(f"❌ No customer found matching '{args.customer}'")
        else:
            print(f"❌ Multiple customers found matching '{args.customer}':")
            for match in matches:
                print(f"   - {match[0]}")
    
    elif args.command == 'skip':
        # Find customer by partial match
        import sqlite3
        conn = sqlite3.connect(tracker.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT customer_name FROM parsing_improvements WHERE customer_name LIKE ?", 
                      (f"%{args.customer}%",))
        matches = cursor.fetchall()
        conn.close()
        
        if len(matches) == 1:
            skip_customer(tracker, matches[0][0], args.reason)
        elif len(matches) == 0:
            print(f"❌ No customer found matching '{args.customer}'")
        else:
            print(f"❌ Multiple customers found matching '{args.customer}':")
            for match in matches:
                print(f"   - {match[0]}")
    
    elif args.command == 'list':
        list_customers(tracker, args.status)

if __name__ == "__main__":
    main()
