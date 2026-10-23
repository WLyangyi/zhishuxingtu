@echo off
chcp 65001 >nul
setlocal
rem Root = parent dir of this script's bin folder
set "ROOT=%~dp0.."

if /i "%~1"=="backend" goto :backend
if /i "%~1"=="frontend" goto :frontend

rem ---- default: start full stack (backend + frontend + browser) ----
echo [zhishuxingtu] starting backend (port 8000) and frontend (port 5173) ...
start "zst-backend" cmd /k "chcp 65001 >nul & set DEBUG=true & cd /d %ROOT%\backend & .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
start "zst-frontend" cmd /k "chcp 65001 >nul & cd /d %ROOT%\frontend & npm run dev"
timeout /t 6 /nobreak >nul
start "" http://localhost:5173
echo [zhishuxingtu] backend window: zst-backend / frontend window: zst-frontend
goto :eof

:backend
start "zst-backend" cmd /k "chcp 65001 >nul & set DEBUG=true & cd /d %ROOT%\backend & .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
goto :eof

:frontend
start "zst-frontend" cmd /k "chcp 65001 >nul & cd /d %ROOT%\frontend & npm run dev"
goto :eof
