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
    "a8-06": "48bb4a7d44b2ff8e38330ff2b2c702d7008b776eef93328b514794620ec2b873",
    "a8-07": "fefa4856e948b9ef686575e41b826ab76aa2b03816e13851a60dccaf462da7b7",
    "a8-08": "e2794258344aca9302650a76fe57e7fb62d4fbd38f60dfc30328e986ad46911e",
    "a8-09": "dd134930cbfafa28372a083df9a88bf1ba1c57e7a2add8a17889dd4a026a8a21",
    "a8-10": "1be4c7469e4eb87c3ce3bd34df0d3e5f7de101a720fc4feaa8018501844f816b",
    "a8-11": "4c317fe2a1524efef12a3fbcf5c91d7109962740031dec7c73518aa7de454562",
    "a8-12": "dd8faf5406c2973539f2bca6b285814d5d768e1d476e31f44dab9ae8e6857c7b",
    "a8-13": "ffe92007b82477b4efa2106ed21539bd4c94654626e3aa49702e440a79d31de2",
    "a8-14": "b1a4c7331cc98eb179a875bab4de7baeca46c127703ae61dcd97653c9ad1c004",
}


def main() -> int:
    creatives = load_a8_creative_catalog()
    assert len(creatives) == 14
    assert {item["id"] for item in creatives} == set(EXPECTED_A8_CHECKSUMS)
    for item in creatives:
        source = (TEMPLATE_ROOT / item["template"]).read_bytes()
        assert hashlib.sha256(source).hexdigest() == EXPECTED_A8_CHECKSUMS[item["id"]]

    seen_a8: set[str] = set()
    a8_counts = {creative_id: 0 for creative_id in EXPECTED_A8_CHECKSUMS}
    start = date(2026, 1, 1)
    paths = ("/", "/tools", "/guide", "/blog/example")
    for offset in range(90):
        day = (start + timedelta(days=offset)).isoformat()
        for path in paths:
            primary = select_a8_creative(path, day, creatives, eligible_sizes={item["size"] for item in creatives})
            assert primary is not None
            seen_a8.add(primary["id"])
            a8_counts[primary["id"]] += 1
            if path in {"/", "/tools", "/guide"}:
                placement = {"/": "landing-lower-a8", "/tools": "tools-lower-a8", "/guide": "content-lower-a8"}[path]
                secondary = select_a8_creative(path, day, creatives, placement=placement, exclude_creative_ids=[primary["id"]], eligible_sizes={item["size"] for item in creatives})
                assert secondary is not None and secondary["id"] != primary["id"]
                seen_a8.add(secondary["id"])
                a8_counts[secondary["id"]] += 1
    assert seen_a8 == set(EXPECTED_A8_CHECKSUMS), seen_a8
    assert min(a8_counts.values()) > 0, a8_counts
    assert max(a8_counts.values()) <= min(a8_counts.values()) * 3, a8_counts
    assert sum(a8_counts[item["id"]] for item in creatives if item["category"] == "english-learning") > 0

    enabled_amazon = {str(item["id"]) for item in AMAZON_THEME_POOL if item.get("enabled")}
    seen_amazon: set[str] = set()
    for offset in range(60):
        bucket = f"daily:{(start + timedelta(days=offset)).isoformat()}"
        with patch("lib.amazon_creators._rotation_bucket_key", return_value=bucket):
            for path, page_type in (("/", "landing"), ("/tools", "tool_index"), ("/guide", "guide"), ("/blog/example", "article")):
                primary = build_rotating_theme_cards(path, page_type, slot_id="primary", count=1)
                assert len(primary) == 1
                secondary = build_rotating_theme_cards(path, page_type, slot_id="secondary", count=1, exclude_theme_ids=[primary[0]["theme_id"]])
                assert len(secondary) == 1 and secondary[0]["theme_id"] != primary[0]["theme_id"]
                seen_amazon.update((primary[0]["theme_id"], secondary[0]["theme_id"]))
    assert len(seen_amazon) >= min(5, len(enabled_amazon)), seen_amazon

    print(f"PASS: A8 reached {len(seen_a8)}/14 exact creatives over 90 days {a8_counts}; Amazon reached {len(seen_amazon)}/{len(enabled_amazon)} themes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
