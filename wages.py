#!/usr/bin/env python3
"""
Main entry point - unified interface for all payslip tools.
"""

import sys
import subprocess


def print_menu():
    print("\n" + "="*80)
    print("WAGES APP - PAYSLIP MANAGEMENT SYSTEM")
    print("="*80)
    print("\n🌐 WEB INTERFACE:")
    print("  1. Start Web Dashboard - Beautiful Bootstrap interface with charts")
    print("\n📊 QUICK ACTIONS:")
    print("  2. Quick Stats - Fast overview of earnings")
    print("  3. Query Database - Interactive search and analysis")
    print("  4. Generate Report - Comprehensive text report")
    print("  5. Export to CSV - Create spreadsheet files")
    print("\n🔧 MAINTENANCE:")
    print("  6. Extract PDFs - Process payslip PDFs (run after adding new files)")
    print("\n📖 HELP:")
    print("  7. View README")
    print("  8. View Usage Guide")
    print("  9. View Web App Guide")
    print("\n  0. Exit")
    print("\n" + "="*80)


def run_script(script_name):
    """Run a Python script."""
    try:
        subprocess.run(["python3", script_name], check=True)
    except subprocess.CalledProcessError:
        print(f"\n❌ Error running {script_name}")
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")


def view_file(filename):
    """View a text file."""
    try:
        with open(filename, 'r') as f:
            content = f.read()
            print("\n" + "="*80)
            print(content)
            print("="*80)
    except FileNotFoundError:
        print(f"\n❌ File not found: {filename}")


def main():
    """Main menu loop."""
    while True:
        print_menu()
        choice = input("\nEnter your choice: ").strip()
        
        if choice == "0":
            print("\n👋 Goodbye!\n")
            break
        elif choice == "1":
            print("\n🌐 Starting Web Dashboard...\n")
            print("📊 Open your browser to: http://localhost:5001")
            print("⏹️  Press Ctrl+C to stop the server\n")
            run_script("web_app.py")
        elif choice == "2":
            print("\n📊 Running Quick Stats...\n")
            run_script("scripts/quick_stats.py")
        elif choice == "3":
            print("\n🔍 Opening Query Tool...\n")
            run_script("scripts/query_payslips.py")
        elif choice == "4":
            print("\n📄 Generating Report...\n")
            run_script("scripts/generate_report.py")
            print("\n✅ Report saved to: output/payslip_report.txt")
        elif choice == "5":
            print("\n💾 Exporting to CSV...\n")
            run_script("scripts/export_to_csv.py")
        elif choice == "6":
            print("\n🔄 Extracting PDFs...\n")
            print("⚠️  This will process all PDF files in the PaySlips directory.")
            confirm = input("Continue? (y/n): ").strip().lower()
            if confirm == 'y':
                run_script("scripts/extract_payslips.py")
            else:
                print("Cancelled.")
        elif choice == "7":
            view_file("README.md")
        elif choice == "8":
            view_file("docs/USAGE_GUIDE.md")
        elif choice == "9":
            view_file("docs/WEB_APP_GUIDE.md")
        else:
            print("\n❌ Invalid choice. Please try again.")
        
        if choice != "0":
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!\n")
        sys.exit(0)
