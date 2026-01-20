#!/bin/bash
# Build script for Secure Media Processor
# Usage: ./scripts/build_package.sh

set -e  # Exit on error

echo "🔨 Building Secure Media Processor Package"
echo "=========================================="

# Clean previous builds
echo ""
echo "1. Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info src/*.egg-info
echo "✓ Cleaned"

# Install/upgrade build tools
echo ""
echo "2. Installing build tools..."
pip install --upgrade build twine
echo "✓ Build tools ready"

# Build package
echo ""
echo "3. Building package..."
python -m build
echo "✓ Package built"

# Check package
echo ""
echo "4. Checking package quality..."
twine check dist/*
echo "✓ Package passed checks"

# List created files
echo ""
echo "5. Created files:"
ls -lh dist/

echo ""
echo "✅ BUILD COMPLETE!"
echo ""
echo "Next steps:"
echo "  • Test locally: pip install dist/*.whl"
echo "  • Upload to Test PyPI: twine upload --repository testpypi dist/*"
echo "  • Upload to PyPI: twine upload dist/*"
echo ""
echo "See PUBLISHING_GUIDE.md for detailed instructions"
