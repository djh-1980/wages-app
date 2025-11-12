#!/usr/bin/env python3
"""
Quick statistics using the new refactored architecture.
Updated to use the new models and services.
"""

import sys
import os

# Add the parent directory to the path to import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.payslip import PayslipModel
from app.models.runsheet import RunsheetModel
from app.services.payslip_service import PayslipService
from app.services.report_service import ReportService
from app.database import init_database


def display_quick_stats():
    """Display comprehensive quick statistics using new architecture."""
    print("\n" + "="*80)
    print("QUICK STATISTICS - REFACTORED ARCHITECTURE")
    print("="*80)
    
    try:
        # Initialize database
        init_database()
        
        # Get enhanced payslip summary
        print("\n📊 PAYSLIP SUMMARY")
        print("-" * 40)
        
        summary = PayslipService.get_dashboard_summary()
        
        if summary['overall']['total_payslips'] == 0:
            print("❌ No payslips found in database.")
        else:
            print(f"📈 Total Payslips: {summary['overall']['total_payslips']}")
            print(f"💰 Total Earnings: £{summary['overall']['total_earnings']:,.2f}")
            print(f"📅 Tax Years: {summary['overall']['tax_years']}")
            print(f"📊 Average Weekly: £{summary['overall']['avg_weekly']:,.2f}")
            
            if 'performance' in summary:
                trend = summary['performance']['trend_direction']
                percentage = summary['performance']['trend_percentage']
                arrow = "↗️" if trend == "up" else "↘️" if trend == "down" else "➡️"
                print(f"📈 Trend: {arrow} {percentage}% {trend}")
        
        # Get runsheet summary
        print("\n🗂️ RUNSHEET SUMMARY")
        print("-" * 40)
        
        runsheet_summary = RunsheetModel.get_summary()
        
        if runsheet_summary['overall']['total_jobs'] == 0:
            print("❌ No runsheets found in database.")
        else:
            print(f"📋 Total Jobs: {runsheet_summary['overall']['total_jobs']}")
            print(f"📅 Total Days: {runsheet_summary['overall']['total_days']}")
            print(f"👥 Unique Customers: {runsheet_summary['overall']['unique_customers']}")
            print(f"📊 Jobs per Day: {runsheet_summary['overall']['total_jobs'] / runsheet_summary['overall']['total_days']:.1f}")
        
        # Get latest records
        print("\n🕒 LATEST RECORDS")
        print("-" * 40)
        
        latest_payslips = PayslipModel.get_all_payslips(limit=3)
        if latest_payslips:
            print("Recent Payslips:")
            for payslip in latest_payslips:
                print(f"  • Week {payslip['week_number']} ({payslip['tax_year']}): £{payslip['net_payment']:,.2f}")
        
        # Try to get earnings forecast
        try:
            print("\n🔮 EARNINGS FORECAST")
            print("-" * 40)
            
            forecast = PayslipService.predict_year_end_earnings()
            if 'error' not in forecast:
                print(f"📊 Current Year: {forecast['current_year']}")
                print(f"📈 Weeks Worked: {forecast['weeks_worked']}")
                print(f"💰 Total Earned: £{forecast['total_earned']:,.2f}")
                print(f"🎯 Year-End Projection: £{forecast['projections']['final_prediction']:,.2f}")
                print(f"📊 Confidence Range: £{forecast['confidence']['lower_bound']:,.2f} - £{forecast['confidence']['upper_bound']:,.2f}")
            else:
                print(f"⚠️ Forecast unavailable: {forecast['error']}")
        except Exception as e:
            print(f"⚠️ Forecast error: {str(e)}")
        
        # Data quality check
        print("\n🔍 DATA QUALITY")
        print("-" * 40)
        
        # Check for missing weeks
        missing_weeks = PayslipModel.check_missing_weeks()
        if missing_weeks:
            total_missing = sum(len(year_data['missing_weeks']) for year_data in missing_weeks.values())
            print(f"⚠️ Missing Weeks: {total_missing}")
        else:
            print("✅ No missing weeks detected")
        
        # System info
        print("\n🏗️ SYSTEM INFO")
        print("-" * 40)
        print("✅ Using refactored architecture")
        print("✅ Modular models and services")
        print("✅ Advanced analytics available")
        print("✅ Business intelligence features")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("Make sure the database is initialized and accessible.")
    
    print("\n" + "="*80)


def display_advanced_analytics():
    """Display advanced analytics using new services."""
    print("\n" + "="*80)
    print("ADVANCED ANALYTICS - NEW FEATURES")
    print("="*80)
    
    try:
        # Client profitability analysis
        print("\n💰 TOP CLIENTS BY REVENUE")
        print("-" * 40)
        
        profitability = ReportService.generate_client_profitability_report()
        
        if 'error' not in profitability:
            top_clients = profitability['client_profitability'][:5]
            for i, client in enumerate(top_clients, 1):
                print(f"{i}. {client['client']} ({client['tier']})")
                print(f"   Revenue: £{client['total_revenue']:,.2f} | Jobs: {client['total_jobs']}")
        
        # Earnings correlation
        print("\n📊 EARNINGS vs JOBS CORRELATION")
        print("-" * 40)
        
        correlation = ReportService.analyze_earnings_vs_jobs_correlation()
        if 'error' not in correlation:
            coeff = correlation['correlation_coefficient']
            strength = correlation['correlation_strength']
            print(f"Correlation: {coeff:.3f} ({strength})")
            print(f"Interpretation: {correlation['interpretation']}")
        
    except Exception as e:
        print(f"❌ Advanced analytics error: {str(e)}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--advanced":
        display_advanced_analytics()
    else:
        display_quick_stats()
        
        print("\n💡 TIP: Run with --advanced for business intelligence features")
        print("💡 TIP: Use the web interface at http://localhost:5001 for full features")
