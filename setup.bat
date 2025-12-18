@echo off
echo ==========================================
echo      Behave Runner App Installer 🚀
echo ==========================================

REM 1. Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ and try again.
    pause
    exit /b
)

REM 2. Create Virtual Environment
if not exist "venv" (
    echo [INFO] Creating virtual environment 'venv'...
    python -m venv venv
) else (
    echo [INFO] Virtual environment 'venv' already exists.
)

REM 3. Activate Virtual Environment & Install Dependencies
echo [INFO] Installing requirements...
call venv\Scripts\activate
pip install --upgrade pip
if exist "requirements.txt" (
    pip install -r requirements.txt
) else (
    echo [WARNING] requirements.txt not found! Installing Streamlit manually...
    pip install streamlit pandas
)

echo.
echo ==========================================
echo      Installation Complete! ✅
echo ==========================================
echo.
echo To run the app, simply execute:
echo venv\Scripts\streamlit run app.py
echo.
pause
