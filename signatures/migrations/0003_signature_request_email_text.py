# Generated for multiple recipient email support.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signatures", "0002_outgoing_email_settings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="signaturerequest",
            name="signer_email",
            field=models.TextField(),
        ),
    ]
