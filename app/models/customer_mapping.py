"""
Customer Mapping Model
Handles customer name mapping and consolidation
"""

import sqlite3
from pathlib import Path

class CustomerMappingModel:
    def __init__(self):
        self.db_path = Path(__file__).parent.parent.parent / 'data/database/payslips.db'
    
    def get_db_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def get_all_mappings(self):
        """Get all customer mappings."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, original_customer, mapped_customer, created_at, notes
                FROM customer_mappings
                ORDER BY mapped_customer, original_customer
            """)
            
            mappings = []
            for row in cursor.fetchall():
                mappings.append({
                    'id': row[0],
                    'original_customer': row[1],
                    'mapped_customer': row[2],
                    'created_at': row[3],
                    'notes': row[4]
                })
            
            return mappings
    
    def get_mapped_customer(self, original_customer):
        """Get the mapped customer name or return original if no mapping exists."""
        if not original_customer:
            return original_customer
            
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT mapped_customer 
                FROM customer_mappings 
                WHERE original_customer = ?
            """, (original_customer,))
            
            result = cursor.fetchone()
            return result[0] if result else original_customer
    
    def add_mapping(self, original_customer, mapped_customer, notes=None):
        """Add a new customer mapping."""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO customer_mappings (original_customer, mapped_customer, notes)
                    VALUES (?, ?, ?)
                """, (original_customer, mapped_customer, notes))
                conn.commit()
                return {'success': True, 'id': cursor.lastrowid}
        except sqlite3.IntegrityError:
            return {'success': False, 'error': 'Mapping already exists for this customer'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_mapping(self, mapping_id, original_customer, mapped_customer, notes=None):
        """Update an existing customer mapping."""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE customer_mappings 
                    SET original_customer = ?, mapped_customer = ?, notes = ?
                    WHERE id = ?
                """, (original_customer, mapped_customer, notes, mapping_id))
                
                if cursor.rowcount == 0:
                    return {'success': False, 'error': 'Mapping not found'}
                
                conn.commit()
                return {'success': True}
        except sqlite3.IntegrityError:
            return {'success': False, 'error': 'Mapping already exists for this customer'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_mapping(self, mapping_id):
        """Delete a customer mapping."""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM customer_mappings WHERE id = ?", (mapping_id,))
                
                if cursor.rowcount == 0:
                    return {'success': False, 'error': 'Mapping not found'}
                
                conn.commit()
                return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_unique_customers(self):
        """Get all unique customer names from run_sheet_jobs for mapping suggestions."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT customer
                FROM run_sheet_jobs
                WHERE customer IS NOT NULL AND customer != ''
                ORDER BY customer
            """)
            
            return [row[0] for row in cursor.fetchall()]
    
    def get_mapping_suggestions(self):
        """Get suggested mappings based on similar customer names."""
        customers = self.get_unique_customers()
        suggestions = []
        
        # Group similar customers (basic fuzzy matching)
        processed = set()
        
        for customer in customers:
            if customer in processed:
                continue
                
            # Find similar customers
            similar = []
            base_name = self._extract_base_name(customer)
            
            for other_customer in customers:
                if other_customer != customer and other_customer not in processed:
                    other_base = self._extract_base_name(other_customer)
                    
                    # Check if they share a common base name
                    if base_name and other_base and (
                        base_name.lower() in other_base.lower() or 
                        other_base.lower() in base_name.lower() or
                        self._similar_names(base_name, other_base)
                    ):
                        similar.append(other_customer)
            
            if similar:
                # Suggest the shortest name as the mapped name
                all_names = [customer] + similar
                mapped_name = min(all_names, key=len)
                
                suggestions.append({
                    'mapped_customer': mapped_name,
                    'original_customers': [name for name in all_names if name != mapped_name]
                })
                
                # Mark all as processed
                processed.add(customer)
                processed.update(similar)
        
        return suggestions
    
    def _extract_base_name(self, customer_name):
        """Extract base company name from customer string."""
        if not customer_name:
            return ""
            
        # Remove common suffixes and prefixes
        name = customer_name
        
        # Remove common business suffixes
        suffixes = [' LIMITED', ' LTD', ' PLC', ' UK', ' SERVICES', ' NETWORK']
        for suffix in suffixes:
            if name.upper().endswith(suffix):
                name = name[:-len(suffix)].strip()
        
        # Extract first part before dash or hyphen
        if ' - ' in name:
            name = name.split(' - ')[0].strip()
        
        return name.strip()
    
    def _similar_names(self, name1, name2):
        """Check if two names are similar (basic similarity check)."""
        name1_words = set(name1.upper().split())
        name2_words = set(name2.upper().split())
        
        # Check if they share significant words
        common_words = name1_words.intersection(name2_words)
        
        # Consider similar if they share at least one significant word (length > 3)
        significant_common = [word for word in common_words if len(word) > 3]
        
        return len(significant_common) > 0
    
    def get_mapping_stats(self):
        """Get statistics about customer mappings."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Count total mappings
            cursor.execute("SELECT COUNT(*) FROM customer_mappings")
            total_mappings = cursor.fetchone()[0]
            
            # Count unique mapped customers
            cursor.execute("SELECT COUNT(DISTINCT mapped_customer) FROM customer_mappings")
            unique_mapped = cursor.fetchone()[0]
            
            # Count total unique customers in system
            cursor.execute("SELECT COUNT(DISTINCT customer) FROM run_sheet_jobs WHERE customer IS NOT NULL")
            total_customers = cursor.fetchone()[0]
            
            return {
                'total_mappings': total_mappings,
                'unique_mapped_customers': unique_mapped,
                'total_customers_in_system': total_customers,
                'unmapped_customers': total_customers - total_mappings
            }
