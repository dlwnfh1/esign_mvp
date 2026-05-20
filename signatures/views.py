import json
from pathlib import Path

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files import File
from django.conf import settings
from django.core.mail import EmailMessage, get_connection, send_mail
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import CustomerForm, CustomerSignatureForm, DocumentTemplateForm, OutgoingEmailSettingsForm, SignatureRequestForm
from .models import Customer, DocumentTemplate, OutgoingEmailSettings, SignatureBatch, SignatureRequest
from .pdf_utils import decode_data_url, get_pdf_page_sizes, render_pdf_page_png, render_signed_pdf


@login_required
def dashboard(request):
    query = request.GET.get("q", "").strip()
    batches = SignatureBatch.objects.select_related("template", "created_by").prefetch_related("requests")
    if query:
        matching_customers = Customer.objects.filter(
            Q(name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(street__icontains=query)
            | Q(city__icontains=query)
            | Q(state__icontains=query)
            | Q(zip_code__icontains=query)
        )
        batches = batches.filter(
            Q(title__icontains=query)
            | Q(template__name__icontains=query)
            | Q(requests__signer_name__icontains=query)
            | Q(requests__signer_email__icontains=query)
            | Q(requests__signer_email__in=matching_customers.values("email"))
        ).distinct()
    batches = batches[:50]
    legacy_requests = SignatureRequest.objects.filter(batch__isnull=True).select_related("created_by")[:20]
    return render(request, "signatures/dashboard.html", {"batches": batches, "legacy_requests": legacy_requests, "query": query})


@login_required
@require_http_methods(["GET", "POST"])
def create_request(request):
    if request.method == "POST":
        form = SignatureRequestForm(request.POST, request.FILES)
        if form.is_valid():
            recipients = list(form.cleaned_data["recipients"])
            template = form.cleaned_data.get("template")
            batch = SignatureBatch.objects.create(
                title=form.cleaned_data["title"],
                email_message=form.cleaned_data.get("email_message", ""),
                template=template,
                created_by=request.user,
            )
            created_requests = []
            for customer in recipients:
                signature_request = SignatureRequest(
                    title=form.cleaned_data["title"],
                    email_message=form.cleaned_data.get("email_message", ""),
                    batch=batch,
                    created_by=request.user,
                    signer_name=customer.name,
                    signer_email=customer.email,
                    fields=template.fields,
                    status=SignatureRequest.Status.DRAFT,
                )
                with template.pdf.open("rb") as template_file:
                    signature_request.original_pdf.save(template.pdf.name.split("/")[-1], File(template_file), save=False)
                signature_request.save()
                created_requests.append(signature_request)
            if len(created_requests) == 1:
                messages.success(request, "Request prepared. Review it before sending.")
                return redirect("batch_review", pk=batch.pk)
            request.session["bulk_batch_id"] = batch.pk
            messages.success(request, f"{len(created_requests)} requests prepared. Review them before sending.")
            return redirect("batch_review", pk=batch.pk)
    else:
        form = SignatureRequestForm()
    return render(request, "signatures/create_request.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def request_review(request, pk):
    signature_request = get_object_or_404(SignatureRequest, pk=pk)
    if request.method == "POST":
        signature_request.status = SignatureRequest.Status.SENT
        signature_request.save(update_fields=["status"])
        email_sent, email_error = send_signature_email(request, signature_request)
        if email_sent:
            messages.success(request, "Signature request email sent.")
        elif not OutgoingEmailSettings.active() and settings.EMAIL_BACKEND.endswith("console.EmailBackend"):
            messages.warning(request, "Email is in console-only mode, so use the signing link from this page.")
        else:
            messages.warning(request, f"Email delivery failed: {email_error or 'Unknown error'}. Use the signing link from this page.")
        return redirect("request_detail", pk=signature_request.pk)

    sign_url = build_public_url(request, signature_request.get_sign_url())
    return render(request, "signatures/request_review.html", {"signature_request": signature_request, "sign_url": sign_url})


@login_required
@require_http_methods(["GET", "POST"])
def batch_review(request, pk):
    batch = get_object_or_404(SignatureBatch.objects.prefetch_related("requests"), pk=pk)
    signature_requests = list(batch.requests.all().order_by("signer_name", "signer_email"))
    if not signature_requests:
        messages.warning(request, "No requests were found in this batch.")
        return redirect("dashboard")

    if request.method == "POST":
        sent = 0
        errors = []
        for signature_request in signature_requests:
            if signature_request.status == SignatureRequest.Status.COMPLETED:
                continue
            signature_request.status = SignatureRequest.Status.SENT
            signature_request.save(update_fields=["status"])
            email_sent, email_error = send_signature_email(request, signature_request)
            if email_sent:
                sent += 1
            else:
                errors.append(f"{signature_request.signer_email}: {email_error or 'Unknown error'}")
        request.session.pop("bulk_batch_id", None)
        if errors:
            messages.warning(request, f"{sent} emails sent. Some failed: {'; '.join(errors)}")
        else:
            messages.success(request, f"{sent} signature request emails sent.")
        return redirect("batch_detail", pk=batch.pk)

    rows = [
        {
            "request": item,
            "sign_url": build_public_url(request, item.get_sign_url()),
        }
        for item in signature_requests
    ]
    return render(request, "signatures/batch_review.html", {"batch": batch, "rows": rows})


@login_required
def batch_detail(request, pk):
    batch = get_object_or_404(SignatureBatch.objects.select_related("template"), pk=pk)
    query = request.GET.get("q", "").strip()
    requests = batch.requests.all().order_by("signer_name", "signer_email")
    all_requests = requests
    if query:
        matching_customers = Customer.objects.filter(
            Q(name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(street__icontains=query)
            | Q(city__icontains=query)
            | Q(state__icontains=query)
            | Q(zip_code__icontains=query)
        )
        requests = requests.filter(
            Q(signer_name__icontains=query)
            | Q(signer_email__icontains=query)
            | Q(signer_email__in=matching_customers.values("email"))
        )
    completed = all_requests.filter(status=SignatureRequest.Status.COMPLETED).count()
    total = all_requests.count()
    return render(
        request,
        "signatures/batch_detail.html",
        {
            "batch": batch,
            "requests": requests,
            "completed": completed,
            "total": total,
            "query": query,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def resend_request_email(request, pk):
    signature_request = get_object_or_404(SignatureRequest.objects.select_related("batch"), pk=pk)
    if signature_request.status == SignatureRequest.Status.COMPLETED:
        messages.warning(request, "This request is already completed, so the email was not resent.")
        if signature_request.batch_id:
            return redirect("batch_detail", pk=signature_request.batch_id)
        return redirect("request_detail", pk=signature_request.pk)
    if request.method == "POST":
        signature_request.status = SignatureRequest.Status.SENT
        signature_request.save(update_fields=["status"])
        email_sent, email_error = send_signature_email(request, signature_request)
        if email_sent:
            messages.success(request, f"Email resent to {signature_request.signer_email}.")
        else:
            messages.warning(request, f"Email resend failed for {signature_request.signer_email}: {email_error or 'Unknown error'}")
        if signature_request.batch_id:
            return redirect("batch_detail", pk=signature_request.batch_id)
        return redirect("request_detail", pk=signature_request.pk)
    return render(request, "signatures/resend_confirm.html", {"signature_request": signature_request})


@login_required
def template_list(request):
    templates = DocumentTemplate.objects.select_related("created_by")
    return render(request, "signatures/template_list.html", {"templates": templates})


@login_required
@require_http_methods(["GET", "POST"])
def template_create(request):
    if request.method == "POST":
        form = DocumentTemplateForm(request.POST, request.FILES)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.fields = []
            template.save()
            messages.success(request, "Template uploaded. Place the fields and save it.")
            return redirect("template_field_designer", pk=template.pk)
    else:
        form = DocumentTemplateForm()
    return render(request, "signatures/template_form.html", {"form": form, "title": "New Template"})


@login_required
@require_http_methods(["GET", "POST"])
def template_update(request, pk):
    template = get_object_or_404(DocumentTemplate, pk=pk)
    if request.method == "POST":
        form = DocumentTemplateForm(request.POST, request.FILES, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, "Template updated.")
            return redirect("template_field_designer", pk=template.pk)
    else:
        form = DocumentTemplateForm(instance=template)
    return render(request, "signatures/template_form.html", {"form": form, "title": "Edit Template"})


@login_required
@require_http_methods(["POST"])
def template_delete(request, pk):
    template = get_object_or_404(DocumentTemplate, pk=pk)
    template.delete()
    messages.success(request, "Template deleted.")
    return redirect("template_list")


@login_required
@require_http_methods(["GET", "POST"])
def template_field_designer(request, pk):
    template = get_object_or_404(DocumentTemplate, pk=pk)
    page_sizes = get_pdf_page_sizes(template.pdf.open("rb"))

    if request.method == "POST":
        fields, error = parse_designer_fields(request.POST.get("fields_json", ""), page_sizes)
        if error:
            messages.error(request, error)
        else:
            template.fields = fields
            template.save(update_fields=["fields", "updated_at"])
            messages.success(request, "Template fields saved.")
            return redirect("template_list")

    return render(
        request,
        "signatures/field_designer.html",
        {
            "designer_title": template.name,
            "designer_subtitle": "Place reusable fields for this template.",
            "page_sizes": page_sizes,
            "saved_fields": template.fields,
            "page_image_base_url": reverse("template_page_image", kwargs={"pk": template.pk, "page": 1}).replace("/1.png", "/"),
            "submit_label": "Save template fields",
        },
    )


@login_required
def template_page_image(request, pk, page):
    template = get_object_or_404(DocumentTemplate, pk=pk)
    try:
        png_bytes = render_pdf_page_png(template.pdf.path, page)
    except Exception as exc:
        return HttpResponse(f"Could not render PDF page: {exc}", status=500)
    return HttpResponse(png_bytes, content_type="image/png")


@login_required
def customer_list(request):
    query = request.GET.get("q", "").strip()
    customers = Customer.objects.all()
    if query:
        customers = (
            customers.filter(name__icontains=query)
            | Customer.objects.filter(email__icontains=query)
            | Customer.objects.filter(phone__icontains=query)
            | Customer.objects.filter(city__icontains=query)
        )
    return render(request, "signatures/customer_list.html", {"customers": customers, "query": query})


@login_required
@require_http_methods(["GET", "POST"])
def customer_create(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer saved.")
            return redirect("customer_list")
    else:
        form = CustomerForm()
    return render(request, "signatures/customer_form.html", {"form": form, "title": "New Customer"})


@login_required
@require_http_methods(["GET", "POST"])
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer updated.")
            return redirect("customer_list")
    else:
        form = CustomerForm(instance=customer)
    return render(request, "signatures/customer_form.html", {"form": form, "title": "Edit Customer"})


@login_required
@require_http_methods(["POST"])
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.delete()
    messages.success(request, "Customer deleted.")
    return redirect("customer_list")


@login_required
@require_http_methods(["GET", "POST"])
def field_designer(request, pk):
    signature_request = get_object_or_404(SignatureRequest, pk=pk)
    page_sizes = get_pdf_page_sizes(signature_request.original_pdf.open("rb"))

    if request.method == "POST":
        fields, error = parse_designer_fields(request.POST.get("fields_json", ""), page_sizes)
        if error:
            messages.error(request, error)
        else:
            signature_request.fields = fields
            signature_request.save(update_fields=["fields"])
            messages.success(request, "Fields saved. Review the request before sending.")
            return redirect("request_review", pk=signature_request.pk)

    return render(
        request,
        "signatures/field_designer.html",
        {
            "designer_title": signature_request.title,
            "designer_subtitle": "Place the fields where the signer should complete the document.",
            "signature_request": signature_request,
            "page_sizes": page_sizes,
            "saved_fields": signature_request.fields,
            "page_image_base_url": reverse("pdf_page_image", kwargs={"pk": signature_request.pk, "page": 1}).replace("/1.png", "/"),
            "submit_label": "Save fields and review",
        },
    )


@login_required
def pdf_page_image(request, pk, page):
    signature_request = get_object_or_404(SignatureRequest, pk=pk)
    try:
        png_bytes = render_pdf_page_png(signature_request.original_pdf.path, page)
    except Exception as exc:
        return HttpResponse(f"Could not render PDF page: {exc}", status=500)
    return HttpResponse(png_bytes, content_type="image/png")


@login_required
@require_http_methods(["GET", "POST"])
def email_settings(request):
    email_config = OutgoingEmailSettings.active() or OutgoingEmailSettings()
    if request.method == "POST":
        form = OutgoingEmailSettingsForm(request.POST, instance=email_config)
        if form.is_valid():
            OutgoingEmailSettings.objects.exclude(pk=email_config.pk).update(is_active=False)
            saved = form.save(commit=False)
            saved.is_active = True
            saved.save()
            messages.success(request, "Email settings saved.")
            return redirect("dashboard")
    else:
        form = OutgoingEmailSettingsForm(instance=email_config)
    return render(request, "signatures/email_settings.html", {"form": form, "email_config": email_config})


@login_required
@require_http_methods(["GET", "POST"])
def clear_test_requests(request):
    counts = {
        "batches": SignatureBatch.objects.count(),
        "requests": SignatureRequest.objects.count(),
    }
    if request.method == "POST":
        SignatureBatch.objects.all().delete()
        SignatureRequest.objects.filter(batch__isnull=True).delete()
        clear_request_media_files()
        messages.success(request, "Test request data deleted. Customers, templates, and email settings were kept.")
        return redirect("dashboard")
    return render(request, "signatures/clear_test_requests.html", {"counts": counts})


@staff_member_required
@require_http_methods(["GET", "POST"])
def admin_clear_test_data(request):
    counts = {
        "batches": SignatureBatch.objects.count(),
        "requests": SignatureRequest.objects.count(),
    }
    if request.method == "POST":
        SignatureBatch.objects.all().delete()
        SignatureRequest.objects.filter(batch__isnull=True).delete()
        clear_request_media_files()
        messages.success(request, "Test request data deleted. Customers, templates, email settings, and users were kept.")
        return redirect("admin:index")
    return render(request, "admin/clear_test_data.html", {"counts": counts})


@login_required
def request_detail(request, pk):
    signature_request = get_object_or_404(SignatureRequest, pk=pk)
    sign_url = build_public_url(request, signature_request.get_sign_url())
    return render(request, "signatures/request_detail.html", {"signature_request": signature_request, "sign_url": sign_url})


@login_required
def download_signed_pdf(request, pk):
    signature_request = get_object_or_404(SignatureRequest, pk=pk)
    if not signature_request.signed_pdf:
        raise Http404("Signed PDF is not available yet.")
    return FileResponse(signature_request.signed_pdf.open("rb"), as_attachment=True, filename=f"signed-{signature_request.pk}.pdf")


@login_required
def open_signed_pdf(request, pk):
    signature_request = get_object_or_404(SignatureRequest, pk=pk)
    if not signature_request.signed_pdf:
        raise Http404("Signed PDF is not available yet.")
    response = FileResponse(signature_request.signed_pdf.open("rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="signed-{signature_request.pk}.pdf"'
    return response


def parse_designer_fields(raw_fields, page_sizes):
    try:
        fields = json.loads(raw_fields)
    except json.JSONDecodeError as exc:
        return [], f"Field data is invalid JSON: {exc}"
    if not isinstance(fields, list) or not fields:
        return [], "Place at least one field before sending."

    cleaned = []
    for index, field in enumerate(fields, start=1):
        if not isinstance(field, dict):
            return [], f"Field {index} is invalid."
        field_type = field.get("type")
        if field_type not in {"signature", "name", "date"}:
            return [], f"Field {index} has an unsupported type."
        try:
            page = int(field.get("page"))
            x = float(field.get("x"))
            y = float(field.get("y"))
            w = float(field.get("w"))
            h = float(field.get("h"))
        except (TypeError, ValueError):
            return [], f"Field {index} has invalid coordinates."
        if page < 1 or page > len(page_sizes):
            return [], f"Field {index} has an invalid page number."
        page_width = page_sizes[page - 1]["width"]
        page_height = page_sizes[page - 1]["height"]
        if w < 12 or h < 12:
            return [], f"Field {index} is too small."
        if x < 0 or y < 0 or x + w > page_width or y + h > page_height:
            return [], f"Field {index} is outside the PDF page."
        cleaned.append(
            {
                "type": field_type,
                "page": page,
                "x": round(x, 2),
                "y": round(y, 2),
                "w": round(w, 2),
                "h": round(h, 2),
                "label": field.get("label") or field_type.title(),
            }
        )
    return cleaned, ""


def preview_original_pdf(request, token):
    signature_request = get_object_or_404(SignatureRequest, token=token)
    response = FileResponse(signature_request.original_pdf.open("rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="document-{signature_request.pk}.pdf"'
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response


@require_http_methods(["GET", "POST"])
def sign_request(request, token):
    signature_request = get_object_or_404(SignatureRequest, token=token)
    if signature_request.status == SignatureRequest.Status.COMPLETED:
        return render(request, "signatures/already_completed.html", {"signature_request": signature_request})

    if request.method == "POST":
        form = CustomerSignatureForm(request.POST)
        if form.is_valid():
            try:
                signature_png = decode_data_url(form.cleaned_data["signature_data"])
                signed_pdf = render_signed_pdf(
                    signature_request.original_pdf.open("rb"),
                    signature_png,
                    signature_request.fields,
                    form.cleaned_data["printed_name"],
                    form.cleaned_data["signed_date"],
                )
            except Exception:
                form.add_error(None, "We could not apply the signature to this PDF. Please contact the sender.")
                return render(
                    request,
                    "signatures/sign_request.html",
                    {
                        "form": form,
                        "signature_request": signature_request,
                        "document_url": reverse("preview_original_pdf", kwargs={"token": signature_request.token}),
                    },
                )
            timestamp = timezone.now()
            signature_request.signature_png.save(f"signature-{signature_request.pk}.png", ContentFile(signature_png), save=False)
            signature_request.signed_pdf.save(f"signed-{signature_request.pk}.pdf", ContentFile(signed_pdf.read()), save=False)
            signature_request.status = SignatureRequest.Status.COMPLETED
            signature_request.completed_at = timestamp
            signature_request.audit_log = {
                "signed_at": timestamp.isoformat(),
                "signer_name": form.cleaned_data["printed_name"],
                "signer_email": signature_request.signer_email,
                "signed_date": form.cleaned_data["signed_date"].isoformat(),
                "ip_address": get_client_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                "consent_text": "I agree to use an electronic signature for this document.",
            }
            signature_request.save()
            return render(request, "signatures/sign_complete.html", {"signature_request": signature_request})
    else:
        form = CustomerSignatureForm(initial={"printed_name": signature_request.signer_name, "signed_date": timezone.localdate()})
    return render(
        request,
        "signatures/sign_request.html",
        {
            "form": form,
            "signature_request": signature_request,
            "document_url": reverse("preview_original_pdf", kwargs={"token": signature_request.token}),
        },
    )


def send_signature_email(request, signature_request):
    recipients = signature_request.recipient_list()
    if not recipients:
        return False, "No recipient email address"

    sign_url = build_public_url(request, signature_request.get_sign_url())
    subject = f"Please sign: {signature_request.title}"
    custom_message = signature_request.email_message.strip()
    message_block = f"{custom_message}\n\n" if custom_message else ""
    body = f"Hello {signature_request.signer_name},\n\n{message_block}Please review and sign this document:\n{sign_url}\n\nThank you."
    email_config = OutgoingEmailSettings.active()
    if email_config:
        try:
            connection = get_connection(
                backend="django.core.mail.backends.smtp.EmailBackend",
                host=email_config.smtp_host,
                port=email_config.smtp_port,
                username=email_config.smtp_username,
                password=email_config.smtp_password,
                use_tls=email_config.use_tls,
                timeout=20,
                fail_silently=False,
            )
            sent_count = 0
            for recipient in recipients:
                message = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=email_config.from_email,
                    to=[recipient],
                    connection=connection,
                )
                sent_count += message.send(fail_silently=False)
            if sent_count == len(recipients):
                return True, ""
            return False, f"Only {sent_count} of {len(recipients)} emails were sent"
        except Exception as exc:
            return False, str(exc)
    try:
        sent_count = send_mail(subject, body, None, recipients, fail_silently=False)
    except Exception as exc:
        return False, str(exc)
    return sent_count == 1, "" if sent_count == 1 else f"Backend returned sent count {sent_count}"


def build_public_url(request, path):
    if settings.PUBLIC_BASE_URL:
        return f"{settings.PUBLIC_BASE_URL}{path}"
    return request.build_absolute_uri(path)


def clear_request_media_files():
    media_root = Path(settings.MEDIA_ROOT).resolve()
    for folder_name in ("originals", "completed", "signatures"):
        folder = (media_root / folder_name).resolve()
        if not str(folder).startswith(str(media_root)) or not folder.exists():
            continue
        for file_path in folder.iterdir():
            if file_path.is_file():
                file_path.unlink()


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
