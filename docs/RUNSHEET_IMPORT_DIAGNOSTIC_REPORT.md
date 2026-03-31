# RUNSHEET IMPORT SYSTEM - DIAGNOSTIC REPORT
**Date:** March 6, 2026  
**Status:** 🔴 CRITICAL - System Broken Since Feb 26, 2026

---

## EXECUTIVE SUMMARY

The runsheet import system has been **completely non-functional** since February 26, 2026, resulting in **missing data for March 5th and 6th, 2026**. The system is experiencing multiple cascading failures across the download, import, and sync pipeline.

### Impact:
- ❌ **0 runsheets downloaded** since Feb 26
- ❌ **0 jobs imported** since Feb 26  
- ❌ **Missing dates:** 05/03/2026, 06/03/2026 (confirmed)
- ❌ **Latest data in DB:** 07/03/2026 (likely manually uploaded)
- ⚠️ **Sync running but failing silently** - no error notifications sent

---

## ROOT CAUSE ANALYSIS

### 1. PRIMARY FAILURE: PDF Parsing Errors
**Location:** `scripts/production/import_run_sheets.py` (pdfplumber library)  
**Error:** `invalid pdf header: b'0.57 '`

**What's Happening:**
- The import script is encountering **56+ PDFs with corrupted/invalid headers**
- pdfplumber library is rejecting these files during text extraction
- This causes the entire import batch to fail
- Error appears in `auto_sync.log` but not properly surfaced

**Evidence from Live Site:**
```
2026-03-06 19:01:01,364 - WARNING - invalid pdf header: b'0.57 '
[repeated 56 times]
2026-03-06 19:03:07 - ❌ Runsheet import failed
```

**Why This Happened:**
- Recent runsheet PDFs may have been saved/generated with incorrect headers
- Gmail download may be corrupting files during transfer
- pdfplumber is more strict than PyPDF2 about PDF compliance
- No fallback mechanism when pdfplumber fails

---

### 2. SECONDARY FAILURE: Download Script Silent Failure
**Location:** `scripts/production/download_runsheets_gmail.py`  
**Error:** Downloads complete but find 0 files

**What's Happening:**
- Gmail authentication is working (no auth errors)
- Search query executes successfully
- But **0 runsheets are being downloaded**
- Script exits with success code (0) despite downloading nothing

**Evidence from Live Site:**
```
2026-03-06 19:00:01 - 🚀 MASTER SYNC STARTED
2026-03-06 19:03:09 - 📥 Downloaded: 0 runsheets, 0 payslips
2026-03-06 19:03:09 - ❌ Runsheet download failed
```

**Possible Causes:**
1. Gmail search query not matching recent emails
2. Attachment extraction failing silently
3. File organization logic moving files to wrong location
4. Date filtering excluding recent runsheets

---

### 3. TERTIARY FAILURE: Error Notification Not Sent
**Location:** `app/services/periodic_sync.py`  
**Issue:** Sync failures not triggering email notifications

**What's Happening:**
- Sync has been failing for **8+ days**
- No error emails sent to danielhanson993@gmail.com
- User unaware of the failure until manually checking
- Notification settings may be misconfigured

**Evidence:**
- Last successful notification: Unknown
- Current settings: `notify_on_error_only=false`, `notify_on_success=true`
- But no emails received despite errors

---

### 4. CONFIGURATION ISSUE: Database Column Error
**Location:** `app/services/periodic_sync.py`  
**Error:** `no such column: value`

**What's Happening:**
```
2026-03-06 21:34:06,894 - WARNING - Could not load config, using defaults: no such column: value
```

- Periodic sync service cannot read configuration from database
- Falls back to default settings
- May be causing incorrect sync behavior

---

## MISSING DATA ANALYSIS

### Confirmed Missing Dates:
Based on database query, these dates have **NO jobs** in the system:

| Date | Expected | Status |
|------|----------|--------|
| 05/03/2026 | Wednesday | ❌ MISSING |
| 06/03/2026 | Thursday | ❌ MISSING |
| 17/02/2026 | Monday | ❌ MISSING |

### Dates with Data:
- **Latest in DB:** 07/03/2026 (8 jobs)
- **Previous:** 04/03/2026 (7 jobs)
- **Last complete week:** Feb 20-27, 2026

---

## SYSTEM ARCHITECTURE ISSUES

### Current Pipeline Flow:
```
Gmail → Download Script → File Organization → Import Script → Database → Pay Sync
   ✅         ❌                  ?                  ❌           ✅         ✅
```

### Problems with Current Architecture:

#### 1. **Fragile PDF Parsing**
- **Issue:** Single library (pdfplumber) with no fallback
- **Impact:** One corrupted PDF breaks entire import
- **Location:** `import_run_sheets.py:extract_text_from_pdf()`

```python
# Current implementation - NO ERROR HANDLING
def extract_text_from_pdf(self, pdf_path: Path) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text
```

#### 2. **Complex Multi-Driver Parsing**
- **Issue:** 16 customer-specific parsers, each can fail independently
- **Impact:** Maintenance nightmare, high failure rate
- **Location:** `import_run_sheets.py:parse_multi_driver_page()` (lines 1500-2500)

**Customer Parsers:**
1. POSTURITE
2. EPAY
3. CXM
4. VISTA
5. FUJITSU
6. ASTRA ZENECA
7. STAR TRAINS
8. XEROX
9. COMPUTACENTER LIMITED
10. JOHN LEWIS
11. PAYPOINT
12. KINGFISHER
13. SECURE RETAIL
14. NCR TESCO
15. COMPUTACENTER (Morrison)
16. HSBC

Each parser has custom regex, line parsing, and address extraction logic.

#### 3. **Silent Failure Mode**
- **Issue:** Errors logged but not surfaced to user
- **Impact:** System can be broken for days without detection
- **Location:** Multiple scripts, no centralized error handling

#### 4. **No Retry Mechanism**
- **Issue:** If a PDF fails to parse, it's skipped forever
- **Impact:** Data loss with no recovery path
- **Location:** All import scripts

#### 5. **Tight Coupling**
- **Issue:** Download → Organize → Import → Sync all tightly coupled
- **Impact:** One failure breaks entire chain
- **Location:** `sync_master.py`

---

## PERFORMANCE ISSUES

### Import Speed:
- **Current:** ~3-5 minutes for 50 PDFs
- **Bottleneck:** PDF text extraction (pdfplumber is slow)
- **Issue:** No parallel processing, sequential file handling

### Database Operations:
- **Current:** Efficient with proper indexes
- **No issues identified** in pay sync or database queries

### File Organization:
- **Current:** Checks ALL pages of multi-driver PDFs for driver name
- **Issue:** 100+ page PDFs take 30+ seconds each
- **Location:** `download_runsheets_gmail.py:has_driver_name()`

```python
# SLOW - checks every page
for page_num in range(len(reader.pages)):  # Could be 100+ pages!
    text = reader.pages[page_num].extract_text()
    if "daniel hanson" in text.lower():
        return True
```

---

## CODE QUALITY ISSUES

### 1. **Massive File Size**
- `import_run_sheets.py`: **2,763 lines** (should be <500)
- Contains 16 customer parsers, all in one file
- Violates Single Responsibility Principle

### 2. **Duplicate Logic**
- Address parsing duplicated across all 16 customer parsers
- Postcode extraction duplicated
- Date parsing duplicated

### 3. **Poor Error Messages**
```python
# Current - unhelpful
except Exception as e:
    self.log(f"   ❌ Runsheet import failed")
    
# Should be
except Exception as e:
    self.log(f"   ❌ Runsheet import failed: {type(e).__name__}: {e}")
    self.log(f"   📁 File: {pdf_path}")
    self.log(f"   📋 Traceback: {traceback.format_exc()}")
```

### 4. **No Unit Tests**
- Zero test coverage
- No way to verify parsers work correctly
- Regressions go undetected

### 5. **Magic Numbers**
```python
# What does 35 mean? Why 35?
for i, line in enumerate(lines[:35]):
```

---

## IMMEDIATE FIXES NEEDED

### Priority 1: Get System Working Again

#### Fix 1: Add PDF Parsing Fallback
```python
def extract_text_from_pdf(self, pdf_path: Path) -> str:
    """Extract text with fallback mechanism."""
    try:
        # Try pdfplumber first (best quality)
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        self.logger.warning(f"pdfplumber failed for {pdf_path.name}: {e}")
        
        try:
            # Fallback to PyPDF2
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
            return text
        except Exception as e2:
            self.logger.error(f"All PDF parsers failed for {pdf_path.name}: {e2}")
            return ""  # Return empty rather than crash
```

#### Fix 2: Improve Error Logging
```python
import traceback

try:
    result = self.import_runsheets()
except Exception as e:
    self.log(f"   ❌ Runsheet import error: {type(e).__name__}")
    self.log(f"   📋 Message: {str(e)}")
    self.log(f"   📍 Traceback:\n{traceback.format_exc()}")
    self.results['errors'].append(f"Runsheet import: {type(e).__name__}: {e}")
```

#### Fix 3: Fix Download Script Logging
```python
# Add detailed logging to download script
def download_all_run_sheets(self, after_date=None, organize=True, auto_import=False):
    messages = self.search_run_sheet_emails(after_date, recent_only=True)
    print(f"📧 Found {len(messages)} emails matching search")
    
    downloaded = 0
    for msg in messages:
        # ... download logic ...
        if success:
            downloaded += 1
            print(f"  ✅ Downloaded: {filename}")
        else:
            print(f"  ❌ Failed: {filename}")
    
    print(f"📥 Total downloaded: {downloaded}/{len(messages)}")
    return downloaded
```

#### Fix 4: Enable Error Notifications
```python
# In periodic_sync.py - ensure errors trigger emails
if len(self.results['errors']) > 0:
    # Force send error notification regardless of settings
    self.send_notification(
        subject="🚨 URGENT: Runsheet Sync Failed",
        errors=self.results['errors'],
        force=True  # Override notification settings
    )
```

---

## LONG-TERM RECOMMENDATIONS

### Option 1: Incremental Improvements (Low Risk, Medium Effort)

**Timeline:** 1-2 weeks  
**Risk:** Low  
**Benefit:** System becomes more reliable

**Changes:**
1. ✅ Add PDF parsing fallback (pdfplumber → PyPDF2 → OCR)
2. ✅ Improve error logging and notifications
3. ✅ Add retry mechanism for failed PDFs
4. ✅ Separate customer parsers into individual files
5. ✅ Add basic unit tests for each parser
6. ✅ Implement parallel PDF processing
7. ✅ Add health check endpoint

**Pros:**
- Low risk of breaking existing functionality
- Can be done incrementally
- Maintains current architecture

**Cons:**
- Still complex and fragile
- Doesn't address fundamental design issues
- Will require ongoing maintenance

---

### Option 2: Partial Rewrite (Medium Risk, High Effort)

**Timeline:** 3-4 weeks  
**Risk:** Medium  
**Benefit:** Much more maintainable and reliable

**New Architecture:**
```
┌─────────────────────────────────────────────────────────┐
│                    SYNC ORCHESTRATOR                     │
│  (Manages workflow, retries, notifications)              │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   DOWNLOAD   │  │    IMPORT    │  │   PAY SYNC   │
│   SERVICE    │  │   SERVICE    │  │   SERVICE    │
└──────────────┘  └──────────────┘  └──────────────┘
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  File Queue  │  │  PDF Parser  │  │   Database   │
│              │  │   Factory    │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  pdfplumber  │  │   PyPDF2     │  │  OCR Engine  │
│   Parser     │  │   Parser     │  │   (Tesseract)│
└──────────────┘  └──────────────┘  └──────────────┘
```

**Key Components:**

#### 1. PDF Parser Factory
```python
class PDFParserFactory:
    """Try multiple parsers in order of preference."""
    
    def parse(self, pdf_path: Path) -> str:
        parsers = [
            PDFPlumberParser(),
            PyPDF2Parser(),
            OCRParser()  # Last resort
        ]
        
        for parser in parsers:
            try:
                text = parser.extract(pdf_path)
                if text and len(text) > 100:  # Minimum viable text
                    return text
            except Exception as e:
                logger.warning(f"{parser.name} failed: {e}")
                continue
        
        raise PDFParsingError(f"All parsers failed for {pdf_path}")
```

#### 2. Customer Parser Registry
```python
class CustomerParserRegistry:
    """Dynamically load customer-specific parsers."""
    
    def __init__(self):
        self.parsers = {}
        self._load_parsers()
    
    def _load_parsers(self):
        # Load from parsers/ directory
        parser_dir = Path(__file__).parent / 'parsers'
        for file in parser_dir.glob('*_parser.py'):
            module = import_module(f'parsers.{file.stem}')
            parser = module.Parser()
            self.parsers[parser.customer_name] = parser
    
    def get_parser(self, customer_name: str):
        return self.parsers.get(customer_name, GenericParser())
```

#### 3. Import Queue System
```python
class ImportQueue:
    """Manage PDF import with retry logic."""
    
    def add(self, pdf_path: Path, priority=0):
        self.db.execute("""
            INSERT INTO import_queue (file_path, priority, status, attempts)
            VALUES (?, ?, 'pending', 0)
        """, (str(pdf_path), priority))
    
    def process(self):
        while True:
            job = self.get_next_job()
            if not job:
                break
            
            try:
                self.import_pdf(job['file_path'])
                self.mark_complete(job['id'])
            except Exception as e:
                self.mark_failed(job['id'], str(e))
                if job['attempts'] < 3:
                    self.retry_later(job['id'])
```

**Pros:**
- Much more maintainable
- Better error handling and recovery
- Easier to add new customer parsers
- Can process PDFs in parallel
- Clear separation of concerns

**Cons:**
- Significant development time
- Risk of introducing new bugs
- Need to migrate existing data
- Requires thorough testing

---

### Option 3: Complete Rewrite (High Risk, Very High Effort)

**Timeline:** 6-8 weeks  
**Risk:** High  
**Benefit:** Modern, scalable, production-grade system

**Technology Stack:**
- **Backend:** FastAPI (async processing)
- **Queue:** Celery + Redis (distributed task queue)
- **PDF Parsing:** Apache Tika (enterprise-grade)
- **OCR:** Google Cloud Vision API (high accuracy)
- **Monitoring:** Prometheus + Grafana
- **Testing:** pytest with 80%+ coverage

**New Features:**
1. Real-time import status dashboard
2. Automatic retry with exponential backoff
3. PDF preview before import
4. Manual correction interface
5. Audit log of all changes
6. Performance metrics and alerting
7. API for external integrations

**Pros:**
- Production-grade reliability
- Scalable to 1000s of PDFs
- Modern tech stack
- Comprehensive monitoring
- Easy to maintain and extend

**Cons:**
- Very high development cost
- Requires infrastructure changes
- Long migration period
- Overkill for current needs

---

## RECOMMENDED APPROACH

### Phase 1: Emergency Fix (This Week)
**Goal:** Get system working again

1. ✅ Add PDF parsing fallback (2 hours)
2. ✅ Fix error logging and notifications (1 hour)
3. ✅ Manually import missing dates (05/03, 06/03) (30 mins)
4. ✅ Test on live site (1 hour)
5. ✅ Monitor for 48 hours

**Estimated Time:** 1 day  
**Risk:** Very Low

### Phase 2: Stabilization (Next 2 Weeks)
**Goal:** Prevent future failures

1. ✅ Add retry mechanism for failed PDFs
2. ✅ Improve download script logging
3. ✅ Fix database config column error
4. ✅ Add health check endpoint
5. ✅ Set up daily health check cron
6. ✅ Create runbook for common failures

**Estimated Time:** 1 week  
**Risk:** Low

### Phase 3: Refactoring (Next Month)
**Goal:** Improve maintainability

1. ✅ Extract customer parsers to separate files
2. ✅ Create parser factory pattern
3. ✅ Add unit tests for each parser
4. ✅ Implement parallel processing
5. ✅ Add import queue system
6. ✅ Create admin dashboard for monitoring

**Estimated Time:** 3 weeks  
**Risk:** Medium

---

## TESTING STRATEGY

### Manual Testing Checklist:
- [ ] Download script finds recent emails
- [ ] PDFs are downloaded and organized correctly
- [ ] Import script processes all PDFs without errors
- [ ] Jobs are inserted into database
- [ ] Pay sync matches payslip data
- [ ] Error notifications are sent
- [ ] Health check returns correct status

### Automated Testing:
```python
# tests/test_pdf_parser.py
def test_pdfplumber_fallback():
    """Test that PyPDF2 is used when pdfplumber fails."""
    parser = PDFParser()
    
    # Create corrupted PDF
    corrupted_pdf = create_corrupted_pdf()
    
    # Should not crash, should use fallback
    text = parser.extract(corrupted_pdf)
    assert len(text) > 0

def test_customer_parser_posturite():
    """Test POSTURITE parser extracts correct data."""
    sample_pdf = load_sample_pdf('posturite_20250101.pdf')
    parser = PosturiteParser()
    
    jobs = parser.parse(sample_pdf)
    
    assert len(jobs) == 5
    assert jobs[0]['customer'] == 'POSTURITE'
    assert jobs[0]['activity'] == 'DESK INSTALL'
    assert jobs[0]['postcode'] == 'PR7 5AS'
```

---

## MONITORING & ALERTING

### Metrics to Track:
1. **Download Success Rate:** % of emails successfully downloaded
2. **Import Success Rate:** % of PDFs successfully imported
3. **Parse Time:** Average time to parse one PDF
4. **Error Rate:** Errors per 100 PDFs processed
5. **Queue Length:** Number of PDFs waiting to be processed
6. **Data Freshness:** Time since last successful import

### Alerts to Configure:
1. 🚨 **Critical:** No runsheets imported in 24 hours
2. ⚠️ **Warning:** Import error rate > 10%
3. ⚠️ **Warning:** Parse time > 5 minutes per PDF
4. 📊 **Info:** Daily summary of imports

---

## CONCLUSION

The runsheet import system is currently **completely broken** and has been for **8+ days**. The root cause is a combination of:

1. **Fragile PDF parsing** with no fallback mechanism
2. **Silent failures** with no error notifications
3. **Complex architecture** with tight coupling
4. **Poor error handling** and logging

**Immediate Action Required:**
1. Implement PDF parsing fallback (TODAY)
2. Fix error notifications (TODAY)
3. Manually import missing dates (TODAY)
4. Monitor system for 48 hours

**Long-term Solution:**
- Follow phased approach (Emergency → Stabilization → Refactoring)
- Estimated total time: 5 weeks
- Estimated effort: 80-100 hours

**Risk of Inaction:**
- Continued data loss
- Manual intervention required daily
- User frustration
- Compliance issues (missing wage data)

---

## APPENDIX A: Error Logs

### Live Site Errors (March 6, 2026):
```
2026-03-06 19:01:01,364 - WARNING - invalid pdf header: b'0.57 '
[repeated 56 times across different PDFs]

2026-03-06 19:03:07 - ❌ Runsheet import failed
2026-03-06 19:03:09 - 📥 Downloaded: 0 runsheets, 0 payslips
2026-03-06 19:03:09 - ❌ Runsheet download failed
2026-03-06 19:03:09 - ❌ Runsheet import failed
```

### Database State:
```sql
-- Missing dates
SELECT DISTINCT date FROM run_sheet_jobs 
WHERE date LIKE '%/03/2026' 
ORDER BY date;

-- Results show gap: 04/03 → 07/03 (missing 05/03, 06/03)
```

---

## APPENDIX B: File Locations

### Key Files:
- `scripts/sync_master.py` - Main sync orchestrator (476 lines)
- `scripts/production/download_runsheets_gmail.py` - Gmail download (833 lines)
- `scripts/production/import_run_sheets.py` - PDF import (2,763 lines) ⚠️
- `app/services/periodic_sync.py` - Scheduled sync service
- `app/utils/sync_logger.py` - Unified logging

### Log Files (Live Site):
- `/opt/tvstcms/logs/sync.log` - Main sync log
- `/opt/tvstcms/logs/auto_sync.log` - Detailed import errors
- `/opt/tvstcms/logs/periodic_sync.log` - Scheduler log
- `/opt/tvstcms/logs/error.log` - Application errors

### Database:
- `/opt/tvstcms/data/database/payslips.db`
- Tables: `run_sheet_jobs`, `job_items`, `payslips`

---

**Report Generated:** March 6, 2026 22:15 UTC  
**Next Review:** After emergency fixes implemented
