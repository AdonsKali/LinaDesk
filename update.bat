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
    echo [%RED%ERROR%RESET%] Python not found in PATH
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
        echo [%RED%ERROR%RESET%] The update failed. Please check your internet connection.
    ) else (
        echo [%GREEN%OK%RESET%] Files have been updated.
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
where nvidia-smi >nul 2>nul
if %errorlevel%==0 (
    echo [%GREEN%OK%RESET%] CUDA NVIDIA is installed
    echo.
    echo CUDA version:
    nvidia-smi --query-gpu=driver_version,cuda_version --format=csv,noheader
    echo.
    set URL=https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.23-cu125/llama_cpp_python-0.3.23-py3-none-win_amd64.whl
    set FILENAME=llama_cpp_python-0.3.23-py3-none-win_amd64.w

    echo Download llama-cpp-python...
    powershell -Command "Invoke-WebRequest -Uri %URL% -OutFile %FILENAME%"
    if exist %FILENAME% (
        echo Installation...
        
        pip install %FILENAME%
        
        if %errorlevel%==0 (
            echo Complete!
            python -c "from llama_cpp import Llama; print('Import check [OK]')"
            del %FILENAME%
        ) else (
            echo [%RED%ERROR%REST%] while installing llama-cpp-python!
        )
    ) else (
        echo [%RED%ERROR%RESET%] while downloading llama-cpp-python!
    )
) else (
    echo [%YELLOW%ERROR%RESET%] CUDA is not available (CPU only)
    goto :no_cuda
)
echo Starting model download...
"%~dp0\.venv\Scripts\python.exe" utils\download_model.py

echo.
python -m pip cache purge


echo ╶┬╮╭─╮╭╮╷╭─╴
echo  │││ ││╰┤├╴ 
echo ╶┴╯╰─╯╵ ╵╰─╴

echo %GREEN%Now you can run the application via run.bat%RESET%

pause