@echo off
setlocal
cd /d "%~dp0"
py -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --icon assets\datasus-downloader.ico ^
  --add-data "assets\datasus-downloader.png;assets" ^
  --add-data "assets\datasus-downloader.ico;assets" ^
  --name DATASUS-Downloader baixar_arquivos_datasus.py
if errorlevel 1 exit /b %errorlevel%
echo Executavel criado em dist\DATASUS-Downloader.exe
