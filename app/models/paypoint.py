"""
Paypoint model - handles Paypoint stock management database operations.
Tracks stock items, usage, and audit trails for Paypoint devices and consumables.
"""

from ..database import get_db_connection, execute_query
import sqlite3
from datetime import datetime


class PaypointModel:
    """Model for Paypoint stock management operations."""
    
    @staticmethod
    def init_tables():
        """Initialize Paypoint-related database tables."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Paypoint stock items table - individual devices with serial/TID
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paypoint_stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paypoint_type TEXT NOT NULL,  -- 'PP One', 'PP Mini', 'P-Pod', 'Rp10', 'Zebra Printer'
                    serial_ptid TEXT NOT NULL UNIQUE,  -- Serial number or TID
                    trace_stock TEXT NOT NULL,  -- Trace/Stock number
                    status TEXT DEFAULT 'available',  -- 'available', 'deployed', 'returned'
                    current_job_number TEXT,  -- Job number if deployed
                    deployment_date TIMESTAMP,
                    return_date TIMESTAMP,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Paypoint deployments table (when devices are deployed to jobs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paypoint_deployments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_item_id INTEGER NOT NULL,
                    job_number TEXT NOT NULL,
                    paypoint_type TEXT NOT NULL,
                    serial_ptid TEXT NOT NULL,
                    trace_stock TEXT NOT NULL,
                    deployment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    customer TEXT,
                    location TEXT,
                    installation_notes TEXT,
                    status TEXT DEFAULT 'deployed',  -- 'deployed', 'returned'
                    FOREIGN KEY (stock_item_id) REFERENCES paypoint_stock(id)
                )
            """)
            
            # Paypoint returns table (when devices are returned from jobs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paypoint_returns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    deployment_id INTEGER NOT NULL,
                    stock_item_id INTEGER NOT NULL,
                    job_number TEXT NOT NULL,
                    paypoint_type TEXT NOT NULL,
                    return_serial_ptid TEXT NOT NULL,  -- Serial/TID being returned
                    return_trace TEXT NOT NULL,  -- Return trace number
                    return_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    return_reason TEXT,
                    return_notes TEXT,
                    FOREIGN KEY (deployment_id) REFERENCES paypoint_deployments(id),
                    FOREIGN KEY (stock_item_id) REFERENCES paypoint_stock(id)
                )
            """)
            
            # Paypoint audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paypoint_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    record_id INTEGER,
                    old_values TEXT,  -- JSON string
                    new_values TEXT,  -- JSON string
                    user_id TEXT DEFAULT 'system',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            print("✅ Paypoint database tables initialized")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Error initializing Paypoint tables: {e}")
            raise
        finally:
            conn.close()
    
    @staticmethod
    def get_all_stock_items():
        """Get all Paypoint devices."""
        query = """
            SELECT 
                id, paypoint_type, serial_ptid, trace_stock, status, 
                current_job_number, deployment_date, return_date, notes, created_at
            FROM paypoint_stock
            ORDER BY paypoint_type, serial_ptid
        """
        
        rows = execute_query(query, fetch_all=True)
        
        items = []
        for row in rows:
            items.append({
                'id': row[0],
                'paypoint_type': row[1],
                'serial_ptid': row[2],
                'trace_stock': row[3],
                'status': row[4],
                'current_job_number': row[5],
                'deployment_date': row[6],
                'return_date': row[7],
                'notes': row[8],
                'created_at': row[9]
            })
        
        return items
    
    @staticmethod
    def add_paypoint_device(paypoint_type, serial_ptid, trace_stock, notes=''):
        """Add a new Paypoint device to stock."""
        if not paypoint_type or not serial_ptid or not trace_stock:
            raise ValueError('Paypoint type, serial/TID, and trace/stock are required')
        
        # Validate Paypoint type
        valid_types = ['PP One', 'PP Mini', 'P-Pod', 'Rp10', 'Zebra Printer']
        if paypoint_type not in valid_types:
            raise ValueError(f'Invalid Paypoint type. Must be one of: {", ".join(valid_types)}')
        
        query = """
            INSERT INTO paypoint_stock 
            (paypoint_type, serial_ptid, trace_stock, notes)
            VALUES (?, ?, ?, ?)
        """
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (paypoint_type, serial_ptid, trace_stock, notes))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError('Device with this serial/TID already exists')
    
    @staticmethod
    def deploy_device(stock_item_id, job_number, customer='', location='', installation_notes=''):
        """Deploy a Paypoint device to a job."""
        if not job_number:
            raise ValueError('Job number is required')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if device is available
            cursor.execute("""
                SELECT paypoint_type, serial_ptid, trace_stock, status 
                FROM paypoint_stock 
                WHERE id = ?
            """, (stock_item_id,))
            
            result = cursor.fetchone()
            if not result:
                raise ValueError('Device not found')
            
            paypoint_type, serial_ptid, trace_stock, status = result
            
            if status != 'available':
                raise ValueError(f'Device is not available (current status: {status})')
            
            # Update device status
            cursor.execute("""
                UPDATE paypoint_stock 
                SET status = 'deployed', current_job_number = ?, deployment_date = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (job_number, stock_item_id))
            
            # Record deployment
            cursor.execute("""
                INSERT INTO paypoint_deployments 
                (stock_item_id, job_number, paypoint_type, serial_ptid, trace_stock, customer, location, installation_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (stock_item_id, job_number, paypoint_type, serial_ptid, trace_stock, customer, location, installation_notes))
            
            deployment_id = cursor.lastrowid
            conn.commit()
            return deployment_id
    
    @staticmethod
    def return_device(deployment_id, return_serial_ptid, return_trace, return_reason='', return_notes=''):
        """Return a deployed Paypoint device."""
        if not return_serial_ptid or not return_trace:
            raise ValueError('Return serial/TID and return trace are required')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get deployment details
            cursor.execute("""
                SELECT d.stock_item_id, d.job_number, d.paypoint_type, d.serial_ptid, d.trace_stock, d.status
                FROM paypoint_deployments d
                WHERE d.id = ?
            """, (deployment_id,))
            
            result = cursor.fetchone()
            if not result:
                raise ValueError('Deployment not found')
            
            stock_item_id, job_number, paypoint_type, serial_ptid, trace_stock, status = result
            
            if status == 'returned':
                raise ValueError('Device has already been returned')
            
            # Update device status to returned
            cursor.execute("""
                UPDATE paypoint_stock 
                SET status = 'returned', current_job_number = NULL, return_date = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (stock_item_id,))
            
            # Update deployment status
            cursor.execute("""
                UPDATE paypoint_deployments 
                SET status = 'returned'
                WHERE id = ?
            """, (deployment_id,))
            
            # Record return
            cursor.execute("""
                INSERT INTO paypoint_returns 
                (deployment_id, stock_item_id, job_number, paypoint_type, return_serial_ptid, return_trace, return_reason, return_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (deployment_id, stock_item_id, job_number, paypoint_type, return_serial_ptid, return_trace, return_reason, return_notes))
            
            return_id = cursor.lastrowid
            conn.commit()
            return return_id
    
    @staticmethod
    def get_deployments(limit=100):
        """Get deployment history."""
        query = """
            SELECT 
                d.id, d.job_number, d.paypoint_type, d.serial_ptid, d.trace_stock,
                d.deployment_date, d.customer, d.location, d.installation_notes, d.status,
                ps.status as device_status
            FROM paypoint_deployments d
            JOIN paypoint_stock ps ON d.stock_item_id = ps.id
            ORDER BY d.deployment_date DESC
            LIMIT ?
        """
        
        rows = execute_query(query, (limit,), fetch_all=True)
        
        deployments = []
        for row in rows:
            deployments.append({
                'id': row[0],
                'job_number': row[1],
                'paypoint_type': row[2],
                'serial_ptid': row[3],
                'trace_stock': row[4],
                'deployment_date': row[5],
                'customer': row[6],
                'location': row[7],
                'installation_notes': row[8],
                'status': row[9],
                'device_status': row[10]
            })
        
        return deployments
    
    @staticmethod
    def get_returns(limit=100):
        """Get return history."""
        query = """
            SELECT 
                r.id, r.job_number, r.paypoint_type, r.return_serial_ptid, r.return_trace,
                r.return_date, r.return_reason, r.return_notes,
                d.deployment_date, d.customer, d.location
            FROM paypoint_returns r
            JOIN paypoint_deployments d ON r.deployment_id = d.id
            ORDER BY r.return_date DESC
            LIMIT ?
        """
        
        rows = execute_query(query, (limit,), fetch_all=True)
        
        returns = []
        for row in rows:
            returns.append({
                'id': row[0],
                'job_number': row[1],
                'paypoint_type': row[2],
                'return_serial_ptid': row[3],
                'return_trace': row[4],
                'return_date': row[5],
                'return_reason': row[6],
                'return_notes': row[7],
                'deployment_date': row[8],
                'customer': row[9],
                'location': row[10]
            })
        
        return returns
    
    @staticmethod
    def get_audit_history(limit=200):
        """Get complete audit history combining deployments and returns."""
        # Get deployments
        deployments = PaypointModel.get_deployments(limit)
        returns = PaypointModel.get_returns(limit)
        
        # Combine and sort by date
        audit_history = []
        
        for deployment in deployments:
            audit_history.append({
                'type': 'deployment',
                'date': deployment['deployment_date'],
                'job_number': deployment['job_number'],
                'paypoint_type': deployment['paypoint_type'],
                'serial_ptid': deployment['serial_ptid'],
                'trace_stock': deployment['trace_stock'],
                'customer': deployment['customer'],
                'location': deployment['location'],
                'notes': deployment['installation_notes'],
                'status': deployment['status']
            })
        
        for return_item in returns:
            audit_history.append({
                'type': 'return',
                'date': return_item['return_date'],
                'job_number': return_item['job_number'],
                'paypoint_type': return_item['paypoint_type'],
                'serial_ptid': return_item['return_serial_ptid'],
                'trace_stock': return_item['return_trace'],
                'customer': return_item['customer'],
                'location': return_item['location'],
                'notes': return_item['return_notes'],
                'status': 'returned'
            })
        
        # Sort by date (newest first)
        audit_history.sort(key=lambda x: x['date'] or '', reverse=True)
        
        return audit_history[:limit]
    
    @staticmethod
    def get_deployed_devices():
        """Get currently deployed devices."""
        query = """
            SELECT id, paypoint_type, serial_ptid, trace_stock, current_job_number, deployment_date
            FROM paypoint_stock
            WHERE status = 'deployed'
            ORDER BY deployment_date DESC
        """
        
        rows = execute_query(query, fetch_all=True)
        
        devices = []
        for row in rows:
            devices.append({
                'id': row[0],
                'paypoint_type': row[1],
                'serial_ptid': row[2],
                'trace_stock': row[3],
                'current_job_number': row[4],
                'deployment_date': row[5]
            })
        
        return devices
    
    @staticmethod
    def get_stock_summary():
        """Get stock summary statistics."""
        query = """
            SELECT 
                COUNT(*) as total_devices,
                COUNT(CASE WHEN status = 'available' THEN 1 END) as available_devices,
                COUNT(CASE WHEN status = 'deployed' THEN 1 END) as deployed_devices,
                COUNT(CASE WHEN status = 'returned' THEN 1 END) as returned_devices
            FROM paypoint_stock
        """
        
        row = execute_query(query, fetch_one=True)
        
        # Get count by device type
        type_query = """
            SELECT paypoint_type, COUNT(*) as count, status
            FROM paypoint_stock
            GROUP BY paypoint_type, status
            ORDER BY paypoint_type
        """
        
        type_rows = execute_query(type_query, fetch_all=True)
        
        device_types = {}
        for type_row in type_rows:
            device_type, count, status = type_row
            if device_type not in device_types:
                device_types[device_type] = {'available': 0, 'deployed': 0, 'returned': 0}
            device_types[device_type][status] = count
        
        return {
            'total_devices': row[0] or 0,
            'available_devices': row[1] or 0,
            'deployed_devices': row[2] or 0,
            'returned_devices': row[3] or 0,
            'device_types': device_types
        }
