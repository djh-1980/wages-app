# Data Folder Organization

This folder contains all data files for the TVS Wages application, organized for better maintainability and clarity.

## Structure

```
data/
├── database/                 # Database files and backups
│   ├── payslips.db          # Main SQLite database
│   └── backups/             # Database backup files
├── documents/               # Document storage
│   ├── runsheets/          # Runsheet PDFs organized by year/month
│   │   ├── 2021/
│   │   ├── 2022/
│   │   ├── 2023/
│   │   ├── 2024/
│   │   └── 2025/
│   │       ├── 01-January/
│   │       ├── 02-February/
│   │       └── ... (MM-MonthName format)
│   └── payslips/           # Payslip PDFs (if stored separately)
├── reports/                # Generated reports organized by date
│   ├── 2024/
│   │   ├── 10-October/
│   │   └── 11-November/
│   └── 2025/
├── exports/                # Data exports and summaries
│   ├── csv/               # CSV export files
│   └── summaries/         # Summary reports and text files
├── processing/            # File processing workflows
│   ├── queue/            # Files waiting to be processed
│   ├── temp/             # Temporary processing files
│   ├── failed/           # Files that failed processing
│   └── manual/           # Files requiring manual intervention
└── uploads/              # File upload staging
    ├── pending/          # Newly uploaded files
    └── processed/        # Successfully processed uploads
```

## Naming Conventions

- **Years**: 4-digit format (2024, 2025)
- **Months**: MM-MonthName format (01-January, 02-February, etc.)
- **Files**: Original naming preserved where possible

## Backup

A backup of the original structure is maintained in `reorganization_backup/` until you're satisfied with the new organization.

## Maintenance

- Reports are automatically organized by date when generated
- Runsheets follow the year/month structure
- Processing folders should be monitored and cleaned regularly
- Database backups are stored in `database/backups/`
