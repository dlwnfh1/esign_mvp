@echo off
cd /d "C:\Users\Jimmy-Gram\Documents\Playground\esign_mvp"

echo Creating virtual environment with Python 3.11...
py -3.11 -m venv .venv
if errorlevel 1 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    pause
    exit /b 1
)

echo Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements.
    pause
    exit /b 1
)

echo Running migrations...
python manage.py migrate
if errorlevel 1 (
    echo Migration failed.
    pause
    exit /b 1
)

echo.
echo Setup complete.
echo If you have not created an admin user yet, run:
echo python manage.py createsuperuser
echo.
cmd
