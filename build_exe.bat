@echo off
setlocal

cd /d %~dp0

echo [1/2] Installing PyInstaller...
python -m pip install -U pyinstaller
if errorlevel 1 (
  echo Failed to install PyInstaller.
  exit /b 1
)

echo [2/2] Building DigitMaid.exe...
pyinstaller --noconfirm --clean --windowed --onefile --name DigitMaid ^
  --icon="icon.ico" ^
  --paths . ^
  --add-data "resource;resource" ^
  --add-data "src/function/apps.yaml;src/function" ^
  --add-data "src/input/dialog_style.yaml;src/input" ^
  --add-data "src/ui/pet_animations.yaml;src/ui" ^
  src/core/run.py
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

echo Build finished: dist\DigitMaid.exe
endlocal
