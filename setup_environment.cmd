@echo off
setlocal
cd /d "%~dp0"

if not exist env\Scripts\python.exe (
    py -3.13 -m venv env
    if errorlevel 1 exit /b 1
)

env\Scripts\python.exe -m pip install --upgrade pip
env\Scripts\python.exe -m pip install -r requirements-dev.txt
env\Scripts\python.exe -c "from custom_components.niko_home_control_local.niko_client import NikoClient; print('Standalone NikoClient import: OK')"
if errorlevel 1 exit /b 1

if not exist debug_config.json copy debug_config.example.json debug_config.json >nul

echo.
echo Omgeving klaar. Vul nu debug_config.json in en start debug_niko_connection.py.
endlocal
