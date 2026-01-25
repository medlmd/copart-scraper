# Master Prompt: Copart Toyota Corolla Scraper & Dashboard

## Project Overview
Build a web scraper and dashboard to find and display Toyota Corolla vehicles from Copart auctions that match specific criteria.

## Requirements

### 1. Data Source
- **Primary Source**: `bid.cars` - aggregates Copart listings
- **Search URL**: `https://bid.cars/en/search/results?search-type=filters&status=All&type=Automobile&make=Toyota&model=Corolla&year-from=2017&year-to=2020&auction-type=Copart&odometer-to=140000&start-code=Run+and+Drive&transmission=Automatic`
- **Secondary Source**: Individual Copart lot pages at `https://www.copart.com/lot/{LOT_NUMBER}` (remove "1-" prefix from lot numbers)

### 2. Filtering Criteria (STRICT - ALL MUST BE MET)
- **Location**: ONLY Maryland (MD), District of Columbia (DC), or New Jersey (NJ)
- **Title**: MUST contain "Salvage" 
- **Status**: Exclude upcoming/future auctions (only current/available vehicles)
- **Year**: 2017-2020 (already filtered by bid.cars URL)

### 3. Data to Extract from Each Copart Lot Page
1. **Lot Number** - Remove "1-" prefix if present
2. **Year** - 2017-2020
3. **Make/Model** - Toyota Corolla
4. **Damage** - Primary damage type (e.g., "Front End", "Rear End", "Side")
5. **Location** - EXACT location text as shown on Copart page (e.g., "Baltimore, MD" or "MD")
6. **Odometer** - Mileage in miles (numbers only, no "miles" text)
7. **Color** - Exterior color (cleaned, no extra text)
8. **Current Bid** - Current bid amount (format: "$XXX")
9. **Auction Countdown** - Time remaining (e.g., "1D 18H 34min")
10. **Link** - Full Copart URL

### 4. Dashboard UI Requirements

#### Display Columns (IN ORDER):
1. Lot #
2. Year
3. Make/Model
4. Damage
5. Location (exact text from Copart)
6. Odometer
7. Color
8. Current Bid
9. Auction Countdown
10. Link

#### DO NOT Display:
- VIN Number
- Sale Status

#### UI Features:
- Modern, responsive design
- Refresh button to scrape new data
- Loading indicator during scraping
- Error handling
- Statistics display (total vehicles, last updated)
- Table format with sortable columns

### 5. Technical Requirements

#### Scraping:
- Use Selenium with ChromeDriver (headless mode)
- Bypass Cloudflare protection (user-agent, CDP commands)
- Handle dynamic content loading
- Wait for page elements to load
- Handle "Load More" pagination on bid.cars
- Extract lot numbers from bid.cars
- Scrape each Copart lot page individually
- Filter vehicles based on strict criteria
- Error handling for failed scrapes

#### Backend:
- Flask web application
- REST API endpoints:
  - `GET /` - Dashboard page
  - `POST /api/refresh` - Scrape new data
  - `GET /api/data` - Get cached data
- Cache scraped data in memory
- Return JSON responses

#### Data Validation:
- Verify location is MD, DC, or NJ from Copart page
- Verify title contains "Salvage"
- Filter out upcoming/future auctions
- Clean extracted data (remove extra text, normalize)

### 6. File Structure
```
copart/
├── scraper.py          # Main scraping logic
├── app.py             # Flask application
├── templates/
│   └── dashboard.html # Dashboard UI
├── requirements.txt   # Python dependencies
└── README.md         # Project documentation
```

### 7. Key Functions Needed

#### In scraper.py:
- `extract_lot_numbers_from_bidcars()` - Get all lot numbers from bid.cars
- `scrape_copart_lot(lot_number)` - Scrape single Copart page
- `scrape_copart_vehicles_from_lots(lot_numbers, limit)` - Scrape multiple lots
- `scrape_copart_corolla(limit)` - Main function (extract lots → scrape Copart)

#### In app.py:
- `refresh_data()` - POST endpoint to scrape new data
- `get_data()` - GET endpoint to return cached data
- `index()` - Render dashboard

### 8. Important Notes
- Location must be EXACT text from Copart page (preserve city, state format)
- Only show vehicles that pass ALL filters (location, title, status)
- Handle Cloudflare protection on bid.cars
- Optimize scraping speed (reduce wait times where possible)
- Handle errors gracefully (don't crash on single failed scrape)
- Display loading state during scraping (can take 1-2 minutes)

### 9. Expected Output Format
```json
{
  "lot_number": "72303855",
  "year": 2020,
  "make": "Toyota",
  "model": "Corolla",
  "damage": "Front End",
  "location": "Baltimore, MD",  // or "MD" if that's what Copart shows
  "odometer": "51325",
  "color": "Blue",
  "current_bid": "$15",
  "auction_countdown": "1D 18H 34min",
  "url": "https://www.copart.com/lot/72303855"
}
```

### 10. Success Criteria
- ✅ Scrapes lot numbers from bid.cars
- ✅ Scrapes vehicle data from Copart pages
- ✅ Filters to only MD/DC/NJ locations
- ✅ Filters to only Salvage titles
- ✅ Excludes upcoming/future auctions
- ✅ Extracts all required fields accurately
- ✅ Displays data in dashboard with correct columns
- ✅ Shows exact location text from Copart
- ✅ Handles errors gracefully
- ✅ Modern, responsive UI
