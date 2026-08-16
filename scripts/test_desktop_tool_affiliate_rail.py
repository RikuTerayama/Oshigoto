#!/usr/bin/env python3
"""Contracts for the seven desktop tool affiliate rails."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["AMAZON_AFFILIATE_ENABLED"] = "true"
os.environ["AMAZON_ASSOCIATE_TAG"] = "desktop-rail-check-22"
os.environ.setdefault("AFFILIATE_ENABLED", "true")
os.environ.setdefault("AFFILIATE_BANNERS_ENABLED", "true")

from app import app  # noqa: E402


TOOL_PATHS = (
    "/tools/pdf",
    "/tools/csv",
    "/tools/image-batch",
    "/tools/image-compress",
    "/tools/image-cleanup",
    "/tools/qr-code",
    "/tools/seo",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    app.config["TESTING"] = True
    with app.test_client() as client:
        for path in TOOL_PATHS:
            response = client.get(path)
            require(response.status_code == 200, f"{path}: expected 200")
            soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
            shell = soup.select_one(".tool-detail-shell")
            layout = shell.select_one(":scope > .tool-detail-layout.page-with-affiliate-rail") if shell else None
            rail = layout.select_one(":scope > .global-affiliate-rail--tool") if layout else None
            workspace = soup.select_one("[data-tool-workspace]")
            require(shell is not None and layout is not None and rail is not None, f"{path}: canonical tool rail contract missing")
            require(workspace is not None and workspace.sourceline < rail.sourceline, f"{path}: workspace must precede rail in DOM")
            require(not rail.select_one(".global-affiliate-rail__publisher"), f"{path}: publisher guide returned to rail")
            require(rail.select_one(".amazon-single-card--rail") is not None, f"{path}: Amazon rail card missing")

    css = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")
    require("@media (min-width: 1240px)" in css, "desktop rail breakpoint missing")
    require("--public-detail-rail-width: 320px" in css, "rail width token missing")
    require("--public-detail-rail-gap: clamp(28px, 3vw, 36px)" in css, "rail gap token missing")
    require("@media (min-width: 1280px) and (min-height: 800px)" in css, "safe sticky breakpoint missing")
    require("@media (max-width: 1239px)" in css, "single-column tablet/mobile fallback missing")
    print("PASS: seven tool routes expose Amazon/A8-only desktop rails after workspace in DOM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
