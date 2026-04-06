"""
HMRC Data Mapping Service for MTD Self-Employment.
Maps expense data to HMRC API format and validates submissions.
"""

from datetime import datetime

from ..models.expense import ExpenseModel
from ..database import execute_query


class HMRCMapper:
    """Map expense data to HMRC MTD format."""
    
    @staticmethod
    def calculate_quarterly_periods(tax_year):
        """
        Calculate quarterly period dates for a tax year.
        
        Args:
            tax_year: Tax year string (e.g., '2024/2025')
            
        Returns:
            list: List of quarterly periods with start/end dates
        """
        start_year = int(tax_year.split('/')[0])
        
        periods = [
            {
                'period_id': 'Q1',
                'start_date': f'{start_year}-04-06',
                'end_date': f'{start_year}-07-05',
                'due_date': f'{start_year}-08-05'
            },
            {
                'period_id': 'Q2',
                'start_date': f'{start_year}-07-06',
                'end_date': f'{start_year}-10-05',
                'due_date': f'{start_year}-11-05'
            },
            {
                'period_id': 'Q3',
                'start_date': f'{start_year}-10-06',
                'end_date': f'{start_year + 1}-01-05',
                'due_date': f'{start_year + 1}-02-05'
            },
            {
                'period_id': 'Q4',
                'start_date': f'{start_year + 1}-01-06',
                'end_date': f'{start_year + 1}-04-05',
                'due_date': f'{start_year + 1}-05-05'
            }
        ]
        
        return periods
    
    @staticmethod
    def get_period_for_date(date_str, tax_year):
        """
        Determine which quarterly period a date falls into.
        
        Args:
            date_str: Date string (DD/MM/YYYY)
            tax_year: Tax year string (e.g., '2024/2025')
            
        Returns:
            str: Period ID (Q1, Q2, Q3, Q4) or None
        """
        date = datetime.strptime(date_str, '%d/%m/%Y')
        periods = HMRCMapper.calculate_quarterly_periods(tax_year)
        
        for period in periods:
            start = datetime.strptime(period['start_date'], '%Y-%m-%d')
            end = datetime.strptime(period['end_date'], '%Y-%m-%d')
            
            if start <= date <= end:
                return period['period_id']
        
        return None
    
    @staticmethod
    def map_expenses_to_hmrc_format(expenses):
        """
        Map expenses to HMRC API format.
        
        Args:
            expenses: List of expense records
            
        Returns:
            dict: HMRC-formatted expense data
        """
        # Initialize expense categories
        expense_data = {
            'costOfGoodsBought': {'amount': 0, 'disallowableAmount': 0},
            'cisPaymentsToSubcontractors': {'amount': 0, 'disallowableAmount': 0},
            'staffCosts': {'amount': 0, 'disallowableAmount': 0},
            'travelCosts': {'amount': 0, 'disallowableAmount': 0},
            'premisesRunningCosts': {'amount': 0, 'disallowableAmount': 0},
            'maintenanceCosts': {'amount': 0, 'disallowableAmount': 0},
            'adminCosts': {'amount': 0, 'disallowableAmount': 0},
            'advertisingCosts': {'amount': 0, 'disallowableAmount': 0},
            'interest': {'amount': 0, 'disallowableAmount': 0},
            'financialCharges': {'amount': 0, 'disallowableAmount': 0},
            'badDebt': {'amount': 0, 'disallowableAmount': 0},
            'professionalFees': {'amount': 0, 'disallowableAmount': 0},
            'depreciation': {'amount': 0, 'disallowableAmount': 0},
            'other': {'amount': 0, 'disallowableAmount': 0}
        }
        
        # Map each expense to HMRC category
        for expense in expenses:
            amount = float(expense['amount'])
            hmrc_box = expense.get('hmrc_box', 'Other expenses')
            
            # Map to HMRC API field names
            if 'Cost of goods bought' in hmrc_box or 'Materials' in hmrc_box:
                expense_data['costOfGoodsBought']['amount'] += amount
            elif 'CIS payments' in hmrc_box:
                expense_data['cisPaymentsToSubcontractors']['amount'] += amount
            elif 'Maintenance costs' in hmrc_box:
                expense_data['maintenanceCosts']['amount'] += amount
            elif 'Motor expenses' in hmrc_box or 'Vehicle costs' in hmrc_box or 'Fuel' in hmrc_box:
                # Motor expenses include van finance, insurance, breakdown, fuel, vehicle costs
                expense_data['travelCosts']['amount'] += amount
            elif 'Travel costs' in hmrc_box:
                expense_data['travelCosts']['amount'] += amount
            elif 'Premises costs' in hmrc_box:
                expense_data['premisesRunningCosts']['amount'] += amount
            elif 'Admin costs' in hmrc_box:
                expense_data['adminCosts']['amount'] += amount
            elif 'Advertising' in hmrc_box:
                expense_data['advertisingCosts']['amount'] += amount
            elif 'Interest' in hmrc_box:
                expense_data['interest']['amount'] += amount
            elif 'Financial charges' in hmrc_box:
                expense_data['financialCharges']['amount'] += amount
            elif 'Professional fees' in hmrc_box:
                expense_data['professionalFees']['amount'] += amount
            elif 'Depreciation' in hmrc_box:
                expense_data['depreciation']['amount'] += amount
            else:
                expense_data['other']['amount'] += amount
        
        # Round all amounts to 2 decimal places
        for category in expense_data:
            expense_data[category]['amount'] = round(expense_data[category]['amount'], 2)
        
        # Remove categories with zero amounts
        expense_data = {k: v for k, v in expense_data.items() if v['amount'] > 0}
        
        return expense_data
    
    @staticmethod
    def get_income_for_period(start_date, end_date):
        """
        Get total income for a period from payslips.
        
        Args:
            start_date: Period start date (YYYY-MM-DD)
            end_date: Period end date (YYYY-MM-DD)
            
        Returns:
            float: Total income
        """
        # Convert dates to DD/MM/YYYY format for database query
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        query = """
            SELECT COALESCE(SUM(gross_subcontractor_payment), 0) as total_income
            FROM payslips
            WHERE date(substr(period_end, 7, 4) || '-' || 
                       substr(period_end, 4, 2) || '-' || 
                       substr(period_end, 1, 2)) 
                  BETWEEN ? AND ?
        """
        
        result = execute_query(query, (start_date, end_date), fetch_one=True)
        return round(float(result['total_income'] or 0), 2)
    
    @staticmethod
    def build_period_submission(tax_year, period_id):
        """
        Build complete period submission data for HMRC.
        
        Args:
            tax_year: Tax year string (e.g., '2024/2025')
            period_id: Period ID (Q1, Q2, Q3, Q4)
            
        Returns:
            dict: Complete submission data
        """
        periods = HMRCMapper.calculate_quarterly_periods(tax_year)
        period_info = next((p for p in periods if p['period_id'] == period_id), None)
        
        if not period_info:
            return None
        
        # Get expenses for this period
        start_date_display = datetime.strptime(period_info['start_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
        end_date_display = datetime.strptime(period_info['end_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
        
        expenses = ExpenseModel.get_expenses(
            start_date=start_date_display,
            end_date=end_date_display
        )
        
        # Get income for this period
        total_income = HMRCMapper.get_income_for_period(
            period_info['start_date'],
            period_info['end_date']
        )
        
        # Map expenses to HMRC format
        expense_data = HMRCMapper.map_expenses_to_hmrc_format(expenses)
        
        # Build submission
        submission = {
            'periodFromDate': period_info['start_date'],
            'periodToDate': period_info['end_date'],
            'from': period_info['start_date'],
            'to': period_info['end_date'],
            'incomes': {
                'turnover': total_income,
                'other': 0
            },
            'expenses': expense_data
        }
        
        return submission
    
    @staticmethod
    def validate_submission(submission_data):
        """
        Validate submission data meets HMRC requirements.
        
        Args:
            submission_data: Submission data to validate
            
        Returns:
            dict: Validation result with success status and errors
        """
        errors = []
        
        # Check required fields
        if 'from' not in submission_data or 'to' not in submission_data:
            errors.append('Missing period dates (from/to)')
        
        # Check income
        if 'incomes' not in submission_data:
            errors.append('Missing income data')
        elif 'turnover' not in submission_data['incomes']:
            errors.append('Missing turnover in income')
        
        # Check expenses
        if 'expenses' not in submission_data:
            errors.append('Missing expense data')
        elif not submission_data['expenses']:
            errors.append('No expenses provided')
        
        # Validate amounts are positive
        if 'incomes' in submission_data and 'turnover' in submission_data['incomes']:
            turnover = submission_data['incomes']['turnover']
            # Handle both dict format and simple number format
            amount = turnover.get('amount', turnover) if isinstance(turnover, dict) else turnover
            if amount < 0:
                errors.append('Turnover amount cannot be negative')
        
        if 'expenses' in submission_data:
            for category, data in submission_data['expenses'].items():
                # Handle both dict format and simple number format
                amount = data.get('amount', data) if isinstance(data, dict) else data
                if amount < 0:
                    errors.append(f'Expense amount for {category} cannot be negative')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def format_tax_year_for_hmrc(tax_year):
        """
        Convert tax year format from '2024/2025' to '2024-25'.
        
        Args:
            tax_year: Tax year in format '2024/2025'
            
        Returns:
            str: Tax year in HMRC format '2024-25'
        """
        years = tax_year.split('/')
        return f"{years[0]}-{years[1][-2:]}"
