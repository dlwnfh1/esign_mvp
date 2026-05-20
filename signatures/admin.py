from pathlib import Path

from django.conf import settings
from django.contrib import admin

from .models import Customer, DocumentTemplate, OutgoingEmailSettings, SignatureBatch, SignatureRequest


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
    list_display = ("name", "email", "phone", "updated_at")
    search_fields = ("name", "email", "phone", "street", "city", "state", "zip_code", "notes")


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
