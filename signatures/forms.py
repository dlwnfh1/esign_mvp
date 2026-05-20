import re

from django import forms

from .models import Customer, DocumentTemplate, OutgoingEmailSettings, SignatureRequest


DEFAULT_EMAIL_MESSAGE = (
    "Please review the attached lease renewal agreement.\n"
    "If everything looks correct, sign the document using the link below."
)


class SignatureRequestForm(forms.ModelForm):
    template = forms.ModelChoiceField(
        queryset=DocumentTemplate.objects.all(),
        required=True,
        label="Template",
        help_text="Choose a saved template.",
    )
    recipients = forms.ModelMultipleChoiceField(
        queryset=Customer.objects.all(),
        required=True,
        label="Recipients",
        widget=forms.SelectMultiple(attrs={"size": 8, "class": "native-recipient-select"}),
        help_text="Select one or more saved customers.",
    )

    class Meta:
        model = SignatureRequest
        fields = ["title", "email_message"]
        widgets = {
            "email_message": forms.Textarea(attrs={"rows": 5}),
        }
        labels = {
            "email_message": "Email message",
        }
        help_texts = {
            "email_message": "Optional message to include in the email body.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["recipients"].queryset = Customer.objects.all()
        self.fields["template"].queryset = DocumentTemplate.objects.all()
        if not self.is_bound and not self.initial.get("email_message"):
            self.initial["email_message"] = DEFAULT_EMAIL_MESSAGE

    def clean(self):
        cleaned_data = super().clean()
        template = cleaned_data.get("template")
        if template and not template.fields:
            raise forms.ValidationError("This template has no fields yet. Add fields to the template before sending.")
        return cleaned_data


class CustomerSignatureForm(forms.Form):
    printed_name = forms.CharField(max_length=200, label="Printed name")
    signed_date = forms.DateField(
        label="Date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    initials = forms.CharField(max_length=20, label="Initials", required=False)
    consent = forms.BooleanField(label="I agree to use an electronic signature for this document.")
    signature_data = forms.CharField(widget=forms.HiddenInput)


class OutgoingEmailSettingsForm(forms.ModelForm):
    smtp_password = forms.CharField(
        label="SMTP password",
        widget=forms.PasswordInput(render_value=True),
        help_text="For Gmail, use a Google app password, not the normal Gmail password.",
    )

    class Meta:
        model = OutgoingEmailSettings
        fields = ["name", "from_email", "smtp_host", "smtp_port", "smtp_username", "smtp_password", "use_tls"]


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "email", "phone", "street", "city", "state", "zip_code", "notes"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        existing = Customer.objects.filter(email__iexact=email)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("A customer with this email already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if not phone:
            return phone
        digits = re.sub(r"\D", "", phone)
        if len(digits) != 10:
            raise forms.ValidationError("Enter a 10-digit phone number.")
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"


class DocumentTemplateForm(forms.ModelForm):
    class Meta:
        model = DocumentTemplate
        fields = ["name", "description", "pdf"]
