"""
RunsheetService - Business logic for runsheet operations.
Handles job management, status tracking, and runsheet analysis.
"""

from ..models.runsheet import RunsheetModel
from ..database import get_db_connection
from datetime import datetime, timedelta
import json


class RunsheetService:
    """Service class for runsheet business logic and complex operations."""
    
    @staticmethod
    def get_dashboard_summary():
        """Get enhanced runsheet dashboard summary with additional metrics."""
        try:
            # Get base summary from model
            summary = RunsheetModel.get_summary()
            
            # Add business logic calculations
            if summary['overall']['total_days'] > 0:
                summary['efficiency'] = {
                    'jobs_per_day': round(summary['overall']['total_jobs'] / summary['overall']['total_days'], 2),
                    'customers_per_day': round(summary['overall']['unique_customers'] / summary['overall']['total_days'], 2)
                }
            
            # Add recent activity analysis
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get last 7 days activity
                cursor.execute("""
                    SELECT COUNT(DISTINCT date) as active_days,
                           COUNT(*) as recent_jobs
                    FROM run_sheet_jobs
                    WHERE date >= date('now', '-7 days')
                """)
                recent = dict(cursor.fetchone())
                summary['recent_activity'] = recent
            
            return summary
        except Exception as e:
            raise Exception(f"Failed to generate runsheet dashboard summary: {str(e)}")
    
    @staticmethod
    def analyze_job_completion_rates(date_from=None, date_to=None):
        """Analyze job completion rates and patterns."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Build date filter
                date_filter = ""
                params = []
                if date_from and date_to:
                    date_filter = "WHERE date BETWEEN ? AND ?"
                    params = [date_from, date_to]
                elif date_from:
                    date_filter = "WHERE date >= ?"
                    params = [date_from]
                elif date_to:
                    date_filter = "WHERE date <= ?"
                    params = [date_to]
                
                # Get completion statistics
                cursor.execute(f"""
                    SELECT 
                        status,
                        COUNT(*) as count,
                        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM run_sheet_jobs {date_filter}), 2) as percentage
                    FROM run_sheet_jobs
                    {date_filter}
                    GROUP BY status
                    ORDER BY count DESC
                """, params * 2 if date_filter else [])
                
                status_breakdown = [dict(row) for row in cursor.fetchall()]
                
                # Get daily completion rates
                cursor.execute(f"""
                    SELECT 
                        date,
                        COUNT(*) as total_jobs,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_jobs,
                        ROUND(COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*), 2) as completion_rate
                    FROM run_sheet_jobs
                    {date_filter}
                    GROUP BY date
                    ORDER BY date DESC
                    LIMIT 30
                """, params)
                
                daily_rates = [dict(row) for row in cursor.fetchall()]
                
                # Calculate overall metrics
                total_jobs = sum(row['count'] for row in status_breakdown)
                completed_jobs = next((row['count'] for row in status_breakdown if row['status'] == 'completed'), 0)
                overall_completion_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
                
                return {
                    'overall_completion_rate': round(overall_completion_rate, 2),
                    'total_jobs_analyzed': total_jobs,
                    'status_breakdown': status_breakdown,
                    'daily_completion_rates': daily_rates,
                    'analysis_period': {
                        'from': date_from,
                        'to': date_to
                    }
                }
        except Exception as e:
            raise Exception(f"Failed to analyze job completion rates: {str(e)}")
    
    @staticmethod
    def get_customer_performance_analysis():
        """Analyze customer job patterns and performance."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get customer statistics
                cursor.execute("""
                    SELECT 
                        customer,
                        COUNT(*) as total_jobs,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_jobs,
                        COUNT(CASE WHEN status = 'missed' THEN 1 END) as missed_jobs,
                        COUNT(CASE WHEN status = 'dnco' THEN 1 END) as dnco_jobs,
                        ROUND(COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*), 2) as completion_rate,
                        MIN(date) as first_job_date,
                        MAX(date) as last_job_date
                    FROM run_sheet_jobs
                    WHERE customer IS NOT NULL AND customer != ''
                    GROUP BY customer
                    HAVING COUNT(*) >= 3
                    ORDER BY total_jobs DESC
                    LIMIT 50
                """)
                
                customer_stats = [dict(row) for row in cursor.fetchall()]
                
                # Categorize customers
                high_volume = [c for c in customer_stats if c['total_jobs'] >= 20]
                high_completion = [c for c in customer_stats if c['completion_rate'] >= 90]
                problematic = [c for c in customer_stats if c['completion_rate'] < 70 and c['total_jobs'] >= 5]
                
                return {
                    'customer_statistics': customer_stats,
                    'categories': {
                        'high_volume': high_volume,
                        'high_completion_rate': high_completion,
                        'problematic': problematic
                    },
                    'summary': {
                        'total_customers': len(customer_stats),
                        'avg_completion_rate': round(sum(c['completion_rate'] for c in customer_stats) / len(customer_stats), 2) if customer_stats else 0
                    }
                }
        except Exception as e:
            raise Exception(f"Failed to analyze customer performance: {str(e)}")
    
    @staticmethod
    def optimize_route_suggestions(date):
        """Suggest route optimizations for a specific date."""
        try:
            jobs = RunsheetModel.get_jobs_for_date(date)
            
            if not jobs:
                return {'error': f'No jobs found for date {date}'}
            
            # Group jobs by postcode/area
            postcode_groups = {}
            for job in jobs:
                postcode = job.get('postcode', 'Unknown')
                if postcode not in postcode_groups:
                    postcode_groups[postcode] = []
                postcode_groups[postcode].append(job)
            
            # Identify potential optimizations
            optimizations = []
            
            # Check for scattered jobs in same postcode
            for postcode, postcode_jobs in postcode_groups.items():
                if len(postcode_jobs) >= 3:
                    optimizations.append({
                        'type': 'group_by_area',
                        'postcode': postcode,
                        'job_count': len(postcode_jobs),
                        'suggestion': f'Consider grouping {len(postcode_jobs)} jobs in {postcode} area together'
                    })
            
            # Check for priority job distribution
            priority_jobs = [j for j in jobs if j.get('priority') == 'High']
            if len(priority_jobs) > 0:
                optimizations.append({
                    'type': 'priority_scheduling',
                    'count': len(priority_jobs),
                    'suggestion': f'Schedule {len(priority_jobs)} high-priority jobs early in the day'
                })
            
            # Check for customer clustering
            customer_jobs = {}
            for job in jobs:
                customer = job.get('customer', 'Unknown')
                if customer not in customer_jobs:
                    customer_jobs[customer] = []
                customer_jobs[customer].append(job)
            
            multi_job_customers = {k: v for k, v in customer_jobs.items() if len(v) > 1}
            if multi_job_customers:
                optimizations.append({
                    'type': 'customer_clustering',
                    'customers': list(multi_job_customers.keys()),
                    'suggestion': f'Group multiple jobs for the same customer: {", ".join(multi_job_customers.keys())}'
                })
            
            return {
                'date': date,
                'total_jobs': len(jobs),
                'postcode_distribution': {k: len(v) for k, v in postcode_groups.items()},
                'optimizations': optimizations,
                'efficiency_score': min(100, max(0, 100 - len(optimizations) * 10))  # Simple scoring
            }
        except Exception as e:
            raise Exception(f"Failed to generate route suggestions: {str(e)}")
    
    @staticmethod
    def track_daily_progress(date):
        """Track and analyze daily progress for a specific date."""
        try:
            jobs = RunsheetModel.get_jobs_for_date(date)
            daily_data = RunsheetModel.get_daily_data(date)
            
            if not jobs:
                return {'error': f'No jobs found for date {date}'}
            
            # Calculate progress metrics
            total_jobs = len(jobs)
            completed_jobs = len([j for j in jobs if j.get('status') == 'completed'])
            missed_jobs = len([j for j in jobs if j.get('status') == 'missed'])
            dnco_jobs = len([j for j in jobs if j.get('status') == 'dnco'])
            extra_jobs = len([j for j in jobs if j.get('status') == 'extra'])
            pending_jobs = len([j for j in jobs if j.get('status') in ['pending', None]])
            
            completion_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            
            # Determine overall status
            if pending_jobs == 0 and daily_data.get('mileage'):
                overall_status = 'completed'
            elif completed_jobs > 0 or daily_data.get('mileage'):
                overall_status = 'in_progress'
            else:
                overall_status = 'not_started'
            
            # Calculate efficiency metrics
            efficiency_score = completion_rate
            if missed_jobs > 0:
                efficiency_score -= (missed_jobs / total_jobs * 20)  # Penalty for missed jobs
            if extra_jobs > 0:
                efficiency_score += (extra_jobs / total_jobs * 10)  # Bonus for extra jobs
            
            efficiency_score = max(0, min(100, efficiency_score))
            
            return {
                'date': date,
                'overall_status': overall_status,
                'job_statistics': {
                    'total_jobs': total_jobs,
                    'completed': completed_jobs,
                    'missed': missed_jobs,
                    'dnco': dnco_jobs,
                    'extra': extra_jobs,
                    'pending': pending_jobs
                },
                'metrics': {
                    'completion_rate': round(completion_rate, 2),
                    'efficiency_score': round(efficiency_score, 2)
                },
                'daily_data': daily_data,
                'recommendations': RunsheetService._generate_daily_recommendations(jobs, daily_data)
            }
        except Exception as e:
            raise Exception(f"Failed to track daily progress: {str(e)}")
    
    @staticmethod
    def _generate_daily_recommendations(jobs, daily_data):
        """Generate recommendations based on daily progress."""
        recommendations = []
        
        pending_jobs = [j for j in jobs if j.get('status') in ['pending', None]]
        if pending_jobs:
            recommendations.append({
                'type': 'action_required',
                'message': f'{len(pending_jobs)} jobs still need status updates'
            })
        
        if not daily_data.get('mileage'):
            recommendations.append({
                'type': 'data_missing',
                'message': 'Mileage data not recorded yet'
            })
        
        missed_jobs = [j for j in jobs if j.get('status') == 'missed']
        if missed_jobs:
            recommendations.append({
                'type': 'follow_up',
                'message': f'{len(missed_jobs)} missed jobs may need rescheduling'
            })
        
        return recommendations
    
    @staticmethod
    def validate_job_data(job_data):
        """Validate job data for consistency and completeness."""
        errors = []
        warnings = []
        
        try:
            # Required fields validation
            required_fields = ['date', 'job_number', 'customer']
            for field in required_fields:
                if field not in job_data or not job_data[field]:
                    errors.append(f"Missing required field: {field}")
            
            # Date format validation
            if 'date' in job_data:
                try:
                    datetime.strptime(job_data['date'], '%d/%m/%Y')
                except ValueError:
                    errors.append("Date must be in DD/MM/YYYY format")
            
            # Status validation
            valid_statuses = ['pending', 'completed', 'missed', 'dnco', 'extra']
            if 'status' in job_data and job_data['status'] not in valid_statuses:
                errors.append(f"Status must be one of: {', '.join(valid_statuses)}")
            
            # Business logic validation
            if 'job_number' in job_data:
                job_num = str(job_data['job_number'])
                if not job_num.isdigit() or len(job_num) < 3:
                    warnings.append("Job number should be a numeric value with at least 3 digits")
            
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
