# 🚗 Copart Toyota Corolla Scraper Dashboard

A web scraper and dashboard for finding Toyota Corolla vehicles (2017-2023, Salvage title) from Copart auctions in MD, NJ, DC, GA, MI, OH.

## Features

- ✅ Real-time scraping from Copart
- ✅ Filters: 2017-2023, Salvage title, specific states only
- ✅ Modern responsive dashboard
- ✅ Auto-refresh capability
- ✅ Detailed vehicle information

## Quick Start

### Deploy to Render.com (Recommended)

1. Fork this repository
2. Go to [render.com](https://render.com)
3. Click "New +" → "Web Service"
4. Connect your GitHub repo
5. Render will auto-detect settings from `render.yaml`
6. Click "Create Web Service"

Your app will be live in minutes!

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python3 app.py

# Access at http://localhost:8080
```

## Project Structure

```
copart/
├── app.py              # Flask web application
├── scraper.py          # Web scraping logic
├── templates/
│   └── dashboard.html  # Frontend UI
├── requirements.txt    # Python dependencies
├── render.yaml         # Render.com configuration
└── README.md           # This file
```

## API Endpoints

- `GET /` - Main dashboard
- `GET /api/data` - Get cached vehicle data
- `POST /api/refresh` - Trigger new scrape

## Technologies

- Python 3.9+
- Flask (Web framework)
- Selenium (Web scraping)
- BeautifulSoup (HTML parsing)
- Gunicorn (Production server)

## License

MIT
