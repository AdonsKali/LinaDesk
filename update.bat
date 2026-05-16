@echo off
chcp 65001 >nul
cls
echo   .---.    .-./`) ,---.   .--.   ____              ___    _ .-------.  ______        ____   ,---------.    .-''-.   
echo   ^| ,_^|    \ .-.')^|    \  ^|  ^| .'  __ `.         .'   ^|  ^| ^|\  _(`)_ \^|    _ `''.  .'  __ `.\          \ .'_ _   \  
echo ,-./  )    / `-' \^|  ,  \ ^|  ^|/   '  \  \        ^|   .'  ^| ^|^| (_ o._)^|^| _ ^| ) _  \/   '  \  \`--.  ,---'/ ( ` )   ' 
echo \  '_ '`)   `-'`"`|  |\_ \|  ||___|  /  |        .'  '_  | ||  (_,_) /|( ''_'  ) ||___|  /  |   |   \  . (_ o _)  | 
echo  > (_)  )   .---. ^|  _( )_\  ^|   _.-`   ^|        '   ( \.-.^|^|   '-.-' ^| . (_) `. ^|   _.-`   ^|   :_ _:  ^|  (_,_)___^| 
echo (  .  .-'   ^|   ^| ^| (_ o _)  ^|.'   _    ^|        ' (`. _` /^|^|   ^|     ^|(_    ._) '.'   _    ^|   (_I_)  '  \   .---. 
echo  `-'`-'^|___ ^|   ^| ^|  (_,_)\  ^|^|  _( )_  ^|        ^| (_ (_) _)^|   ^|     ^|  (_.\.' / ^|  _( )_  ^|  (_(=)_)  \  `-'    / 
echo   ^|        \^|   ^| ^|  ^|    ^|  ^|\ (_ o _) /         \ /  . \ //   )     ^|       .'  \ (_ o _) /   (_I_)    \       /  
echo   `--------`'---' '--'    '--' '.(_,_).'           ``-'`-'' `---'     '-----'`     '.(_,_).'    '---'     `'-..-'   
                                                                                                              

where python >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Python не найден в PATH
    echo Установите Python 3.10.6 или добавьте его в PATH
    pause
    exit /b 1
)
echo.

where git >nul 2>nul
if errorlevel 1 (
    echo [WARN] Git не найден в PATH. Обновление файлов из репозитория пропущено.
    echo Установите Git или добавьте его в PATH.
) else (
    echo [INFO] Обновление файлов из репозитория...
    git pull
    if errorlevel 1 (
        echo [ERROR] Не удалось выполнить git pull. Проверьте подключение к интернету и права доступа.
    ) else (
        echo [OK] Репозиторий обновлён.
    )
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
echo Starting model download...
"%~dp0\.venv\Scripts\python.exe" utils\download_model.py

echo.
python -m pip list --outdated

echo.
python -m pip cache purge

echo╶┬╮╭─╮╭╮╷╭─╴
echo │││ ││╰┤├╴ 
echo╶┴╯╰─╯╵ ╵╰─╴

"%~dp0\.venv\Scripts\python.exe" -m main
pause