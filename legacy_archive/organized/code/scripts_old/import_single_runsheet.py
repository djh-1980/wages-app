#!/usr/bin/env python3
"""
Import a single runsheet file to test the improved parsing.
"""

import sys
import os
from pathlib import Path

# Change to parent directory so relative paths work correctly
os.chdir(Path(__file__).parent.parent)
sys.path.append(str(Path.cwd()))

from scripts.import_run_sheets import RunSheetImporter

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 import_single_runsheet.py <path_to_pdf>")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)
    
    print(f"Importing single runsheet: {file_path}")
    
    importer = RunSheetImporter()
    try:
        imported_count = importer.import_run_sheet(file_path)
        print(f"Successfully imported {imported_count} jobs")
    finally:
        importer.close()

if __name__ == "__main__":
    main()
