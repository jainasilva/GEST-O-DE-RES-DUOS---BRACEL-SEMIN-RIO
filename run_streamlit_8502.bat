@echo off
setlocal
cd /d "%~dp0"

set "PORT=8502"
set "URL=http://127.0.0.1:%PORT%"
set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

echo Iniciando Streamlit...
echo URL: %URL%
echo.

"%PYTHON_EXE%" -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port %PORT% --server.headless true

echo.
echo O Streamlit foi encerrado.
pause
endlocal
