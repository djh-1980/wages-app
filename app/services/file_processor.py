"""
Real-time File Processor
Processes payslips and runsheets immediately as they're downloaded.
"""

import os
import time
import threading
import logging
from pathlib import Path
from datetime import datetime
import subprocess
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileProcessorHandler(FileSystemEventHandler):
    """Handles file system events for immediate processing."""
    
    def __init__(self, processor):
        self.processor = processor
        self.logger = processor.logger
        
    def on_created(self, event):
        """Handle new file creation."""
        if not event.is_directory and event.src_path.endswith('.pdf'):
            self.logger.info(f"New PDF detected: {event.src_path}")
            # Add small delay to ensure file is fully written
            threading.Timer(2.0, self.processor.process_new_file, args=[event.src_path]).start()

class RealTimeFileProcessor:
    """Processes files immediately as they're downloaded."""
    
    def __init__(self):
        self.is_monitoring = False
        self.observers = []
        
        # Setup logging
        self.logger = logging.getLogger('file_processor')
        handler = logging.FileHandler('logs/file_processor.log')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
        # Directories to monitor using the new organized structure
        self.watch_dirs = [
            Path('data/processing/manual'),      # User manual uploads
            Path('data/uploads/pending'),        # Web interface uploads
            Path('data/processing/temp'),        # Gmail downloads
            Path('data/processing/queue'),       # Files being processed
            Path('data/processing/failed')       # Failed processing files
        ]
    
    def start_monitoring(self):
        """Start monitoring directories for new files."""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.logger.info("Starting real-time file monitoring")
        
        # Create observers for each directory
        for watch_dir in self.watch_dirs:
            if watch_dir.exists():
                observer = Observer()
                handler = FileProcessorHandler(self)
                observer.schedule(handler, str(watch_dir), recursive=True)
                observer.start()
                self.observers.append(observer)
                self.logger.info(f"Monitoring directory: {watch_dir}")
    
    def stop_monitoring(self):
        """Stop monitoring directories."""
        self.is_monitoring = False
        
        for observer in self.observers:
            observer.stop()
            observer.join()
        
        self.observers.clear()
        self.logger.info("Stopped real-time file monitoring")
    
    def process_new_file(self, file_path):
        """Process a newly detected file immediately."""
        try:
            file_path = Path(file_path)
            self.logger.info(f"Processing new file: {file_path}")
            
            # Determine file type based on path
            if 'PaySlips' in str(file_path) or 'payslip' in file_path.name.lower():
                success = self._process_payslip(file_path)
            elif 'RunSheets' in str(file_path) or 'runsheet' in file_path.name.lower():
                success = self._process_runsheet(file_path)
            else:
                # Try to auto-detect based on content
                success = self._auto_process_file(file_path)
            
            if success:
                self.logger.info(f"Successfully processed: {file_path}")
            else:
                self.logger.warning(f"Failed to process: {file_path}")
                
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")
    
    def _process_payslip(self, file_path):
        """Process a single payslip file."""
        try:
            self.logger.info(f"Processing payslip: {file_path}")
            
            process = subprocess.run([
                sys.executable, 
                'scripts/extract_payslips.py', 
                '--file', str(file_path),
                '--quiet'
            ], capture_output=True, text=True, timeout=60)
            
            if process.returncode == 0:
                self.logger.info(f"Payslip processed successfully: {file_path}")
                return True
            else:
                self.logger.warning(f"Payslip processing failed: {process.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing payslip {file_path}: {str(e)}")
            return False
    
    def _process_runsheet(self, file_path):
        """Process a single runsheet file."""
        try:
            self.logger.info(f"Processing runsheet: {file_path}")
            
            process = subprocess.run([
                sys.executable, 
                'scripts/import_run_sheets.py', 
                '--file', str(file_path),
                '--quiet'
            ], capture_output=True, text=True, timeout=120)
            
            if process.returncode == 0:
                self.logger.info(f"Runsheet processed successfully: {file_path}")
                return True
            else:
                self.logger.warning(f"Runsheet processing failed: {process.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing runsheet {file_path}: {str(e)}")
            return False
    
    def _auto_process_file(self, file_path):
        """Auto-detect file type and process accordingly."""
        try:
            self.logger.info(f"Auto-detecting file type: {file_path}")
            
            # Try payslip first
            if self._process_payslip(file_path):
                return True
            
            # If payslip processing failed, try runsheet
            if self._process_runsheet(file_path):
                return True
            
            self.logger.warning(f"Could not process file as payslip or runsheet: {file_path}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error auto-processing file {file_path}: {str(e)}")
            return False
    
    def process_directory(self, directory_path, file_type=None):
        """Process all PDF files in a directory immediately."""
        try:
            directory = Path(directory_path)
            if not directory.exists():
                self.logger.warning(f"Directory does not exist: {directory}")
                return 0
            
            pdf_files = list(directory.glob('**/*.pdf'))
            processed_count = 0
            
            self.logger.info(f"Processing {len(pdf_files)} files in {directory}")
            
            for pdf_file in pdf_files:
                if file_type == 'payslips':
                    success = self._process_payslip(pdf_file)
                elif file_type == 'runsheets':
                    success = self._process_runsheet(pdf_file)
                else:
                    success = self._auto_process_file(pdf_file)
                
                if success:
                    processed_count += 1
            
            self.logger.info(f"Processed {processed_count}/{len(pdf_files)} files in {directory}")
            return processed_count
            
        except Exception as e:
            self.logger.error(f"Error processing directory {directory_path}: {str(e)}")
            return 0
    
    def get_status(self):
        """Get current processor status."""
        return {
            'is_monitoring': self.is_monitoring,
            'watched_directories': [str(d) for d in self.watch_dirs if d.exists()],
            'active_observers': len(self.observers)
        }

# Global instance
file_processor = RealTimeFileProcessor()
