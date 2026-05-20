# Generated for customer management.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signatures", "0003_signature_request_email_text"),
    ]

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("email", models.EmailField(max_length=254)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("address", models.TextField(blank=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name", "email"],
            },
        ),
    ]
