#!/usr/bin/env python3
"""
Test if the PDF has form fields we can extract directly.
"""

import PyPDF2
from pathlib import Path

def check_pdf_fields(pdf_path):
    """Check if PDF has extractable form fields."""
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        print(f"PDF: {pdf_path}")
        print(f"Pages: {len(reader.pages)}")
        
        # Check if PDF has form fields
        if reader.metadata:
            print(f"Metadata: {reader.metadata}")
        
        # Try to get form fields
        if hasattr(reader, 'get_form_text_fields'):
            fields = reader.get_form_text_fields()
            if fields:
                print("Form fields found:")
                for field_name, field_value in fields.items():
                    print(f"  {field_name}: {field_value}")
                return True
        
        # Check first page for form fields
        page = reader.pages[0]
        if hasattr(page, 'get_form_text_fields'):
            fields = page.get_form_text_fields()
            if fields:
                print("Page form fields found:")
                for field_name, field_value in fields.items():
                    print(f"  {field_name}: {field_value}")
                return True
        
        print("No form fields found - PDF is likely flattened")
        return False

def main():
    pdf_path = Path("RunSheets/Runsheet_12_runs_2025_11_12.pdf")
    if pdf_path.exists():
        check_pdf_fields(pdf_path)
    else:
        print(f"File not found: {pdf_path}")

if __name__ == "__main__":
    main()
