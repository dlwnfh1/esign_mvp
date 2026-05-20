@echo off
cd /d "C:\Users\Jimmy-Gram\Documents\Playground\esign_mvp"

rem Replace this with your PC's Wi-Fi/LAN IPv4 address.
rem Example: set DJANGO_PUBLIC_BASE_URL=http://192.168.1.25:8000
set DJANGO_PUBLIC_BASE_URL=http://10.0.100.132:8000
set DJANGO_ALLOWED_HOSTS=*

call ".venv\Scripts\activate.bat"
python manage.py check
if errorlevel 1 (
    pause
    exit /b 1
)

python manage.py runserver 0.0.0.0:8000

cmd
