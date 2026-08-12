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
REVEAL_CSS = (ROOT / "static/css/scroll-reveal.css").read_text(encoding="utf-8")
JS = (ROOT / "static/js/ui-polish.js").read_text(encoding="utf-8")
REVEAL_JS = (ROOT / "static/js/scroll-reveal.js").read_text(encoding="utf-8")
HEAD = (ROOT / "templates/includes/head_meta.html").read_text(encoding="utf-8")
STYLE_INCLUDE = (ROOT / "templates/includes/public_system_styles.html").read_text(encoding="utf-8")
NAV = (ROOT / "templates/includes/header_v2.html").read_text(encoding="utf-8")
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

    app.config["TESTING"] = True
    with app.test_client() as client:
        for path in PUBLIC_PATHS:
            response = client.get(path)
            require(response.status_code == 200, f"{path}: expected 200")
            html = response.get_data(as_text=True)
            require(html.count("css/ui-motion.css") == 1, f"{path}: ui-motion.css must load once")
            require(html.count("js/ui-polish.js") == 1, f"{path}: ui-polish.js must load once")
            require(html.count("css/public-system.css") == 1, f"{path}: public-system.css must load once")

        not_found = client.get("/ui-polish-contract-not-found")
        require(not_found.status_code == 404, "404 route contract changed")
        not_found_html = not_found.get_data(as_text=True)
        require(not_found_html.count("css/ui-motion.css") == 1, "404: ui-motion.css must load once")
        require(not_found_html.count("js/ui-polish.js") == 1, "404: ui-polish.js must load once")

        for path, nav_id in (
            ("/tools/pdf", "nav-tools"),
            ("/guide/pdf", "nav-guide"),
            ("/glossary", "nav-resource"),
            ("/business", "nav-business"),
        ):
            soup = BeautifulSoup(client.get(path).get_data(as_text=True), "html.parser")
            active = soup.select_one(f"#{nav_id}.site-nav__link--active")
            require(active is not None, f"{path}: expected active nav group {nav_id}")

        tools_soup = BeautifulSoup(client.get("/tools").get_data(as_text=True), "html.parser")
        require(tools_soup.select_one('a[href="/tools"][aria-current="page"]') is not None, "/tools: exact link needs aria-current")

    print("OK: UI polish contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
