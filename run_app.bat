@echo off
setlocal
title Behave Runner Launcher 🚀

echo ==========================================
echo      Behave Runner App Launcher
echo ==========================================

REM 1. Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ from python.org
    pause
    exit /b
)

REM 2. Create Virtual Environment if missing
if not exist "venv" (
    echo [INFO] Creating virtual environment 'venv'...
    python -m venv venv
)

REM 3. Activate & Install Requirements
echo [INFO] Checking dependencies...
call venv\Scripts\activate

REM Upgrade pip just in case
python -m pip install --upgrade pip >nul 2>&1

if exist "requirements.txt" (
    pip install -r requirements.txt
) else (
    echo [WARNING] requirements.txt not found! Installing Streamlit manually...
    pip install streamlit pandas behave allure-behave requests selenium Appium-Python-Client psutil
)

REM 4. Launch Streamlit
echo.
echo [INFO] Launching App...
streamlit run app.py

pause
