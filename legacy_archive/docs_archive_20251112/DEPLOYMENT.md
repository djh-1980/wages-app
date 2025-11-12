# Deployment Guide

## Production Deployment

### Environment Variables
```bash
export FLASK_ENV=production
export DATABASE_PATH=/path/to/production.db
export LOG_LEVEL=INFO
export FEATURE_INTELLIGENT_SYNC=false
```

### Configuration
- Use ProductionConfig for production settings
- Enable only tested features
- Configure proper logging
- Set up database backups

### Security
- Change SECRET_KEY
- Configure rate limiting
- Set up HTTPS
- Validate all inputs
