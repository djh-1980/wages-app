# 📋 Daily Parsing Quality Workflow

## 🎯 **Quick Daily Check**

### **Check Recent Days:**
```bash
python3 scripts/daily_parsing_check.py --recent
```

### **Check Specific Date:**
```bash
python3 scripts/daily_parsing_check.py 2025-11-30
```

### **Check Today:**
```bash
python3 scripts/daily_parsing_check.py
```

## 🔧 **When You Find Issues:**

### **1. Start Working on Customer:**
```bash
python3 scripts/parsing_manager.py start "Customer Name"
```

### **2. Fix the Parser:**
- Edit `scripts/production/import_run_sheets.py`
- Find the relevant `parse_*_job` function
- Improve address/activity extraction

### **3. Re-parse the Date:**
```bash
python3 scripts/production/import_run_sheets.py --date 2025-11-30 --force-reparse
```

### **4. Verify the Fix:**
```bash
python3 scripts/daily_parsing_check.py 2025-11-30
```

### **5. Mark as Complete:**
```bash
python3 scripts/parsing_manager.py complete "Customer Name" "parse_function_name" --notes "Fixed address extraction issue"
```

## 📊 **Track Progress:**

### **Overall Status:**
```bash
python3 scripts/parsing_manager.py status
```

### **Next Priorities:**
```bash
python3 scripts/parsing_manager.py next --limit 5
```

### **Completed Work:**
```bash
python3 scripts/parsing_manager.py list --status completed
```

## 🎯 **Example Workflow:**

```bash
# 1. Check today's parsing
python3 scripts/daily_parsing_check.py

# 2. Found issue with "Diebold Nixdorf" - start working on it
python3 scripts/parsing_manager.py start "Diebold Nixdorf"

# 3. Edit the parser in import_run_sheets.py
# (create parse_diebold_nixdorf_job function)

# 4. Re-parse the problematic date
python3 scripts/production/import_run_sheets.py --date 2025-11-30 --force-reparse

# 5. Verify it's fixed
python3 scripts/daily_parsing_check.py 2025-11-30

# 6. Mark as complete
python3 scripts/parsing_manager.py complete "Diebold Nixdorf" "parse_diebold_nixdorf_job" --notes "Created parser for ATM services"

# 7. Check overall progress
python3 scripts/parsing_manager.py status
```

## ✅ **Perfect Parsers (Don't Need Changes):**
- POSTURITE LIMITED (99.6% success)
- Vista Retail Support Limited (100% success)
- Fujitsu Services Limited - Star Trains - ME (100% success)
- CXM (100% success)
- EPAY Limited (100% success)
- Multiple Computacenter variants (100% success)

## 🎯 **Benefits:**
- **Quick identification** of parsing issues
- **Targeted fixes** for specific customers
- **Progress tracking** across all improvements
- **Minimal disruption** - only re-parse affected dates
- **Quality assurance** - verify fixes immediately
