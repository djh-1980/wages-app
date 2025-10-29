"""
ReportService - Business logic for analytics and reporting.
Handles complex data analysis, report generation, and business intelligence.
"""

from ..models.payslip import PayslipModel
from ..models.runsheet import RunsheetModel
from ..database import get_db_connection
from datetime import datetime, timedelta
import json
import csv
import io


class ReportService:
    """Service class for analytics, reporting, and business intelligence."""
    
    @staticmethod
    def generate_comprehensive_report(year=None, month=None):
        """Generate a comprehensive business report."""
        try:
            report = {
                'generated_at': datetime.now().isoformat(),
                'period': {
                    'year': year,
                    'month': month
                }
            }
            
            # Payslip analytics
            if year:
                payslip_summary = PayslipModel.get_summary()
                report['payslip_analytics'] = {
                    'summary': payslip_summary,
                    'tax_year_data': PayslipModel.get_all_payslips(tax_year=year) if year else None
                }
            
            # Runsheet analytics
            runsheet_summary = RunsheetModel.get_summary()
            report['runsheet_analytics'] = {
                'summary': runsheet_summary,
                'completion_status': RunsheetModel.get_completion_status()
            }
            
            # Cross-system analysis
            report['cross_analysis'] = ReportService._analyze_payslip_runsheet_correlation(year, month)
            
            # Performance metrics
            report['performance_metrics'] = ReportService._calculate_performance_metrics(year, month)
            
            return report
        except Exception as e:
            raise Exception(f"Failed to generate comprehensive report: {str(e)}")
    
    @staticmethod
    def analyze_earnings_vs_jobs_correlation():
        """Analyze correlation between job counts and earnings."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get weekly job counts and earnings
                cursor.execute("""
                    SELECT 
                        p.tax_year,
                        p.week_number,
                        p.net_payment,
                        COUNT(ji.id) as job_count,
                        SUM(ji.amount) as total_job_amount
                    FROM payslips p
                    LEFT JOIN job_items ji ON p.id = ji.payslip_id
                    GROUP BY p.tax_year, p.week_number, p.net_payment
                    ORDER BY p.tax_year DESC, p.week_number DESC
                """)
                
                data = [dict(row) for row in cursor.fetchall()]
                
                if len(data) < 2:
                    return {'error': 'Insufficient data for correlation analysis'}
                
                # Calculate correlation coefficient
                job_counts = [row['job_count'] for row in data]
                earnings = [row['net_payment'] for row in data]
                
                n = len(data)
                sum_x = sum(job_counts)
                sum_y = sum(earnings)
                sum_xy = sum(x * y for x, y in zip(job_counts, earnings))
                sum_x2 = sum(x * x for x in job_counts)
                sum_y2 = sum(y * y for y in earnings)
                
                numerator = n * sum_xy - sum_x * sum_y
                denominator = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5
                
                correlation = numerator / denominator if denominator != 0 else 0
                
                # Interpret correlation strength
                if abs(correlation) >= 0.7:
                    strength = 'strong'
                elif abs(correlation) >= 0.3:
                    strength = 'moderate'
                else:
                    strength = 'weak'
                
                return {
                    'correlation_coefficient': round(correlation, 3),
                    'correlation_strength': strength,
                    'interpretation': ReportService._interpret_correlation(correlation),
                    'data_points': len(data),
                    'sample_data': data[:10]  # First 10 records for reference
                }
        except Exception as e:
            raise Exception(f"Failed to analyze earnings vs jobs correlation: {str(e)}")
    
    @staticmethod
    def generate_client_profitability_report():
        """Generate detailed client profitability analysis."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get client statistics with profitability metrics
                cursor.execute("""
                    SELECT 
                        ji.client,
                        COUNT(*) as total_jobs,
                        SUM(ji.amount) as total_revenue,
                        AVG(ji.amount) as avg_job_value,
                        MIN(ji.amount) as min_job_value,
                        MAX(ji.amount) as max_job_value,
                        COUNT(DISTINCT p.tax_year) as years_active,
                        MIN(ji.date) as first_job_date,
                        MAX(ji.date) as last_job_date
                    FROM job_items ji
                    JOIN payslips p ON ji.payslip_id = p.id
                    WHERE ji.client IS NOT NULL AND ji.client != ''
                    GROUP BY ji.client
                    HAVING COUNT(*) >= 3
                    ORDER BY total_revenue DESC
                """)
                
                client_data = [dict(row) for row in cursor.fetchall()]
                
                # Calculate additional metrics
                for client in client_data:
                    # Calculate job frequency (jobs per year)
                    client['jobs_per_year'] = round(client['total_jobs'] / max(client['years_active'], 1), 2)
                    
                    # Calculate revenue consistency (coefficient of variation would be ideal, but we'll use range/mean)
                    if client['avg_job_value'] > 0:
                        client['value_consistency'] = round((client['max_job_value'] - client['min_job_value']) / client['avg_job_value'], 2)
                    else:
                        client['value_consistency'] = 0
                    
                    # Categorize client value
                    if client['total_revenue'] >= 5000:
                        client['tier'] = 'Premium'
                    elif client['total_revenue'] >= 2000:
                        client['tier'] = 'Standard'
                    else:
                        client['tier'] = 'Basic'
                
                # Generate insights
                total_clients = len(client_data)
                total_revenue = sum(c['total_revenue'] for c in client_data)
                
                # Top 20% of clients by revenue
                top_20_percent = int(total_clients * 0.2)
                top_clients = client_data[:top_20_percent]
                top_client_revenue = sum(c['total_revenue'] for c in top_clients)
                
                insights = {
                    'pareto_analysis': {
                        'top_20_percent_clients': top_20_percent,
                        'top_20_percent_revenue': round(top_client_revenue, 2),
                        'top_20_percent_share': round((top_client_revenue / total_revenue * 100), 2) if total_revenue > 0 else 0
                    },
                    'tier_distribution': {
                        'premium': len([c for c in client_data if c['tier'] == 'Premium']),
                        'standard': len([c for c in client_data if c['tier'] == 'Standard']),
                        'basic': len([c for c in client_data if c['tier'] == 'Basic'])
                    }
                }
                
                return {
                    'client_profitability': client_data,
                    'insights': insights,
                    'summary': {
                        'total_clients': total_clients,
                        'total_revenue': round(total_revenue, 2),
                        'avg_revenue_per_client': round(total_revenue / total_clients, 2) if total_clients > 0 else 0
                    }
                }
        except Exception as e:
            raise Exception(f"Failed to generate client profitability report: {str(e)}")
    
    @staticmethod
    def analyze_seasonal_patterns():
        """Analyze seasonal patterns in earnings and job activity."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get monthly data across all years
                cursor.execute("""
                    SELECT 
                        CAST((p.week_number - 1) / 4.33 AS INTEGER) + 1 as month,
                        p.tax_year,
                        AVG(p.net_payment) as avg_earnings,
                        COUNT(ji.id) as total_jobs,
                        COUNT(DISTINCT ji.client) as unique_clients
                    FROM payslips p
                    LEFT JOIN job_items ji ON p.id = ji.payslip_id
                    GROUP BY month, p.tax_year
                    ORDER BY p.tax_year, month
                """)
                
                monthly_data = [dict(row) for row in cursor.fetchall()]
                
                # Aggregate by month across all years
                month_aggregates = {}
                for i in range(1, 13):
                    month_data = [row for row in monthly_data if row['month'] == i]
                    if month_data:
                        month_aggregates[i] = {
                            'month': i,
                            'avg_earnings': round(sum(row['avg_earnings'] or 0 for row in month_data) / len(month_data), 2),
                            'avg_jobs': round(sum(row['total_jobs'] for row in month_data) / len(month_data), 2),
                            'avg_clients': round(sum(row['unique_clients'] for row in month_data) / len(month_data), 2),
                            'data_points': len(month_data)
                        }
                
                # Identify patterns
                if month_aggregates:
                    earnings_by_month = [month_aggregates[i]['avg_earnings'] for i in range(1, 13) if i in month_aggregates]
                    
                    peak_month = max(month_aggregates.items(), key=lambda x: x[1]['avg_earnings'])
                    low_month = min(month_aggregates.items(), key=lambda x: x[1]['avg_earnings'])
                    
                    # Calculate seasonal variation
                    if earnings_by_month:
                        avg_earnings = sum(earnings_by_month) / len(earnings_by_month)
                        variation = max(earnings_by_month) - min(earnings_by_month)
                        variation_percentage = (variation / avg_earnings * 100) if avg_earnings > 0 else 0
                    else:
                        variation_percentage = 0
                
                return {
                    'monthly_patterns': month_aggregates,
                    'seasonal_insights': {
                        'peak_month': {
                            'month': peak_month[0],
                            'month_name': ReportService._get_month_name(peak_month[0]),
                            'avg_earnings': peak_month[1]['avg_earnings']
                        },
                        'lowest_month': {
                            'month': low_month[0],
                            'month_name': ReportService._get_month_name(low_month[0]),
                            'avg_earnings': low_month[1]['avg_earnings']
                        },
                        'seasonal_variation': round(variation_percentage, 2)
                    }
                }
        except Exception as e:
            raise Exception(f"Failed to analyze seasonal patterns: {str(e)}")
    
    @staticmethod
    def export_custom_report(filters, format='csv'):
        """Export custom filtered data in specified format."""
        try:
            # Build query based on filters
            query = """
                SELECT 
                    p.tax_year,
                    p.week_number,
                    p.pay_date,
                    p.net_payment,
                    ji.job_number,
                    ji.client,
                    ji.location,
                    ji.job_type,
                    ji.date as job_date,
                    ji.amount as job_amount,
                    ji.description
                FROM payslips p
                LEFT JOIN job_items ji ON p.id = ji.payslip_id
                WHERE 1=1
            """
            
            params = []
            
            if filters.get('tax_year'):
                query += " AND p.tax_year = ?"
                params.append(filters['tax_year'])
            
            if filters.get('client'):
                query += " AND ji.client = ?"
                params.append(filters['client'])
            
            if filters.get('week_from'):
                query += " AND p.week_number >= ?"
                params.append(filters['week_from'])
            
            if filters.get('week_to'):
                query += " AND p.week_number <= ?"
                params.append(filters['week_to'])
            
            query += " ORDER BY p.tax_year DESC, p.week_number DESC"
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                data = [dict(row) for row in cursor.fetchall()]
            
            if format.lower() == 'csv':
                return ReportService._export_to_csv(data)
            elif format.lower() == 'json':
                return json.dumps(data, indent=2)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            raise Exception(f"Failed to export custom report: {str(e)}")
    
    @staticmethod
    def _analyze_payslip_runsheet_correlation(year, month):
        """Analyze correlation between payslip and runsheet data."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get jobs that appear in both payslips and runsheets
                cursor.execute("""
                    SELECT 
                        ji.job_number,
                        ji.client as payslip_client,
                        ji.amount as payslip_amount,
                        rs.customer as runsheet_customer,
                        rs.status as runsheet_status,
                        rs.date as runsheet_date
                    FROM job_items ji
                    JOIN payslips p ON ji.payslip_id = p.id
                    LEFT JOIN run_sheet_jobs rs ON ji.job_number = rs.job_number
                    WHERE ji.job_number IS NOT NULL
                    LIMIT 100
                """)
                
                correlations = [dict(row) for row in cursor.fetchall()]
                
                # Analyze discrepancies
                discrepancies = []
                for corr in correlations:
                    if corr['runsheet_customer'] and corr['payslip_client']:
                        if corr['runsheet_customer'].lower() != corr['payslip_client'].lower():
                            discrepancies.append({
                                'job_number': corr['job_number'],
                                'issue': 'client_mismatch',
                                'payslip_client': corr['payslip_client'],
                                'runsheet_customer': corr['runsheet_customer']
                            })
                
                return {
                    'total_correlations': len(correlations),
                    'discrepancies': discrepancies,
                    'data_quality_score': round((1 - len(discrepancies) / len(correlations)) * 100, 2) if correlations else 100
                }
        except Exception as e:
            return {'error': f"Failed to analyze correlation: {str(e)}"}
    
    @staticmethod
    def _calculate_performance_metrics(year, month):
        """Calculate key performance indicators."""
        try:
            metrics = {}
            
            # Revenue metrics
            if year:
                payslips = PayslipModel.get_all_payslips(tax_year=year)
                if payslips:
                    total_revenue = sum(p.get('net_payment', 0) for p in payslips)
                    avg_weekly = total_revenue / len(payslips) if payslips else 0
                    
                    metrics['revenue'] = {
                        'total': round(total_revenue, 2),
                        'average_weekly': round(avg_weekly, 2),
                        'weeks_count': len(payslips)
                    }
            
            # Efficiency metrics
            completion_status = RunsheetModel.get_completion_status()
            completed_days = len([status for status in completion_status.values() if status['status'] == 'completed'])
            total_days = len(completion_status)
            
            metrics['efficiency'] = {
                'completion_rate': round((completed_days / total_days * 100), 2) if total_days > 0 else 0,
                'completed_days': completed_days,
                'total_days': total_days
            }
            
            return metrics
        except Exception as e:
            return {'error': f"Failed to calculate performance metrics: {str(e)}"}
    
    @staticmethod
    def _export_to_csv(data):
        """Export data to CSV format."""
        if not data:
            return ""
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    
    @staticmethod
    def _interpret_correlation(correlation):
        """Interpret correlation coefficient."""
        if correlation >= 0.7:
            return "Strong positive correlation - more jobs typically mean higher earnings"
        elif correlation >= 0.3:
            return "Moderate positive correlation - some relationship between job count and earnings"
        elif correlation >= -0.3:
            return "Weak correlation - little relationship between job count and earnings"
        elif correlation >= -0.7:
            return "Moderate negative correlation - unusual pattern detected"
        else:
            return "Strong negative correlation - investigate data quality"
    
    @staticmethod
    def _get_month_name(month_num):
        """Convert month number to name."""
        months = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                 'July', 'August', 'September', 'October', 'November', 'December']
        return months[month_num] if 1 <= month_num <= 12 else 'Unknown'
