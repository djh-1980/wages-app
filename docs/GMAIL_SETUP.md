# Gmail Run Sheet Downloader Setup

This guide will help you set up automatic downloading of run sheets from Gmail.

## Step 1: Install Dependencies

```bash
pip3 install -r requirements-gmail.txt
```

## Step 2: Set Up Gmail API Access

1. **Go to Google Cloud Console:**
   - Visit: <https://console.cloud.google.com/>

2. **Create a New Project:**
   - Click the project dropdown at the top (next to "Google Cloud")
   - Click "NEW PROJECT"
   - Project name: "Wages App" (or similar)
   - Click "CREATE"
   - Wait for project creation, then select it from the dropdown

3. **Enable Gmail API:**
   - Click the hamburger menu (☰) → "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click on "Gmail API"
   - Click "ENABLE"

4. **Configure OAuth Consent Screen:**
   - Go to "APIs & Services" → "OAuth consent screen"
   - User Type: Select "External"
   - Click "CREATE"
   - Fill in required fields:
     - App name: "Wages App"
     - User support email: (select your email)
     - Developer contact information: (enter your email)
   - Click "SAVE AND CONTINUE"
   - Scopes: Click "SAVE AND CONTINUE" (no changes needed)
   - Test users: Click "ADD USERS" and add your Gmail address
   - Click "SAVE AND CONTINUE"
   - Review and click "BACK TO DASHBOARD"

5. **Create OAuth Credentials:**
   - Go to "APIs & Services" → "Credentials"
   - Click "+ CREATE CREDENTIALS" at the top
   - Select "OAuth client ID"
   - Application type: Select "Desktop app"
   - Name: "Wages App Desktop"
   - Click "CREATE"
   - A dialog will appear with your credentials
   - Click "DOWNLOAD JSON"

6. **Save Credentials:**
   - Rename the downloaded file to `credentials.json`
   - Move it to the Wages-App directory:

     ```bash
     mv ~/Downloads/client_secret_*.json /Users/danielhanson/CascadeProjects/Wages-App/credentials.json
     ```

## Step 3: Run the Automated Downloader

The script now automatically:
1. 📥 Downloads PDFs from Gmail
2. 🗂️ Organizes them into year/month folders
3. 💾 Imports jobs to the database

```bash
# Download, organize, and import all run sheets from January 1st, 2025
python3 scripts/download_runsheets_gmail.py

# Or specify a custom date (format: YYYY/MM/DD)
python3 scripts/download_runsheets_gmail.py 2025/10/01
```

**First Run:**
- A browser window will open
- Sign in with your Gmail account
- Click "Allow" to grant access
- The script will save a `token.json` file for future runs

**What It Does:**
1. Connects to Gmail and searches for run sheet emails
2. Downloads PDF attachments to `RunSheets/` folder
3. Extracts the date from each PDF
4. Moves PDFs to `RunSheets/YYYY/MM/` folders
5. Imports all jobs to the database automatically
6. Shows summary of downloaded and imported jobs

## Manual Import (Optional)

If you want to import run sheets manually:

```bash
python3 scripts/import_run_sheets.py
```

## Troubleshooting

### "credentials.json not found"
- Make sure you downloaded the OAuth credentials from Google Cloud Console
- Rename it to `credentials.json`
- Place it in the Wages-App directory

### "Access blocked: This app's request is invalid"
- Make sure you configured the OAuth consent screen
- Add your email as a test user in the OAuth consent screen settings

### No emails found
- Check the search query in the script matches your email subject lines
- Try adjusting the `query` variable in `search_run_sheet_emails()`
- Common patterns:
  - `subject:"run sheet"`
  - `subject:"RUN SHEETS"`
  - `from:sender@example.com has:attachment filename:pdf`

## Customizing the Search

Edit `scripts/download_runsheets_gmail.py` line ~60 to customize the search:

```python
query = f'has:attachment filename:pdf subject:"run sheet" after:{after_date}'
```

You can add:
- `from:specific@email.com` - Only from specific sender
- `subject:"exact subject"` - Specific subject line
- `filename:"RUN SHEETS"` - Specific filename pattern

## Security Notes

- `credentials.json` - Your OAuth app credentials (keep private)
- `token.json` - Your access token (keep private, auto-generated)
- Both files are gitignored by default
- Never commit these files to version control
