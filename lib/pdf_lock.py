# -*- coding: utf-8 -*-
"""Server-side PDF password protection helper."""
from io import BytesIO
from typing import Optional

from pypdf import PdfReader, PdfWriter


def encrypt_pdf(
    pdf_bytes: bytes,
    password: str,
    *,
    max_pages: Optional[int] = None,
    max_output_bytes: Optional[int] = None,
) -> bytes:
    """Add a user password to a PDF and return the protected bytes."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False)
    except Exception:
        raise ValueError("corrupt_pdf")
    if reader.is_encrypted:
        raise ValueError("already_encrypted")
    try:
        if max_pages is not None and len(reader.pages) > max_pages:
            raise ValueError("too_many_pages")
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(user_password=password)
        out = BytesIO()
        writer.write(out)
        out_bytes = out.getvalue()
        if max_output_bytes is not None and len(out_bytes) > max_output_bytes:
            raise ValueError("output_too_large")
        return out_bytes
    except ValueError:
        raise
    except Exception:
        raise ValueError("unsupported_pdf")
