import os
import sys

# Replace YOUR_USERNAME with your PythonAnywhere username.
project_home = "/home/YOUR_USERNAME/esign_mvp"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esign_mvp.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
