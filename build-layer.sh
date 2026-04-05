#!/bin/bash
# build-layer.sh - Run this in AWS CloudShell

echo "Creating Lambda Layer..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
echo "Python version: $PYTHON_VERSION"

# Clean up
rm -rf python layer.zip

# Create directory structure for Lambda layer
# Lambda expects: python/lib/python3.12/site-packages/
mkdir -p python/lib/python${PYTHON_VERSION}/site-packages

# Install dependencies
echo "Installing dependencies (this may take a few minutes)..."
python3 -m pip install -r requirements-lambda.txt -t python/lib/python${PYTHON_VERSION}/site-packages/ --no-cache-dir

# Verify installation
if [ ! -d "python/lib/python${PYTHON_VERSION}/site-packages" ] || [ -z "$(ls -A python/lib/python${PYTHON_VERSION}/site-packages)" ]; then
    echo "❌ ERROR: Dependencies were not installed!"
    echo "Check if python3 -m pip is available and requirements-lambda.txt exists"
    exit 1
fi

# Verify critical packages are installed
echo "Verifying critical packages..."
if [ ! -d "python/lib/python${PYTHON_VERSION}/site-packages/mangum" ]; then
    echo "❌ ERROR: mangum is missing from the layer!"
    exit 1
fi
if [ ! -d "python/lib/python${PYTHON_VERSION}/site-packages/fastapi" ]; then
    echo "❌ ERROR: fastapi is missing from the layer!"
    exit 1
fi
echo "✅ Critical packages verified (mangum, fastapi)"

# Create zip file (keep top-level 'python/' directory for Lambda layer)
echo "Creating layer zip..."
zip -r layer.zip python -q

# Check size
if [ -f "layer.zip" ]; then
SIZE=$(du -h layer.zip | cut -f1)
    FILE_COUNT=$(unzip -l layer.zip | tail -1 | awk '{print $2}')
echo ""
echo "✅ Layer created successfully!"
echo "File: layer.zip"
echo "Size: $SIZE"
    echo "Files: $FILE_COUNT"
echo ""
echo "Next steps:"
echo "1. Download layer.zip (Actions → Download file)"
echo "2. Go to Lambda Console → Layers → Create layer"
echo "3. Upload layer.zip"
echo "4. Attach layer to your Lambda function"
else
    echo "❌ ERROR: layer.zip was not created!"
    exit 1
fi