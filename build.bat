@echo off
echo ========================================
echo    AutoFollow X - Building EXE
echo ========================================
echo.

REM Проверяем установку Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR - Python not found!
    echo Please install Python from python.org
    pause
    exit /b 1
)

echo [1/6] Installing dependencies...
pip install pyinstaller --quiet --upgrade

echo.
echo [2/6] Installing Playwright browsers...
echo This may take a few minutes...
python -m playwright install chromium
if errorlevel 1 (
    echo.
    echo ERROR - Failed to install Playwright browsers!
    echo Please run: python -m playwright install chromium
    pause
    exit /b 1
)

echo.
echo [3/6] Checking browser installation...
REM Ищем браузеры в разных местах
set BROWSER_FOUND=0

if exist "%USERPROFILE%\.cache\ms-playwright\chromium*" (
    set BROWSER_FOUND=1
    echo ✓ Found browsers in: %%USERPROFILE%%\.cache\ms-playwright
)

if exist "%LOCALAPPDATA%\ms-playwright\chromium*" (
    set BROWSER_FOUND=1
    echo ✓ Found browsers in: %%LOCALAPPDATA%%\ms-playwright
)

if exist "browsers\ms-playwright\chromium*" (
    set BROWSER_FOUND=1
    echo ✓ Found browsers in: local browsers folder
)

if !BROWSER_FOUND! == 0 (
    echo.
    echo ⚠ WARNING: Browsers not found!
    echo.
    echo Playwright browsers will be downloaded on first run.
    echo The application will handle this automatically.
    echo.
)

echo.
echo [4/6] Cleaning old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

echo.
echo [5/6] Building EXE file with bundled browsers...
pyinstaller --onefile ^
    --windowed ^
    --name "AutoFollow-X" ^
    --icon=NONE ^
    --add-data "telegram_bot.py;." ^
    --add-data "browsers;browsers" ^
    --hidden-import=telebot ^
    --hidden-import=customtkinter ^
    --hidden-import=playwright ^
    --hidden-import=playwright.sync_api ^
    --hidden-import=playwright._impl ^
    --hidden-import=nest_asyncio ^
    --collect-all=playwright ^
    --collect-all=customtkinter ^
    start.py

echo.
echo [6/6] Finalizing...

REM Проверяем успешность сборки
if exist "dist\AutoFollow-X.exe" (
    echo.
    echo ========================================
    echo    BUILD SUCCESSFUL!
    echo ========================================
    echo.
    echo EXE file created: dist\AutoFollow-X.exe
    echo.
    
    REM Создаем папку для готового приложения
    if not exist "Release" mkdir Release
    copy "dist\AutoFollow-X.exe" "Release\AutoFollow-X.exe" /Y >nul
    copy "config.json" "Release\config.json" /Y >nul
    copy "cookies.txt" "Release\cookies.txt" 2>nul
    copy "processed.txt" "Release\processed.txt" 2>nul
    copy "proxies.txt" "Release\proxies.txt" 2>nul
    copy "telegram_bot.py" "Release\telegram_bot.py" /Y >nul
    
    echo.
    echo ========================================
    echo  Ready-to-use folder: Release\
    echo ========================================
    echo.
    echo Files included:
    dir /b Release
    echo.
    echo SIZE of EXE:
    for %%A in ("Release\AutoFollow-X.exe") do echo   %%~zA bytes
    echo.
    echo PRESS ANY KEY TO EXIT
    pause >nul
    exit /b 0
) else (
    echo.
    echo ========================================
    echo    BUILD FAILED!
    echo ========================================
    echo.
    echo Please check the error messages above.
    echo.
    pause
    exit /b 1
)
