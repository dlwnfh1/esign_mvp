@echo off
cd /d "C:\Users\Jimmy-Gram\Documents\Playground\esign_mvp"

set DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
set DJANGO_EMAIL_HOST=smtp.gmail.com
set DJANGO_EMAIL_PORT=587
set DJANGO_EMAIL_USE_TLS=1
set DJANGO_EMAIL_HOST_USER=yourgmail@gmail.com
set DJANGO_EMAIL_HOST_PASSWORD=your-google-app-password
set DJANGO_DEFAULT_FROM_EMAIL=yourgmail@gmail.com

call ".venv\Scripts\activate.bat"
python manage.py check
if errorlevel 1 (
    pause
    exit /b 1
)

python manage.py runserver 0.0.0.0:8000

cmd
