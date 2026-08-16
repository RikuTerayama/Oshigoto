#!/usr/bin/env python3
"""Verify that Tool and Guide detail pages share one rail skeleton."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["AMAZON_AFFILIATE_ENABLED"] = "true"
os.environ["AMAZON_ASSOCIATE_TAG"] = "rail-consistency-22"

from app import app  # noqa: E402


SLUGS = ("pdf", "csv", "image-batch", "image-compress", "image-cleanup", "qr-code", "seo")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    app.config["TESTING"] = True
    with app.test_client() as client:
        for family in ("tools", "guide"):
            for slug in SLUGS:
                path = f"/{family}/{slug}"
                response = client.get(path)
                require(response.status_code == 200, f"{path}: expected 200")
                soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
                shell = soup.select_one(".page-with-affiliate-rail")
                require(shell is not None, f"{path}: shared rail shell missing")
                rail = shell.select_one(":scope > .global-affiliate-rail")
                require(rail is not None, f"{path}: direct primary rail missing")
                if family == "tools":
                    require("global-affiliate-rail--tool" in rail.get("class", []), f"{path}: tool rail modifier missing")
                    require(not rail.select_one(".global-affiliate-rail__publisher"), f"{path}: publisher block must stay absent")

    css = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")
    require("--public-detail-rail-width: 320px" in css, "shared rail width token missing")
    require("--public-detail-rail-gap: clamp(28px, 3vw, 36px)" in css, "shared rail gap token missing")
    require(".guide-detail-page .page-with-affiliate-rail.guide-shell" in css, "Guide selector missing from shared layout")
    require("@media (min-width: 1240px)" in css and "@media (max-width: 1239px)" in css, "shared breakpoint contract missing")
    require("@media (min-width: 1280px) and (min-height: 800px)" in css and "top: 92px" in css, "shared sticky contract missing")
    print("PASS: seven Tool and seven Guide routes share the canonical 320px rail contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
