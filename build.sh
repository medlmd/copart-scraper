#!/bin/bash
set -e

echo "🔧 Upgrading build tools..."
pip install --upgrade pip setuptools wheel

echo "🔧 Installing greenlet (Playwright dependency)..."
# Try multiple installation methods for greenlet
pip install --no-cache-dir greenlet || \
pip install --no-cache-dir --no-build-isolation greenlet || \
pip install --no-cache-dir --prefer-binary greenlet || \
echo "⚠️  Warning: greenlet installation had issues, continuing..."

echo "🔧 Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt || {
    echo "⚠️  Standard installation failed, trying with --no-build-isolation..."
    pip install --no-cache-dir --no-build-isolation -r requirements.txt
}

echo "🔧 Installing gunicorn..."
pip install --no-cache-dir gunicorn

echo "🔧 Installing Playwright browsers..."
# Only install browsers if not using Browserless (saves build time and space)
if [ -z "$BROWSERLESS_URL" ]; then
    echo "   Installing Chromium (Browserless not configured)..."
    playwright install chromium || echo "⚠️  Playwright browser install failed, continuing..."
    playwright install-deps chromium || echo "⚠️  Playwright deps install failed, continuing..."
else
    echo "ℹ️  Browserless configured - skipping local browser installation (saves ~200MB)"
fi

echo "✅ Build complete!"
