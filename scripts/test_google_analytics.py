#!/usr/bin/env python3
"""Verify the shared GA4 tag across public Oshigoto HTML responses."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import GA_MEASUREMENT_ID_DEFAULT, app, get_ga_measurement_id


PUBLIC_PATHS = (
    "/",
    "/tools",
    "/tools/pdf",
    "/tools/csv",
    "/tools/image-batch",
    "/tools/image-compress",
    "/tools/qr-code",
    "/tools/image-cleanup",
    "/tools/seo",
    "/guide",
    "/guide/pdf",
    "/guide/csv",
    "/faq",
    "/glossary",
    "/best-practices",
    "/blog",
    "/about",
    "/business",
    "/contact",
    "/privacy",
    "/terms",
)

ADSENSE_LOADER = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4232725615106709"


def assert_tracking(html: str, measurement_id: str, path: str) -> None:
    loader = f"https://www.googletagmanager.com/gtag/js?id={measurement_id}"
    config = f"gtag('config', '{measurement_id}'"
    assert html.count(loader) == 1, f"{path}: GA loader count must be 1"
    assert html.count(config) == 1, f"{path}: GA config count must be 1"
    assert html.count(ADSENSE_LOADER) == 1, f"{path}: AdSense loader count must remain 1"
    assert "GTM-" not in html, f"{path}: unexpected Google Tag Manager container"
    assert "window.gaEvent" in html, f"{path}: gaEvent helper missing"
    assert "tool_open" in html, f"{path}: tool_open event missing"
    assert "contact_open" in html, f"{path}: contact_open event missing"


def main() -> int:
    original = os.environ.pop("GA_MEASUREMENT_ID", None)
    app.config.update(TESTING=True)
    try:
        assert GA_MEASUREMENT_ID_DEFAULT == "G-T51PVK40M0"
        assert get_ga_measurement_id() == GA_MEASUREMENT_ID_DEFAULT

        with app.test_client() as client:
            for path in PUBLIC_PATHS:
                response = client.get(path, follow_redirects=True)
                assert response.status_code == 200, f"{path}: expected 200 after redirects"
                assert_tracking(response.get_data(as_text=True), GA_MEASUREMENT_ID_DEFAULT, path)

            response = client.get("/missing-ga4-regression-page")
            assert response.status_code == 404
            not_found = response.get_data(as_text=True)
            assert_tracking(not_found, GA_MEASUREMENT_ID_DEFAULT, "404")
            assert 'name="robots" content="noindex,follow"' in not_found
            assert 'rel="canonical"' not in not_found
            assert 'application/ld+json' not in not_found

            os.environ["GA_MEASUREMENT_ID"] = "G-TEST123"
            overridden = client.get("/").get_data(as_text=True)
            assert_tracking(overridden, "G-TEST123", "environment override")
            assert GA_MEASUREMENT_ID_DEFAULT not in overridden
            assert get_ga_measurement_id() == "G-TEST123"
    finally:
        if original is None:
            os.environ.pop("GA_MEASUREMENT_ID", None)
        else:
            os.environ["GA_MEASUREMENT_ID"] = original

    print(f"PASS: GA4 {GA_MEASUREMENT_ID_DEFAULT} renders once across public HTML and supports env override")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
