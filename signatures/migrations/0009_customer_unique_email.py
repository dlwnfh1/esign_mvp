from django.db import migrations, models


def normalize_customer_emails(apps, schema_editor):
    Customer = apps.get_model("signatures", "Customer")
    for customer in Customer.objects.order_by("id"):
        normalized_email = (customer.email or "").strip().lower()
        if normalized_email and customer.email != normalized_email:
            customer.email = normalized_email
            customer.save(update_fields=["email"])


class Migration(migrations.Migration):
    dependencies = [
        ("signatures", "0008_signature_batch"),
    ]

    operations = [
        migrations.RunPython(normalize_customer_emails, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="customer",
            name="email",
            field=models.EmailField(max_length=254, unique=True),
        ),
    ]
