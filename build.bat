@echo off
setlocal
echo Building Seenema...

where pyinstaller >nul 2>nul
if errorlevel 1 (
  echo ERROR: pyinstaller not found on PATH.
  echo Activate your venv first:  .\.venv\Scripts\Activate.ps1   ^(PowerShell^)
  echo                       or:  source .venv/Scripts/activate  ^(Git Bash^)
  exit /b 1
)

pyinstaller ^
  --onefile ^
  --noconsole ^
  --windowed ^
  --name seenema ^
  --icon assets\icon.ico ^
  --add-data "assets\icon.ico;assets" ^
  main.py
if errorlevel 1 (
  echo.
  echo Build FAILED.
  exit /b 1
)

echo.
echo Build complete: dist\seenema.exe
endlocal
