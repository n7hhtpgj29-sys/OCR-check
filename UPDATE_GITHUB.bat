@echo off
setlocal
cd /d "%~dp0"
where git >nul 2>&1
if errorlevel 1 (
 echo Git for Windows not found. Please install Git for Windows on this upload PC or upload via GitHub web.
 pause
 exit /b 1
)
set "WORK=%TEMP%\CustomsOCR_git_update"
if exist "%WORK%" rmdir /s /q "%WORK%"
git clone https://github.com/n7hhtpgj29-sys/OCR-check.git "%WORK%"
if errorlevel 1 (echo Clone failed - check GitHub sign-in and access rights.&pause&exit /b 1)
copy /y app.py "%WORK%\app.py" >nul
copy /y launcher.py "%WORK%\launcher.py" >nul
copy /y requirements-build.txt "%WORK%\requirements-build.txt" >nul
copy /y Customs_Import_OCR_Template.xlsx "%WORK%\Customs_Import_OCR_Template.xlsx" >nul
copy /y sample.pdf "%WORK%\sample.pdf" >nul
if not exist "%WORK%\.github\workflows" mkdir "%WORK%\.github\workflows"
copy /y .github\workflows\main.yml "%WORK%\.github\workflows\main.yml" >nul
cd /d "%WORK%"
git add -A
git commit -m "Update complete Customs OCR v1.2 package"
if errorlevel 1 (echo Nothing changed or commit failed. Check git user.name and user.email.&pause&exit /b 1)
git push origin main
if errorlevel 1 (echo Push failed. Check access or branch protection.&pause&exit /b 1)
echo SUCCESS: GitHub source updated. Go to Actions and Run workflow.
pause
