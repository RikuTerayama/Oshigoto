#!/usr/bin/env python3
"""Deterministic diversity checks without inventing affiliate creatives."""

from __future__ import annotations

import hashlib
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.a8_affiliate_catalog import (  # noqa: E402
    TEMPLATE_ROOT,
    load_a8_creative_catalog,
    select_a8_creative,
)
from lib.amazon_affiliate_map import AMAZON_THEME_POOL  # noqa: E402
from lib.amazon_creators import build_rotating_theme_cards  # noqa: E402


EXPECTED_A8_CHECKSUMS = {
    "a8-01": "63cb848baaddaeb5f4be77f4a56cdec9eeb8a2f6882f46f64f2e5b179c07c8b8",
    "a8-02": "96cc5c6909169ceb8de511b572118149dc11b37315a20460096c5562afe8ab05",
    "a8-03": "e6d9f2692a1a94e1ed6e1939ab2598369ff12c91838cc94adf60c58abd6f016c",
    "a8-04": "acb6adb31d5d0662fb5d14a9a8d8c8a09fe1c754022f061ebfd416e971265a29",
    "a8-05": "035c1ed40219ac565559bfe1a9f4550bd8b86d3a51f68ea6ad2f1ce2039f93b9",
}


def main() -> int:
    creatives = load_a8_creative_catalog()
    assert len(creatives) == 5
    assert {item["id"] for item in creatives} == set(EXPECTED_A8_CHECKSUMS)
    for item in creatives:
        source = (TEMPLATE_ROOT / item["template"]).read_bytes()
        assert hashlib.sha256(source).hexdigest() == EXPECTED_A8_CHECKSUMS[item["id"]]

    seen_a8: set[str] = set()
    start = date(2026, 1, 1)
    paths = ("/", "/tools", "/guide", "/blog/example")
    for offset in range(30):
        day = (start + timedelta(days=offset)).isoformat()
        for path in paths:
            primary = select_a8_creative(path, day, creatives)
            assert primary is not None
            seen_a8.add(primary["id"])
            if path in {"/", "/tools", "/guide"}:
                placement = {"/": "landing-lower-a8", "/tools": "tools-lower-a8", "/guide": "content-lower-a8"}[path]
                secondary = select_a8_creative(path, day, creatives, placement=placement, exclude_creative_ids=[primary["id"]])
                assert secondary is not None and secondary["id"] != primary["id"]
                seen_a8.add(secondary["id"])
    assert seen_a8 == set(EXPECTED_A8_CHECKSUMS), seen_a8

    enabled_amazon = {str(item["id"]) for item in AMAZON_THEME_POOL if item.get("enabled")}
    seen_amazon: set[str] = set()
    for offset in range(30):
        bucket = f"daily:{(start + timedelta(days=offset)).isoformat()}"
        with patch("lib.amazon_creators._rotation_bucket_key", return_value=bucket):
            for path, page_type in (("/", "landing"), ("/tools", "tool_index"), ("/guide", "guide"), ("/blog/example", "article")):
                primary = build_rotating_theme_cards(path, page_type, slot_id="primary", count=1)
                assert len(primary) == 1
                secondary = build_rotating_theme_cards(path, page_type, slot_id="secondary", count=1, exclude_theme_ids=[primary[0]["theme_id"]])
                assert len(secondary) == 1 and secondary[0]["theme_id"] != primary[0]["theme_id"]
                seen_amazon.update((primary[0]["theme_id"], secondary[0]["theme_id"]))
    assert len(seen_amazon) >= min(5, len(enabled_amazon)), seen_amazon

    print(f"PASS: A8 reached {len(seen_a8)}/5 exact creatives; Amazon reached {len(seen_amazon)}/{len(enabled_amazon)} themes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
