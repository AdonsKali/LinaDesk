@echo off
chcp 65001 >nul
echo ========================================
echo  Обновление Lina AI
echo ========================================

where python >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Python не найден в PATH
    echo Установите Python 3.10.6 или добавьте его в PATH
    pause
    exit /b 1
)

echo.

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)  else (
    py -3.10 -m venv .venv
    call .venv\Scripts\activate.bat
)

echo.
python -m pip install --upgrade pip setuptools wheel

echo.

if exist "requirements.txt" (
    python -m pip install --upgrade -r requirements.txt
)

echo.
python -m pip list --outdated

echo.
python -m pip cache purge

echo.
echo ========================================
echo  Обновление завершено!
echo ========================================
"%~dp0\.venv\Scripts\python.exe" -m main
pause