#!/usr/bin/env python3
"""Contract checks for restrained mobile-capable motion."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CSS = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")
MOTION_CSS = (ROOT / "static/css/ui-motion.css").read_text(encoding="utf-8")
REVEAL_CSS = (ROOT / "static/css/scroll-reveal.css").read_text(encoding="utf-8")
REVEAL_JS = (ROOT / "static/js/scroll-reveal.js").read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    require("IntersectionObserver" in REVEAL_JS, "scroll reveal must use IntersectionObserver")
    require("translateY(10px)" in REVEAL_CSS and "0.32s" in REVEAL_CSS, "reveal motion must stay subtle")
    require("@keyframes public-tool-signal" in PUBLIC_CSS and "4.8s" in PUBLIC_CSS, "hero signal animation missing")
    require("@keyframes public-tool-icon-float" in PUBLIC_CSS and "translateY(-2px)" in PUBLIC_CSS, "icon micro motion missing")
    require("(hover: none), (pointer: coarse)" in PUBLIC_CSS and "translateY(1px)" in PUBLIC_CSS, "touch feedback missing")
    require("@media (prefers-reduced-motion: reduce)" in PUBLIC_CSS + MOTION_CSS + REVEAL_CSS, "reduced motion guard missing")
    require(".amazon-single-card" in PUBLIC_CSS and ".a8-creative-slot" in PUBLIC_CSS and "animation: none !important" in PUBLIC_CSS, "ad animation guard missing")
    require("@media (max-width: 767px), (hover: none), (pointer: coarse)" in MOTION_CSS, "mobile cursor halo guard missing")
    require(not any(name in (PUBLIC_CSS + MOTION_CSS + REVEAL_JS).lower() for name in ("gsap", "three.js", "lottie", "framer")), "external motion library detected")
    print("PASS: mobile reveal, signal, icon, touch, ad and reduced-motion contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
