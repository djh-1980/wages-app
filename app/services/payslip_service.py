"""
PayslipService - Business logic for payslip operations.
Handles complex payslip calculations, analysis, and data processing.
"""

from ..models.payslip import PayslipModel
from ..database import get_db_connection
from datetime import datetime, timedelta
import json


class PayslipService:
    """Service class for payslip business logic and complex operations."""
    
    @staticmethod
    def get_dashboard_summary():
        """Get comprehensive dashboard summary with additional calculations."""
        try:
            # Get base summary from model
            summary = PayslipModel.get_summary()
            
            # Normalize field names for consistency
            if 'total_weeks' in summary['overall']:
                summary['overall']['total_payslips'] = summary['overall']['total_weeks']
            
            # Add business logic calculations
            if summary['overall']['total_earnings']:
                # Calculate additional metrics
                summary['overall']['weekly_average'] = summary['overall']['total_earnings'] / summary['overall']['total_payslips'] if summary['overall']['total_payslips'] > 0 else 0
                summary['overall']['monthly_estimate'] = summary['overall']['weekly_average'] * 4.33
                summary['overall']['yearly_estimate'] = summary['overall']['weekly_average'] * 52
            
            # Add performance indicators
            if summary['last_4_weeks_avg'] and summary['overall']['avg_weekly']:
                trend_percentage = ((summary['last_4_weeks_avg'] - summary['overall']['avg_weekly']) / summary['overall']['avg_weekly']) * 100
                summary['performance'] = {
                    'trend_percentage': round(trend_percentage, 2),
                    'trend_direction': 'up' if trend_percentage > 0 else 'down' if trend_percentage < 0 else 'stable'
                }
            
            return summary
        except Exception as e:
            raise Exception(f"Failed to generate dashboard summary: {str(e)}")
    
    @staticmethod
    def analyze_earnings_trend(weeks=12):
        """Analyze earnings trend with statistical analysis."""
        try:
            trend_data = PayslipModel.get_weekly_trend(limit=weeks)
            
            if len(trend_data) < 2:
                return {'error': 'Insufficient data for trend analysis'}
            
            # Calculate moving averages
            amounts = [row['net_payment'] for row in trend_data]
            
            # Simple moving average (4 weeks)
            sma_4 = []
            for i in range(3, len(amounts)):
                sma_4.append(sum(amounts[i-3:i+1]) / 4)
            
            # Calculate trend slope
            x_values = list(range(len(amounts)))
            y_values = amounts
            
            n = len(x_values)
            sum_x = sum(x_values)
            sum_y = sum(y_values)
            sum_xy = sum(x * y for x, y in zip(x_values, y_values))
            sum_x2 = sum(x * x for x in x_values)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
            
            # Determine trend strength
            if abs(slope) > 50:
                strength = 'strong'
            elif abs(slope) > 20:
                strength = 'moderate'
            else:
                strength = 'weak'
            
            return {
                'trend_data': trend_data,
                'moving_averages': sma_4,
                'slope': round(slope, 2),
                'trend_direction': 'increasing' if slope > 5 else 'decreasing' if slope < -5 else 'stable',
                'trend_strength': strength,
                'analysis_period': weeks
            }
        except Exception as e:
            raise Exception(f"Failed to analyze earnings trend: {str(e)}")
    
    @staticmethod
    def generate_tax_year_report(tax_year):
        """Generate comprehensive tax year report."""
        try:
            # Get payslips for the year
            payslips = PayslipModel.get_all_payslips(tax_year=tax_year)
            
            if not payslips:
                return {'error': f'No data found for tax year {tax_year}'}
            
            # Calculate totals
            total_gross = sum(p.get('gross_pay', 0) or 0 for p in payslips)
            total_tax = sum(p.get('tax', 0) or 0 for p in payslips)
            total_ni = sum(p.get('ni', 0) or 0 for p in payslips)
            total_pension = sum(p.get('pension', 0) or 0 for p in payslips)
            total_net = sum(p.get('net_payment', 0) or 0 for p in payslips)
            total_hours = sum(p.get('hours', 0) or 0 for p in payslips)
            
            # Calculate averages
            weeks_count = len(payslips)
            avg_gross = total_gross / weeks_count if weeks_count > 0 else 0
            avg_net = total_net / weeks_count if weeks_count > 0 else 0
            avg_hours = total_hours / weeks_count if weeks_count > 0 else 0
            
            # Calculate effective tax rate
            effective_tax_rate = (total_tax / total_gross * 100) if total_gross > 0 else 0
            effective_ni_rate = (total_ni / total_gross * 100) if total_gross > 0 else 0
            
            # Find best and worst weeks
            best_week = max(payslips, key=lambda p: p.get('net_payment', 0) or 0)
            worst_week = min(payslips, key=lambda p: p.get('net_payment', 0) or 0)
            
            return {
                'tax_year': tax_year,
                'summary': {
                    'weeks_worked': weeks_count,
                    'total_gross': round(total_gross, 2),
                    'total_tax': round(total_tax, 2),
                    'total_ni': round(total_ni, 2),
                    'total_pension': round(total_pension, 2),
                    'total_net': round(total_net, 2),
                    'total_hours': round(total_hours, 2)
                },
                'averages': {
                    'weekly_gross': round(avg_gross, 2),
                    'weekly_net': round(avg_net, 2),
                    'weekly_hours': round(avg_hours, 2),
                    'hourly_rate': round(avg_gross / avg_hours, 2) if avg_hours > 0 else 0
                },
                'tax_analysis': {
                    'effective_tax_rate': round(effective_tax_rate, 2),
                    'effective_ni_rate': round(effective_ni_rate, 2),
                    'total_deductions': round(total_tax + total_ni + total_pension, 2),
                    'take_home_percentage': round((total_net / total_gross * 100), 2) if total_gross > 0 else 0
                },
                'performance': {
                    'best_week': {
                        'week': best_week.get('week_number'),
                        'amount': best_week.get('net_payment', 0),
                        'date': best_week.get('pay_date')
                    },
                    'worst_week': {
                        'week': worst_week.get('week_number'),
                        'amount': worst_week.get('net_payment', 0),
                        'date': worst_week.get('pay_date')
                    }
                }
            }
        except Exception as e:
            raise Exception(f"Failed to generate tax year report: {str(e)}")
    
    @staticmethod
    def predict_year_end_earnings():
        """Predict year-end earnings with multiple forecasting methods."""
        try:
            # Get current year data
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT tax_year, week_number, net_payment, pay_date
                    FROM payslips
                    WHERE tax_year = (SELECT MAX(tax_year) FROM payslips)
                    ORDER BY week_number
                """)
                
                current_year_data = [dict(row) for row in cursor.fetchall()]
            
            if not current_year_data:
                return {'error': 'No current year data available'}
            
            current_year = current_year_data[0]['tax_year']
            weeks_worked = len(current_year_data)
            total_earned = sum(row['net_payment'] for row in current_year_data)
            
            # Method 1: Simple average
            avg_weekly = total_earned / weeks_worked if weeks_worked > 0 else 0
            simple_projection = avg_weekly * 52
            
            # Method 2: Trend-based projection
            recent_weeks = current_year_data[-8:] if len(current_year_data) >= 8 else current_year_data
            if len(recent_weeks) >= 2:
                x_values = list(range(len(recent_weeks)))
                y_values = [row['net_payment'] for row in recent_weeks]
                
                n = len(x_values)
                sum_x = sum(x_values)
                sum_y = sum(y_values)
                sum_xy = sum(x * y for x, y in zip(x_values, y_values))
                sum_x2 = sum(x * x for x in x_values)
                
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
                intercept = (sum_y - slope * sum_x) / n
                
                # Project remaining weeks
                weeks_remaining = 52 - weeks_worked
                trend_projection = total_earned
                for i in range(weeks_remaining):
                    week_prediction = intercept + slope * (weeks_worked + i)
                    trend_projection += max(0, week_prediction)  # Don't predict negative
            else:
                trend_projection = simple_projection
            
            # Method 3: Seasonal adjustment (if we have previous year data)
            cursor.execute("""
                SELECT AVG(net_payment) as avg_payment
                FROM payslips
                WHERE tax_year = ? AND week_number BETWEEN ? AND 52
            """, (current_year - 1, weeks_worked + 1))
            
            seasonal_row = cursor.fetchone()
            if seasonal_row and seasonal_row['avg_payment']:
                seasonal_avg = seasonal_row['avg_payment']
                seasonal_projection = total_earned + (seasonal_avg * (52 - weeks_worked))
            else:
                seasonal_projection = simple_projection
            
            # Weighted average of methods
            final_projection = (simple_projection * 0.4 + trend_projection * 0.4 + seasonal_projection * 0.2)
            
            # Calculate confidence intervals
            variance = sum((row['net_payment'] - avg_weekly) ** 2 for row in current_year_data) / weeks_worked if weeks_worked > 1 else 0
            std_dev = variance ** 0.5
            
            confidence_range = std_dev * 1.96 * (52 - weeks_worked) ** 0.5  # 95% confidence
            
            return {
                'current_year': current_year,
                'weeks_worked': weeks_worked,
                'total_earned': round(total_earned, 2),
                'projections': {
                    'simple_average': round(simple_projection, 2),
                    'trend_based': round(trend_projection, 2),
                    'seasonal_adjusted': round(seasonal_projection, 2),
                    'final_prediction': round(final_projection, 2)
                },
                'confidence': {
                    'lower_bound': round(final_projection - confidence_range, 2),
                    'upper_bound': round(final_projection + confidence_range, 2),
                    'confidence_level': '95%'
                },
                'remaining_weeks': 52 - weeks_worked,
                'avg_weekly_needed': round((final_projection - total_earned) / (52 - weeks_worked), 2) if weeks_worked < 52 else 0
            }
        except Exception as e:
            raise Exception(f"Failed to predict year-end earnings: {str(e)}")
    
    @staticmethod
    def validate_payslip_data(payslip_data):
        """Validate payslip data for consistency and accuracy."""
        errors = []
        warnings = []
        
        try:
            # Required fields validation
            required_fields = ['tax_year', 'week_number', 'net_payment']
            for field in required_fields:
                if field not in payslip_data or payslip_data[field] is None:
                    errors.append(f"Missing required field: {field}")
            
            # Data type validation
            if 'net_payment' in payslip_data:
                try:
                    float(payslip_data['net_payment'])
                except (ValueError, TypeError):
                    errors.append("Net payment must be a valid number")
            
            # Business logic validation
            if 'week_number' in payslip_data:
                week_num = payslip_data['week_number']
                if not (1 <= week_num <= 53):
                    errors.append("Week number must be between 1 and 53")
            
            if 'tax_year' in payslip_data:
                tax_year = payslip_data['tax_year']
                current_year = datetime.now().year
                if not (2020 <= tax_year <= current_year + 1):
                    warnings.append(f"Tax year {tax_year} seems unusual")
            
            # Cross-field validation
            if all(field in payslip_data for field in ['gross_pay', 'tax', 'ni', 'net_payment']):
                calculated_net = payslip_data['gross_pay'] - payslip_data['tax'] - payslip_data['ni']
                if abs(calculated_net - payslip_data['net_payment']) > 0.01:
                    warnings.append("Net payment doesn't match gross minus deductions")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Validation failed: {str(e)}"],
                'warnings': []
            }
