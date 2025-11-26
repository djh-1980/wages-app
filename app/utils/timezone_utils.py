"""
UK Timezone Utilities
Provides consistent UK timezone handling across the application.
"""

import pytz
from datetime import datetime, timedelta
from flask import current_app

# UK timezone constant
UK_TZ = pytz.timezone('Europe/London')

def now_uk():
    """Get current datetime in UK timezone."""
    return datetime.now(UK_TZ)

def to_uk_timezone(dt):
    """Convert datetime to UK timezone."""
    if dt.tzinfo is None:
        # Assume naive datetime is already in UK timezone
        return UK_TZ.localize(dt)
    else:
        # Convert from other timezone to UK
        return dt.astimezone(UK_TZ)

def uk_date_string(dt=None):
    """Get UK date string in DD/MM/YYYY format."""
    if dt is None:
        dt = now_uk()
    elif dt.tzinfo is None:
        dt = UK_TZ.localize(dt)
    else:
        dt = dt.astimezone(UK_TZ)
    
    return dt.strftime('%d/%m/%Y')

def uk_datetime_string(dt=None):
    """Get UK datetime string in DD/MM/YYYY HH:MM:SS format."""
    if dt is None:
        dt = now_uk()
    elif dt.tzinfo is None:
        dt = UK_TZ.localize(dt)
    else:
        dt = dt.astimezone(UK_TZ)
    
    return dt.strftime('%d/%m/%Y %H:%M:%S')

def parse_uk_date(date_str):
    """Parse DD/MM/YYYY date string to UK timezone datetime."""
    dt = datetime.strptime(date_str, '%d/%m/%Y')
    return UK_TZ.localize(dt)

def uk_week_start(dt=None):
    """Get the Sunday (week start) for a given UK date."""
    if dt is None:
        dt = now_uk()
    elif dt.tzinfo is None:
        dt = UK_TZ.localize(dt)
    else:
        dt = dt.astimezone(UK_TZ)
    
    # Find the Sunday of this week
    days_since_sunday = dt.weekday() + 1  # Monday=0, so +1 makes Sunday=0
    if days_since_sunday == 7:  # Already Sunday
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        sunday = dt - timedelta(days=days_since_sunday)
        return sunday.replace(hour=0, minute=0, second=0, microsecond=0)

def uk_week_end(dt=None):
    """Get the Saturday (week end) for a given UK date."""
    sunday = uk_week_start(dt)
    saturday = sunday + timedelta(days=6)
    return saturday.replace(hour=23, minute=59, second=59, microsecond=999999)

# Template filter for Jinja2
def uk_datetime_filter(dt):
    """Jinja2 filter to format datetime in UK timezone."""
    return uk_datetime_string(dt)

def uk_date_filter(dt):
    """Jinja2 filter to format date in UK timezone."""
    return uk_date_string(dt)
