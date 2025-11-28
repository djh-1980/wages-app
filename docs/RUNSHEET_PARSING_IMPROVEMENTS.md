# Runsheet Parsing Improvements

## Overview
Comprehensive improvements to the runsheet parsing system to enhance data quality, accuracy, and reliability of job data extraction from PDF runsheets.

## Key Improvements Made

### 1. Enhanced Customer Name Extraction
- **Improved Cleaning**: Removes artifacts like "Customer Signature", "Customer Print", and "***DO NOT INVOICE***"
- **Pattern Matching**: Handles various customer name formats and removes leading numbers
- **Artifact Removal**: Cleans up trailing dashes and non-word characters
- **Result**: Cleaner, more consistent customer names in the database

### 2. Advanced Address Parsing
- **Multi-line Processing**: Better handling of complex multi-line addresses
- **Contact Name Filtering**: Removes contact names like "1Ellie", "tbcWILLIAM HARRIS", "MANAGER"
- **Reference Code Skipping**: Ignores store codes like "16661UK 6661UK" and "1614510810TESCO"
- **Instruction Detection**: Stops address collection when hitting job instructions or notes
- **Smart Combination**: Intelligently combines address lines with proper comma separation

### 3. Enhanced Activity Recognition
- **Expanded Patterns**: Added support for MAINTENANCE, SURVEY, INSPECTION, UPGRADE, CONFIGURATION, TRAINING, CONSULTATION
- **Partial Matching**: Maps partial terms like "TECH" → "TECH EXCHANGE", "REPAIR" → "REPAIR WITH PARTS"
- **Standardization**: Normalizes activity variations to consistent naming

### 4. Improved Postcode Extraction
- **UK Format Validation**: Proper UK postcode pattern matching
- **Automatic Formatting**: Ensures correct spacing (e.g., "M11AA" → "M1 1AA")
- **Context Awareness**: Extracts postcodes from mixed content lines

### 5. Data Validation & Cleaning
- **Job Validation**: Ensures jobs have required fields (job number + customer/activity)
- **RICO Filtering**: Skips RICO depot visits without activities (not real jobs)
- **PayPoint Audit Filtering**: Excludes Van Stock Audit jobs (zero pay administrative tasks)
- **Data Standardization**: Consistent formatting for activities, addresses, and postcodes

### 6. Enhanced Error Handling
- **Comprehensive Logging**: Better debugging information for parsing failures
- **Graceful Degradation**: Continues processing when individual lines fail
- **Validation Feedback**: Logs skipped jobs with reasons

## Technical Implementation

### New Helper Methods
```python
def clean_customer_name(self, customer_line: str) -> str
def extract_activity(self, line: str) -> Optional[str]
def extract_postcode(self, line: str) -> Optional[str]
def clean_address_line(self, line: str) -> str
def combine_address_lines(self, address_lines: List[str]) -> str
def validate_job(self, job: Dict) -> bool
def clean_job_data(self, job: Dict) -> Dict
```

### Enhanced Patterns
- **Customer Cleanup**: Regex patterns for removing common artifacts
- **Activity Variations**: Mapping of partial terms to full activity names
- **UK Postcode**: Comprehensive UK postcode validation pattern
- **Address Filtering**: Skip patterns for non-address content

### Improved Processing Flow
1. **Extract Raw Data**: Parse PDF text line by line
2. **Clean Individual Fields**: Apply field-specific cleaning rules
3. **Validate Job Data**: Ensure job meets minimum requirements
4. **Standardize Format**: Apply consistent formatting rules
5. **Database Insert**: Store cleaned, validated data

## Data Quality Improvements

### Before Improvements
- Inconsistent customer names with artifacts
- Fragmented or incomplete addresses
- Missing activity classifications
- Malformed postcodes
- Invalid job entries in database

### After Improvements
- Clean, consistent customer names
- Complete, properly formatted addresses
- Comprehensive activity classification
- Properly formatted UK postcodes
- Only valid, complete job entries

## Testing Results

The improved parsing system successfully handles:
- ✅ Customer name cleaning (removes artifacts, leading numbers)
- ✅ Activity extraction (exact matches + partial matching)
- ✅ Postcode extraction (proper UK format validation)
- ✅ Address line cleaning (filters out contact names, codes)
- ✅ Address combination (smart comma separation)
- ✅ Job validation (ensures data completeness)

## Benefits Achieved

1. **Higher Data Quality**: Cleaner, more consistent job data
2. **Better Address Parsing**: More complete and accurate addresses
3. **Improved Activity Recognition**: Better classification of job types
4. **Enhanced Validation**: Only valid jobs enter the database
5. **Better Error Handling**: More robust parsing with detailed logging
6. **Maintainable Code**: Modular helper functions for easy updates

## Future Enhancements

Potential areas for further improvement:
- Machine learning-based address parsing
- Automated activity classification training
- Real-time parsing validation dashboard
- Integration with external address validation services
- Enhanced customer name normalization

## Usage

The improved parsing system is automatically used when importing runsheets:

```bash
python3 scripts/production/import_run_sheets.py --recent 0
```

All improvements are backward compatible and preserve existing functionality while enhancing data quality.
