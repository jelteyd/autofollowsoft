@echo off
echo ========================================
echo    AutoFollow X - Installing Browsers
echo ========================================
echo.
echo Installing Playwright browsers to system...
echo This will download ~200MB, please wait...
echo.

python -m playwright install chromium

if errorlevel 1 (
    echo.
    echo ERROR - Failed to install browsers!
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo ✓ Browsers installed successfully!
echo.
echo Now building EXE...
build.bat
