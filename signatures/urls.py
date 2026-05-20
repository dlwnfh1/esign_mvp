from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("settings/email/", views.email_settings, name="email_settings"),
    path("settings/clear-test-requests/", views.clear_test_requests, name="clear_test_requests"),
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/new/", views.customer_create, name="customer_create"),
    path("customers/<int:pk>/edit/", views.customer_update, name="customer_update"),
    path("customers/<int:pk>/delete/", views.customer_delete, name="customer_delete"),
    path("templates/", views.template_list, name="template_list"),
    path("templates/new/", views.template_create, name="template_create"),
    path("templates/<int:pk>/edit/", views.template_update, name="template_update"),
    path("templates/<int:pk>/delete/", views.template_delete, name="template_delete"),
    path("templates/<int:pk>/fields/", views.template_field_designer, name="template_field_designer"),
    path("templates/<int:pk>/pages/<int:page>.png", views.template_page_image, name="template_page_image"),
    path("requests/new/", views.create_request, name="create_request"),
    path("batches/<int:pk>/review/", views.batch_review, name="batch_review"),
    path("batches/<int:pk>/", views.batch_detail, name="batch_detail"),
    path("requests/<int:pk>/review/", views.request_review, name="request_review"),
    path("requests/<int:pk>/resend/", views.resend_request_email, name="resend_request_email"),
    path("requests/<int:pk>/fields/", views.field_designer, name="field_designer"),
    path("requests/<int:pk>/pages/<int:page>.png", views.pdf_page_image, name="pdf_page_image"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("requests/<int:pk>/open-pdf/", views.open_signed_pdf, name="open_signed_pdf"),
    path("requests/<int:pk>/download/", views.download_signed_pdf, name="download_signed_pdf"),
    path("sign/<uuid:token>/document/", views.preview_original_pdf, name="preview_original_pdf"),
    path("sign/<uuid:token>/", views.sign_request, name="sign_request"),
]
