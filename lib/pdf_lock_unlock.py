# -*- coding: utf-8 -*-
"""
PDF ロック解除・ロック付与（サーバ側）
- 案B採用: 復号/暗号化をサーバで実行。パスワードはログ・永続化しない。
- 正しいパスワードを知っている前提のみ。推測/迂回は行わない。
"""
from io import BytesIO

from pypdf import PdfReader, PdfWriter


# 設計メモ: 案B（サーバ併用）を採用。
# 理由: 保護付与は pdf-lib でクライアント実装が困難なため、サーバで pypdf により確実に実装する。
# 保護解除も同一エンドポイントで行い、パスワードをログに出さず一時メモリのみで処理する。


def decrypt_pdf(pdf_bytes: bytes, password: str) -> bytes:
    """
    パスワード保護されたPDFを復号してバイト列で返す。
    非暗号化PDFの場合はそのまま返す。暗号化PDFでパスワード未入力は need_password、
    誤りは invalid_password を投げる。パスワードはログに一切出さない。
    読込・書き出し失敗時は corrupt_pdf / unsupported_encryption を投げる。
    """
    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False)
    except Exception:
        raise ValueError("corrupt_pdf")
    if not reader.is_encrypted:
        return pdf_bytes
    if not (password and password.strip()):
        raise ValueError("need_password")
    try:
        ok = reader.decrypt(password)
    except Exception:
        raise ValueError("invalid_password")
    if ok == 0:
        raise ValueError("invalid_password")
    try:
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        out = BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception:
        raise ValueError("corrupt_pdf")


def encrypt_pdf(pdf_bytes: bytes, password: str) -> bytes:
    """
    PDFにユーザーパスワードを付与して暗号化し、バイト列で返す。
    既に暗号化されているPDFは already_encrypted を投げる。パスワードはログに一切出さない。
    """
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
