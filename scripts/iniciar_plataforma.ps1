# Inicia la plataforma completa en Windows (API + App Administrador + App EPS) en ventanas separadas.
# Uso (desde la raíz del proyecto):  powershell -ExecutionPolicy Bypass -File scripts\iniciar_plataforma.ps1
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Error "No existe .venv. Ejecute primero la instalación del README."; exit 1 }

Start-Process -WorkingDirectory $root -FilePath $py -ArgumentList "-m uvicorn ecnt_api.main:app --port 8000"
Start-Sleep -Seconds 3
Start-Process -WorkingDirectory $root -FilePath $py -ArgumentList "-m streamlit run apps/admin/app.py --server.port 8501"
Start-Process -WorkingDirectory $root -FilePath $py -ArgumentList "-m streamlit run apps/eps/app.py --server.port 8502 --theme.primaryColor #065F46"

Write-Host "API:            http://localhost:8000/docs"
Write-Host "Administrador:  http://localhost:8501"
Write-Host "EPS:            http://localhost:8502"
