@echo off
echo =========================================
echo   SSK Zvezda KPI Monitor v5 — Build EXE
echo =========================================
echo.

pip install pyinstaller --quiet

echo [1/2] Сборка основного приложения...
pyinstaller --onefile --windowed ^
  --name "SSK_Zvezda_KPI" ^
  --icon "assets\izolde.ico" ^
  --add-data "assets;assets" ^
  --add-data "modules;modules" ^
  --hidden-import customtkinter ^
  --hidden-import bcrypt ^
  --hidden-import cryptography ^
  --hidden-import cryptography.fernet ^
  --hidden-import pystray ^
  --hidden-import pystray._win32 ^
  --hidden-import PIL ^
  --hidden-import PIL._imagingtk ^
  --hidden-import PIL.ImageTk ^
  --hidden-import PIL.Image ^
  --hidden-import PIL.ImageDraw ^
  --hidden-import docx ^
  --hidden-import docx.oxml ^
  --hidden-import docx.oxml.ns ^
  --hidden-import matplotlib ^
  --hidden-import matplotlib.backends.backend_agg ^
  --hidden-import requests ^
  --collect-all customtkinter ^
  --collect-all pystray ^
  The_Storm.py

echo.
echo [2/2] Сборка установщика...
pyinstaller --onefile --windowed ^
  --name "SSK_Zvezda_Setup" ^
  --icon "assets\izolde.ico" ^
  --add-data "dist\SSK_Zvezda_KPI.exe;." ^
  --add-data "assets;assets" ^
  --add-data "modules;modules" ^
  SSK_Zvezda_Setup.py

echo.
echo =========================================
echo  ГОТОВО!
echo  Дистрибутив: dist\SSK_Zvezda_Setup.exe
echo  (запускать этот файл для установки)
echo =========================================
pause
