"""
Weekly Summary PDF Report Generation Service
Creates professional PDF reports for weekly summaries.
"""

from pathlib import Path
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.platypus.flowables import HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.graphics.shapes import Drawing, Rect
    from reportlab.graphics import renderPDF
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class WeeklySummaryPDFService:
    """Service for generating weekly summary PDF reports."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet() if REPORTLAB_AVAILABLE else None
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom paragraph styles for the reports."""
        if not REPORTLAB_AVAILABLE:
            return
            
        # Title style - Modern bold
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            spaceAfter=10,
            textColor=colors.HexColor('#1a1a1a'),
            fontName='Helvetica-Bold',
            alignment=TA_LEFT
        )
        
        # Subtitle style - Elegant
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=20,
            textColor=colors.HexColor('#666666'),
            fontName='Helvetica',
            alignment=TA_LEFT
        )
        
        # Section header style - Clean and modern
        self.section_style = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=16,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor('#2c3e50'),
            fontName='Helvetica-Bold',
            leftIndent=0
        )
        
        # Body text style
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            textColor=colors.HexColor('#333333')
        )
        
        # Header info style
        self.header_info_style = ParagraphStyle(
            'HeaderInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=TA_RIGHT
        )
    
    def create_weekly_summary_pdf(self, data, filename=None):
        """Generate weekly summary PDF report."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")
        
        if filename is None:
            week_num = data.get('week_number', 'XX')
            filename = f"weekly_summary_week{week_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Create reports directory
        try:
            project_root = Path(__file__).parent.parent.parent
            reports_dir = project_root / 'data' / 'reports'
            reports_dir.mkdir(parents=True, exist_ok=True)
            filepath = reports_dir / filename
        except Exception:
            reports_dir = Path.cwd() / 'reports'
            reports_dir.mkdir(exist_ok=True)
            filepath = reports_dir / filename
        
        # Create PDF document in LANDSCAPE orientation
        doc = SimpleDocTemplate(str(filepath), pagesize=landscape(A4),
                               rightMargin=30, leftMargin=30,
                               topMargin=25, bottomMargin=25)
        
        story = []
        
        # Try to load logo
        logo_path = Path(__file__).parent.parent.parent / 'static' / 'images' / 'logo.png'
        
        # Header with logo and title
        header_content = []
        if logo_path.exists():
            try:
                logo = Image(str(logo_path), width=60, height=60)
                header_content.append(logo)
            except:
                header_content.append(Paragraph('<b>TVS</b>', 
                    ParagraphStyle('Logo', fontSize=24, textColor=colors.HexColor('#3498db'), fontName='Helvetica-Bold')))
        else:
            # Fallback: Create a simple colored box as logo placeholder
            header_content.append(Paragraph('<b>TVS</b>', 
                ParagraphStyle('Logo', fontSize=24, textColor=colors.HexColor('#3498db'), fontName='Helvetica-Bold')))
        
        header_content.append(
            Paragraph('<b>WEEKLY PERFORMANCE REPORT</b><br/><font size="10" color="#666">Week {week} • {dates}</font>'.format(
                week=data.get('week_number', 'N/A'),
                dates=data.get('week_label', '')
            ), ParagraphStyle('HeaderTitle', fontSize=20, textColor=colors.HexColor('#1a1a1a'), 
                            fontName='Helvetica-Bold', leftIndent=10))
        )
        
        header_content.append(
            Paragraph(f'<font size="8" color="#999">Generated: {datetime.now().strftime("%d/%m/%Y %H:%M")}</font>',
                     ParagraphStyle('GenDate', fontSize=8, textColor=colors.HexColor('#999'), alignment=TA_RIGHT))
        )
        
        header_table = Table([header_content], colWidths=[0.8*inch, 5.5*inch, 1.5*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#3498db')))
        story.append(Spacer(1, 10))
        
        # KEY METRICS CARDS - Compact horizontal layout
        summary = data.get('summary', {})
        
        metrics_data = [[
            Paragraph(f'<b>{summary.get("total_jobs", 0)}</b><br/><font size="7" color="#666">Total Jobs</font>',
                     ParagraphStyle('Metric', fontSize=16, alignment=TA_CENTER, textColor=colors.HexColor('#2c3e50'), fontName='Helvetica-Bold')),
            Paragraph(f'<b>£{summary.get("total_earnings", 0):,.2f}</b><br/><font size="7" color="#666">Earnings</font>',
                     ParagraphStyle('Metric', fontSize=16, alignment=TA_CENTER, textColor=colors.HexColor('#27ae60'), fontName='Helvetica-Bold')),
            Paragraph(f'<b>{summary.get("completion_rate", 0)}%</b><br/><font size="7" color="#666">Complete</font>',
                     ParagraphStyle('Metric', fontSize=16, alignment=TA_CENTER, textColor=colors.HexColor('#3498db'), fontName='Helvetica-Bold')),
            Paragraph(f'<b>{summary.get("total_mileage", 0):.0f}</b><br/><font size="7" color="#666">Miles</font>',
                     ParagraphStyle('Metric', fontSize=16, alignment=TA_CENTER, textColor=colors.HexColor('#e67e22'), fontName='Helvetica-Bold')),
            Paragraph(f'<b>{summary.get("working_days", 0)}</b><br/><font size="7" color="#666">Days</font>',
                     ParagraphStyle('Metric', fontSize=16, alignment=TA_CENTER, textColor=colors.HexColor('#9b59b6'), fontName='Helvetica-Bold')),
        ]]
        
        metrics_table = Table(metrics_data, colWidths=[1.5*inch]*5)
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 10))
        
        # TWO-COLUMN LAYOUT: Status Breakdown + Daily Breakdown
        
        # Status Breakdown (Left Column) - in specific order
        status_data = [['Status', 'Count', '£']]
        status_order = ['completed', 'extra', 'DNCO', 'dnco', 'PDA Licence', 'SASER Auto Billing', 'missed', 'pending']
        status_breakdown = data.get('status_breakdown', {})
        
        for status in status_order:
            if status in status_breakdown:
                info = status_breakdown[status]
                status_label = status.replace('_', ' ').title() if status not in ['DNCO', 'PDA Licence', 'SASER Auto Billing'] else status
                
                # Add estimated loss for DNCO
                earnings_display = f"£{info.get('earnings', 0):.2f}"
                if status in ['DNCO', 'dnco'] and info.get('estimated_loss'):
                    earnings_display = f"£{info.get('earnings', 0):.2f}\n(Est: £{info.get('estimated_loss', 0):.2f})"
                
                status_data.append([status_label, str(info.get('count', 0)), earnings_display])
        
        # Add any remaining statuses not in the order list
        for status, info in status_breakdown.items():
            if status not in status_order:
                status_label = status.replace('_', ' ').title()
                status_data.append([status_label, str(info.get('count', 0)), f"£{info.get('earnings', 0):.2f}"])
        
        status_table = Table(status_data, colWidths=[1.3*inch, 0.5*inch, 0.7*inch])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ]))
        
        # Daily Breakdown (Right Column)
        daily_data = [['Day', 'Jobs', 'Done', 'Extra', '£']]
        for day in data.get('daily_breakdown', []):
            daily_data.append([
                day.get('day_name', '')[:3],  # Abbreviate day names
                str(day.get('jobs', 0)),
                str(day.get('completed', 0)),
                str(day.get('extra', 0)),
                f"£{day.get('earnings', 0):.0f}"
            ])
        
        daily_table = Table(daily_data, colWidths=[0.5*inch, 0.5*inch, 0.5*inch, 0.5*inch, 0.7*inch])
        daily_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ]))
        
        # Combine status and daily tables side by side
        combined_row = [[status_table, Spacer(0.3*inch, 0), daily_table]]
        combined_table = Table(combined_row, colWidths=[2.5*inch, 0.3*inch, 2.7*inch])
        combined_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(combined_table)
        story.append(Spacer(1, 10))
        
        # Top Customers - Compact horizontal layout
        if data.get('top_customers'):
            customer_data = [['Customer', 'Jobs', '£']]
            for customer in data.get('top_customers', [])[:5]:  # Top 5 only
                customer_data.append([
                    customer.get('customer', 'Unknown')[:25],  # Truncate long names
                    str(customer.get('jobs', 0)),
                    f"£{customer.get('earnings', 0):.0f}"
                ])
            
            customer_table = Table(customer_data, colWidths=[4.5*inch, 0.5*inch, 0.7*inch])
            customer_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e67e22')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ]))
            story.append(customer_table)
        
        # Footer with branding - minimal spacing
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#dee2e6')))
        story.append(Spacer(1, 5))
        footer_text = f'<font size="7" color="#999999">TVS Driver Services • Weekly Performance Report • Generated {datetime.now().strftime("%d/%m/%Y %H:%M")}</font>'
        story.append(Paragraph(footer_text, 
                              ParagraphStyle('Footer', parent=self.styles['Normal'], 
                                           alignment=TA_CENTER)))
        
        doc.build(story)
        return str(filepath)
