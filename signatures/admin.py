import csv
import io
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django import forms
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path
from django.contrib import messages

from .models import Customer, DocumentTemplate, OutgoingEmailSettings, SignatureBatch, SignatureRequest


CUSTOMER_CSV_FIELDS = ("name", "email", "phone", "street", "city", "state", "zip_code", "notes")


class CustomerImportForm(forms.Form):
    csv_file = forms.FileField(label="CSV file")


def customer_csv_response(customers, filename="customers.csv"):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(CUSTOMER_CSV_FIELDS)
    for customer in customers:
        writer.writerow([getattr(customer, field) for field in CUSTOMER_CSV_FIELDS])
    return response


@admin.register(SignatureRequest)
class SignatureRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "signer_name", "signer_email", "status", "batch", "created_at", "completed_at")
    list_filter = ("status", "created_at", "completed_at")
    search_fields = ("title", "signer_name", "signer_email", "token")
    readonly_fields = ("token", "audit_log", "created_at", "completed_at")


@admin.register(SignatureBatch)
class SignatureBatchAdmin(admin.ModelAdmin):
    list_display = ("title", "template", "created_by", "created_at")
    search_fields = ("title",)


@admin.register(OutgoingEmailSettings)
class OutgoingEmailSettingsAdmin(admin.ModelAdmin):
    list_display = ("name", "from_email", "smtp_host", "smtp_port", "use_tls", "is_active", "updated_at")
    list_filter = ("is_active", "use_tls")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    change_list_template = "admin/signatures/customer/change_list.html"
    list_display = ("name", "email", "phone", "updated_at")
    search_fields = ("name", "email", "phone", "street", "city", "state", "zip_code", "notes")
    actions = ("export_selected_customers",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-csv/", self.admin_site.admin_view(self.import_csv), name="signatures_customer_import_csv"),
            path("export-csv/", self.admin_site.admin_view(self.export_csv), name="signatures_customer_export_csv"),
        ]
        return custom_urls + urls

    @admin.action(description="Export selected customers to CSV")
    def export_selected_customers(self, request, queryset):
        return customer_csv_response(queryset.order_by("name", "email"), "selected_customers.csv")

    def export_csv(self, request):
        return customer_csv_response(Customer.objects.all().order_by("name", "email"))

    def import_csv(self, request):
        if request.method == "POST":
            form = CustomerImportForm(request.POST, request.FILES)
            if form.is_valid():
                uploaded_file = form.cleaned_data["csv_file"]
                decoded_file = uploaded_file.read().decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(decoded_file))
                missing_columns = [field for field in ("name", "email") if field not in (reader.fieldnames or [])]
                if missing_columns:
                    messages.error(request, "CSV must include name and email columns.")
                    return redirect("admin:signatures_customer_import_csv")

                created_count = 0
                updated_count = 0
                skipped_rows = []
                for row_number, row in enumerate(reader, start=2):
                    cleaned = {field: (row.get(field) or "").strip() for field in CUSTOMER_CSV_FIELDS}
                    cleaned["email"] = cleaned["email"].lower()
                    if not cleaned["name"] or not cleaned["email"]:
                        skipped_rows.append(str(row_number))
                        continue

                    customer = Customer.objects.filter(email__iexact=cleaned["email"]).order_by("id").first()
                    if customer:
                        for field, value in cleaned.items():
                            setattr(customer, field, value)
                        customer.save()
                        created = False
                    else:
                        Customer.objects.create(**cleaned)
                        created = True
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                message = f"Imported customers. Created: {created_count}. Updated: {updated_count}."
                if skipped_rows:
                    message += f" Skipped rows without name/email: {', '.join(skipped_rows)}."
                messages.success(request, message)
                return redirect("admin:signatures_customer_changelist")
        else:
            form = CustomerImportForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "form": form,
            "title": "Import customers",
            "csv_fields": CUSTOMER_CSV_FIELDS,
        }
        return render(request, "admin/signatures/customer/import_csv.html", context)


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "updated_at")
    search_fields = ("name", "description")


def clear_request_media_files():
    media_root = Path(settings.MEDIA_ROOT).resolve()
    for folder_name in ("originals", "completed", "signatures"):
        folder = (media_root / folder_name).resolve()
        if not str(folder).startswith(str(media_root)) or not folder.exists():
            continue
        for file_path in folder.iterdir():
            if file_path.is_file():
                file_path.unlink()


admin.site.site_header = "Signature Portal Admin"
admin.site.site_title = "Signature Portal Admin"
admin.site.index_title = "Administration"
