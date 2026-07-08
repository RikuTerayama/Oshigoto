#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
デプロイ前ガード: manifest の鮮度チェックと preflight を順に実行する。
失敗時は非ゼロで終了。成功時は短いメッセージを出力。
"""
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd, env=None):
    """サブプロセス実行。戻り値が非ゼロなら (False, code)、ゼロなら (True, 0)"""
    env = env or os.environ.copy()
    result = subprocess.run(cmd, cwd=REPO_ROOT, env=env)
    return (result.returncode == 0, result.returncode)


def main():
    ok, code = run([sys.executable, "scripts/generate_sitemap_lastmod_manifest.py", "--check"])
    if not ok:
        if code == 2:
            print("FAIL: manifest check skipped (git unavailable). Run --write locally and commit.", file=sys.stderr)
        else:
            print("FAIL: manifest stale. Run: python scripts/generate_sitemap_lastmod_manifest.py --write", file=sys.stderr)
        return code if code != 0 else 1

    ok, code = run([sys.executable, "scripts/adsense_preflight.py"])
    if not ok:
        print("FAIL: adsense_preflight.py failed.", file=sys.stderr)
        return code if code != 0 else 1

    print("OK: manifest up-to-date, preflight passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
