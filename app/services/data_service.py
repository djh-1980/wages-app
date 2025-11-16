"""
DataService - Business logic for data management operations.
Handles sync, backup, validation, and data integrity operations.
"""

from ..models.payslip import PayslipModel
from ..models.runsheet import RunsheetModel
from ..models.attendance import AttendanceModel
from ..models.settings import SettingsModel
from ..database import get_db_connection, DB_PATH
from ..utils.logging_utils import log_settings_action
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import sys
import sqlite3
import shutil
import json
import os


class DataService:
    """Service class for data management and integrity operations."""
    
    @staticmethod
    def perform_intelligent_sync(sync_type='auto'):
        """Perform intelligent sync based on data analysis."""
        try:
            log_settings_action('INTELLIGENT_SYNC', f'Starting intelligent sync (type: {sync_type})')
            
            sync_plan = DataService._analyze_sync_requirements()
            results = {
                'sync_plan': sync_plan,
                'operations_performed': [],
                'success': True,
                'total_time': 0
            }
            
            start_time = datetime.now()
            
            # Execute sync operations based on analysis
            if sync_plan['payslips']['needs_sync']:
                log_settings_action('INTELLIGENT_SYNC', 'Syncing payslips based on analysis')
                payslip_result = DataService._sync_payslips_intelligent(sync_plan['payslips'])
                results['operations_performed'].append({
                    'type': 'payslips',
                    'result': payslip_result
                })
            
            if sync_plan['runsheets']['needs_sync']:
                log_settings_action('INTELLIGENT_SYNC', 'Syncing runsheets based on analysis')
                runsheet_result = DataService._sync_runsheets_intelligent(sync_plan['runsheets'])
                results['operations_performed'].append({
                    'type': 'runsheets',
                    'result': runsheet_result
                })
            
            # Auto-backup if significant changes
            if len(results['operations_performed']) > 0:
                backup_result = DataService.create_intelligent_backup('auto_sync')
                results['operations_performed'].append({
                    'type': 'backup',
                    'result': backup_result
                })
            
            end_time = datetime.now()
            results['total_time'] = (end_time - start_time).total_seconds()
            
            log_settings_action('INTELLIGENT_SYNC', f'Intelligent sync completed in {results["total_time"]:.2f} seconds')
            return results
            
        except Exception as e:
            log_settings_action('INTELLIGENT_SYNC', f'Intelligent sync failed: {str(e)}', 'ERROR')
            raise Exception(f"Intelligent sync failed: {str(e)}")
    
    @staticmethod
    def validate_data_integrity():
        """Comprehensive data integrity validation."""
        try:
            validation_results = {
                'overall_health': 'good',
                'issues_found': [],
                'warnings': [],
                'statistics': {},
                'recommendations': []
            }
            
            # Database connectivity test
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                    table_count = cursor.fetchone()[0]
                    validation_results['statistics']['table_count'] = table_count
            except Exception as e:
                validation_results['issues_found'].append({
                    'type': 'database_connectivity',
                    'severity': 'critical',
                    'message': f'Database connection failed: {str(e)}'
                })
                validation_results['overall_health'] = 'critical'
                return validation_results
            
            # Payslip data validation
            payslip_validation = DataService._validate_payslip_integrity()
            validation_results['statistics']['payslips'] = payslip_validation['statistics']
            validation_results['issues_found'].extend(payslip_validation['issues'])
            validation_results['warnings'].extend(payslip_validation['warnings'])
            
            # Runsheet data validation
            runsheet_validation = DataService._validate_runsheet_integrity()
            validation_results['statistics']['runsheets'] = runsheet_validation['statistics']
            validation_results['issues_found'].extend(runsheet_validation['issues'])
            validation_results['warnings'].extend(runsheet_validation['warnings'])
            
            # Cross-system validation
            cross_validation = DataService._validate_cross_system_integrity()
            validation_results['statistics']['cross_system'] = cross_validation['statistics']
            validation_results['issues_found'].extend(cross_validation['issues'])
            validation_results['warnings'].extend(cross_validation['warnings'])
            
            # Determine overall health
            critical_issues = [issue for issue in validation_results['issues_found'] if issue['severity'] == 'critical']
            major_issues = [issue for issue in validation_results['issues_found'] if issue['severity'] == 'major']
            
            if critical_issues:
                validation_results['overall_health'] = 'critical'
            elif major_issues:
                validation_results['overall_health'] = 'poor'
            elif validation_results['warnings']:
                validation_results['overall_health'] = 'fair'
            
            # Generate recommendations
            validation_results['recommendations'] = DataService._generate_health_recommendations(validation_results)
            
            return validation_results
            
        except Exception as e:
            raise Exception(f"Data integrity validation failed: {str(e)}")
    
    @staticmethod
    def create_intelligent_backup(backup_type='manual'):
        """Create intelligent backup with metadata and compression."""
        try:
            backup_dir = Path('data/database/backups')
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f'intelligent_backup_{backup_type}_{timestamp}'
            
            # Create backup metadata
            metadata = {
                'backup_type': backup_type,
                'created_at': datetime.now().isoformat(),
                'database_size': os.path.getsize(DB_PATH),
                'statistics': DataService._get_database_statistics()
            }
            
            # Copy database
            backup_db_path = backup_dir / f'{backup_name}.db'
            shutil.copy2(DB_PATH, backup_db_path)
            
            # Save metadata
            metadata_path = backup_dir / f'{backup_name}_metadata.json'
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Calculate backup size
            backup_size = backup_db_path.stat().st_size
            
            # Clean old backups if needed
            DataService._cleanup_old_backups(backup_dir)
            
            return {
                'success': True,
                'backup_name': backup_name,
                'backup_path': str(backup_db_path),
                'metadata_path': str(metadata_path),
                'size_mb': round(backup_size / (1024 * 1024), 2),
                'metadata': metadata
            }
            
        except Exception as e:
            raise Exception(f"Intelligent backup failed: {str(e)}")
    
    @staticmethod
    def optimize_database():
        """Optimize database performance and clean up."""
        try:
            optimization_results = {
                'operations_performed': [],
                'space_saved': 0,
                'performance_improvement': 'estimated'
            }
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get initial database size
                initial_size = os.path.getsize(DB_PATH)
                
                # Vacuum database
                cursor.execute("VACUUM")
                optimization_results['operations_performed'].append('vacuum')
                
                # Analyze database
                cursor.execute("ANALYZE")
                optimization_results['operations_performed'].append('analyze')
                
                # Reindex
                cursor.execute("REINDEX")
                optimization_results['operations_performed'].append('reindex')
                
                conn.commit()
            
            # Calculate space saved
            final_size = os.path.getsize(DB_PATH)
            optimization_results['space_saved'] = initial_size - final_size
            optimization_results['space_saved_mb'] = round(optimization_results['space_saved'] / (1024 * 1024), 2)
            
            log_settings_action('DATABASE_OPTIMIZATION', f'Database optimized, saved {optimization_results["space_saved_mb"]} MB')
            
            return optimization_results
            
        except Exception as e:
            raise Exception(f"Database optimization failed: {str(e)}")
    
    @staticmethod
    def _analyze_sync_requirements():
        """Analyze what needs to be synced based on data patterns."""
        try:
            sync_plan = {
                'payslips': {'needs_sync': False, 'reason': '', 'priority': 'low'},
                'runsheets': {'needs_sync': False, 'reason': '', 'priority': 'low'}
            }
            
            # Check payslip sync requirements
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check last payslip date
                cursor.execute("SELECT MAX(pay_date) FROM payslips WHERE pay_date IS NOT NULL")
                last_payslip = cursor.fetchone()[0]
                
                if last_payslip:
                    last_date = datetime.strptime(last_payslip, '%d/%m/%Y')
                    days_since_last = (datetime.now() - last_date).days
                    
                    if days_since_last > 14:
                        sync_plan['payslips']['needs_sync'] = True
                        sync_plan['payslips']['reason'] = f'Last payslip is {days_since_last} days old'
                        sync_plan['payslips']['priority'] = 'high' if days_since_last > 21 else 'medium'
                else:
                    sync_plan['payslips']['needs_sync'] = True
                    sync_plan['payslips']['reason'] = 'No payslips found in database'
                    sync_plan['payslips']['priority'] = 'high'
                
                # Check runsheet sync requirements
                cursor.execute("SELECT MAX(date) FROM run_sheet_jobs WHERE date IS NOT NULL")
                last_runsheet = cursor.fetchone()[0]
                
                if last_runsheet:
                    last_date = datetime.strptime(last_runsheet, '%d/%m/%Y')
                    days_since_last = (datetime.now() - last_date).days
                    
                    if days_since_last > 7:
                        sync_plan['runsheets']['needs_sync'] = True
                        sync_plan['runsheets']['reason'] = f'Last runsheet is {days_since_last} days old'
                        sync_plan['runsheets']['priority'] = 'high' if days_since_last > 14 else 'medium'
                else:
                    sync_plan['runsheets']['needs_sync'] = True
                    sync_plan['runsheets']['reason'] = 'No runsheets found in database'
                    sync_plan['runsheets']['priority'] = 'high'
            
            return sync_plan
            
        except Exception as e:
            return {
                'payslips': {'needs_sync': False, 'reason': f'Analysis failed: {str(e)}', 'priority': 'low'},
                'runsheets': {'needs_sync': False, 'reason': f'Analysis failed: {str(e)}', 'priority': 'low'}
            }
    
    @staticmethod
    def _sync_payslips_intelligent(sync_config):
        """Intelligent payslip sync based on configuration."""
        try:
            # Determine optimal date range for sync
            if sync_config['priority'] == 'high':
                days_back = 30
            elif sync_config['priority'] == 'medium':
                days_back = 14
            else:
                days_back = 7
            
            search_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
            
            # Run sync process
            process = subprocess.Popen(
                [sys.executable, 'scripts/production/download_runsheets_gmail.py', '--payslips', f'--date={search_date}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=180)
            
            if process.returncode == 0:
                # Run extraction
                extract_process = subprocess.Popen(
                    [sys.executable, 'scripts/production/extract_payslips.py', '--recent', str(days_back // 7)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                extract_stdout, extract_stderr = extract_process.communicate(timeout=120)
                
                return {
                    'success': extract_process.returncode == 0,
                    'download_output': stdout,
                    'extract_output': extract_stdout,
                    'error': extract_stderr if extract_process.returncode != 0 else None
                }
            else:
                return {
                    'success': False,
                    'error': stderr,
                    'output': stdout
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _sync_runsheets_intelligent(sync_config):
        """Intelligent runsheet sync based on configuration."""
        try:
            # Determine optimal date range for sync
            if sync_config['priority'] == 'high':
                days_back = 21
            elif sync_config['priority'] == 'medium':
                days_back = 14
            else:
                days_back = 7
            
            search_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
            
            # Run sync process
            process = subprocess.Popen(
                [sys.executable, 'scripts/production/download_runsheets_gmail.py', '--runsheets', f'--date={search_date}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=180)
            
            if process.returncode == 0:
                # Run import
                import_process = subprocess.Popen(
                    [sys.executable, 'scripts/production/import_run_sheets.py', '--recent', str(days_back)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                import_stdout, import_stderr = import_process.communicate(timeout=300)
                
                return {
                    'success': import_process.returncode == 0,
                    'download_output': stdout,
                    'import_output': import_stdout,
                    'error': import_stderr if import_process.returncode != 0 else None
                }
            else:
                return {
                    'success': False,
                    'error': stderr,
                    'output': stdout
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _validate_payslip_integrity():
        """Validate payslip data integrity."""
        issues = []
        warnings = []
        statistics = {}
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Count records
                cursor.execute("SELECT COUNT(*) FROM payslips")
                statistics['total_payslips'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM job_items")
                statistics['total_job_items'] = cursor.fetchone()[0]
                
                # Check for missing data
                cursor.execute("SELECT COUNT(*) FROM payslips WHERE net_payment IS NULL OR net_payment = 0")
                missing_payments = cursor.fetchone()[0]
                if missing_payments > 0:
                    warnings.append({
                        'type': 'missing_data',
                        'severity': 'minor',
                        'message': f'{missing_payments} payslips have missing or zero net payment'
                    })
                
                # Check for duplicate weeks
                cursor.execute("""
                    SELECT tax_year, week_number, COUNT(*) as count
                    FROM payslips
                    GROUP BY tax_year, week_number
                    HAVING count > 1
                """)
                duplicates = cursor.fetchall()
                if duplicates:
                    issues.append({
                        'type': 'duplicate_data',
                        'severity': 'major',
                        'message': f'{len(duplicates)} duplicate week entries found'
                    })
                
                statistics['duplicate_weeks'] = len(duplicates)
                
        except Exception as e:
            issues.append({
                'type': 'validation_error',
                'severity': 'critical',
                'message': f'Payslip validation failed: {str(e)}'
            })
        
        return {
            'issues': issues,
            'warnings': warnings,
            'statistics': statistics
        }
    
    @staticmethod
    def _validate_runsheet_integrity():
        """Validate runsheet data integrity."""
        issues = []
        warnings = []
        statistics = {}
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Count records
                cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs")
                statistics['total_jobs'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT date) FROM run_sheet_jobs")
                statistics['unique_dates'] = cursor.fetchone()[0]
                
                # Check for missing customer data
                cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs WHERE customer IS NULL OR customer = ''")
                missing_customers = cursor.fetchone()[0]
                if missing_customers > 0:
                    warnings.append({
                        'type': 'missing_data',
                        'severity': 'minor',
                        'message': f'{missing_customers} jobs have missing customer information'
                    })
                
                statistics['missing_customers'] = missing_customers
                
        except Exception as e:
            issues.append({
                'type': 'validation_error',
                'severity': 'critical',
                'message': f'Runsheet validation failed: {str(e)}'
            })
        
        return {
            'issues': issues,
            'warnings': warnings,
            'statistics': statistics
        }
    
    @staticmethod
    def _validate_cross_system_integrity():
        """Validate data consistency across systems."""
        issues = []
        warnings = []
        statistics = {}
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check for job numbers that exist in payslips but not runsheets
                cursor.execute("""
                    SELECT COUNT(DISTINCT ji.job_number)
                    FROM job_items ji
                    LEFT JOIN run_sheet_jobs rs ON ji.job_number = rs.job_number
                    WHERE ji.job_number IS NOT NULL 
                    AND rs.job_number IS NULL
                """)
                payslip_only_jobs = cursor.fetchone()[0]
                
                # Check for job numbers that exist in runsheets but not payslips
                cursor.execute("""
                    SELECT COUNT(DISTINCT rs.job_number)
                    FROM run_sheet_jobs rs
                    LEFT JOIN job_items ji ON rs.job_number = ji.job_number
                    WHERE rs.job_number IS NOT NULL 
                    AND ji.job_number IS NULL
                """)
                runsheet_only_jobs = cursor.fetchone()[0]
                
                statistics['payslip_only_jobs'] = payslip_only_jobs
                statistics['runsheet_only_jobs'] = runsheet_only_jobs
                
                if payslip_only_jobs > 0:
                    warnings.append({
                        'type': 'data_mismatch',
                        'severity': 'minor',
                        'message': f'{payslip_only_jobs} jobs exist in payslips but not runsheets'
                    })
                
                if runsheet_only_jobs > 0:
                    warnings.append({
                        'type': 'data_mismatch',
                        'severity': 'minor',
                        'message': f'{runsheet_only_jobs} jobs exist in runsheets but not payslips'
                    })
                
        except Exception as e:
            issues.append({
                'type': 'validation_error',
                'severity': 'critical',
                'message': f'Cross-system validation failed: {str(e)}'
            })
        
        return {
            'issues': issues,
            'warnings': warnings,
            'statistics': statistics
        }
    
    @staticmethod
    def _get_database_statistics():
        """Get comprehensive database statistics."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Table counts
                tables = ['payslips', 'job_items', 'run_sheet_jobs', 'attendance', 'settings']
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        stats[f'{table}_count'] = cursor.fetchone()[0]
                    except:
                        stats[f'{table}_count'] = 0
                
                # Date ranges
                cursor.execute("SELECT MIN(pay_date), MAX(pay_date) FROM payslips WHERE pay_date IS NOT NULL")
                payslip_dates = cursor.fetchone()
                if payslip_dates[0]:
                    stats['payslip_date_range'] = {
                        'from': payslip_dates[0],
                        'to': payslip_dates[1]
                    }
                
                cursor.execute("SELECT MIN(date), MAX(date) FROM run_sheet_jobs WHERE date IS NOT NULL")
                runsheet_dates = cursor.fetchone()
                if runsheet_dates[0]:
                    stats['runsheet_date_range'] = {
                        'from': runsheet_dates[0],
                        'to': runsheet_dates[1]
                    }
                
                return stats
                
        except Exception as e:
            return {'error': f'Failed to get statistics: {str(e)}'}
    
    @staticmethod
    def _cleanup_old_backups(backup_dir, keep_count=10):
        """Clean up old backup files, keeping only the most recent ones."""
        try:
            backup_files = list(backup_dir.glob('intelligent_backup_*.db'))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove old backups
            for old_backup in backup_files[keep_count:]:
                old_backup.unlink()
                # Also remove corresponding metadata file
                metadata_file = backup_dir / f'{old_backup.stem}_metadata.json'
                if metadata_file.exists():
                    metadata_file.unlink()
                    
        except Exception as e:
            log_settings_action('BACKUP_CLEANUP', f'Failed to cleanup old backups: {str(e)}', 'WARNING')
    
    @staticmethod
    def _generate_health_recommendations(validation_results):
        """Generate recommendations based on validation results."""
        recommendations = []
        
        critical_issues = [issue for issue in validation_results['issues_found'] if issue['severity'] == 'critical']
        if critical_issues:
            recommendations.append({
                'priority': 'urgent',
                'action': 'Address critical database issues immediately',
                'details': 'Critical issues detected that may cause data loss or system instability'
            })
        
        if validation_results['statistics'].get('duplicate_weeks', 0) > 0:
            recommendations.append({
                'priority': 'high',
                'action': 'Remove duplicate payslip entries',
                'details': 'Duplicate week entries can cause incorrect calculations'
            })
        
        if len(validation_results['warnings']) > 5:
            recommendations.append({
                'priority': 'medium',
                'action': 'Review and clean up data quality issues',
                'details': 'Multiple data quality warnings detected'
            })
        
        return recommendations
