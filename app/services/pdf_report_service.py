"""
PDF Report Generation Service for Mileage Reports
Creates professional-looking PDF reports with charts and tables.
"""

import io
import os
from datetime import datetime
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.lib.colors import HexColor
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

class MileagePDFReportService:
    """Service for generating professional mileage PDF reports."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet() if REPORTLAB_AVAILABLE else None
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom paragraph styles for the reports."""
        if not REPORTLAB_AVAILABLE:
            return
            
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2c3e50'),
            alignment=1  # Center alignment
        )
        
        # Subtitle style
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            textColor=colors.HexColor('#34495e'),
            alignment=1
        )
        
        # Section header style
        self.section_style = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#2980b9'),
            borderWidth=1,
            borderColor=colors.HexColor('#3498db'),
            borderPadding=5,
            backColor=colors.HexColor('#ecf0f1')
        )
        
        # Body text style
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            textColor=colors.HexColor('#2c3e50')
        )
    
    def create_monthly_mileage_pdf(self, data, filename=None):
        """Generate monthly mileage PDF report."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")
        
        if filename is None:
            filename = f"monthly_mileage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Create reports directory if it doesn't exist (in project root)
        try:
            project_root = Path(__file__).parent.parent.parent  # Go up from app/services/ to project root
            reports_dir = project_root / 'reports'
            reports_dir.mkdir(exist_ok=True)
            filepath = reports_dir / filename
        except Exception:
            # Fallback to current working directory
            reports_dir = Path.cwd() / 'reports'
            reports_dir.mkdir(exist_ok=True)
            filepath = reports_dir / filename
        
        # Create PDF document
        doc = SimpleDocTemplate(str(filepath), pagesize=A4, 
                              rightMargin=72, leftMargin=72, 
                              topMargin=72, bottomMargin=18)
        
        # Build content
        story = []
        
        # Title
        story.append(Paragraph("Monthly Mileage Report", self.title_style))
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y')}", self.subtitle_style))
        story.append(Spacer(1, 20))
        
        # Summary section
        if data:
            total_miles = sum(row['total_miles'] for row in data)
            total_fuel_cost = sum(row['total_fuel_cost'] for row in data)
            avg_cost_per_mile = total_fuel_cost / total_miles if total_miles > 0 else 0
            
            story.append(Paragraph("Executive Summary", self.section_style))
            summary_data = [
                ['Metric', 'Value'],
                ['Total Months Analyzed', str(len(data))],
                ['Total Miles Driven', f"{total_miles:,.1f}"],
                ['Total Fuel Cost', f"£{total_fuel_cost:,.2f}"],
                ['Average Cost per Mile', f"£{avg_cost_per_mile:.3f}"],
                ['Average Miles per Month', f"{total_miles/len(data):,.1f}" if data else "0"]
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7'))
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 20))
        
        # Monthly breakdown table
        story.append(Paragraph("Monthly Breakdown", self.section_style))
        
        if data:
            # Prepare table data
            table_data = [['Month', 'Days Worked', 'Total Miles', 'Avg Miles/Day', 'Total Fuel Cost', 'Avg Fuel/Day', 'Cost per Mile']]
            
            for row in data:
                cost_per_mile = 0
                if row['total_miles'] > 0 and row['total_fuel_cost'] > 0:
                    cost_per_mile = row['total_fuel_cost'] / row['total_miles']
                
                table_data.append([
                    row['month'],
                    str(row['days_worked']),
                    f"{row['total_miles']:,.1f}",
                    f"{row['avg_miles_per_day']:,.1f}",
                    f"£{row['total_fuel_cost']:,.2f}",
                    f"£{row['avg_fuel_per_day']:,.2f}",
                    f"£{cost_per_mile:.3f}"
                ])
            
            # Create table
            table = Table(table_data, colWidths=[0.8*inch, 0.8*inch, 0.9*inch, 0.9*inch, 1*inch, 0.9*inch, 0.9*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2980b9')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                # Alternate row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No data available for the selected period.", self.body_style))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph("Report generated by TVS Mileage Tracking System", 
                              ParagraphStyle('Footer', parent=self.styles['Normal'], 
                                           fontSize=8, textColor=colors.grey, alignment=1)))
        
        # Build PDF
        doc.build(story)
        
        return str(filepath)
    
    def create_high_mileage_pdf(self, data, filename=None):
        """Generate high mileage days PDF report."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF generation")
        
        if filename is None:
            filename = f"high_mileage_days_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Create reports directory if it doesn't exist (in project root)
        try:
            project_root = Path(__file__).parent.parent.parent  # Go up from app/services/ to project root
            reports_dir = project_root / 'reports'
            reports_dir.mkdir(exist_ok=True)
            filepath = reports_dir / filename
        except Exception:
            # Fallback to current working directory
            reports_dir = Path.cwd() / 'reports'
            reports_dir.mkdir(exist_ok=True)
            filepath = reports_dir / filename
        
        doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        story = []
        
        # Title
        story.append(Paragraph("High Mileage Days Report", self.title_style))
        story.append(Paragraph("Days with 200+ Miles", self.subtitle_style))
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y')}", 
                              ParagraphStyle('Date', parent=self.styles['Normal'], 
                                           fontSize=12, alignment=1, textColor=colors.grey)))
        story.append(Spacer(1, 20))
        
        if data:
            # Summary
            story.append(Paragraph("Summary", self.section_style))
            total_high_days = len(data)
            total_miles = sum(row['mileage'] for row in data)
            total_fuel = sum(row['fuel_cost'] for row in data)
            avg_miles = total_miles / total_high_days if total_high_days > 0 else 0
            
            summary_data = [
                ['Metric', 'Value'],
                ['Total High Mileage Days', str(total_high_days)],
                ['Total Miles on High Days', f"{total_miles:,.1f}"],
                ['Average Miles per High Day', f"{avg_miles:,.1f}"],
                ['Total Fuel Cost on High Days', f"£{total_fuel:,.2f}"],
                ['Highest Single Day', f"{max(row['mileage'] for row in data):,.1f} miles" if data else "N/A"]
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2.5*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fadbd8')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#c0392b'))
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 20))
            
            # Detailed table
            story.append(Paragraph("Detailed Breakdown", self.section_style))
            
            table_data = [['Date', 'Miles', 'Fuel Cost', 'Cost per Mile']]
            for row in data:
                table_data.append([
                    row['date'],
                    f"{row['mileage']:,.1f}",
                    f"£{row['fuel_cost']:,.2f}",
                    f"£{row['cost_per_mile']:,.3f}"
                ])
            
            table = Table(table_data, colWidths=[1.5*inch, 1.2*inch, 1.3*inch, 1.3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No high mileage days (200+ miles) found in the data.", self.body_style))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph("Report generated by TVS Mileage Tracking System", 
                              ParagraphStyle('Footer', parent=self.styles['Normal'], 
                                           fontSize=8, textColor=colors.grey, alignment=1)))
        
        doc.build(story)
        return str(filepath)
    
    def create_missing_data_pdf(self, missing_mileage, missing_fuel_cost, summary_stats, filename=None):
        """Generate missing data analysis PDF report."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF generation")
        
        if filename is None:
            filename = f"missing_mileage_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Create reports directory if it doesn't exist (in project root)
        try:
            project_root = Path(__file__).parent.parent.parent  # Go up from app/services/ to project root
            reports_dir = project_root / 'reports'
            reports_dir.mkdir(exist_ok=True)
            filepath = reports_dir / filename
        except Exception:
            # Fallback to current working directory
            reports_dir = Path.cwd() / 'reports'
            reports_dir.mkdir(exist_ok=True)
            filepath = reports_dir / filename
        
        doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        story = []
        
        # Title
        story.append(Paragraph("Missing Mileage Data Analysis", self.title_style))
        story.append(Paragraph("Data Quality Assessment Report", self.subtitle_style))
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y')}", 
                              ParagraphStyle('Date', parent=self.styles['Normal'], 
                                           fontSize=12, alignment=1, textColor=colors.grey)))
        story.append(Spacer(1, 20))
        
        # Summary
        story.append(Paragraph("Data Completeness Summary", self.section_style))
        
        completeness_pct = (summary_stats['days_with_mileage'] / summary_stats['total_working_days'] * 100) if summary_stats['total_working_days'] > 0 else 0
        
        summary_data = [
            ['Metric', 'Value'],
            ['Total Working Days', str(summary_stats['total_working_days'])],
            ['Days with Mileage Data', str(summary_stats['days_with_mileage'])],
            ['Missing Mileage Records', str(summary_stats['missing_mileage'])],
            ['Missing Fuel Cost Records', str(summary_stats['missing_fuel_cost'])],
            ['Data Completeness', f"{completeness_pct:.1f}%"]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f39c12')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fdeaa7')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e67e22'))
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Missing mileage data
        if missing_mileage:
            story.append(Paragraph("Missing Mileage Data", self.section_style))
            story.append(Paragraph(f"The following {len(missing_mileage)} working days have no mileage records:", self.body_style))
            story.append(Spacer(1, 10))
            
            # Create table with missing dates (in columns for space efficiency)
            cols = 4
            rows = []
            for i in range(0, len(missing_mileage), cols):
                row = missing_mileage[i:i+cols]
                while len(row) < cols:
                    row.append('')  # Pad with empty strings
                rows.append(row)
            
            if rows:
                missing_table = Table(rows, colWidths=[1.3*inch]*cols)
                missing_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff3cd'))
                ]))
                story.append(missing_table)
                story.append(Spacer(1, 15))
        
        # Missing fuel cost data
        if missing_fuel_cost:
            story.append(Paragraph("Missing Fuel Cost Data", self.section_style))
            story.append(Paragraph(f"The following {len(missing_fuel_cost)} days have mileage but no fuel cost:", self.body_style))
            story.append(Spacer(1, 10))
            
            fuel_data = [['Date', 'Miles Recorded']]
            for item in missing_fuel_cost[:20]:  # Limit to first 20 for space
                fuel_data.append([item['date'], f"{item['mileage']:.1f}"])
            
            if len(missing_fuel_cost) > 20:
                fuel_data.append(['...', f'({len(missing_fuel_cost) - 20} more records)'])
            
            fuel_table = Table(fuel_data, colWidths=[2*inch, 1.5*inch])
            fuel_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#17a2b8')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#d1ecf1')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bee5eb'))
            ]))
            story.append(fuel_table)
        
        # Recommendations
        story.append(Spacer(1, 20))
        story.append(Paragraph("Recommendations", self.section_style))
        
        recommendations = []
        if summary_stats['missing_mileage'] > 0:
            recommendations.append("• Review and add mileage data for the missing working days listed above")
        if summary_stats['missing_fuel_cost'] > 0:
            recommendations.append("• Add fuel cost information for days with recorded mileage")
        if completeness_pct < 90:
            recommendations.append("• Implement daily mileage recording procedures to improve data completeness")
        recommendations.append("• Regular data quality checks to maintain accurate records")
        
        for rec in recommendations:
            story.append(Paragraph(rec, self.body_style))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph("Report generated by TVS Mileage Tracking System", 
                              ParagraphStyle('Footer', parent=self.styles['Normal'], 
                                           fontSize=8, textColor=colors.grey, alignment=1)))
        
        doc.build(story)
        return str(filepath)
