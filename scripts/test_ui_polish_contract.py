#!/usr/bin/env python3
"""Contract checks for the shared, capability-aware public UI polish layer."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402

CSS = (ROOT / "static/css/ui-motion.css").read_text(encoding="utf-8")
PUBLIC_CSS = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")
REVEAL_CSS = (ROOT / "static/css/scroll-reveal.css").read_text(encoding="utf-8")
JS = (ROOT / "static/js/ui-polish.js").read_text(encoding="utf-8")
REVEAL_JS = (ROOT / "static/js/scroll-reveal.js").read_text(encoding="utf-8")
HEAD = (ROOT / "templates/includes/head_meta.html").read_text(encoding="utf-8")
STYLE_INCLUDE = (ROOT / "templates/includes/public_system_styles.html").read_text(encoding="utf-8")
NAV = (ROOT / "templates/includes/header_v2.html").read_text(encoding="utf-8")
FOOTER = (ROOT / "templates/includes/footer.html").read_text(encoding="utf-8")
TOOL_IDS = ("pdf", "csv", "image-batch", "image-compress", "image-cleanup", "qr-code", "seo")
TOOL_PATHS = tuple(f"/tools/{tool_id}" for tool_id in TOOL_IDS)
PUBLIC_PATHS = (
    "/", "/tools", "/tools/pdf", "/tools/csv", "/tools/image-batch",
    "/tools/image-compress", "/tools/image-cleanup", "/tools/qr-code", "/tools/seo",
    "/guide", "/guide/pdf", "/guide/csv", "/guide/image-batch", "/guide/image-compress",
    "/guide/image-cleanup", "/guide/qr-code", "/guide/seo", "/faq", "/glossary",
    "/best-practices", "/blog", "/about", "/business", "/contact", "/privacy", "/terms",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    require(JS.count("document.createElement('span')") == 1, "cursor halo must use one DOM node")
    require("pointer-events: none" in CSS, "cursor halo must never capture pointer events")
    require(re.search(r"cursor\s*:\s*none", CSS, re.I) is None, "native cursor must remain visible")
    require("(pointer: coarse)" in CSS and "(hover: none)" in CSS, "touch/coarse cursor opt-out missing")
    require("prefers-reduced-motion: reduce" in CSS, "reduced motion contract missing")
    require("html:not(.js) [data-reveal]" in REVEAL_CSS, "reveal must stay visible without JS")
    require("html.reveal-ready [data-reveal]" in REVEAL_CSS, "reveal initial state must require successful initialization")
    require("root.classList.add('reveal-ready')" in REVEAL_JS, "reveal readiness class missing")
    require("IntersectionObserver" in REVEAL_JS, "reveal must use IntersectionObserver")
    require(not any(name in (CSS + JS).lower() for name in ("gsap", "three.js", "lottie", "framer")), "external motion library detected")
    require(".a8-creative-slot:hover" in CSS and "transform: none" in CSS, "A8 creative hover safeguard missing")
    require(STYLE_INCLUDE.count("css/ui-motion.css") == 1 and HEAD.count("js/ui-polish.js") == 1, "UI assets must load once")
    require(STYLE_INCLUDE.count("css/public-system.css") == 1, "public system must load once")
    require("startswith('/tools/')" in NAV and "startswith('/guide/')" in NAV, "child-route nav active contract missing")
    require("_resource_paths" in NAV and "startswith('/blog/')" in NAV, "resource nav active contract missing")
    require('aria-current="page"' in NAV, "exact active links need aria-current")
    require("data-affiliate" not in JS and "localStorage" not in JS and "document.cookie" not in JS, "visual polish must not add tracking")
    require(".editorial-kicker," in PUBLIC_CSS, "canonical editorial kicker style missing")
    require("--kicker-size" in PUBLIC_CSS and "--kicker-spacing" in PUBLIC_CSS, "kicker tokens missing")
    require("<h" not in re.search(r'<p class="editorial-kicker">HOW TO USE</p>', (ROOT / "templates/tools/pdf.html").read_text(encoding="utf-8")).group(0), "kicker must not alter heading hierarchy")
    for tool_id in TOOL_IDS:
        require(f"tool-accent--{tool_id}" in PUBLIC_CSS, f"missing accent mapping: {tool_id}")
    require(PUBLIC_CSS.count(":is(.tool-page--") == len(TOOL_IDS), "tool accents must have exactly seven mappings")
    require("page full background" not in PUBLIC_CSS and "body.tool-accent" not in PUBLIC_CSS, "tool accent must not theme the page background")
    require(":focus-visible" in PUBLIC_CSS and "--focus-ring-color" in PUBLIC_CSS, "canonical form focus-visible style missing")
    require('[aria-invalid="true"]' in PUBLIC_CSS and "rgba(155, 44, 44, .14)" in PUBLIC_CSS, "error focus state must remain distinct")
    require("outline: none" not in PUBLIC_CSS, "focus ring must not be removed")
    require("[data-file-dropzone].is-dragging" in PUBLIC_CSS, "file drop drag state missing")
    require("prepareFileDropzones" in JS and "event.key !== 'Enter'" in JS, "file drop keyboard interaction missing")
    require(FOOTER.count("SMALL TOOLS FOR EVERYDAY WORK") == 1, "footer English statement must appear once")
    require(FOOTER.count("小さな仕事を、軽くする。") == 1, "footer Japanese statement must appear once")
    require("@import" not in PUBLIC_CSS and "https://" not in PUBLIC_CSS, "public polish must not add external CSS assets")
    require("@media (max-width: 767px)" in CSS and "scaleY(1)" in CSS, "mobile active nav indicator missing")

    app.config["TESTING"] = True
    with app.test_client() as client:
        for path in PUBLIC_PATHS:
            response = client.get(path)
            require(response.status_code == 200, f"{path}: expected 200")
            html = response.get_data(as_text=True)
            require(html.count("css/ui-motion.css") == 1, f"{path}: ui-motion.css must load once")
            require(html.count("js/ui-polish.js") == 1, f"{path}: ui-polish.js must load once")
            require(html.count("css/public-system.css") == 1, f"{path}: public-system.css must load once")
            require(html.count("SMALL TOOLS FOR EVERYDAY WORK") == 1, f"{path}: footer brand block must render once")

        home_soup = BeautifulSoup(client.get("/").get_data(as_text=True), "html.parser")
        require(len(home_soup.select(".hero-tool-card[class*='tool-accent--']")) == 7, "home hero must render seven subtle tool accents")
        require(len(home_soup.select(".tool-card-v2[class*='tool-accent--']")) == 7, "home catalog must render seven subtle tool accents")

        catalog_soup = BeautifulSoup(client.get("/tools").get_data(as_text=True), "html.parser")
        require(len(catalog_soup.select(".tool-catalog-card[class*='tool-accent--']")) == 7, "tools catalog must render seven subtle tool accents")

        for path in TOOL_PATHS:
            tool_soup = BeautifulSoup(client.get(path).get_data(as_text=True), "html.parser")
            kickers = [node.get_text(" ", strip=True) for node in tool_soup.select(".tool-flow > .editorial-kicker")]
            require(kickers == ["HOW TO USE"], f"{path}: HOW TO USE kicker must appear once")

        not_found = client.get("/ui-polish-contract-not-found")
        require(not_found.status_code == 404, "404 route contract changed")
        not_found_html = not_found.get_data(as_text=True)
        require(not_found_html.count("css/ui-motion.css") == 1, "404: ui-motion.css must load once")
        require(not_found_html.count("js/ui-polish.js") == 1, "404: ui-polish.js must load once")

        for path, nav_id in (
            ("/", "nav-home"),
            ("/tools/pdf", "nav-tools"),
            ("/guide/pdf", "nav-guide"),
            ("/glossary", "nav-resource"),
            ("/business", "nav-business"),
        ):
            soup = BeautifulSoup(client.get(path).get_data(as_text=True), "html.parser")
            active = soup.select_one(f"#{nav_id}.site-nav__link--active")
            require(active is not None, f"{path}: expected active nav group {nav_id}")

        for path in ("/faq", "/glossary", "/best-practices", "/blog", "/about", "/sitemap.html", "/privacy", "/terms", "/contact"):
            soup = BeautifulSoup(client.get(path).get_data(as_text=True), "html.parser")
            require(soup.select_one("#nav-resource.site-nav__link--active") is not None, f"{path}: Resources must be active")

        tools_soup = BeautifulSoup(client.get("/tools").get_data(as_text=True), "html.parser")
        require(tools_soup.select_one('a[href="/tools"][aria-current="page"]') is not None, "/tools: exact link needs aria-current")

    print("OK: UI polish contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
