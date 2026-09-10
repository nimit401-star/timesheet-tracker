@echo off
cd /d %~dp0
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Setup failed. Make sure Python is installed and available as 'python'.
  pause
  exit /b 1
)
echo.
echo Setup complete.
pause
