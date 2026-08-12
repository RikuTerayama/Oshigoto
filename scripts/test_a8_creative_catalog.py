#!/usr/bin/env python3
"""Regression checks for exact A8 creatives, policy, and responsive rendering."""

from __future__ import annotations

import hashlib
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.a8_affiliate_catalog import (  # noqa: E402
    A8_HARD_EXCLUDED_PATHS,
    ALLOWED_A8_TEMPLATES,
    MOBILE_A8_SIZES,
    RAIL_DESKTOP_A8_SIZES,
    TEMPLATE_ROOT,
    WIDE_DESKTOP_A8_SIZES,
    get_a8_visible_limit,
    load_a8_creative_catalog,
    select_a8_creative,
    select_a8_responsive_creative,
)

EXPECTED = {
    "a8-01": ("300x250", "63cb848baaddaeb5f4be77f4a56cdec9eeb8a2f6882f46f64f2e5b179c07c8b8", "work-tools"),
    "a8-02": ("300x250", "96cc5c6909169ceb8de511b572118149dc11b37315a20460096c5562afe8ab05", "work-tools"),
    "a8-03": ("300x250", "e6d9f2692a1a94e1ed6e1939ab2598369ff12c91838cc94adf60c58abd6f016c", "work-tools"),
    "a8-04": ("300x250", "acb6adb31d5d0662fb5d14a9a8d8c8a09fe1c754022f061ebfd416e971265a29", "work-tools"),
    "a8-05": ("300x250", "035c1ed40219ac565559bfe1a9f4550bd8b86d3a51f68ea6ad2f1ce2039f93b9", "work-tools"),
    "a8-06": ("200x200", "48bb4a7d44b2ff8e38330ff2b2c702d7008b776eef93328b514794620ec2b873", "english-learning"),
    "a8-07": ("120x600", "fefa4856e948b9ef686575e41b826ab76aa2b03816e13851a60dccaf462da7b7", "english-learning"),
    "a8-08": ("300x250", "e2794258344aca9302650a76fe57e7fb62d4fbd38f60dfc30328e986ad46911e", "english-learning"),
    "a8-09": ("336x280", "dd134930cbfafa28372a083df9a88bf1ba1c57e7a2add8a17889dd4a026a8a21", "english-learning"),
    "a8-10": ("300x250", "1be4c7469e4eb87c3ce3bd34df0d3e5f7de101a720fc4feaa8018501844f816b", "english-learning"),
    "a8-11": ("250x250", "4c317fe2a1524efef12a3fbcf5c91d7109962740031dec7c73518aa7de454562", "english-learning"),
    "a8-12": ("350x240", "dd8faf5406c2973539f2bca6b285814d5d768e1d476e31f44dab9ae8e6857c7b", "english-learning"),
    "a8-13": ("728x90", "ffe92007b82477b4efa2106ed21539bd4c94654626e3aa49702e440a79d31de2", "english-learning"),
    "a8-14": ("300x250", "b1a4c7331cc98eb179a875bab4de7baeca46c127703ae61dcd97653c9ad1c004", "english-learning"),
}


def main() -> int:
    creatives = load_a8_creative_catalog()
    assert len(creatives) == 14
    assert {item["id"] for item in creatives} == set(EXPECTED)
    assert {item["template"] for item in creatives} == ALLOWED_A8_TEMPLATES
    for item in creatives:
        size, checksum, category = EXPECTED[item["id"]]
        source = (TEMPLATE_ROOT / item["template"]).read_bytes()
        text = source.decode("utf-8")
        width, height = map(int, size.split("x"))
        assert item["size"] == size and item["width"] == width and item["height"] == height
        assert item["category"] == category
        assert hashlib.sha256(source).hexdigest() == checksum == item["sha256"]
        assert text.count("https://px.a8.net/svt/ejp") == 1
        assert text.count("/0.gif?a8mat=") == 1
        assert f'width="{width}" height="{height}"' in text
        assert 'width="1" height="1"' in text and 'rel="nofollow"' in text

    start = date(2026, 1, 1)
    seen = set()
    for offset in range(90):
        day = (start + timedelta(days=offset)).isoformat()
        for sizes, placement in ((MOBILE_A8_SIZES, "global-primary-a8"), (RAIL_DESKTOP_A8_SIZES, "global-primary-a8"), (WIDE_DESKTOP_A8_SIZES, "content-lower-a8")):
            item = select_a8_creative("/guide/pdf", day, creatives, placement=placement, eligible_sizes=sizes)
            assert item and item["size"] in sizes
            seen.add(item["id"])
    assert seen == set(EXPECTED), sorted(set(EXPECTED) - seen)

    responsive = select_a8_responsive_creative("/guide/pdf", "2026-08-08", creatives)
    assert responsive and responsive["size"] in MOBILE_A8_SIZES
    assert responsive.get("desktop_variant", responsive)["size"] in RAIL_DESKTOP_A8_SIZES
    primary_ids = {
        responsive["id"],
        (responsive.get("desktop_variant") or {}).get("id"),
    } - {None}
    secondary = select_a8_responsive_creative(
        "/guide/pdf",
        "2026-08-08",
        creatives,
        placement="content-lower-a8",
        exclude_creative_ids=primary_ids,
    )
    secondary_ids = {
        secondary["id"],
        (secondary.get("desktop_variant") or {}).get("id"),
    } - {None}
    assert primary_ids.isdisjoint(secondary_ids)
    for path in A8_HARD_EXCLUDED_PATHS:
        assert select_a8_responsive_creative(path, "2026-08-08", creatives) is None

    from app import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        body = client.get("/tools/pdf").get_data(as_text=True)
        assert 'data-a8-responsive-slot' in body
        assert '<template data-a8-mobile-template' in body
        assert body.count('data-a8-responsive-slot') <= get_a8_visible_limit("/tools/pdf")
        assert re.search(r'<template data-a8-mobile-template[^>]*>[\s\S]*width="(?:200|250|300)"', body)
    print("PASS: 14 exact A8 creatives and responsive placement policy verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
