"""
PDF Report Generator for Discrepancy Reports
Creates professional PDF reports with proper formatting, tables, and charts.
"""

import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os

class DiscrepancyPDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom paragraph styles for the report."""
        # Title style - TVS Primary
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a365d')  # TVS Dark
        )
        
        # Subtitle style - TVS Secondary
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2c5282')  # TVS Secondary
        )
        
        # Section header style - TVS Primary
        self.section_style = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceAfter=10,
            spaceBefore=20,
            textColor=colors.HexColor('#4a6fa5')  # TVS Primary
        )
        
        # Summary box style
        self.summary_style = ParagraphStyle(
            'Summary',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
            leftIndent=20,
            rightIndent=20
        )
    
    def generate_discrepancy_report(self, report_data, filters=None):
        """Generate a comprehensive discrepancy report PDF."""
        buffer = io.BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build the story (content)
        story = []
        
        # Add title and header
        story.extend(self._build_header(filters))
        
        # Add executive summary
        story.extend(self._build_summary(report_data))
        
        # Add detailed findings
        if report_data.get('missing_jobs'):
            story.extend(self._build_missing_jobs_table(report_data['missing_jobs']))
        
        # Add recommendations
        story.extend(self._build_recommendations(report_data))
        
        # Build the PDF
        doc.build(story)
        
        # Get the PDF data
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_header(self, filters):
        """Build the report header section."""
        story = []
        
        # Add TVS branding
        tvs_header = Paragraph(
            '<b>TVS Supply Chain Solutions</b><br/>Wages Management System',
            ParagraphStyle(
                'TVSHeader',
                parent=self.styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#4a6fa5'),
                alignment=TA_CENTER,
                spaceAfter=15
            )
        )
        story.append(tvs_header)
        
        # Main title
        title = "Wages vs Runsheets Discrepancy Report"
        story.append(Paragraph(title, self.title_style))
        
        # Subtitle with date and filters
        subtitle_parts = [f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"]
        
        if filters:
            filter_text = []
            if filters.get('year'):
                filter_text.append(f"Year: {filters['year']}")
            if filters.get('month'):
                month_names = {
                    '01': 'January', '02': 'February', '03': 'March', '04': 'April',
                    '05': 'May', '06': 'June', '07': 'July', '08': 'August',
                    '09': 'September', '10': 'October', '11': 'November', '12': 'December'
                }
                filter_text.append(f"Month: {month_names.get(filters['month'], filters['month'])}")
            
            if filter_text:
                subtitle_parts.append(f"Filters Applied: {', '.join(filter_text)}")
        
        subtitle = " | ".join(subtitle_parts)
        story.append(Paragraph(subtitle, self.subtitle_style))
        story.append(Spacer(1, 20))
        
        return story
    
    def _build_summary(self, report_data):
        """Build the executive summary section."""
        story = []
        
        story.append(Paragraph("Executive Summary", self.section_style))
        
        # Create summary statistics table
        summary_data = [
            ['Metric', 'Value', 'Description'],
            ['Total Payslip Jobs', f"{report_data.get('total_payslip_jobs', 0):,}", 'Jobs found in payslip records'],
            ['Total Runsheet Jobs', f"{report_data.get('total_runsheet_jobs', 0):,}", 'Jobs found in runsheet records'],
            ['Missing from Runsheets', f"{report_data.get('total_missing_count', 0):,}", 'Jobs paid but not in runsheets'],
            ['Match Rate', f"{report_data.get('match_rate', 0):.1f}%", 'Percentage of jobs properly matched'],
            ['Total Missing Value', f"£{report_data.get('total_missing_value', 0):,.2f}", 'Financial impact of missing jobs']
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a6fa5')),  # TVS Primary
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),  # Light blue-gray
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e0'))  # TVS light gray
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Add interpretation
        match_rate = report_data.get('match_rate', 0)
        if match_rate >= 95:
            status_text = "Excellent data integrity with minimal discrepancies."
            status_color = colors.HexColor('#48bb78')  # TVS Success Green
        elif match_rate >= 85:
            status_text = "Good data integrity with some discrepancies requiring attention."
            status_color = colors.HexColor('#ed8936')  # TVS Warning Orange
        else:
            status_text = "Significant discrepancies detected requiring immediate review."
            status_color = colors.HexColor('#f56565')  # TVS Error Red
        
        status_style = ParagraphStyle(
            'Status',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=status_color,
            alignment=TA_CENTER,
            spaceBefore=10,
            spaceAfter=20
        )
        
        story.append(Paragraph(f"<b>Status: {status_text}</b>", status_style))
        
        return story
    
    def _build_missing_jobs_table(self, missing_jobs):
        """Build the detailed missing jobs table."""
        story = []
        
        story.append(Paragraph("Missing Jobs Details", self.section_style))
        
        if not missing_jobs:
            story.append(Paragraph("No missing jobs found for the selected criteria.", self.styles['Normal']))
            return story
        
        # Limit to first 50 jobs for PDF readability
        display_jobs = missing_jobs[:50]
        
        if len(missing_jobs) > 50:
            story.append(Paragraph(
                f"Showing first 50 of {len(missing_jobs)} missing jobs. Download CSV for complete list.",
                self.styles['Italic']
            ))
            story.append(Spacer(1, 10))
        
        # Create table data
        table_data = [['Job #', 'Client', 'Location', 'Amount', 'Week/Year']]
        
        for job in display_jobs:
            client = (job.get('client') or 'N/A')[:30]  # Truncate long names
            location = f"{job.get('location') or ''} {job.get('postcode') or ''}".strip()[:25]
            amount = f"£{job.get('amount', 0):.2f}"
            week_year = f"W{job.get('week_number', '')}/{job.get('tax_year', '')}"
            
            table_data.append([
                str(job.get('job_number', '')),
                client,
                location,
                amount,
                week_year
            ])
        
        # Create and style the table
        jobs_table = Table(table_data, colWidths=[1*inch, 2*inch, 1.8*inch, 0.8*inch, 0.8*inch])
        jobs_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),  # TVS Secondary
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),  # Amount column
            ('ALIGN', (4, 0), (4, -1), 'CENTER'), # Week/Year column
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0'))
        ]))
        
        story.append(jobs_table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _build_recommendations(self, report_data):
        """Build the recommendations section."""
        story = []
        
        story.append(Paragraph("Recommendations", self.section_style))
        
        recommendations = []
        missing_count = report_data.get('total_missing_count', 0)
        match_rate = report_data.get('match_rate', 0)
        
        if missing_count > 100:
            recommendations.append("High number of missing jobs detected - review runsheet import processes")
        
        if match_rate < 90:
            recommendations.append("Match rate below 90% - investigate data collection workflows")
        
        recommendations.extend([
            "Review missing jobs to identify patterns (specific agencies, job types, or date ranges)",
            "Verify that all runsheet files are being imported correctly",
            "Check for systematic issues in data entry or processing",
            "Consider implementing automated validation checks",
            "Schedule regular discrepancy reports to maintain data integrity"
        ])
        
        for i, rec in enumerate(recommendations, 1):
            story.append(Paragraph(f"{i}. {rec}", self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Add footer
        footer_text = f"TVS Supply Chain Solutions - Wages Management System | Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#4a6fa5'),
            alignment=TA_CENTER
        )
        story.append(Paragraph(footer_text, footer_style))
        
        return story
