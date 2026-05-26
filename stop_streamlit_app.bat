@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$lines = netstat -ano | Select-String 'LISTENING';" ^
  "$pids = @();" ^
  "foreach ($l in $lines) {" ^
  "  $parts = ($l.ToString() -replace '\s+', ' ').Trim().Split(' ');" ^
  "  if ($parts.Length -lt 5) { continue }" ^
  "  $local = $parts[1]; $ownPid = $parts[4];" ^
  "  if ($local -match ':(85(0[1-9]|1[0-9]|20))$' -and $ownPid -match '^\d+$') { $pids += [int]$ownPid }" ^
  "}" ^
  "$pids = $pids | Sort-Object -Unique;" ^
  "if (-not $pids) { Write-Host 'Nenhum processo ouvindo entre as portas 8501 e 8520.'; exit 0 }" ^
  "foreach ($streamlitPid in $pids) {" ^
  "  Stop-Process -Id $streamlitPid -Force -ErrorAction SilentlyContinue;" ^
  "  Write-Host ('Encerrado PID: ' + $streamlitPid);" ^
  "}"

endlocal
