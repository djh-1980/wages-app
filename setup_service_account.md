# Gmail Service Account Setup Guide

## Quick Setup Steps:

### 1. Create Service Account
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing one
3. Go to **IAM & Admin** → **Service Accounts**
4. Click **Create Service Account**
5. Name: `tvs-wages-gmail-sync`
6. Click **Create and Continue** → **Done**

### 2. Enable Gmail API
1. Go to **APIs & Services** → **Library**
2. Search "Gmail API" → **Enable**

### 3. Create Key
1. Go back to **Service Accounts**
2. Click on your service account
3. Go to **Keys** tab
4. **Add Key** → **Create New Key** → **JSON**
5. Download and save as `service-account.json`

### 4. Grant Access (Choose One):

#### Option A: Domain Admin (Best)
1. Go to [Google Admin Console](https://admin.google.com/)
2. **Security** → **API Controls** → **Domain-wide Delegation**
3. Add Client ID from service account
4. Scopes: `https://www.googleapis.com/auth/gmail.readonly`

#### Option B: Share Gmail (Simpler)
1. Share your Gmail with the service account email
2. Give it **read** permissions

### 5. Deploy Files
```bash
# Copy service account file to your server
scp service-account.json tvswages@192.168.1.202:/var/www/tvs-wages/

# Copy updated script
scp scripts/production/download_runsheets_gmail.py tvswages@192.168.1.202:/var/www/tvs-wages/scripts/production/
```

### 6. Test
```bash
# On your server
cd /var/www/tvs-wages
python3 scripts/production/download_runsheets_gmail.py
```

## Benefits:
- ✅ **No more token expiration**
- ✅ **Works in automation**
- ✅ **No browser required**
- ✅ **Permanent solution**

## Fallback:
If service account fails, it will automatically fall back to OAuth (current method).
