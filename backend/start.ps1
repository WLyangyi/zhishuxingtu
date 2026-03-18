$ErrorActionPreference = "Continue"
Write-Host "Starting 知枢星图 Backend..."
Set-Location "d:\知枢星图\backend"
& "C:\Users\流离\AppData\Roaming\Python\Python313\Scripts\uvicorn.exe" app.main:app --reload --port 8000
Write-Host ""
Write-Host "Service stopped. Press Enter to exit..."
Read-Host
