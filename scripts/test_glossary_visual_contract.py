#!/usr/bin/env python3
"""Regression checks for the shared glossary layout contract."""

import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    response = app.test_client().get("/glossary")
    require(response.status_code == 200, "/glossary must return 200")

    soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
    require(soup.select_one(".glossary-hero") is not None, "canonical glossary hero is missing")
    require(soup.select_one('link[href*="public-system.css"]') is not None, "public system stylesheet is missing")

    grid = soup.select_one(".glossary-grid")
    require(grid is not None, "glossary grid is missing")
    require(len(grid.select(":scope > .glossary-card")) == 5, "glossary must render five canonical cards")
    require(soup.select_one(".related-content") is not None, "related content is missing")

    css = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")
    for marker in (
        ".glossary-page-layout .glossary-grid",
        "--public-glossary-hero-gap: clamp(48px, 4vw, 56px)",
        ".glossary-page-layout .glossary-grid > .glossary-card",
        "overflow: hidden",
        "border-radius: var(--public-radius)",
        ".glossary-grid + .related-content",
        "--public-related-eyebrow-gap",
        "--public-related-grid-gap",
    ):
        require(marker in css, f"missing glossary design-system marker: {marker}")

    print("OK: glossary visual contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
