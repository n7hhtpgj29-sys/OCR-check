@echo off
cd /d "%~dp0"
set "STREAMLIT_GLOBAL_DEVELOPMENT_MODE=false"
set "STREAMLIT_SERVER_PORT=8501"
start "" "http://127.0.0.1:8501"
"%~dp0CustomsOCR.exe"
if errorlevel 1 pause
