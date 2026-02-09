#!/bin/bash
set -e

echo "🔧 Checking Python version..."
python --version
python3 --version 2>/dev/null || true

echo "🔧 Upgrading build tools..."
python3 -m pip install --upgrade pip setuptools wheel || pip install --upgrade pip setuptools wheel

echo "🔧 Installing greenlet (Playwright dependency)..."
# Pin greenlet version for compatibility (works with Python 3.12)
pip install --no-cache-dir --prefer-binary "greenlet>=3.0,<4" || \
pip install --no-cache-dir "greenlet>=3.0,<4" || \
echo "⚠️  Warning: greenlet installation had issues, continuing..."

echo "🔧 Installing Python dependencies..."
# We always need Playwright (even with Browserless) to connect via CDP
# But we can skip the browser binaries if Browserless is configured
if [ -n "$BROWSERLESS_URL" ]; then
    echo "ℹ️  Browserless configured - installing dependencies..."
    # Install all dependencies normally (greenlet is now compatible with Python 3.12)
    pip install --no-cache-dir --prefer-binary -r requirements.txt || \
    pip install --no-cache-dir -r requirements.txt || \
    echo "⚠️  Some dependencies had issues, continuing..."
    echo "✅ Dependencies installed (for Browserless CDP connection)"
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
