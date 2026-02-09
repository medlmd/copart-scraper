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
# If Browserless is configured, we can skip Playwright entirely
if [ -n "$BROWSERLESS_URL" ]; then
    echo "ℹ️  Browserless configured - installing minimal dependencies..."
    # Install everything except playwright
    pip install --no-cache-dir --prefer-binary flask==3.0.0 requests==2.31.0 beautifulsoup4==4.12.2 python-dotenv==1.0.0 || \
    pip install --no-cache-dir flask==3.0.0 requests==2.31.0 beautifulsoup4==4.12.2 python-dotenv==1.0.0
    
    # Install playwright without dependencies (we won't use it)
    pip install --no-cache-dir --no-deps playwright==1.40.0 || \
    echo "⚠️  Playwright install skipped (not needed with Browserless)"
else
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
fi

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
