# Deployment Guide for Copart Scraper

## Quick Deploy to Render.com

1. **Go to [render.com](https://render.com)** and sign up/login
2. **Click "New +" → "Web Service"**
3. **Connect your GitHub repository**: `https://github.com/medlmd/copart-scraper`
4. **Settings** (Render will auto-detect from `render.yaml`):
   - **Name**: `copart-scraper`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && pip install gunicorn`
   - **Start Command**: `gunicorn -w 1 -b 0.0.0.0:$PORT --timeout 600 --preload app:app`
   - **Publish Directory**: Leave empty
5. **Click "Create Web Service"**

Render will automatically:
- Install Python dependencies
- Start your Flask app
- Provide a public URL

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python3 app.py
```

Access at: `http://localhost:8080`

## Production with Gunicorn (Local)

```bash
pip install gunicorn
gunicorn -w 1 -b 0.0.0.0:8080 --timeout 600 app:app
```

## Requirements

- Python 3.9+
- Chrome/Chromium (for scraping)
- ChromeDriver (auto-managed by webdriver-manager)

## Notes

- The app uses lazy loading - ChromeDriver only initializes when scraping
- App will start even if Chrome is not available (scraping will show error)
- Free tier on Render may have limitations with Chrome/Selenium
