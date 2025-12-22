#!/bin/bash

echo "=========================================="
echo "     Behave Runner App Launcher 🚀"
echo "=========================================="

# 1. Check for Python 3
if ! command -v python3 &> /dev/null
then
    echo "[ERROR] python3 could not be found. Please install Python."
    exit 1
fi

# 2. Create venv if missing
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment 'venv'..."
    python3 -m venv venv
fi

# 3. Activate & Install
echo "[INFO] Activating environment..."
source venv/bin/activate

echo "[INFO] Installing dependencies..."
pip install --upgrade pip > /dev/null
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "[WARNING] requirements.txt missing. Installing defaults..."
    pip install streamlit pandas behave allure-behave requests selenium Appium-Python-Client psutil
fi

# 4. Run App
echo ""
echo "[INFO] Launching Streamlit..."
streamlit run app.py
