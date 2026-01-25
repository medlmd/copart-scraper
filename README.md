# Copart Toyota Corolla Dashboard

A web dashboard that scrapes and displays Toyota Corolla vehicles from Copart (2017-2020, Salvage, unsold, located in MD, NJ, DC).

## Features

- Scrapes Toyota Corolla data from Copart
- Filters: 2017-2020, Salvage status, Not sold, Locations: MD, NJ, DC
- Displays up to 100 cars in a table
- Refresh button to update data

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open your browser and navigate to:
```
http://localhost:5000
```

## Usage

- Click the "Refresh Data" button to scrape and update the vehicle data
- The dashboard will display up to 100 Toyota Corolla vehicles matching the criteria
