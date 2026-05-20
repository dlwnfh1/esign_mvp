# Generated for structured customer address fields.

from django.db import migrations, models


def split_existing_address(apps, schema_editor):
    Customer = apps.get_model("signatures", "Customer")
    for customer in Customer.objects.all():
        address = getattr(customer, "address", "") or ""
        if address and not customer.street:
            customer.street = address
            customer.save(update_fields=["street"])


class Migration(migrations.Migration):
    dependencies = [
        ("signatures", "0004_customer"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="street",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="customer",
            name="city",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="customer",
            name="state",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="customer",
            name="zip_code",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.RunPython(split_existing_address, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="customer",
            name="address",
        ),
    ]
