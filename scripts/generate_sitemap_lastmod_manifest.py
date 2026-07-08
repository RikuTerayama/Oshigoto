#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sitemap lastmod マニフェスト生成スクリプト
ビルド/起動前に実行し、data/sitemap_lastmod.json を生成する。
- 優先: git log -1 --format=%cs で最終コミット日 (YYYY-MM-DD)
- fallback: ファイル mtime（本番Dockerでは同一化し得る）

CLI:
  --write : マニフェストを書き込む（デフォルト動作）
  --check : 現行 data/sitemap_lastmod.json と一致するか検査。不一致なら exit 1。
            .git が無い場合は exit 2（判定不能）
"""
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
    """app.py の _sitemap_lastmod_for_path と同一のマッピング"""
    path = (url_path or "").strip("/") or ""
    special = {
        "": "landing.html",
        "autofill": "autofill.html",
        "guide": "guide/index.html",
        "guide/complete": "guide/complete-guide.html",
        "guide/comprehensive-guide": "guide/comprehensive-guide.html",
        "blog": "blog/index.html",
        "tools": "tools/index.html",
        "sitemap.html": "sitemap.html",
        "case-studies": "case-studies.html",
        "case-study/contact-center": "case-study-contact-center.html",
        "case-study/consulting-firm": "case-study-consulting-firm.html",
        "case-study/remote-startup": "case-study-remote-startup.html",
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
    """sitemap に含まれる URL パスの一覧（固定＋PRODUCTS 相当）"""
    fixed = [
        "/", "/autofill", "/about", "/faq",
        "/glossary", "/best-practices", "/case-studies",
        "/guide", "/guide/autofill", "/guide/complete", "/guide/comprehensive-guide",
        "/guide/getting-started", "/guide/excel-format", "/guide/troubleshooting",
        "/tools", "/blog",
        "/blog/implementation-checklist", "/blog/automation-roadmap",
        "/blog/workstyle-reform-automation", "/blog/excel-attendance-limits",
        "/blog/playwright-security", "/blog/month-end-closing-hell-and-automation",
        "/blog/excel-format-mistakes-and-design", "/blog/convince-it-and-hr-for-automation",
        "/blog/playwright-jobcan-challenges-and-solutions", "/blog/jobcan-auto-input-tools-overview",
        "/blog/reduce-manual-work-checklist", "/blog/jobcan-month-end-tips",
        "/blog/jobcan-auto-input-dos-and-donts", "/blog/month-end-closing-checklist",
        "/case-study/contact-center", "/case-study/consulting-firm", "/case-study/remote-startup",
    ]
    try:
        sys.path.insert(0, REPO_ROOT)
        from lib.products_catalog import PRODUCTS
        for p in PRODUCTS:
            if p.get("status") == "available":
                if p.get("path") and p["path"] not in fixed:
                    fixed.append(p["path"])
                if p.get("guide_path") and p["guide_path"] not in fixed:
                    fixed.append(p["guide_path"])
    except Exception:
        pass
    return fixed


def get_git_date(filepath):
    """git log -1 --format=%cs で YYYY-MM-DD を取得。失敗時は None"""
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
    """ファイル mtime を YYYY-MM-DD で返す"""
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    except (OSError, TypeError):
        return None


def has_git():
    """.git が存在し git コマンドが使えるか"""
    git_dir = os.path.join(REPO_ROOT, ".git")
    if not os.path.isdir(git_dir):
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
    """マニフェスト dict を生成。use_git=False のときは mtime のみ使用。"""
    manifest = {}
    url_paths = get_sitemap_url_paths()
    seen_templates = set()

    for url_path in url_paths:
        rel = url_path_to_template_rel(url_path)
        fpath = os.path.join(TEMPLATES_DIR, rel.replace("/", os.sep))
        if rel in seen_templates:
            continue
        seen_templates.add(rel)
        if not os.path.isfile(fpath):
            continue
        date_str = get_git_date(fpath) if use_git else None
        if not date_str:
            date_str = get_mtime_date(fpath)
        if date_str:
            manifest[rel] = date_str
    return dict(sorted(manifest.items()))


def manifest_to_json(manifest):
    """安定した JSON 文字列（キー順）"""
    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)


def run_check():
    """--check: 生成結果と現行ファイルを比較。不一致なら exit 1。git 無い場合は exit 2。"""
    if not has_git():
        print(
            "ERROR: .git not found or git unavailable. --check requires git for accurate comparison.",
            file=sys.stderr,
        )
        print("Run: python scripts/generate_sitemap_lastmod_manifest.py --write", file=sys.stderr)
        return 2
    expected = generate_manifest(use_git=True)
    expected_json = manifest_to_json(expected)
    try:
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            current = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: Cannot read {OUTPUT_PATH}: {e}", file=sys.stderr)
        print("Run: python scripts/generate_sitemap_lastmod_manifest.py --write", file=sys.stderr)
        return 1
    current_sorted = dict(sorted(current.items()))
    current_json = manifest_to_json(current_sorted)
    if expected_json != current_json:
        print("ERROR: data/sitemap_lastmod.json is outdated or differs from expected.", file=sys.stderr)
        print("Run: python scripts/generate_sitemap_lastmod_manifest.py --write", file=sys.stderr)
        print("Then commit the updated file.", file=sys.stderr)
        return 1
    return 0


def run_write():
    """--write: マニフェストをファイルに書き込む"""
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    manifest = generate_manifest(use_git=has_git())
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(manifest_to_json(manifest) + "\n")
    print(f"Generated {OUTPUT_PATH} with {len(manifest)} entries", file=sys.stderr)
    return 0


def main():
    parser = argparse.ArgumentParser(description="sitemap lastmod manifest generator")
    parser.add_argument("--check", action="store_true", help="Check manifest freshness, exit 1 if stale")
    parser.add_argument("--write", action="store_true", help="Write manifest to data/sitemap_lastmod.json")
    args = parser.parse_args()

    if args.check:
        return run_check()
    return run_write()


if __name__ == "__main__":
    sys.exit(main())
