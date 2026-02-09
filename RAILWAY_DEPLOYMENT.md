# Railway.app Deployment Guide

## Quick Setup (5 minutes)

### Step 1: Sign up for Railway
1. Go to [railway.app](https://railway.app)
2. Click "Start a New Project"
3. Sign up with GitHub (recommended)

### Step 2: Deploy from GitHub
1. Click "New Project" → "Deploy from GitHub repo"
2. Select your repository: `medlmd/copart-scraper`
3. Railway will automatically:
   - Detect Python from `runtime.txt`
   - Install dependencies from `requirements.txt`
   - Use `Procfile` for start command

### Step 3: Configure Environment Variables
1. In Railway dashboard, go to your service
2. Click "Variables" tab
3. Add these environment variables:

```
BROWSERLESS_URL=wss://chrome.browserless.io
BROWSERLESS_TOKEN=your-browserless-token-here
```

**To get your Browserless token:**
- Go to https://www.browserless.io/
- Sign up/login
- Copy your API token from the dashboard

### Step 4: Deploy
1. Railway will automatically deploy when you connect the repo
2. Or click "Deploy" button to trigger manually
3. Wait 2-3 minutes for build to complete

### Step 5: Get Your URL
1. Click on your service
2. Click "Settings" tab
3. Under "Domains", Railway provides a public URL
4. Or generate a custom domain

## What Railway Does Automatically

✅ Detects Python 3.12.17 from `runtime.txt`
✅ Installs all dependencies from `requirements.txt`
✅ Runs your app using `Procfile`
✅ Provides public URL automatically
✅ Handles HTTPS/SSL automatically

## Configuration Files

Railway uses these files (already in your repo):

- **`runtime.txt`** - Specifies Python 3.12.17
- **`requirements.txt`** - Lists all Python dependencies
- **`Procfile`** - Defines how to start the app
- **`railway.json`** - Optional Railway-specific config

## Environment Variables

Required variables (set in Railway dashboard):

| Variable | Value | Description |
|----------|-------|-------------|
| `BROWSERLESS_URL` | `wss://chrome.browserless.io` | Browserless WebSocket URL |
| `BROWSERLESS_TOKEN` | `your-token` | Your Browserless API token |

## Troubleshooting

### Build Fails
- Check Railway logs for error messages
- Verify `runtime.txt` has `python-3.12.17`
- Ensure `requirements.txt` has all dependencies

### App Won't Start
- Check that `Procfile` exists and is correct
- Verify environment variables are set
- Check Railway logs for startup errors

### Scraping Doesn't Work
- Verify `BROWSERLESS_TOKEN` is set correctly
- Check Browserless dashboard for token validity
- Check Railway logs for connection errors

## Railway vs Render

| Feature | Railway | Render |
|---------|---------|--------|
| Python 3.12 Support | ✅ Excellent | ⚠️ Issues with 3.13 |
| Greenlet Handling | ✅ Automatic | ❌ Compilation errors |
| Setup Complexity | ⭐⭐⭐⭐⭐ Easy | ⭐⭐⭐ Medium |
| Free Tier | ✅ Yes | ✅ Yes |
| Auto-deploy | ✅ Yes | ✅ Yes |

## Free Tier Limits

Railway free tier includes:
- $5/month credit
- 500 hours of usage
- Perfect for testing and small apps

## Next Steps

1. **Deploy to Railway** (follow steps above)
2. **Test the deployment** - Visit your Railway URL
3. **Click "Refresh Data"** - Test scraping functionality
4. **Monitor logs** - Check Railway dashboard for any issues

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Your app logs: Railway Dashboard → Your Service → Logs

---

**Ready to deploy?** Follow the steps above and your app will be live in minutes! 🚀
