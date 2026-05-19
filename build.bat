@echo off
echo Building Seenema...
pyinstaller ^
  --onefile ^
  --noconsole ^
  --windowed ^
  --name seenema ^
  --icon assets\icon.ico ^
  --add-data "assets\icon.ico;assets" ^
  main.py
echo.
echo Build complete: dist\seenema.exe
