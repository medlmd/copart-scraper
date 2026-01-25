# Quick Deployment Guide

## What You Need:

1. **Python 3.9+** - Already installed on most systems
2. **Google Chrome** - Download from google.com/chrome
3. **Internet Connection** - For scraping Copart
4. **Port 8080** - Available port for the web server

## Quick Start (5 minutes):

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python3 app.py

# 3. Open browser
# Go to: http://localhost:8080
```

## For Production:

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

## Files Needed:
- ✅ `app.py` - Flask application
- ✅ `scraper.py` - Scraping logic
- ✅ `templates/dashboard.html` - Web interface
- ✅ `requirements.txt` - Python dependencies

That's it! The scraper will automatically:
- Download ChromeDriver
- Handle Chrome browser setup
- Extract data from Copart search results
