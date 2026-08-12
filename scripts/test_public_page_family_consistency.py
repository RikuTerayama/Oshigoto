#!/usr/bin/env python3
"""Protect canonical public-page families and the shared seven-tool hero."""

from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402


TOOLS = ("pdf", "csv", "image-batch", "image-compress", "image-cleanup", "qr-code", "seo")
GUIDES = tuple(f"/guide/{tool_id}" for tool_id in TOOLS)
FAMILIES = {
    "index": ("/", "/tools", "/guide"),
    "resource": ("/faq", "/glossary", "/best-practices", "/blog", "/about"),
    "business": ("/business",),
    "legal": ("/privacy", "/terms", "/contact"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    partial = (ROOT / "templates/includes/tool_hero.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")
    require('class="tool-hero"' in partial, "shared tool hero partial missing")
    require(".landing-page.tool-page .tool-hero" in css, "canonical tool hero CSS missing")
    require(".tool-hero::after" in css, "canonical accent dot missing")

    app.config["TESTING"] = True
    with app.test_client() as client:
        for tool_id in TOOLS:
            path = f"/tools/{tool_id}"
            response = client.get(path)
            require(response.status_code == 200, f"{path}: expected 200")
            soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
            heroes = soup.select(".tool-intro-layout__content > .tool-hero")
            require(len(heroes) == 1, f"{path}: expected one canonical hero")
            hero = heroes[0]
            require(hero.select_one(":scope > .tool-hero__icon svg") is not None, f"{path}: hero icon missing")
            require(hero.select_one(":scope > h1#tool-hero-heading") is not None, f"{path}: hero heading missing")
            require(hero.select_one(":scope > .tool-hero__lead") is not None, f"{path}: hero lead missing")
            require(hero.select_one(":scope > .tool-processing-note") is not None, f"{path}: processing note missing")
            require(hero.select_one(".editorial-kicker") is None, f"{path}: hero English kicker must not render")
            require(hero.select_one(".amazon-single-card, .a8-creative-slot") is None, f"{path}: affiliate nested in hero")
            require(soup.select_one(".page-header, .compress-hero, .qr-hero") is None, f"{path}: legacy hero rendered")

            flow = soup.select_one(".tool-intro-layout__content > .tool-flow")
            require(flow is not None, f"{path}: canonical flow missing")
            require(len(flow.select(":scope > .editorial-kicker")) == 1, f"{path}: HOW TO USE count changed")
            require(flow.select_one(":scope > .editorial-kicker").get_text(strip=True) == "HOW TO USE", f"{path}: kicker text changed")
            require(len(flow.select(":scope > .tool-step-list > li")) == 4, f"{path}: expected four steps")
            require(response.get_data(as_text=True).count("css/public-system.css") == 1, f"{path}: shared CSS duplicated")

            source = (ROOT / f"templates/tools/{tool_id}.html").read_text(encoding="utf-8")
            require(source.count("includes/tool_hero.html") == 1, f"{path}: shared partial not used once")
            for legacy in (".page-header", ".compress-hero", ".qr-hero"):
                require(legacy not in source, f"{path}: legacy hero CSS remains: {legacy}")

        for path in GUIDES:
            response = client.get(path)
            require(response.status_code == 200, f"{path}: expected 200")
            soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
            require(soup.select_one("body.guide-detail-page .guide-hero h1") is not None, f"{path}: guide family shell missing")
            require(response.get_data(as_text=True).count("css/public-system.css") == 1, f"{path}: shared CSS duplicated")

        for family, paths in FAMILIES.items():
            for path in paths:
                response = client.get(path)
                require(response.status_code == 200, f"{family} {path}: expected 200")
                html = response.get_data(as_text=True)
                soup = BeautifulSoup(html, "html.parser")
                require(html.count("css/public-system.css") == 1, f"{family} {path}: shared CSS duplicated")
                require(soup.select_one("main, .container, .guide-shell") is not None, f"{family} {path}: public content shell missing")

    print("PASS: public page families retain shared shells and all seven tools use one canonical hero")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
