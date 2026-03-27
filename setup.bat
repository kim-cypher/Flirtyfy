@echo off
REM Flirty App Setup Script for Windows
REM This script automates the setup of both backend and frontend

echo ================================
echo Flirty App - Windows Setup Script
echo ================================
echo.

REM Check Python installation
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Failed: Python is not installed. Please install Python 3.8+
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] %PYTHON_VERSION%
echo.

REM Check Node.js installation
echo Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo Failed: Node.js is not installed. Please install Node.js 14+
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo [OK] Node.js %NODE_VERSION%
for /f "tokens=*" %%i in ('npm --version') do set NPM_VERSION=%%i
echo [OK] npm %NPM_VERSION%
echo.

REM Backend Setup
echo ================================
echo Setting up Backend...
echo ================================
cd backend

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing backend dependencies...
pip install -r requirements.txt

REM Copy .env file
if not exist .env (
    echo Creating .env file from .env.example...
    copy .env.example .env
)

REM Run migrations
echo Running database migrations...
python manage.py migrate

echo [OK] Backend setup complete!
echo.
echo To start the backend, run:
echo   cd backend
echo   venv\Scripts\activate.bat
echo   python manage.py runserver
echo.

REM Frontend Setup
echo ================================
echo Setting up Frontend...
echo ================================
cd ..\frontend

REM Copy .env file
if not exist .env (
    echo Creating .env file from .env.example...
    copy .env.example .env
)

REM Install dependencies
echo Installing frontend dependencies...
call npm install

echo [OK] Frontend setup complete!
echo.
echo To start the frontend, run:
echo   cd frontend
echo   npm start
echo.

echo ================================
echo Setup Complete!
echo ================================
echo.
echo Next steps:
echo 1. Terminal 1: cd backend && venv\Scripts\activate.bat && python manage.py runserver
echo 2. Terminal 2: cd frontend && npm start
echo 3. Visit http://localhost:3000 in your browser
echo.
pause