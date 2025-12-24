#!/bin/bash

# Build script for Mac and Linux
echo "🚀 Starting Build for $(uname -s)..."

# 1. Install Requirements
echo "📦 Installing Dependencies..."
pip install -r requirements.txt
pip install pyinstaller

# 2. Run PyInstaller
echo "🔨 Building Executable..."
pyinstaller behave_runner.spec --clean --noconfirm

# 3. Verify Output
if [ -d "dist/behave_runner" ]; then
    echo "✅ Build Complete!"
    echo "📂 Output: dist/behave_runner"
    
    # Zip for distribution
    echo "📦 Creating Distribution Zip..."
    cd dist
    zip -r Behave_Runner_Distribution_$(uname -s).zip behave_runner
    echo "🎉 Created: dist/Behave_Runner_Distribution_$(uname -s).zip"
else
    echo "❌ Build Failed."
    exit 1
fi
