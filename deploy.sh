#!/bin/bash

# Deployment script for Copart Scraper Dashboard

echo "🚀 Copart Scraper Deployment Script"
echo "===================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+ first."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Check if Chrome is installed
if ! command -v google-chrome &> /dev/null && ! command -v chromium-browser &> /dev/null; then
    echo "⚠️  Chrome/Chromium not found. Installing dependencies..."
    echo "   Please install Google Chrome manually: https://www.google.com/chrome/"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

echo ""
echo "✅ Installation complete!"
echo ""
echo "To run the application:"
echo "  1. Development: python3 app.py"
echo "  2. Production:  gunicorn -w 4 -b 0.0.0.0:8080 app:app"
echo ""
echo "Or use Docker:"
echo "  docker-compose up -d"
echo ""
