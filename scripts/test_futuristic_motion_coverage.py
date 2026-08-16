#!/usr/bin/env python3
"""Contract checks for the quiet signal motion system."""

from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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
        landing = BeautifulSoup(client.get("/").get_data(as_text=True), "html.parser")
        visual = landing.select_one(".hero-v2__signal[aria-hidden='true'] .work-signal-visual")
        require(visual is not None, "landing Work Signal Visual missing")
        require(len(visual.select(".work-signal-node")) == 5, "landing visual must have five nodes")
        require(landing.select_one(".landing-tools-zone > .signal-track") is not None, "landing section signal missing")

        for path in TOOL_PATHS:
            soup = BeautifulSoup(client.get(path).get_data(as_text=True), "html.parser")
            require(soup.select_one("[data-tool-hero]") is not None, f"{path}: tool hero missing")
            require(soup.select_one("[data-tool-flow] > .signal-track") is not None, f"{path}: flow signal missing")

    public_css = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")
    reveal_css = (ROOT / "static/css/scroll-reveal.css").read_text(encoding="utf-8")
    reveal_js = (ROOT / "static/js/scroll-reveal.js").read_text(encoding="utf-8")
    combined = (public_css + reveal_css + reveal_js).lower()
    require("@keyframes public-signal-track" in public_css, "shared signal keyframes missing")
    require("work-signal-visual" in public_css and "work-signal-strip" in public_css, "responsive hero signal missing")
    require("opacity: 0.76" in reveal_css and "translatey(12px)" in reveal_css.lower(), "recognizable reveal missing")
    require("60ms" in reveal_css and "nth-child(n+5)" in reveal_css, "bounded stagger missing")
    require("prefers-reduced-motion: reduce" in combined, "reduced-motion guard missing")
    require(".amazon-single-card" in public_css and "animation: none !important" in public_css, "Amazon animation guard missing")
    require(".a8-creative-slot" in public_css, "A8 animation guard missing")
    require(not any(name in combined for name in ("gsap", "three.js", "lottie", "framer-motion")), "external motion dependency detected")
    print("PASS: landing, tools, reveal, ads and reduced-motion signal contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
