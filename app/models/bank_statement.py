"""
Bank Statement Parser Model
Parses RBS CSV files and categorizes transactions for expense import
"""

import csv
import re
from datetime import datetime
from typing import List, Dict, Optional


class BankStatementParser:
    """Parse and categorize bank statement transactions."""
    
    # Categorization rules based on merchant/description patterns
    CATEGORY_RULES = {
        'Fuel': [
            'SHELL', 'BP ', 'ESSO', 'TEXACO', 'TESCO FUEL', 'ASDA FUEL', 
            'SAINSBURY FUEL', 'MORRISONS FUEL', 'PETROL', 'DIESEL'
        ],
        'Vehicle Costs': [
            'VAN FINANCE', 'VAN LOAN', 'INSURANCE', 'MOT', 'HALFORDS',
            'KWIK FIT', 'GARAGE', 'TYRES', 'CAR PARTS', 'AUTO'
        ],
        'Admin Costs': [
            'EE ', 'O2', 'VODAFONE', 'THREE', 'PHONE', 'MOBILE',
            'BT ', 'SKY', 'VIRGIN MEDIA', 'BROADBAND', 'INTERNET'
        ],
        'Other Expenses': [
            'SCREWFIX', 'TOOLSTATION', 'B&Q', 'WICKES', 'TOOL',
            'WORKWEAR', 'BOOTS', 'SAFETY', 'EQUIPMENT'
        ],
        'Professional Fees': [
            'ACCOUNTANT', 'SUBSCRIPTION', 'SOFTWARE', 'APPLE.COM',
            'MICROSOFT', 'GOOGLE', 'ADOBE'
        ]
    }
    
    # Exclude these from business expenses
    EXCLUDE_PATTERNS = [
        'SASER', 'SALARY', 'WAGES', 'PAYROLL',  # Income
        'TRANSFER', 'SAVINGS',  # Internal transfers
        'CASH WITHDRAWAL', 'ATM',  # Cash withdrawals
        'SUPERMARKET', 'TESCO STORE', 'ASDA STORE', 'SAINSBURY STORE',  # Personal shopping
        'AMAZON', 'EBAY',  # Personal online shopping (unless tools)
        'RESTAURANT', 'TAKEAWAY', 'PIZZA', 'MCDONALDS', 'KFC'  # Food (not claimable)
    ]
    
    @staticmethod
    def parse_rbs_csv(file_content: str) -> List[Dict]:
        """
        Parse RBS CSV format.
        
        Expected columns: Date, Type, Description, Value, Balance, Account Name, Account Number
        """
        transactions = []
        
        # Parse CSV
        lines = file_content.strip().split('\n')
        reader = csv.DictReader(lines)
        
        for row in reader:
            try:
                # Parse date (format: "06 Apr 2023" or "06-Apr-23")
                date_str = row['Date'].strip()
                
                # Try different date formats
                date_obj = None
                for fmt in ['%d %b %Y', '%d-%b-%y', '%d/%m/%Y']:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if not date_obj:
                    continue  # Skip if can't parse date
                
                # Format as DD/MM/YYYY for our system
                formatted_date = date_obj.strftime('%d/%m/%Y')
                
                # Parse value (negative = expense, positive = income)
                value = float(row['Value'].strip())
                
                # Only process debits (expenses)
                if value < 0:
                    amount = abs(value)
                    description = row['Description'].strip()
                    trans_type = row['Type'].strip()
                    
                    # Categorize transaction
                    category = BankStatementParser._categorize_transaction(description, trans_type)
                    
                    # Check if should be excluded
                    if not BankStatementParser._should_exclude(description):
                        transactions.append({
                            'date': formatted_date,
                            'description': description,
                            'amount': amount,
                            'type': trans_type,
                            'category': category,
                            'suggested': category is not None,  # True if auto-categorized
                            'selected': category is not None  # Pre-select if categorized
                        })
            except Exception as e:
                # Skip malformed rows
                print(f"Error parsing row: {e}")
                continue
        
        return transactions
    
    @staticmethod
    def _categorize_transaction(description: str, trans_type: str) -> Optional[str]:
        """
        Auto-categorize transaction based on description.
        Returns category name or None if can't categorize.
        """
        description_upper = description.upper()
        
        # Check each category's patterns
        for category, patterns in BankStatementParser.CATEGORY_RULES.items():
            for pattern in patterns:
                if pattern.upper() in description_upper:
                    return category
        
        # Special handling for direct debits (often recurring expenses)
        if trans_type == 'DPC' or trans_type == 'DD':
            # Check if it's a known recurring expense
            if any(word in description_upper for word in ['FINANCE', 'LOAN', 'INSURANCE']):
                return 'Vehicle Costs'
            if any(word in description_upper for word in ['PHONE', 'MOBILE', 'BROADBAND']):
                return 'Admin Costs'
        
        return None  # Unknown category
    
    @staticmethod
    def _should_exclude(description: str) -> bool:
        """Check if transaction should be excluded from business expenses."""
        description_upper = description.upper()
        
        for pattern in BankStatementParser.EXCLUDE_PATTERNS:
            if pattern.upper() in description_upper:
                return True
        
        return False
    
    @staticmethod
    def get_summary(transactions: List[Dict]) -> Dict:
        """Get summary statistics for parsed transactions."""
        total_amount = sum(t['amount'] for t in transactions)
        categorized_count = sum(1 for t in transactions if t['suggested'])
        
        # Group by category
        by_category = {}
        for trans in transactions:
            cat = trans['category'] or 'Uncategorized'
            if cat not in by_category:
                by_category[cat] = {'count': 0, 'total': 0}
            by_category[cat]['count'] += 1
            by_category[cat]['total'] += trans['amount']
        
        return {
            'total_transactions': len(transactions),
            'total_amount': round(total_amount, 2),
            'categorized_count': categorized_count,
            'categorization_rate': round(categorized_count / len(transactions) * 100, 1) if transactions else 0,
            'by_category': by_category
        }
