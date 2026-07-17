#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check request isolation and upload guardrails for public processing APIs."""

import io
import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

os.environ.setdefault("MAX_ACTIVE_PDF_JOBS", "2")
os.environ.setdefault("MAX_FILE_SIZE_MB", "1")
os.environ.setdefault("MAX_TOTAL_UPLOAD_MB", "2")
os.environ.setdefault("MAX_FILES_PER_REQUEST", "20")
os.environ.setdefault("MAX_PDF_PAGES", "3")
os.environ.setdefault("MAX_OUTPUT_SIZE_MB", "2")
os.environ.setdefault("RATE_LIMIT_PDF_PER_MIN", "60")

_TEMP_ROOT = Path(tempfile.mkdtemp(prefix="oshigoto-safety-"))
os.environ["TMP"] = str(_TEMP_ROOT)
os.environ["TEMP"] = str(_TEMP_ROOT)
tempfile.tempdir = str(_TEMP_ROOT)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pypdf import PdfReader, PdfWriter  # noqa: E402
from werkzeug.datastructures import MultiDict  # noqa: E402

import app as app_module  # noqa: E402


def make_pdf(width=72, height=72, pages=1, encrypted=False, password="secret"):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=width, height=height)
    if encrypted:
        writer.encrypt(user_password=password)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def post_lock(pdf_bytes, password, filename="document.pdf"):
    with app_module.app.test_client() as client:
        return client.post(
            "/api/pdf/lock",
            data={"file": (io.BytesIO(pdf_bytes), filename), "password": password},
            content_type="multipart/form-data",
        )


def assert_locked_pdf(pdf_bytes, password, expected_width, expected_height):
    reader = PdfReader(io.BytesIO(pdf_bytes), strict=False)
    assert reader.is_encrypted, "output PDF is not encrypted"
    assert reader.decrypt(password), "output PDF cannot be opened with expected password"
    page = reader.pages[0]
    assert int(float(page.mediabox.width)) == expected_width
    assert int(float(page.mediabox.height)) == expected_height


def check_parallel_requests_do_not_mix():
    pdf_a = make_pdf(width=72, height=96)
    pdf_b = make_pdf(width=144, height=180)
    results = {}

    def worker(label, pdf_bytes, password, filename):
        response = post_lock(pdf_bytes, password, filename)
        results[label] = (response.status_code, response.data)

    threads = [
        threading.Thread(target=worker, args=("a", pdf_a, "alpha-pass", "alpha.pdf")),
        threading.Thread(target=worker, args=("b", pdf_b, "beta-pass", "beta.pdf")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results["a"][0] == 200, results["a"][0]
    assert results["b"][0] == 200, results["b"][0]
    assert_locked_pdf(results["a"][1], "alpha-pass", 72, 96)
    assert_locked_pdf(results["b"][1], "beta-pass", 144, 180)


def check_busy_limit_returns_429():
    acquired_count = 0
    for _ in range(app_module.MAX_ACTIVE_PDF_JOBS):
        acquired = app_module._PDF_JOB_SEMAPHORE.acquire(blocking=False)
        assert acquired, "could not acquire PDF semaphore for busy-limit test"
        acquired_count += 1
    try:
        response = post_lock(make_pdf(), "busy-pass", "busy.pdf")
        assert response.status_code == 429, response.status_code
        assert response.headers.get("Retry-After"), "missing Retry-After header"
    finally:
        for _ in range(acquired_count):
            app_module._PDF_JOB_SEMAPHORE.release()


def check_file_count_limit():
    pdf = make_pdf()
    with app_module.app.test_client() as client:
        response = client.post(
            "/api/pdf/lock",
            data=MultiDict([
                ("file", (io.BytesIO(pdf), "a.pdf")),
                ("file", (io.BytesIO(pdf), "b.pdf")),
                ("password", "count-pass"),
            ]),
            content_type="multipart/form-data",
        )
    assert response.status_code == 400, response.status_code
    assert response.get_json()["error_code"] == "single_file_only"


def check_size_and_pdf_validation_limits():
    too_large = b"%PDF-1.4\n" + (b"x" * (app_module.PDF_API_MAX_BYTES + 1))
    assert post_lock(too_large, "size-pass", "large.pdf").status_code == 413

    invalid = post_lock(b"not a pdf", "invalid-pass", "invalid.pdf")
    assert invalid.status_code == 422, invalid.status_code
    assert invalid.get_json()["error_code"] == "corrupt_pdf"

    encrypted = post_lock(make_pdf(encrypted=True, password="old-pass"), "new-pass", "encrypted.pdf")
    assert encrypted.status_code == 400, encrypted.status_code
    assert encrypted.get_json()["error_code"] == "already_encrypted"

    too_many_pages = post_lock(make_pdf(pages=4), "pages-pass", "pages.pdf")
    assert too_many_pages.status_code == 413, too_many_pages.status_code
    assert too_many_pages.get_json()["error_code"] == "too_many_pages"


def check_no_tempfile_leftovers():
    leftovers = [p for p in _TEMP_ROOT.rglob("*") if p.exists()]
    assert not leftovers, f"unexpected temporary files: {leftovers}"


def main():
    try:
        check_parallel_requests_do_not_mix()
        check_busy_limit_returns_429()
        check_file_count_limit()
        check_size_and_pdf_validation_limits()
        check_no_tempfile_leftovers()
    finally:
        shutil.rmtree(_TEMP_ROOT, ignore_errors=True)
    print("multi-user safety checks passed")


if __name__ == "__main__":
    main()
