# Cloud Deployment Guide

## Recommended: Deploy Without Docker (Easier for Free Tiers)

**For Render.com:**
1. Go to render.com
2. New Web Service
3. Connect GitHub repo
4. **Don't use Docker** - use native Python
5. Settings:
   - Build: `pip install -r requirements.txt && pip install gunicorn`
   - Start: `gunicorn -w 2 -b 0.0.0.0:$PORT --timeout 300 app:app`

**Note**: Render free tier may struggle with Chrome. Consider:
- Using Playwright instead of Selenium
- Optimizing scraper to be lighter
- Using a paid tier for better resources

### Solution 3: Use Railway.app (Better Chrome Support)

Railway has better support for Chrome/Selenium:
1. Connect GitHub repo
2. Railway auto-detects Python
3. Uses `railway.json` config
4. Better resource allocation

### Solution 4: Optimize for Cloud

The scraper already extracts data from search results (no individual page visits), which is much lighter. But Chrome still needs resources.

**Consider:**
- Reduce workers: `-w 2` instead of `-w 4`
- Increase timeout: `--timeout 600` (10 minutes)
- Use fewer concurrent requests

## Quick Fix for Render

1. **Deploy as Python service** (not Docker)
2. **Use render.yaml** config
3. **Reduce workers** to 2

The app should work, but scraping may be slower on free tier.

## Recommended: Railway.app

Railway has better free tier for this type of app:
- Better Chrome support
- More resources
- Easier deployment

Try Railway instead of Render for this scraper!
