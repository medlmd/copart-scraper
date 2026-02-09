#!/bin/bash
set -e

echo "🔧 Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install --no-cache-dir -r requirements.txt
pip install --no-cache-dir gunicorn

echo "✅ Build complete!"
echo "ℹ️  Note: Chrome/Chromium should be installed via Render's system packages or Docker"
