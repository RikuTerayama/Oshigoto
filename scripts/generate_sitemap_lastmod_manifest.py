#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate or check data/sitemap_lastmod.json for public sitemap dates."""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(REPO_ROOT, "templates")
OUTPUT_PATH = os.path.join(REPO_ROOT, "data", "sitemap_lastmod.json")


def url_path_to_template_rel(url_path):
    path = (url_path or "").strip("/")
    special = {
        "": "landing.html",
        "guide": "guide/index.html",
        "blog": "blog/index.html",
        "tools": "tools/index.html",
        "sitemap.html": "sitemap.html",
    }
    if path in special:
        return special[path]
    if path.startswith("guide/"):
        return "guide/" + path.split("/", 1)[1] + ".html"
    if path.startswith("blog/"):
        return "blog/" + path.split("/", 1)[1] + ".html"
    if path.startswith("tools/"):
        return "tools/" + path.split("/", 1)[1] + ".html"
    return (path + ".html") if path else "landing.html"


def get_sitemap_url_paths():
    fixed = [
        "/", "/about", "/privacy", "/terms", "/contact", "/faq", "/glossary",
        "/guide", "/guide/csv", "/guide/image-batch", "/guide/image-cleanup", "/guide/pdf", "/guide/seo",
        "/tools", "/blog", "/blog/excel-format-mistakes-and-design",
    ]
    try:
        sys.path.insert(0, REPO_ROOT)
        from lib.products_catalog import PRODUCTS
        for product in PRODUCTS:
            if product.get("status") == "available":
                if product.get("path") and product["path"] not in fixed:
                    fixed.append(product["path"])
                if product.get("guide_path") and product["guide_path"] not in fixed:
                    fixed.append(product["guide_path"])
    except Exception:
        pass
    return fixed


def get_git_date(filepath):
    try:
        relpath = os.path.relpath(filepath, REPO_ROOT).replace(os.sep, "/")
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", relpath],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()[:10]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def get_mtime_date(filepath):
    try:
        return datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d")
    except (OSError, TypeError):
        return None


def has_git():
    if not os.path.isdir(os.path.join(REPO_ROOT, ".git")):
        return False
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=3,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def generate_manifest(use_git=True):
    manifest = {}
    seen_templates = set()
    for url_path in get_sitemap_url_paths():
        rel = url_path_to_template_rel(url_path)
        if rel in seen_templates:
            continue
        seen_templates.add(rel)
        fpath = os.path.join(TEMPLATES_DIR, rel.replace("/", os.sep))
        if not os.path.isfile(fpath):
            continue
        date_str = get_git_date(fpath) if use_git else None
        if not date_str:
            date_str = get_mtime_date(fpath)
        if date_str:
            manifest[rel] = date_str
    return dict(sorted(manifest.items()))


def manifest_to_json(manifest):
    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)


def run_check():
    if not has_git():
        print("ERROR: .git not found or git unavailable. --check requires git.", file=sys.stderr)
        print("Run: python scripts/generate_sitemap_lastmod_manifest.py --write", file=sys.stderr)
        return 2
    expected_json = manifest_to_json(generate_manifest(use_git=True))
    try:
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            current = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: Cannot read {OUTPUT_PATH}: {exc}", file=sys.stderr)
        print("Run: python scripts/generate_sitemap_lastmod_manifest.py --write", file=sys.stderr)
        return 1
    current_json = manifest_to_json(dict(sorted(current.items())))
    if expected_json != current_json:
        print("ERROR: data/sitemap_lastmod.json is outdated or differs from expected.", file=sys.stderr)
        print("Run: python scripts/generate_sitemap_lastmod_manifest.py --write", file=sys.stderr)
        print("Then commit the updated file.", file=sys.stderr)
        return 1
    return 0


def run_write():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    manifest = generate_manifest(use_git=has_git())
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(manifest_to_json(manifest) + "\n")
    print(f"Generated {OUTPUT_PATH} with {len(manifest)} entries", file=sys.stderr)
    return 0


def main():
    parser = argparse.ArgumentParser(description="sitemap lastmod manifest generator")
    parser.add_argument("--check", action="store_true", help="Check manifest freshness")
    parser.add_argument("--write", action="store_true", help="Write manifest")
    args = parser.parse_args()
    if args.check:
        return run_check()
    return run_write()


if __name__ == "__main__":
    sys.exit(main())
