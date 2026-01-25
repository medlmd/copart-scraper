# 🆓 Quick Free Deployment Guide

## Easiest Option: Render.com (No Credit Card Needed!)

### Step 1: Prepare Your Code
```bash
# Make sure all files are ready
git init
git add .
git commit -m "Initial commit"
```

### Step 2: Push to GitHub
```bash
# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/copart-scraper.git
git push -u origin main
```

### Step 3: Deploy on Render
1. Go to https://render.com
2. Sign up (free, no credit card)
3. Click "New +" → "Web Service"
4. Connect your GitHub repo
5. Settings:
   - **Name**: copart-scraper
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt && pip install gunicorn`
   - **Start Command**: `gunicorn -w 4 -b 0.0.0.0:$PORT --timeout 300 app:app`
6. Click "Create Web Service"
7. Wait 5-10 minutes for deployment
8. Your app will be live at: `https://copart-scraper.onrender.com`

## Alternative: Railway.app (Easier, but needs credit card)

1. Go to https://railway.app
2. Sign up with GitHub
3. "New Project" → "Deploy from GitHub repo"
4. Select your repo
5. Railway auto-detects and deploys!
6. Done! 🎉

## Alternative: Fly.io (CLI-based)

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Deploy
fly launch
```

## ⚡ Fastest: Use ngrok (Local + Public URL)

```bash
# 1. Run app locally
python3 app.py

# 2. In another terminal, expose it
ngrok http 8080

# 3. Use the ngrok URL (e.g., https://abc123.ngrok.io)
```

**Note**: URL changes each time you restart ngrok (free tier)

## 📋 Checklist:

- [ ] Code pushed to GitHub
- [ ] Account created on Render/Railway/Fly
- [ ] Web service created
- [ ] Build command set
- [ ] Start command set
- [ ] App deployed and running

## 🎯 Recommended for You:

**Render.com** - Easiest, truly free, no credit card needed!

Just:
1. Push to GitHub
2. Connect to Render
3. Deploy!

Done in 5 minutes! 🚀
