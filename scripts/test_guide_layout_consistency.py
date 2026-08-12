#!/usr/bin/env python3
"""Verify the shared guide shell across the catalog and seven detail routes."""

from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402


GUIDES = ("pdf", "csv", "image-batch", "image-compress", "image-cleanup", "qr-code", "seo")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    app.config["TESTING"] = True
    with app.test_client() as client:
        index = BeautifulSoup(client.get("/guide").get_data(as_text=True), "html.parser")
        require(index.select_one("body.guide-index-page") is not None, "/guide: canonical page class missing")
        require(index.select_one(".guide-shell .guide-hero") is not None, "/guide: shared hero missing")
        require(len(index.select(".guide-catalog-grid > .guide-catalog-card")) == 7, "/guide: expected seven guide cards")

        for guide_id in GUIDES:
            path = f"/guide/{guide_id}"
            response = client.get(path)
            require(response.status_code == 200, f"{path}: expected 200")
            soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
            require(soup.select_one("body.guide-detail-page") is not None, f"{path}: canonical body class missing")
            require(soup.select_one(".guide-shell") is not None, f"{path}: shared shell missing")
            require(soup.select_one(".guide-hero h1") is not None, f"{path}: shared hero missing")
            require(soup.select_one('link[href*="public-system.css"]') is not None, f"{path}: shared stylesheet missing")
            require(soup.select_one(f'a[href="/tools/{guide_id}"]') is not None, f"{path}: tool CTA missing")
            require(
                soup.select_one(".guide-section-card") is not None or soup.select_one(".guide-content") is not None,
                f"{path}: canonical information surface missing",
            )

    print("PASS: guide index and all seven detail guides use the canonical shared format")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
