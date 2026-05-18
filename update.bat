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

set "GREEN=%ESC%[92m"     
set "RED=%ESC%[91m"    
set "YELLOW=%ESC%[93m"                                                                                     

where python >nul 2>nul
if errorlevel 1 (
    echo [%RED%ERROR%RED%] Python not found in PATH
    echo Install Python 3.10.6 or add it to your PATH
    pause
    exit /b 1
)
echo.

where git >nul 2>nul
if errorlevel 1 (
    echo [%YELLOW%WARN%YELLOW%] Git is not find in the PATH. Updating files from the repository was missed.
    echo Install Git or add it to your PATH.
) else (
    echo [%GREEN%INFO%GREEN%] Updating files from repository...
    
    git pull
    
    if errorlevel 1 (
        echo [%RED%ERROR%RED%] The update failed. Please check your internet connection.
    ) else (
        echo [%GREEN%OK%GREEN%] Files have been updated.
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

if exist "requirements.txt" (
    python -m pip install --upgrade -r requirements.txt
)
echo Starting model download...
"%~dp0\.venv\Scripts\python.exe" utils\download_model.py

echo.
python -m pip cache purge

echo╶┬╮╭─╮╭╮╷╭─╴
echo │││ ││╰┤├╴ 
echo╶┴╯╰─╯╵ ╵╰─╴

echo %GREEN%Now you can run the application via run.bat%GREEN%

pause