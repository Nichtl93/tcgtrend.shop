@echo off
setlocal
cd /d "%~dp0"

if not exist "dist\TCG Image Processor\TCG Image Processor.exe" (
    echo Bitte zuerst BUILD_WINDOWS.bat ausfuehren.
    pause
    exit /b 1
)

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo Inno Setup 6 wurde nicht gefunden.
    echo Bitte Inno Setup installieren und danach erneut starten.
    pause
    exit /b 1
)

"%ISCC%" "installer\setup.iss"
if errorlevel 1 (
    echo Installer-Build fehlgeschlagen.
    pause
    exit /b 1
)

echo Installer wurde unter installer\output erstellt.
pause
