@echo off
chcp 65001 >nul
echo =====================================================
echo     AutoFollow-X — Сборка EXE (исправленная версия)
echo =====================================================
echo.

echo [1/5] Очистка...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo [2/5] Зависимости...
pip install nest_asyncio pyTelegramBotAPI customtkinter playwright

echo [3/5] Playwright браузер...
python -m playwright install chromium --with-deps

echo [4/5] Сборка...
pyinstaller --clean --onedir --windowed ^
  --name "AutoFollow-X" ^
  --distpath "dist" ^
  --hidden-import=nest_asyncio ^
  --hidden-import=telebot ^
  --hidden-import=customtkinter ^
  --hidden-import=playwright.sync_api ^
  --add-data "config.json;." ^
  --add-data "processed.txt;." ^
  --add-data "daily_stats.json;." ^
  --add-data "proxies.txt;." ^
  --add-data "cookies.txt;." ^
  --add-data "mat.txt;." ^
  start.py

echo.
echo =====================================================
echo.

if exist "dist\AutoFollow-X\AutoFollow-X.exe" (
    echo ✅ УСПЕХ! Файл готов:
    echo    dist\AutoFollow-X\AutoFollow-X.exe
) else if exist "dist\start\start.exe" (
    echo ✅ УСПЕХ! (старое имя)
    echo    dist\start\start.exe
) else (
    echo ❌ dist папка пуста или файл удалён.
    echo    Скорее всего виноват антивирус!
)
echo.
pause