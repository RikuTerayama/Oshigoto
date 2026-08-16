#!/usr/bin/env python3
"""Contract checks for the canonical 4+3/2+1/1 tool catalog layout."""

from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402
from lib.products_catalog import get_public_products  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    app.config["TESTING"] = True
    products = get_public_products()
    paths = {item["path"] for item in products}
    require(len(products) == 7, "public product catalog must contain exactly seven tools")

    with app.test_client() as client:
        home = BeautifulSoup(client.get("/").get_data(as_text=True), "html.parser")
        tools = BeautifulSoup(client.get("/tools").get_data(as_text=True), "html.parser")
        landing = home.select_one(".landing-tool-grid.balanced-seven-grid")
        catalog = tools.select_one(".tools-catalog-grid.balanced-seven-grid")
        require(not home.select(".hero-tool-grid, .hero-tool-card"), "homepage hero mini catalog returned")
        require(landing is not None and len(landing.select(":scope > *")) == 7, "homepage main grid differs from catalog")
        require({item.get("href") for item in landing.select(":scope > article a.btn-primary")} == paths, "homepage paths differ from catalog")
        require(catalog is not None and len(catalog.select(":scope > *")) == 7, "tools grid differs from catalog")

    css = (ROOT / "static" / "css" / "public-system.css").read_text(encoding="utf-8")
    require("display: flex" in css and "flex-wrap: wrap" in css and "justify-content: center" in css, "balanced flex layout missing")
    require("/ 4)" in css, "desktop four-card width contract missing")
    require("@media (max-width: 1199px)" in css and "/ 2)" in css, "tablet two-card contract missing")
    require("@media (max-width: 640px)" in css and "flex-basis: 100%" in css, "mobile one-card contract missing")
    require("nth-child" not in css, "new shared layout must not use item-specific nth-child positioning")

    print("PASS: homepage and tools use one canonical seven-item responsive catalog")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
