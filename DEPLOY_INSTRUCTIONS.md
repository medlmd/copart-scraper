# Deployment Instructions

## Quick Deploy Options

### Option 1: Automated Script (Easiest)

```bash
# Run the deployment script
./deploy.sh

# Then start the app
source venv/bin/activate
python3 app.py
```

### Option 2: Docker (Recommended for Production)

```bash
# Build and run with Docker
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 3: Heroku (Cloud Deployment)

```bash
# Install Heroku CLI first: https://devcenter.heroku.com/articles/heroku-cli

# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Deploy
git push heroku main

# Open app
heroku open
```

### Option 4: Manual Production Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt gunicorn

# 2. Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 --timeout 300 app:app
```

## What I've Created For You:

✅ **Dockerfile** - For containerized deployment
✅ **docker-compose.yml** - Easy Docker deployment
✅ **deploy.sh** - Automated setup script
✅ **Procfile** - For Heroku deployment
✅ **.gitignore** - Git ignore file
✅ **DEPLOYMENT.md** - Complete deployment guide

## Next Steps:

1. **Local Testing**: Run `./deploy.sh` then `python3 app.py`
2. **Docker**: Run `docker-compose up -d`
3. **Cloud**: Follow Heroku instructions above

The app will be available at `http://localhost:8080` (or your server's IP)
