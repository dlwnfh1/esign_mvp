import base64
from pathlib import Path
from io import BytesIO

from django.utils import timezone
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import black
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

TEXT_FONT_NAME = None


def decode_data_url(data_url):
    if "," not in data_url:
        raise ValueError("Signature data is missing a data URL header.")
    header, encoded = data_url.split(",", 1)
    if "image/png" not in header:
        raise ValueError("Signature must be a PNG image.")
    return base64.b64decode(encoded)


def get_pdf_page_sizes(original_file):
    original_file.seek(0)
    reader = PdfReader(original_file)
    sizes = []
    for page in reader.pages:
        sizes.append(
            {
                "width": float(page.mediabox.width),
                "height": float(page.mediabox.height),
            }
        )
    return sizes


def render_pdf_page_png(pdf_path, page_number, zoom=1.6):
    import fitz

    document = fitz.open(pdf_path)
    try:
        page = document.load_page(page_number - 1)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return pixmap.tobytes("png")
    finally:
        document.close()


def get_text_font_name():
    global TEXT_FONT_NAME
    if TEXT_FONT_NAME:
        return TEXT_FONT_NAME

    font_candidates = [
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/malgunbd.ttf"),
        Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    ]
    for font_path in font_candidates:
        if font_path.exists():
            pdfmetrics.registerFont(TTFont("SignatureTextFont", str(font_path)))
            TEXT_FONT_NAME = "SignatureTextFont"
            return TEXT_FONT_NAME

    TEXT_FONT_NAME = "Helvetica"
    return TEXT_FONT_NAME


def render_signed_pdf(original_file, signature_png_bytes, fields, signer_name, signed_date=None, initials=""):
    original_file.seek(0)
    reader = PdfReader(original_file)
    writer = PdfWriter()
    today = (signed_date or timezone.localdate()).strftime("%m/%d/%Y")

    fields_by_page = {}
    for field in fields:
        fields_by_page.setdefault(int(field["page"]) - 1, []).append(field)

    for page_index, page in enumerate(reader.pages):
        page_fields = fields_by_page.get(page_index, [])
        if page_fields:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            overlay_buffer = BytesIO()
            overlay = canvas.Canvas(overlay_buffer, pagesize=(width, height))
            overlay.setFillColor(black)

            for field in page_fields:
                x = float(field["x"])
                y = float(field["y"])
                w = float(field["w"])
                h = float(field["h"])
                field_type = field["type"]
                if field_type == "signature":
                    overlay.drawImage(ImageReader(BytesIO(signature_png_bytes)), x, y, width=w, height=h, mask="auto")
                elif field_type == "date":
                    overlay.setFont(get_text_font_name(), min(14, max(8, h * 0.65)))
                    overlay.drawString(x, y + max(2, h * 0.2), today)
                elif field_type == "name":
                    overlay.setFont(get_text_font_name(), min(14, max(8, h * 0.65)))
                    overlay.drawString(x, y + max(2, h * 0.2), signer_name)
                elif field_type == "initial":
                    overlay.setFont(get_text_font_name(), min(14, max(8, h * 0.65)))
                    overlay.drawString(x, y + max(2, h * 0.2), initials)

            overlay.save()
            overlay_buffer.seek(0)
            overlay_page = PdfReader(overlay_buffer).pages[0]
            page.merge_page(overlay_page)
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output
