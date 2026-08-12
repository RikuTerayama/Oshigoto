#!/usr/bin/env python3
"""Ensure A8 native sizes are eligible only in compatible placements."""

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.a8_affiliate_catalog import (  # noqa: E402
    MOBILE_A8_SIZES,
    RAIL_DESKTOP_A8_SIZES,
    WIDE_DESKTOP_A8_SIZES,
    load_a8_creative_catalog,
    select_a8_creative,
)


def main() -> int:
    creatives = load_a8_creative_catalog()
    assert "120x600" not in MOBILE_A8_SIZES and "728x90" not in MOBILE_A8_SIZES
    assert "336x280" not in RAIL_DESKTOP_A8_SIZES and "350x240" not in RAIL_DESKTOP_A8_SIZES
    assert "120x600" in RAIL_DESKTOP_A8_SIZES and "728x90" in WIDE_DESKTOP_A8_SIZES

    reached = {"mobile": set(), "rail": set(), "wide": set()}
    start = date(2026, 1, 1)
    for offset in range(180):
        day = (start + timedelta(days=offset)).isoformat()
        for label, sizes, placement in (
            ("mobile", MOBILE_A8_SIZES, "global-primary-a8"),
            ("rail", RAIL_DESKTOP_A8_SIZES, "global-primary-a8"),
            ("wide", WIDE_DESKTOP_A8_SIZES, "content-lower-a8"),
        ):
            item = select_a8_creative("/guide/pdf", day, creatives, placement=placement, eligible_sizes=sizes)
            assert item and item["size"] in sizes
            reached[label].add(item["size"])
    assert "120x600" in reached["rail"]
    assert "728x90" in reached["wide"]
    print(f"PASS: native-size placement eligibility {reached}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
