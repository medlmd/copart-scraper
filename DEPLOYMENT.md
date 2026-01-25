# Deployment Guide for Copart Scraper Dashboard

## System Requirements

### Minimum Requirements:
- **OS**: Linux, macOS, or Windows
- **Python**: 3.9 or higher
- **RAM**: 2GB minimum (4GB recommended)
- **Disk Space**: 500MB for dependencies
- **Chrome Browser**: Latest version installed
- **ChromeDriver**: Automatically managed by `webdriver-manager`

### For Production Deployment:
- **OS**: Linux (Ubuntu 20.04+ recommended)
- **Python**: 3.9+
- **RAM**: 4GB+ (8GB recommended for headless Chrome)
- **CPU**: 2+ cores
- **Internet**: Stable connection for scraping

## Dependencies

All dependencies are listed in `requirements.txt`:

```
flask==3.0.0
requests==2.31.0
beautifulsoup4==4.12.2
selenium==4.15.2
lxml==4.9.3
pandas==2.1.3
webdriver-manager==4.0.1
```

## Installation Steps

### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv
sudo apt-get install -y chromium-browser chromium-chromedriver
# OR install Google Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt-get install -f
```

**macOS:**
```bash
brew install python3
brew install --cask google-chrome
```

**Windows:**
- Install Python 3.9+ from python.org
- Install Google Chrome from google.com/chrome

### 2. Set Up Python Environment

```bash
# Navigate to project directory
cd /path/to/copart

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Verify ChromeDriver

The `webdriver-manager` package will automatically download ChromeDriver, but you can verify:

```bash
python3 -c "from selenium import webdriver; from webdriver_manager.chrome import ChromeDriverManager; print(ChromeDriverManager().install())"
```

## Deployment Options

### Option 1: Local Development Server

```bash
# Activate virtual environment
source venv/bin/activate

# Run Flask app
python3 app.py
```

Access at: `http://localhost:8080`

### Option 2: Production with Gunicorn (Recommended)

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

### Option 3: Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]
```

Build and run:
```bash
docker build -t copart-scraper .
docker run -p 8080:8080 copart-scraper
```

### Option 4: Cloud Deployment (AWS, GCP, Azure)

#### AWS EC2:
1. Launch Ubuntu instance (t2.medium or larger)
2. SSH into instance
3. Follow installation steps above
4. Use systemd service or PM2 for process management

#### Google Cloud Run:
1. Create `Dockerfile` (see above)
2. Build and push to Container Registry
3. Deploy to Cloud Run

#### Heroku:
1. Create `Procfile`:
```
web: gunicorn -w 4 -b 0.0.0.0:$PORT app:app
```
2. Deploy:
```bash
heroku create your-app-name
git push heroku main
```

## Configuration

### Environment Variables (Optional)

Create `.env` file:
```
FLASK_ENV=production
FLASK_DEBUG=False
PORT=8080
```

### Chrome Options for Production

The scraper already includes optimized Chrome options for headless mode. No additional configuration needed.

## Process Management

### Using systemd (Linux)

Create `/etc/systemd/system/copart-scraper.service`:
```ini
[Unit]
Description=Copart Scraper Dashboard
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/copart
Environment="PATH=/path/to/copart/venv/bin"
ExecStart=/path/to/copart/venv/bin/gunicorn -w 4 -b 0.0.0.0:8080 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable copart-scraper
sudo systemctl start copart-scraper
```

### Using PM2 (Node.js process manager)

```bash
npm install -g pm2
pm2 start app.py --interpreter python3 --name copart-scraper
pm2 save
pm2 startup
```

## Security Considerations

1. **Firewall**: Only expose port 8080 to trusted networks
2. **HTTPS**: Use reverse proxy (nginx) with SSL certificate
3. **Authentication**: Add authentication if exposing publicly
4. **Rate Limiting**: Implement rate limiting for API endpoints

## Nginx Reverse Proxy (Optional)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Monitoring

### Check if app is running:
```bash
curl http://localhost:8080/api/data
```

### View logs:
```bash
# If using systemd
sudo journalctl -u copart-scraper -f

# If using PM2
pm2 logs copart-scraper
```

## Troubleshooting

### ChromeDriver Issues:
- Ensure Chrome is installed and up to date
- `webdriver-manager` will auto-download matching ChromeDriver
- Check Chrome version: `google-chrome --version`

### Port Already in Use:
```bash
# Find process using port 8080
lsof -i :8080
# Kill process
kill -9 <PID>
```

### Memory Issues:
- Reduce Gunicorn workers: `-w 2` instead of `-w 4`
- Increase server RAM
- Monitor memory usage: `htop` or `free -h`

## Quick Start Checklist

- [ ] Python 3.9+ installed
- [ ] Google Chrome installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Test run successful (`python3 app.py`)
- [ ] Port 8080 available
- [ ] Firewall configured (if needed)
- [ ] Process manager configured (systemd/PM2)
- [ ] Monitoring set up

## Production Deployment Command

```bash
# Full production deployment
gunicorn -w 4 -b 0.0.0.0:8080 --timeout 300 --access-logfile - --error-logfile - app:app
```

This command:
- Uses 4 worker processes
- Binds to all interfaces on port 8080
- Sets 5-minute timeout (for long scraping operations)
- Logs to stdout/stderr
