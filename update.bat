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
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
set "GREEN=%ESC%[92m"     
set "RED=%ESC%[91m"    
set "YELLOW=%ESC%[93m"  
set "RESET=%ESC%[0m"                                                                                   

where python >nul 2>nul
if errorlevel 1 (
    echo [%RED%ERR%RESET%] Python not found in PATH
    echo Install Python 3.10.6 or add it to your PATH
    pause
    exit /b 1
)
echo.

where git >nul 2>nul
if errorlevel 1 (
    echo [%YELLOW%WARN%RESET%] Git is not find in the PATH. Updating files from the repository was missed.
    echo Install Git or add it to your PATH.
) else (
    echo [%GREEN%INFO%RESET%] Updating files from repository...
    
    git fetch --all >nul 2>&1
    git reset --hard origin/dev >nul 2>&1
    
    if errorlevel 1 (
        echo [%RED%ERR%RESET%] The update failed. Please check your internet connection.
    ) else (
        echo [%GREEN%INFO%RESET%] Files have been updated.
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
cd backend\infrastructure\services\inference

reg query "HKLM\SOFTWARE\NVIDIA Corporation\GPU Computing Toolkit\CUDA" >nul 2>&1
if %errorlevel%==0 (
    echo [%GREEN%INFO%RESET%] CUDA ToolKit is found
    echo.
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
    echo.
    echo [%GREEN%INFO%RESET%] Install/update llama-cpp-python
    if exist "llama-cpp-python" (
        echo [%GREEN%INFO%RESET%] Updating existing installation...
        cd llama-cpp-python
        git pull --recurse-submodules
        pip install -e . --no-build-isolation --no-cache-dir --upgrade
    ) else (
        echo [%GREEN%INFO%RESET%] Cloning repository...
        git clone --recursive https://github.com/abetlen/llama-cpp-python
        cd llama-cpp-python
        pip install -e . --no-build-isolation --no-cache-dir
    )
) else (
    echo [%YELLOW%WARN%RESET%] CUDA ToolKit is not found
    pip install llama-cpp-python --upgrade
)

cd ..\..\..\..\..

echo Starting model download...
"%~dp0\.venv\Scripts\python.exe" utils\download_model.py

echo.
python -m pip cache purge


echo ╶┬╮╭─╮╭╮╷╭─╴
echo  │││ ││╰┤├╴ 
echo ╶┴╯╰─╯╵ ╵╰─╴

echo %GREEN%Now you can run the application via run.bat%RESET%

pause