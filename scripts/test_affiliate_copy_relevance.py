#!/usr/bin/env python3
"""Verify route-specific Amazon copy and env-only associate tags."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["AMAZON_AFFILIATE_ENABLED"] = "true"
os.environ["AMAZON_ASSOCIATE_TAG"] = "relevance-check-22"

from lib.amazon_affiliate_map import AMAZON_EXACT_PATH_THEME_IDS  # noqa: E402
from lib.amazon_creators import build_rotating_theme_cards  # noqa: E402


EXPECTED = {
    "/tools/pdf": ("PDF", "資料", "書類", "文書"),
    "/tools/csv": ("CSV", "Excel", "データ", "表"),
    "/tools/image-batch": ("画像",),
    "/tools/image-compress": ("画像", "Web"),
    "/tools/image-cleanup": ("画像",),
    "/tools/qr-code": ("QR",),
    "/tools/seo": ("SEO", "Web"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    rows = []
    for path, expected_words in EXPECTED.items():
        cards = build_rotating_theme_cards(path, "tool", count=2)
        require(len(cards) == 2, f"{path}: expected two route themes")
        require(len({card["theme_id"] for card in cards}) == 2, f"{path}: duplicate theme")
        require({card["theme_id"] for card in cards} == set(AMAZON_EXACT_PATH_THEME_IDS[path]), f"{path}: unrelated theme")
        for card in cards:
            visible_copy = " ".join(str(card.get(key) or "") for key in ("category_label", "title", "lead", "cta"))
            require(any(word in visible_copy for word in expected_words), f"{path}: unrelated visible copy {visible_copy!r}")
            query = parse_qs(urlparse(card["url"]).query)
            require(query.get("tag") == ["relevance-check-22"], f"{path}: associate tag is not env-derived")
            rows.append((path, card["theme_id"], card["category_label"], card["title"], card["lead"], card["cta"], card["keyword"]))

    source = (ROOT / "lib/amazon_creators.py").read_text(encoding="utf-8")
    source += (ROOT / "lib/amazon_affiliate_map.py").read_text(encoding="utf-8")
    production_tag = "ielts" + "consult-22"
    require(production_tag not in source, "production associate tag must not be hardcoded")
    print("route | theme_id | category | title | lead | CTA | keyword")
    for row in rows:
        print(" | ".join(row))
    print("PASS: 14 route-specific Amazon theme rows are relevant and env-tagged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
