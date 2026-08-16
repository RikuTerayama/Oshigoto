#!/usr/bin/env python3
"""Contract checks for Hotfix 7 content width and tool inventory."""

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
    with app.test_client() as client:
        landing = BeautifulSoup(client.get("/").get_data(as_text=True), "html.parser")
        catalog_paths = {item["path"] for item in get_public_products()}
        hero = landing.select_one(".hero-v2")
        require(hero is not None, "homepage hero missing")
        require(not hero.select(".hero-tool-panel, .hero-tool-card"), "homepage hero mini catalog returned")
        catalog = landing.select_one(".landing-tools-zone")
        catalog_links = {anchor.get("href") for anchor in catalog.select(".tool-card-v2 a.btn-primary")}
        require(len(catalog_paths) == 7, "public catalog must contain seven tools")
        require(catalog_links == catalog_paths, "homepage catalog hrefs differ from public catalog")
        require(len(landing.select(".landing-tools-zone")) == 1, "homepage must have one canonical tool catalog")

        glossary = BeautifulSoup(client.get("/glossary").get_data(as_text=True), "html.parser")
        glossary_grid = glossary.select_one(".glossary-grid.content-grid--single")
        require(glossary_grid is not None, "glossary single-column class missing")
        require(len(glossary_grid.select(":scope > .info-card")) >= 5, "glossary entries missing")

        qr = BeautifulSoup(client.get("/tools/qr-code").get_data(as_text=True), "html.parser")
        flow = qr.select_one("#qr-flow-heading")
        require(flow is not None and flow.get_text(strip=True) == "使う順番", "QR overview missing")
        require(len(qr.select("#qr-flow-heading + .tool-step-list > li")) == 4, "QR overview must contain four steps")
        require(qr.select_one("#qr-code-app") is not None, "QR workspace regressed")

        image_compress = BeautifulSoup(client.get("/tools/image-compress").get_data(as_text=True), "html.parser")
        output_values = [option.get("value") for option in image_compress.select("#compress-output-format option")]
        require(output_values == ["original", "jpeg", "png", "webp", "avif"], "image output order changed")
        avif_option = image_compress.select_one("#compress-output-avif")
        require(avif_option is not None and avif_option.has_attr("hidden") and avif_option.has_attr("disabled"), "AVIF must fail closed")

    css = (ROOT / "static" / "css" / "common.css").read_text(encoding="utf-8")
    final_guard = css[css.rindex("/* Hotfix 7 final cascade guard. */") :]
    require("repeat(auto-fit, minmax(min(100%, 360px), 1fr))" in final_guard, "related grids do not enforce readable widths")
    require("@media (max-width: 820px)" in final_guard, "single-column narrow-screen breakpoint missing")
    require("grid-template-columns: minmax(0, 1fr) !important" in final_guard, "single-column glossary guard missing")
    require("word-break: keep-all !important" in final_guard, "Japanese title wrapping guard missing")

    template = (ROOT / "templates" / "tools" / "image-compress.html").read_text(encoding="utf-8")
    controller = (ROOT / "static" / "js" / "image-compress.js").read_text(encoding="utf-8")
    require("detectAvifEncodeSupport" in controller, "AVIF runtime detection missing")
    require("validateEncodedBuffer" in controller, "encoded AVIF identity validation missing")
    for unsupported in ("TIFF", "HEIC", "HEIF", "ICO"):
        require(f'value="{unsupported.lower()}"' not in template, f"unsupported {unsupported} output advertised")

    print("PASS: tool inventory, glossary, QR steps, AVIF gating, and wide-card contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
