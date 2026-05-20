# Generated for the Signature Portal MVP.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SignatureRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("signer_name", models.CharField(max_length=200)),
                ("signer_email", models.TextField()),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Draft"), ("sent", "Sent"), ("completed", "Completed")],
                        default="sent",
                        max_length=20,
                    ),
                ),
                ("original_pdf", models.FileField(upload_to="originals/")),
                ("signed_pdf", models.FileField(blank=True, upload_to="completed/")),
                ("signature_png", models.FileField(blank=True, upload_to="signatures/")),
                ("fields", models.JSONField(default=list)),
                ("audit_log", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="signature_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
