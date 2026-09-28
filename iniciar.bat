@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo O ambiente do programa ainda nao foi configurado.
    echo Siga as instrucoes do README.md antes de usar.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" gui.py

if errorlevel 1 (
    echo.
    echo O programa fechou com um erro. Veja a mensagem acima.
    pause
)
