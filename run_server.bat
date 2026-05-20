@echo off
cd /d "C:\Users\Jimmy-Gram\Documents\Playground\esign_mvp"

set DJANGO_ALLOWED_HOSTS=*

if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found.
    echo Run setup_env.bat first.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

python --version
python manage.py check
if errorlevel 1 (
    echo.
    echo Django check failed. If Python path errors appear, delete/recreate .venv by running setup_env.bat.
    pause
    exit /b 1
)

python manage.py runserver 0.0.0.0:8000

cmd
