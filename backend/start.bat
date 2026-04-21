@echo off
cd /d D:\知枢星图\backend
F:\ANACONDA\python.exe -m uvicorn app.main:app --reload --port 8000
