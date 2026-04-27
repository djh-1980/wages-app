# Phase 0 — Pre-rebuild Snapshot

**Captured:** 2026-04-27 21:27 BST (dev box).

## Git

- Branch: `main`
- HEAD: `35045596c90ef271221bc423321926f59bb075d9` — *fix: only mark runsheet complete when tomorrow's data is in DB*
- Working tree: 3 untracked audit docs (`SYNC_AUDIT.md`, `SYNC_REDESIGN.md`, `SYNC_MIGRATION_PLAN.md`).
- Tag created: `pre-sync-rebuild` → `35045596...` (push to origin separately).

## Database (`data/database/payslips.db`)

| Table | Count |
|---|---:|
| `run_sheet_jobs` | 18,407 |
| `payslips` | 260 |
| `job_items` | 16,336 |

- Latest runsheet date: `27/04/2026`.
- Tomorrow (`28/04/2026`) **not present** at snapshot time.

## `settings` table contents

```
addressLine1                  401 New Victoria Building
addressLine2                  103 Corporation Street
auto_send_confirmations       true
auto_sync_payslips_enabled    true
auto_sync_runsheets_enabled   true
city                          Manchester
manager_email                 North_GB_Technical@tvsscs.com
niNumber                      JN628069B
notification_email            danielhanson993@gmail.com
notify_on_error_only          false
notify_on_new_files_only      true
notify_on_success             true
payslip_sync_day              Tuesday
payslip_sync_end              14
payslip_sync_start            6
postcode                      M44LJ
sync_interval_minutes         15
sync_start_time               19:00
userName                      Daniel Hanson
userPhone                     07487553746
user_email                    danielhanson993@gmail.com
utrNumber                     5155358938
```

## NAS (`/Volumes/pdfs/runsheets`)

- Mounted on dev box.
- Year folders: 2021, 2022, 2023, 2024, 2025, 2026, plus `manual/`.
- Total `DH_*.pdf` files: **1,851**.
- 2026 month folders: 01-January … 12-December (all present).

## Restoration plan if needed

1. `git reset --hard pre-sync-rebuild` (local) / `git push -f origin pre-sync-rebuild:main` (only if explicitly required).
2. DB restore: from latest backup under `data/database/backups/` (if recovery required).
3. NAS files are read/append-only during these phases — no rollback required for filesystem.

---

*This file is reference-only; do not edit during the rebuild.*
