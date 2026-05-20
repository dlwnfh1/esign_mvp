# Generated for configurable outgoing email settings.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signatures", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="signaturerequest",
            name="signer_email",
            field=models.TextField(),
        ),
        migrations.CreateModel(
            name="OutgoingEmailSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="Default", max_length=100)),
                ("from_email", models.EmailField(max_length=254)),
                ("smtp_host", models.CharField(default="smtp.gmail.com", max_length=200)),
                ("smtp_port", models.PositiveIntegerField(default=587)),
                ("smtp_username", models.CharField(max_length=200)),
                ("smtp_password", models.CharField(max_length=500)),
                ("use_tls", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Outgoing email setting",
                "verbose_name_plural": "Outgoing email settings",
            },
        ),
    ]
