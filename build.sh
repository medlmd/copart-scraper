#!/bin/bash
set -e

echo "🔧 Checking Python version..."
python --version
python3 --version 2>/dev/null || true

echo "🔧 Upgrading build tools..."
python3 -m pip install --upgrade pip setuptools wheel || pip install --upgrade pip setuptools wheel

# Skip greenlet entirely if using Browserless (we don't need it for CDP connection)
if [ -n "$BROWSERLESS_URL" ]; then
    echo "ℹ️  Browserless configured - skipping greenlet installation (not needed for CDP)"
    SKIP_GREENLET=1
else
    echo "🔧 Installing greenlet (Playwright dependency)..."
    # Check Python version first
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1 || echo "unknown")
    echo "   Detected Python version: $PYTHON_VERSION"

    # For Python 3.13, try newer greenlet version or skip
    if [[ "$PYTHON_VERSION" == "3.13"* ]]; then
        echo "⚠️  Python 3.13 detected - trying greenlet 3.1.0+ (supports Python 3.13)"
        # Try newer greenlet version that supports Python 3.13
        pip install --no-cache-dir --prefer-binary "greenlet>=3.1.0" || \
        pip install --no-cache-dir --only-binary :all: greenlet || \
        pip install --no-cache-dir --prefer-binary greenlet || \
        echo "⚠️  Greenlet installation failed - continuing without it"
        SKIP_GREENLET=1
    else
        # For Python 3.11 and earlier, normal installation
        pip install --no-cache-dir --only-binary :all: greenlet || \
        pip install --no-cache-dir --prefer-binary greenlet || \
        pip install --no-cache-dir "greenlet>=2.0.0,<3.0.0" || \
        echo "⚠️  Warning: greenlet installation had issues, continuing..."
    fi
fi

echo "🔧 Installing Python dependencies..."
# We always need Playwright (even with Browserless) to connect via CDP
# But we can skip the browser binaries if Browserless is configured
if [ -n "$BROWSERLESS_URL" ]; then
    echo "ℹ️  Browserless configured - installing dependencies (skipping greenlet)..."
    # Install core dependencies first
    python3 -m pip install --no-cache-dir --prefer-binary flask==3.0.0 requests==2.31.0 beautifulsoup4==4.12.2 python-dotenv==1.0.0 || \
    pip install --no-cache-dir --prefer-binary flask==3.0.0 requests==2.31.0 beautifulsoup4==4.12.2 python-dotenv==1.0.0 || \
    pip install --no-cache-dir flask==3.0.0 requests==2.31.0 beautifulsoup4==4.12.2 python-dotenv==1.0.0
    
    # Install Playwright without greenlet dependency (we don't need it for CDP connection)
    echo "   Installing Playwright without greenlet (Browserless CDP doesn't require it)..."
    # Install Playwright's other dependencies first (except greenlet)
    pip install --no-cache-dir --prefer-binary pyee typing-extensions || true
    
    # Install Playwright without greenlet dependency
    pip install --no-cache-dir --no-deps playwright==1.40.0 || \
    pip install --no-cache-dir playwright==1.40.0 --no-deps || \
    echo "⚠️  Playwright installation had issues, but CDP connection may still work"
    echo "✅ Playwright installed (for Browserless CDP connection)"
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
