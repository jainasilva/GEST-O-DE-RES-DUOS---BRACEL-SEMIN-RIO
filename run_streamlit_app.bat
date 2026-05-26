@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
set "PORT=8501"

if /I "%PYTHON_EXE%"=="python" (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python nao encontrado.
    echo Instale o Python ou ative o ambiente virtual do projeto.
    pause
    endlocal
    exit /b 1
  )
)

rem Escolhe uma porta livre entre 8501 e 8520.
for /f %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$start=8501; $end=8520; $found=$null; for($p=$start; $p -le $end; $p++){ try { $l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse('127.0.0.1'), $p); $l.Start(); $l.Stop(); $found = $p; break } catch {} } if($found -ne $null){ Write-Output $found }"') do set "PORT=%%P"

if "%PORT%"=="" (
  echo Nao foi possivel encontrar porta livre entre 8501 e 8520.
  pause
  endlocal
  exit /b 1
)

set "URL=http://127.0.0.1:%PORT%"

echo Iniciando o aplicativo Streamlit...
echo URL esperada: %URL%
echo Mantenha esta janela aberta enquanto usar o aplicativo.
echo.

rem Abre o navegador automaticamente quando a URL responder.
start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
  "$u = '%URL%';" ^
  "for ($i = 0; $i -lt 90; $i++) {" ^
  "  try { $r = Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -ge 200) { Start-Process $u; break } } catch {};" ^
  "  Start-Sleep -Seconds 1;" ^
  "}"

"%PYTHON_EXE%" -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port %PORT% --server.headless true

echo.
echo O Streamlit foi encerrado.
pause
endlocal
