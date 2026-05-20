import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse


class SignatureRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        COMPLETED = "completed", "Completed"

    title = models.CharField(max_length=200)
    email_message = models.TextField(blank=True)
    batch = models.ForeignKey("SignatureBatch", on_delete=models.CASCADE, related_name="requests", blank=True, null=True)
    signer_name = models.CharField(max_length=200)
    signer_email = models.TextField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SENT)
    original_pdf = models.FileField(upload_to="originals/")
    signed_pdf = models.FileField(upload_to="completed/", blank=True)
    signature_png = models.FileField(upload_to="signatures/", blank=True)
    fields = models.JSONField(default=list)
    audit_log = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="signature_requests")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} for {self.signer_name}"

    def get_sign_url(self):
        return reverse("sign_request", kwargs={"token": self.token})

    def recipient_list(self):
        return [email.strip() for email in self.signer_email.replace(";", ",").split(",") if email.strip()]


class SignatureBatch(models.Model):
    title = models.CharField(max_length=200)
    email_message = models.TextField(blank=True)
    template = models.ForeignKey("DocumentTemplate", on_delete=models.PROTECT, related_name="signature_batches")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="signature_batches")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def total_count(self):
        return self.requests.count()

    def completed_count(self):
        return self.requests.filter(status=SignatureRequest.Status.COMPLETED).count()


class DocumentTemplate(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    pdf = models.FileField(upload_to="templates/")
    fields = models.JSONField(default=list)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="document_templates")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OutgoingEmailSettings(models.Model):
    name = models.CharField(max_length=100, default="Default")
    from_email = models.EmailField()
    smtp_host = models.CharField(max_length=200, default="smtp.gmail.com")
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_username = models.CharField(max_length=200)
    smtp_password = models.CharField(max_length=500)
    use_tls = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Outgoing email setting"
        verbose_name_plural = "Outgoing email settings"

    def __str__(self):
        return f"{self.name} <{self.from_email}>"

    @classmethod
    def active(cls):
        return cls.objects.filter(is_active=True).order_by("-updated_at").first()


class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    street = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "email"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    def full_address(self):
        parts = [self.street, self.city, self.state, self.zip_code]
        return ", ".join(part for part in parts if part)
