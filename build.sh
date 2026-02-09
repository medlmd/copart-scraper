#!/bin/bash
set -e

echo "🔧 Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install --no-cache-dir -r requirements.txt
pip install --no-cache-dir gunicorn

echo "🔧 Installing Playwright browsers..."
playwright install chromium
playwright install-deps chromium

echo "✅ Build complete!"
