@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo TCG Image Processor 1.0.0-rc1 Build
echo ==========================================
echo.

python -m pip install --upgrade pip
if errorlevel 1 goto :error

python -m pip install -r requirements-build.txt
if errorlevel 1 goto :error

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

python -m PyInstaller --noconfirm TCGImageProcessor.spec
if errorlevel 1 goto :error

echo.
echo Build erfolgreich.
echo Portable Programm:
echo %CD%\dist\TCG Image Processor
echo.
pause
exit /b 0

:error
echo.
echo Der Build ist fehlgeschlagen.
pause
exit /b 1
