# -*- coding: utf-8 -*-
"""Server-side PDF password protection helper."""
from io import BytesIO

from pypdf import PdfReader, PdfWriter


def encrypt_pdf(pdf_bytes: bytes, password: str) -> bytes:
    """Add a user password to a PDF and return the protected bytes."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False)
    except Exception:
        raise ValueError("corrupt_pdf")
    if reader.is_encrypted:
        raise ValueError("already_encrypted")
    try:
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(user_password=password)
        out = BytesIO()
        writer.write(out)
        return out.getvalue()
    except ValueError:
        raise
    except Exception:
        raise ValueError("unsupported_pdf")
