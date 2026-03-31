# HMRC Making Tax Digital (MTD) Integration Guide

## Overview

This application integrates with HMRC's Making Tax Digital (MTD) API for Self-Employment Income & Expenses. This allows you to submit quarterly updates of your income and expenses directly to HMRC digitally.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup Instructions](#setup-instructions)
3. [Configuration](#configuration)
4. [Using the Integration](#using-the-integration)
5. [API Endpoints](#api-endpoints)
6. [Troubleshooting](#troubleshooting)
7. [Security Considerations](#security-considerations)

---

## Prerequisites

### 1. HMRC Developer Account

1. Visit [HMRC Developer Hub](https://developer.service.hmrc.gov.uk)
2. Create an account or sign in
3. Create a new application
4. Note your **Client ID** and **Client Secret**

### 2. MTD Registration

1. Sign up for Making Tax Digital at [gov.uk](https://www.gov.uk/guidance/sign-up-for-making-tax-digital-for-income-tax)
2. You'll receive a **National Insurance Number (NINO)** and **Business ID**
3. Keep these details safe - you'll need them for submissions

### 3. System Requirements

- Python 3.8+
- Flask application running
- Internet connection for API calls
- Valid SSL certificate (for production)

---

## Setup Instructions

### Step 1: Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your HMRC credentials:
   ```bash
   # HMRC MTD Configuration
   HMRC_CLIENT_ID=your-client-id-from-developer-hub
   HMRC_CLIENT_SECRET=your-client-secret-from-developer-hub
   HMRC_REDIRECT_URI=http://localhost:5000/api/hmrc/auth/callback
   HMRC_ENVIRONMENT=sandbox  # Use 'sandbox' for testing
   ```

3. **Important**: Never commit your `.env` file to version control!

### Step 2: Update Redirect URI in HMRC Developer Hub

1. Go to your application in HMRC Developer Hub
2. Add the redirect URI: `http://localhost:5000/api/hmrc/auth/callback`
3. For production, use your live domain: `https://yourdomain.com/api/hmrc/auth/callback`

### Step 3: Initialize Database

The database tables are created automatically when you start the application. The following tables are created:

- `hmrc_credentials` - Stores OAuth tokens
- `hmrc_obligations` - Stores quarterly obligations
- `hmrc_submissions` - Tracks submission history

### Step 4: Test in Sandbox

**Always test in sandbox environment first!**

1. Set `HMRC_ENVIRONMENT=sandbox` in `.env`
2. Use HMRC's test user credentials
3. Verify all functionality works
4. Review test submissions

### Step 5: Go Live

1. Change `HMRC_ENVIRONMENT=production` in `.env`
2. Use your real NINO and Business ID
3. Connect with your real HMRC credentials
4. Submit actual data

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HMRC_CLIENT_ID` | Yes | - | Your application's Client ID from HMRC Developer Hub |
| `HMRC_CLIENT_SECRET` | Yes | - | Your application's Client Secret |
| `HMRC_REDIRECT_URI` | Yes | `http://localhost:5000/api/hmrc/auth/callback` | OAuth callback URL |
| `HMRC_ENVIRONMENT` | No | `sandbox` | Environment: `sandbox` or `production` |
| `HMRC_SERVER_TOKEN` | No | - | Optional server-to-server token |

### Application Settings

Configure your NINO and Business ID in the HMRC Settings page:

1. Navigate to Settings → HMRC MTD
2. Enter your National Insurance Number (format: AA123456A)
3. Enter your Business ID (provided by HMRC)
4. Click "Save Configuration"

---

## Using the Integration

### 1. Connect to HMRC

1. Go to **Settings → HMRC MTD**
2. Click **"Connect to HMRC"**
3. You'll be redirected to HMRC's authorization page
4. Sign in with your HMRC credentials
5. Authorize the application
6. You'll be redirected back with a success message

### 2. View Quarterly Obligations

1. After connecting, click **"Refresh Obligations"**
2. View your quarterly deadlines in the **Obligations** tab
3. Each quarter shows:
   - Period dates (e.g., Q1: Apr 6 - Jul 5)
   - Due date
   - Status (Open or Fulfilled)

### 3. Submit Quarterly Updates

**From the Expenses Page:**

1. Go to **Expenses** page
2. Ensure all expenses for the quarter are entered
3. Click **"Submit to HMRC"** button
4. Select the quarter (Q1, Q2, Q3, Q4)
5. Review the submission preview
6. Click **"Confirm Submission"**
7. View confirmation and receipt ID

**What Gets Submitted:**

- **Income**: Total from payslips for the period
- **Expenses**: Categorized by HMRC box numbers
  - Vehicle costs
  - Travel costs
  - Premises costs (home office)
  - Admin costs
  - Professional fees
  - Other expenses

### 4. View Submission History

1. Go to **Settings → HMRC MTD**
2. Click **"Submission History"** tab
3. View all past submissions with:
   - Submission date
   - Period (Q1-Q4)
   - Status (Submitted/Failed)
   - HMRC Receipt ID
   - Error messages (if any)

---

## API Endpoints

### Authentication

#### Start OAuth Flow
```
GET /api/hmrc/auth/start
```
Returns authorization URL to redirect user to HMRC.

#### OAuth Callback
```
GET /api/hmrc/auth/callback?code=xxx&state=xxx
```
Handles OAuth callback and exchanges code for tokens.

#### Get Auth Status
```
GET /api/hmrc/auth/status
```
Returns current connection status and token expiry.

#### Disconnect
```
POST /api/hmrc/auth/disconnect
```
Revokes stored credentials.

### Obligations

#### Get Obligations from HMRC
```
GET /api/hmrc/obligations?nino=AA123456A&from_date=2024-04-06&to_date=2025-04-05
```

#### Get Stored Obligations
```
GET /api/hmrc/obligations/stored?tax_year=2024/2025
```

### Submissions

#### Preview Period Submission
```
GET /api/hmrc/period/preview?tax_year=2024/2025&period_id=Q1
```
Returns formatted submission data without submitting.

#### Submit Period
```
POST /api/hmrc/period/submit
Content-Type: application/json

{
  "nino": "AA123456A",
  "business_id": "XAIS12345678901",
  "tax_year": "2024/2025",
  "period_id": "Q1"
}
```

#### Get Submission History
```
GET /api/hmrc/submissions?tax_year=2024/2025
```

### Testing

#### Test Connection
```
GET /api/hmrc/test-connection
```
Tests connectivity to HMRC API.

---

## Troubleshooting

### Common Issues

#### 1. "Not authenticated" Error

**Problem**: Access token expired or not found.

**Solution**:
- Go to Settings → HMRC MTD
- Click "Disconnect" then "Connect to HMRC"
- Re-authorize the application

#### 2. "Invalid NINO format" Error

**Problem**: NINO not in correct format.

**Solution**:
- Format should be: 2 letters, 6 numbers, 1 letter (e.g., AA123456A)
- No spaces or special characters
- All uppercase

#### 3. "Validation failed" Error

**Problem**: Submission data doesn't meet HMRC requirements.

**Solution**:
- Ensure you have income for the period
- Ensure you have at least one expense
- Check all amounts are positive
- Verify period dates are correct

#### 4. "Fraud prevention headers" Error

**Problem**: Required headers missing or invalid.

**Solution**:
- This is handled automatically by the system
- Ensure your server has internet access
- Check firewall settings

#### 5. Connection Test Fails

**Problem**: Cannot connect to HMRC API.

**Solution**:
- Check internet connection
- Verify `HMRC_ENVIRONMENT` is set correctly
- Ensure credentials are valid
- Check HMRC service status

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG
```

Check logs in `logs/` directory for detailed error messages.

---

## Security Considerations

### 1. Credential Storage

- **Never** commit `.env` file to version control
- Add `.env` to `.gitignore`
- Use environment variables in production
- Rotate credentials regularly

### 2. Token Management

- Access tokens expire after 4 hours
- Refresh tokens are used automatically
- Tokens are encrypted in database
- Only active tokens are used

### 3. Fraud Prevention

The system automatically includes required fraud prevention headers:
- Connection method
- Public IP address
- Timezone
- User agent
- Device ID
- Local IPs
- Screen information

### 4. HTTPS in Production

**Critical**: Always use HTTPS in production!

```bash
# Update redirect URI for production
HMRC_REDIRECT_URI=https://yourdomain.com/api/hmrc/auth/callback
```

### 5. Data Validation

All submissions are validated before sending:
- Required fields checked
- Amounts validated (positive, 2 decimal places)
- Dates verified
- NINO format validated

---

## Quarterly Deadlines

### Tax Year 2024/2025

| Quarter | Period | Due Date |
|---------|--------|----------|
| Q1 | 6 Apr 2024 - 5 Jul 2024 | 5 Aug 2024 |
| Q2 | 6 Jul 2024 - 5 Oct 2024 | 5 Nov 2024 |
| Q3 | 6 Oct 2024 - 5 Jan 2025 | 5 Feb 2025 |
| Q4 | 6 Jan 2025 - 5 Apr 2025 | 5 May 2025 |

**Important**: Late submissions may incur penalties from HMRC.

---

## Support Resources

### HMRC Resources

- [MTD for Income Tax](https://www.gov.uk/guidance/using-making-tax-digital-for-income-tax)
- [Developer Hub](https://developer.service.hmrc.gov.uk)
- [API Documentation](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/self-assessment-api)
- [Test Users](https://developer.service.hmrc.gov.uk/api-test-user)

### Getting Help

1. Check HMRC service status
2. Review API documentation
3. Test in sandbox environment
4. Contact HMRC support for API issues
5. Check application logs for errors

---

## Development Notes

### Architecture

```
┌─────────────────┐
│   Frontend UI   │
│  (Settings Page)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API Routes     │
│ (api_hmrc.py)   │
└────────┬────────┘
         │
         ├──────────────┬──────────────┐
         ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ HMRCAuth     │ │ HMRCClient   │ │ HMRCMapper   │
│ Service      │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
         │              │              │
         └──────────────┴──────────────┘
                        │
                        ▼
                ┌──────────────┐
                │   Database   │
                │  (SQLite)    │
                └──────────────┘
```

### Key Components

1. **HMRCAuthService** (`app/services/hmrc_auth.py`)
   - OAuth 2.0 flow
   - Token management
   - Credential storage

2. **HMRCClient** (`app/services/hmrc_client.py`)
   - API communication
   - Fraud prevention headers
   - Error handling

3. **HMRCMapper** (`app/services/hmrc_mapper.py`)
   - Data transformation
   - Validation
   - Period calculations

4. **API Routes** (`app/routes/api_hmrc.py`)
   - REST endpoints
   - Request handling
   - Response formatting

### Testing

Create test user at HMRC Developer Hub:
```bash
curl -X POST https://test-api.service.hmrc.gov.uk/create-test-user/individuals
```

---

## Changelog

### Version 1.0.0 (2026-03-18)
- Initial HMRC MTD integration
- OAuth 2.0 authentication
- Quarterly obligation tracking
- Period submission
- Submission history
- Sandbox and production support

---

## License

This integration follows HMRC's API terms and conditions. Ensure compliance with all HMRC requirements when using this integration.
