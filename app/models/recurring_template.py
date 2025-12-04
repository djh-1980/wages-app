"""
Recurring Payment Template Model
Manages templates for recurring expenses with smart matching
"""

from datetime import datetime, timedelta
from ..database import get_db_connection, execute_query


class RecurringTemplateModel:
    """Model for recurring payment templates."""
    
    @staticmethod
    def create_template(name, category_id, expected_amount, frequency, 
                       merchant_pattern, day_of_month=None, is_active=True,
                       tolerance_amount=5.0, auto_import=False):
        """
        Create a new recurring payment template.
        
        Args:
            name: Template name (e.g., "Van Finance")
            category_id: Expense category ID
            expected_amount: Expected payment amount
            frequency: monthly, quarterly, annually, weekly
            merchant_pattern: Pattern to match in bank description (e.g., "SANTANDER VAN")
            day_of_month: Expected day of month (1-31) for monthly payments
            is_active: Whether template is active
            tolerance_amount: Amount variance tolerance for matching (default £5)
            auto_import: Automatically import matched transactions
        """
        query = """
            INSERT INTO recurring_templates 
            (name, category_id, expected_amount, frequency, merchant_pattern, 
             day_of_month, is_active, tolerance_amount, auto_import, next_expected_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Calculate next expected date
        next_date = RecurringTemplateModel._calculate_next_date(
            frequency, day_of_month
        )
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                name, category_id, expected_amount, frequency, merchant_pattern,
                day_of_month, is_active, tolerance_amount, auto_import, next_date
            ))
            conn.commit()
            return cursor.lastrowid
    
    @staticmethod
    def get_templates(active_only=False):
        """Get all recurring templates."""
        query = """
            SELECT 
                rt.id, rt.name, rt.category_id, rt.expected_amount, rt.frequency,
                rt.merchant_pattern, rt.day_of_month, rt.is_active, rt.tolerance_amount,
                rt.auto_import, rt.next_expected_date, rt.last_matched_date,
                rt.created_at, rt.updated_at,
                c.name as category_name, c.hmrc_box
            FROM recurring_templates rt
            JOIN expense_categories c ON rt.category_id = c.id
        """
        
        if active_only:
            query += " WHERE rt.is_active = 1"
        
        query += " ORDER BY rt.name"
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_template_by_id(template_id):
        """Get a single template by ID."""
        query = """
            SELECT 
                rt.id, rt.name, rt.category_id, rt.expected_amount, rt.frequency,
                rt.merchant_pattern, rt.day_of_month, rt.is_active, rt.tolerance_amount,
                rt.auto_import, rt.next_expected_date, rt.last_matched_date,
                c.name as category_name
            FROM recurring_templates rt
            JOIN expense_categories c ON rt.category_id = c.id
            WHERE rt.id = ?
        """
        row = execute_query(query, (template_id,), fetch_one=True)
        return dict(row) if row else None
    
    @staticmethod
    def update_template(template_id, **kwargs):
        """Update a recurring template."""
        allowed_fields = [
            'name', 'category_id', 'expected_amount', 'frequency', 
            'merchant_pattern', 'day_of_month', 'is_active', 
            'tolerance_amount', 'auto_import'
        ]
        
        updates = []
        params = []
        
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                updates.append(f"{field} = ?")
                params.append(value)
        
        if not updates:
            return False
        
        # Recalculate next expected date if frequency or day changed
        if 'frequency' in kwargs or 'day_of_month' in kwargs:
            template = RecurringTemplateModel.get_template_by_id(template_id)
            if template:
                next_date = RecurringTemplateModel._calculate_next_date(
                    kwargs.get('frequency', template['frequency']),
                    kwargs.get('day_of_month', template['day_of_month'])
                )
                updates.append("next_expected_date = ?")
                params.append(next_date)
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(template_id)
        
        query = f"UPDATE recurring_templates SET {', '.join(updates)} WHERE id = ?"
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    def delete_template(template_id):
        """Delete a recurring template."""
        query = "DELETE FROM recurring_templates WHERE id = ?"
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (template_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    def match_transaction(description, amount, date):
        """
        Try to match a transaction to a recurring template.
        
        Returns: (template_id, confidence_score) or (None, 0)
        """
        templates = RecurringTemplateModel.get_templates(active_only=True)
        
        best_match = None
        best_score = 0
        
        for template in templates:
            score = 0
            
            # Check merchant pattern match (case-insensitive)
            pattern = template['merchant_pattern'].upper()
            desc_upper = description.upper()
            
            if pattern in desc_upper:
                score += 50  # Strong match
            elif any(word in desc_upper for word in pattern.split()):
                score += 25  # Partial match
            
            # Check amount match (within tolerance)
            amount_diff = abs(amount - template['expected_amount'])
            if amount_diff <= template['tolerance_amount']:
                score += 30
                # Bonus for exact match
                if amount_diff == 0:
                    score += 10
            
            # Check date proximity to expected date
            if template['next_expected_date']:
                try:
                    expected = datetime.strptime(template['next_expected_date'], '%d/%m/%Y')
                    actual = datetime.strptime(date, '%d/%m/%Y')
                    days_diff = abs((actual - expected).days)
                    
                    if days_diff <= 3:
                        score += 20
                    elif days_diff <= 7:
                        score += 10
                except:
                    pass
            
            if score > best_score:
                best_score = score
                best_match = template['id']
        
        # Require minimum confidence of 60% to match
        if best_score >= 60:
            return best_match, best_score
        
        return None, 0
    
    @staticmethod
    def update_last_matched(template_id, matched_date):
        """Update the last matched date and calculate next expected date."""
        template = RecurringTemplateModel.get_template_by_id(template_id)
        if not template:
            return False
        
        # Calculate next expected date based on matched date
        try:
            matched = datetime.strptime(matched_date, '%d/%m/%Y')
            next_date = RecurringTemplateModel._calculate_next_date_from(
                matched, template['frequency']
            )
            
            query = """
                UPDATE recurring_templates 
                SET last_matched_date = ?, next_expected_date = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (matched_date, next_date, template_id))
                conn.commit()
                return True
        except:
            return False
    
    @staticmethod
    def get_due_templates():
        """Get templates that are due for payment (within next 7 days)."""
        today = datetime.now()
        week_ahead = today + timedelta(days=7)
        
        templates = RecurringTemplateModel.get_templates(active_only=True)
        due_templates = []
        
        for template in templates:
            if template['next_expected_date']:
                try:
                    expected = datetime.strptime(template['next_expected_date'], '%d/%m/%Y')
                    if today <= expected <= week_ahead:
                        due_templates.append(template)
                except:
                    pass
        
        return due_templates
    
    @staticmethod
    def _calculate_next_date(frequency, day_of_month=None):
        """Calculate next expected date based on frequency."""
        today = datetime.now()
        return RecurringTemplateModel._calculate_next_date_from(today, frequency, day_of_month)
    
    @staticmethod
    def _calculate_next_date_from(from_date, frequency, day_of_month=None):
        """Calculate next expected date from a given date."""
        if frequency == 'monthly':
            # Next month, same day
            if day_of_month:
                next_date = from_date.replace(day=min(day_of_month, 28))
            else:
                next_date = from_date
            
            # Add one month
            if next_date.month == 12:
                next_date = next_date.replace(year=next_date.year + 1, month=1)
            else:
                next_date = next_date.replace(month=next_date.month + 1)
        
        elif frequency == 'quarterly':
            next_date = from_date + timedelta(days=90)
        
        elif frequency == 'annually':
            next_date = from_date.replace(year=from_date.year + 1)
        
        elif frequency == 'weekly':
            next_date = from_date + timedelta(days=7)
        
        else:
            next_date = from_date + timedelta(days=30)  # Default to monthly
        
        return next_date.strftime('%d/%m/%Y')
    
    @staticmethod
    def get_statistics():
        """Get statistics about recurring templates."""
        query = """
            SELECT 
                COUNT(*) as total_templates,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_templates,
                SUM(expected_amount) as total_monthly_amount
            FROM recurring_templates
            WHERE is_active = 1 AND frequency = 'monthly'
        """
        
        row = execute_query(query, fetch_one=True)
        return dict(row) if row else {}
