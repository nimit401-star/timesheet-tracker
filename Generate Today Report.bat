@echo off
cd /d %~dp0
python daily_report.py
if errorlevel 1 (
  echo.
  echo Report generation failed. Check the message above.
  pause
  exit /b 1
)
echo.
echo Report generated in the reports folder.
pause
