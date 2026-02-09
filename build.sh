#!/bin/bash
set -e

echo "🔧 Upgrading build tools..."
pip install --upgrade pip setuptools wheel

echo "🔧 Installing greenlet (Playwright dependency)..."
# Force binary wheel installation to avoid compilation errors
pip install --no-cache-dir --only-binary :all: greenlet || \
pip install --no-cache-dir --prefer-binary greenlet || \
pip install --no-cache-dir "greenlet>=2.0.0,<4.0.0" || \
echo "⚠️  Warning: greenlet installation had issues, continuing..."

echo "🔧 Installing Python dependencies..."
# Try to install with binary wheels first to avoid compilation
pip install --no-cache-dir --prefer-binary -r requirements.txt || {
    echo "⚠️  Standard installation failed, trying with --only-binary for problematic packages..."
    # Install playwright separately with binary preference
    pip install --no-cache-dir --prefer-binary playwright==1.40.0 || \
    pip install --no-cache-dir playwright==1.40.0
    # Install other dependencies
    pip install --no-cache-dir --prefer-binary flask requests beautifulsoup4 python-dotenv || \
    pip install --no-cache-dir flask requests beautifulsoup4 python-dotenv
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
