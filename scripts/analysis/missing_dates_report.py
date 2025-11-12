#!/usr/bin/env python3
"""
Generate a PDF report of missing run sheet dates.
"""

import sqlite3
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os

DB_PATH = "data/payslips.db"
OUTPUT_PATH = "data/reports/missing_dates_report.pdf"


def get_missing_dates():
    """Get all missing dates from the run sheets."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all unique dates
    cursor.execute("""
        SELECT DISTINCT date 
        FROM run_sheet_jobs 
        WHERE date IS NOT NULL 
        ORDER BY substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2)
    """)
    
    dates_raw = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Convert to datetime objects
    date_objects = []
    for date_str in dates_raw:
        try:
            dt = datetime.strptime(date_str, '%d/%m/%Y')
            date_objects.append(dt)
        except:
            pass
    
    if not date_objects:
        return [], None, None, []
    
    # Find date range
    start_date = min(date_objects)
    end_date = max(date_objects)
    
    # Find missing dates
    all_dates = set()
    current = start_date
    while current <= end_date:
        all_dates.add(current)
        current += timedelta(days=1)
    
    present_dates = set(date_objects)
    missing_dates = sorted(all_dates - present_dates)
    
    return missing_dates, start_date, end_date, date_objects


def generate_pdf_report():
    """Generate PDF report of missing dates."""
    print("\n" + "="*70)
    print("MISSING RUN SHEET DATES REPORT")
    print("="*70 + "\n")
    
    # Get missing dates
    print("📊 Analyzing run sheet dates...")
    missing_dates, start_date, end_date, present_dates = get_missing_dates()
    
    if not start_date:
        print("❌ No run sheet dates found in database")
        return
    
    # Create reports directory if it doesn't exist
    os.makedirs("reports", exist_ok=True)
    
    # Create PDF
    doc = SimpleDocTemplate(OUTPUT_PATH, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Title
    story.append(Paragraph("Missing Run Sheet Dates Report", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Summary section
    story.append(Paragraph("Summary", heading_style))
    
    total_days = (end_date - start_date).days + 1
    coverage_pct = (len(present_dates) / total_days * 100) if total_days > 0 else 0
    
    summary_data = [
        ['Date Range:', f"{start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}"],
        ['Total Days in Range:', str(total_days)],
        ['Days with Run Sheets:', str(len(present_dates))],
        ['Missing Days:', str(len(missing_dates))],
        ['Coverage:', f"{coverage_pct:.1f}%"]
    ]
    
    summary_table = Table(summary_data, colWidths=[2.5*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f7fafc')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0'))
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Missing dates section
    if missing_dates:
        story.append(Paragraph(f"Missing Dates ({len(missing_dates)} days)", heading_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Group by year and month
        by_year_month = {}
        for dt in missing_dates:
            key = (dt.year, dt.month)
            if key not in by_year_month:
                by_year_month[key] = []
            by_year_month[key].append(dt)
        
        # Create table data
        table_data = [['Date', 'Day of Week', 'Month', 'Year']]
        
        for (year, month), dates in sorted(by_year_month.items()):
            for dt in dates:
                table_data.append([
                    dt.strftime('%d/%m/%Y'),
                    dt.strftime('%A'),
                    dt.strftime('%B'),
                    str(dt.year)
                ])
        
        # Create table with pagination
        rows_per_page = 35
        for i in range(0, len(table_data), rows_per_page):
            chunk = table_data[i:min(i+rows_per_page, len(table_data))]
            
            # Add header if not first chunk
            if i > 0:
                chunk = [table_data[0]] + chunk[1:]
            
            missing_table = Table(chunk, colWidths=[1.3*inch, 1.5*inch, 1.5*inch, 0.8*inch])
            missing_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')])
            ]))
            
            story.append(missing_table)
            
            # Add page break if not last chunk
            if i + rows_per_page < len(table_data):
                story.append(PageBreak())
    else:
        story.append(Paragraph("✅ No missing dates! All days have run sheets.", styles['Normal']))
    
    # Build PDF
    print(f"📄 Generating PDF report...")
    doc.build(story)
    
    print(f"✅ Report saved to: {OUTPUT_PATH}")
    print(f"\n📊 Summary:")
    print(f"   Total days in range: {total_days}")
    print(f"   Days with run sheets: {len(present_dates)}")
    print(f"   Missing days: {len(missing_dates)}")
    print(f"   Coverage: {coverage_pct:.1f}%")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    generate_pdf_report()
