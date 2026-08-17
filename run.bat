@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "APP_PYTHON=.venv\Scripts\python.exe"
    goto run_app
)

if exist "venv\Scripts\python.exe" (
    set "APP_PYTHON=venv\Scripts\python.exe"
    goto run_app
)

echo Creating Python virtual environment...
where py >nul 2>nul
if errorlevel 1 goto use_python

py -3 -m venv .venv
goto check_venv

:use_python
python -m venv .venv

:check_venv
if not exist ".venv\Scripts\python.exe" (
    echo Python 3 was not found. Install Python and run this file again.
    pause
    exit /b 1
)

set "APP_PYTHON=.venv\Scripts\python.exe"
"%APP_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto install_failed

"%APP_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto install_failed

:run_app
"%APP_PYTHON%" -m capillaroscope_app
if errorlevel 1 pause
exit /b %errorlevel%

:install_failed
echo Could not install Python dependencies.
pause
exit /b 1
