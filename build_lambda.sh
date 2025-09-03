#!/bin/bash
# Build script for AWS Lambda deployment

set -e

echo "🚀 Building Lambda deployment package..."

# Create lambda package directory
mkdir -p terraform/lambda_package

# Copy required files
echo "📁 Copying source files..."
cp lambda_handler.py terraform/lambda_package/
cp centralized_mcp_server.py terraform/lambda_package/
cp core.py terraform/lambda_package/
cp utils.py terraform/lambda_package/
cp requirements.txt terraform/lambda_package/

# Create directories
mkdir -p terraform/lambda_package/contexts
mkdir -p terraform/lambda_package/personas

# Copy data files
cp -r contexts/* terraform/lambda_package/contexts/ 2>/dev/null || true
cp -r personas/* terraform/lambda_package/personas/ 2>/dev/null || true

# Install dependencies
echo "📦 Installing dependencies..."
cd terraform/lambda_package
pip install -r requirements.txt -t .

# Remove unnecessary files to reduce package size
echo "🧹 Cleaning up package..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.pyc" -delete 2>/dev/null || true
find . -type d -name "*.pyo" -delete 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

# Remove development dependencies
rm -rf *.egg-info 2>/dev/null || true
rm -rf .pytest_cache 2>/dev/null || true

cd ../..

echo "✅ Lambda package built successfully!"
echo "📦 Package location: terraform/lambda_package"
echo "📏 Package size: $(du -sh terraform/lambda_package | cut -f1)"
