# Signature Portal MVP

A small Django web app for a company-managed electronic signature workflow.

## What this first version does

- Staff login through Django auth.
- Customer management for saved names, emails, phone numbers, structured addresses, and notes.
- Configurable sender email account from the web screen.
- Upload a PDF and create a customer signing link.
- Place signature/name/date fields visually on the uploaded PDF.
- Save reusable document templates with PDF field positions.
- Send the signing link to one or more recipients.
- Customer signs once in the browser.
- The same signature can be stamped into multiple PDF positions.
- Name/date fields can be stamped automatically.
- Completed PDF, signature PNG, and basic audit log are stored.

This is a practical MVP, not a DocuSign-equivalent legal/compliance platform.

## Local setup

```powershell
cd C:\Users\Jimmy-Gram\Documents\Playground\esign_mvp
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

If you already created the database before email settings were added, run:

```powershell
python manage.py migrate
```

## PDF field coordinates

When creating a request, the `Signature fields JSON` box controls where values are placed.
Coordinates are PDF points from the bottom-left corner. Pages start at 1.

Example:

```json
[
  {"type": "signature", "page": 1, "x": 72, "y": 144, "w": 180, "h": 48, "label": "Customer signature"},
  {"type": "date", "page": 1, "x": 300, "y": 144, "w": 120, "h": 24, "label": "Date"},
  {"type": "name", "page": 1, "x": 72, "y": 110, "w": 180, "h": 24, "label": "Printed name"}
]
```

## PythonAnywhere notes

Use a paid account for a real company workflow so the app can use a custom domain, proper outbound email/API access, and enough file storage.

Basic deployment shape:

1. Upload this folder to PythonAnywhere.
2. Create a virtualenv and install `requirements.txt`.
3. Set environment variables:
   - `DJANGO_SECRET_KEY`
   - `DJANGO_DEBUG=0`
   - `DJANGO_ALLOWED_HOSTS=yourdomain.com,yourusername.pythonanywhere.com`
4. Run migrations and create a staff user.
5. Configure static files with `python manage.py collectstatic`.
6. Configure email through a provider such as SendGrid or Mailgun for production.

### PythonAnywhere quick deployment

In a PythonAnywhere Bash console:

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git ~/esign_mvp
cd ~/esign_mvp
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
```

On the PythonAnywhere Web tab:

- Add a new manual web app.
- Use the same Python version as the virtualenv.
- Set virtualenv path to `/home/YOUR_USERNAME/esign_mvp/.venv`.
- Edit the WSGI file and use `pythonanywhere_wsgi.py` as the guide.
- Add static files mappings:
  - URL: `/static/` -> Directory: `/home/YOUR_USERNAME/esign_mvp/staticfiles`
  - URL: `/media/` -> Directory: `/home/YOUR_USERNAME/esign_mvp/media`
- Reload the web app.

Suggested environment variables:

```bash
export DJANGO_DEBUG=0
export DJANGO_ALLOWED_HOSTS=YOUR_USERNAME.pythonanywhere.com
export DJANGO_PUBLIC_BASE_URL=https://YOUR_USERNAME.pythonanywhere.com
export DJANGO_SECRET_KEY="replace-with-a-long-random-secret"
```

On PythonAnywhere, environment variables for web apps should be set in the WSGI file or through a helper file that is not committed to Git.

Free PythonAnywhere accounts have outbound internet restrictions. Gmail SMTP is the practical email option for free accounts; use a Google app password.

## Email setup

By default, local development uses Django's console email backend. That means emails appear in the server terminal, not in the real inbox.

For real email delivery, set SMTP environment variables before running the server.

Example for Gmail with an app password:

```powershell
$env:DJANGO_EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"
$env:DJANGO_EMAIL_HOST="smtp.gmail.com"
$env:DJANGO_EMAIL_PORT="587"
$env:DJANGO_EMAIL_USE_TLS="1"
$env:DJANGO_EMAIL_HOST_USER="yourgmail@gmail.com"
$env:DJANGO_EMAIL_HOST_PASSWORD="your-gmail-app-password"
$env:DJANGO_DEFAULT_FROM_EMAIL="yourgmail@gmail.com"
python manage.py runserver 0.0.0.0:8000
```

Gmail requires a Google app password, not the normal Gmail password.

## Next practical upgrades

- Visual PDF field placement instead of JSON coordinates.
- Email delivery status tracking.
- Link expiration and resend controls.
- Separate audit certificate PDF.
- PostgreSQL for production.
- S3/private object storage for larger document volume.
