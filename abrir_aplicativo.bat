@echo off
setlocal
cd /d "%~dp0"

echo Iniciando aplicativo...
echo.

if exist "%~dp0run_streamlit_app.bat" (
  call "%~dp0run_streamlit_app.bat"
  if errorlevel 1 (
    echo.
    echo Nao foi possivel iniciar o Streamlit.
    echo Abrindo a versao HTML local...
    start "" "%~dp0index.html"
    pause
  )
) else (
  start "" "%~dp0index.html"
)

endlocal
