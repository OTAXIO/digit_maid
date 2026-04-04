@echo off
setlocal

cd /d %~dp0

set "PYTHON_EXE=python"
if defined CONDA_PREFIX (
  if exist "%CONDA_PREFIX%\python.exe" set "PYTHON_EXE=%CONDA_PREFIX%\python.exe"
)
if not "%DM_PYTHON%"=="" set "PYTHON_EXE=%DM_PYTHON%"

set SKIP_INSTALL=0
if /I "%~1"=="--skip-install" set SKIP_INSTALL=1

echo [0/3] Checking Python...
"%PYTHON_EXE%" -c "import sys; print(sys.executable)"
if errorlevel 1 (
  echo Python is not available in PATH.
  exit /b 1
)

if "%SKIP_INSTALL%"=="0" (
  echo [1/3] Installing runtime dependencies...
  "%PYTHON_EXE%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Failed to install runtime dependencies.
    exit /b 1
  )

  echo [2/3] Installing build dependency PyInstaller...
  "%PYTHON_EXE%" -m pip install pyinstaller==6.16.0
  if errorlevel 1 (
    echo Failed to install PyInstaller.
    exit /b 1
  )
) else (
  echo [1/3] Skipping dependency install --skip-install.
)

echo [3/3] Building DigitMaid.exe from DigitMaid.spec...
"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean DigitMaid.spec
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

if not exist "dist\DigitMaid.exe" (
  echo Build finished but dist\DigitMaid.exe was not found.
  exit /b 1
)

echo Build finished: dist\DigitMaid.exe
endlocal
