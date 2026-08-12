#!/usr/bin/env python3
"""Run the deterministic checks required before deploying Oshigoto."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PYTHON_CHECKS = (
    ("manifest", "scripts/generate_sitemap_lastmod_manifest.py", "--check"),
    ("smoke", "scripts/smoke_test.py"),
    ("deploy smoke", "scripts/smoke_test.py", "--deploy"),
    ("release candidate", "scripts/test_release_candidate.py"),
    ("AdSense preflight", "scripts/adsense_preflight.py"),
    ("A8 catalog", "scripts/test_a8_creative_catalog.py"),
    ("Amazon single recommendation", "scripts/test_amazon_single_recommendation.py"),
    ("affiliate diversity", "scripts/test_affiliate_diversity.py"),
    ("content readability", "scripts/test_content_readability.py"),
    ("tool catalog layout", "scripts/test_tool_catalog_layout.py"),
    ("tool layout consistency", "scripts/test_tool_layout_consistency.py"),
    ("guide layout consistency", "scripts/test_guide_layout_consistency.py"),
    ("public theme", "scripts/test_public_theme.py"),
    ("public visual consistency", "scripts/test_public_visual_consistency.py"),
    ("affiliate size placement", "scripts/test_affiliate_size_placement.py"),
    ("multi-user safety", "scripts/test_multi_user_safety.py"),
    ("security preflight", "scripts/security_preflight.py"),
)

NODE_CHECKS = (
    ("PDF page operations", "scripts/test_pdf_page_ops.js"),
    ("PDF shared script scope", "scripts/test_pdf_script_scope.js"),
    ("image compression", "scripts/test_image_compress.js"),
    ("image format core", "scripts/test_image_format_core.js"),
    ("QR code", "scripts/test_qr_code.js"),
    ("OCR NO-GO", "scripts/test_ocr_spike.js"),
    ("background removal NO-GO", "scripts/test_background_removal_spike.js"),
    ("CSV formula injection", "scripts/test_csv_formula_injection.js"),
)


def run(label: str, command: list[str], env: dict[str, str]) -> bool:
    print(f"\n== {label} ==", flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env)
    if result.returncode:
        print(f"FAIL: {label} (exit {result.returncode})", file=sys.stderr)
        return False
    return True


def main() -> int:
    env = os.environ.copy()
    env.setdefault("AMAZON_AFFILIATE_ENABLED", "true")
    env.setdefault("AMAZON_ASSOCIATE_TAG", "predeploy-check-22")
    env.setdefault("AFFILIATE_ENABLED", "true")
    env.setdefault("AFFILIATE_BANNERS_ENABLED", "true")
    env.setdefault("PYTHONPYCACHEPREFIX", str(Path(tempfile.gettempdir()) / "oshigoto-predeploy-pycache"))

    if not run("Python compile", [sys.executable, "-m", "compileall", "-q", "app.py", "lib", "scripts"], env):
        return 1
    if not run("application import", [sys.executable, "-c", "import app; print('app imports successfully')"], env):
        return 1

    for label, script, *args in PYTHON_CHECKS:
        if not run(label, [sys.executable, script, *args], env):
            return 1

    node = shutil.which("node")
    if not node:
        print("FAIL: Node.js is required for browser-tool contract tests.", file=sys.stderr)
        return 1
    for label, script in NODE_CHECKS:
        if not run(label, [node, script], env):
            return 1

    print("\nOK: all predeploy checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
