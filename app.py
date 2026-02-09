"""
Flask application for Copart Toyota Corolla Dashboard
"""
from flask import Flask, render_template, jsonify
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Store cached data
cached_data = []

# Lazy import to avoid Playwright browser initialization on startup
def get_scraper():
    """Lazy import of scraper to avoid Playwright browser initialization on startup"""
    try:
        from scraper import scrape_copart_corolla
        return scrape_copart_corolla
    except Exception as e:
        print(f"Warning: Could not import scraper: {e}")
        return None

@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Refresh vehicle data by scraping Copart"""
    global cached_data  # Declare global at the top of the function
    
    try:
        scrape_func = get_scraper()
        if not scrape_func:
            return jsonify({
                'success': False,
                'error': 'Scraper not available. Chrome/ChromeDriver may not be installed on this platform.'
            }), 500
        
        print("=" * 80)
        print("Starting scrape from Flask API...")
        print("=" * 80)
        # Scrape new data (maximum possible)
        vehicles = scrape_func(limit=1000)  # High limit to scrape as many as possible
        print("=" * 80)
        print(f"Scrape completed. Found {len(vehicles)} vehicles")
        print("=" * 80)
        
        if len(vehicles) == 0:
            print("⚠️  WARNING: No vehicles found. This could indicate:")
            print("   1. Chrome/ChromeDriver not available on this platform")
            print("   2. Network/connection issues")
            print("   3. Copart website blocking requests")
            print("   4. Search criteria too strict")
            # Don't clear cached data if scraping fails - keep old data
            if len(cached_data) > 0:
                print(f"ℹ️  Keeping {len(cached_data)} cached vehicles from previous scrape")
                return jsonify({
                    'success': False,
                    'error': 'Scraping returned 0 vehicles. This usually means Chrome/ChromeDriver is not available. Showing cached data instead.',
                    'data': cached_data,
                    'count': len(cached_data),
                    'cached': True
                })
        
        # Update cached data
        cached_data = vehicles
        
        return jsonify({
            'success': True,
            'data': vehicles,
            'count': len(vehicles)
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"ERROR in refresh_data: {error_msg}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get current vehicle data"""
    global cached_data
    return jsonify({
        'success': True,
        'data': cached_data,
        'count': len(cached_data)
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
