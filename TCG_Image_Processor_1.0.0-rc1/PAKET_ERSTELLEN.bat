@echo off
setlocal
cd /d "%~dp0"

if not exist "dist\TCG Image Processor" (
    echo Bitte zuerst BUILD_WINDOWS.bat ausfuehren.
    pause
    exit /b 1
)

powershell -NoProfile -Command ^
  "Compress-Archive -Path 'dist\TCG Image Processor\*' -DestinationPath 'TCG-Image-Processor-1.0.0-rc1-Portable.zip' -Force"

echo Portable ZIP wurde erstellt.
pause
