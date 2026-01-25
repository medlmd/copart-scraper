"""
Flask application for Copart Toyota Corolla Dashboard
"""
from flask import Flask, render_template, jsonify
from scraper import scrape_copart_corolla

app = Flask(__name__)

# Store cached data
cached_data = []

@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Refresh vehicle data by scraping Copart"""
    try:
        # Scrape new data (maximum possible)
        vehicles = scrape_copart_corolla(limit=1000)  # High limit to scrape as many as possible
        
        # Update cached data
        global cached_data
        cached_data = vehicles
        
        return jsonify({
            'success': True,
            'data': vehicles,
            'count': len(vehicles)
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
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
