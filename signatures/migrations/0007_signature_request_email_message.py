# Generated for custom email messages on signature requests.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signatures", "0006_document_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="signaturerequest",
            name="email_message",
            field=models.TextField(blank=True),
        ),
    ]
