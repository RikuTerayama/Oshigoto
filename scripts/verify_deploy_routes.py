#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本番デプロイ前ルート検証: curl 風の証跡ログを出力する。
- テストクライアント使用（サーバ不要）: デフォルト
- 実サーバ使用: --live BASE_URL を指定

証跡: ブランチ・rev・Python版・各URLの HTTP status と Location を標準出力とオプションでファイルに出力。
使用例:
  python scripts/verify_deploy_routes.py
  python scripts/verify_deploy_routes.py --output evidence.log
  python scripts/verify_deploy_routes.py --live http://127.0.0.1:5000
"""
import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 検証対象URLパス（curl -I で確認するもの）
ROUTE_CHECKS = [
    ('/tools/seo', 200, None),
    ('/tools/csv', 200, None),
    ('/guide/csv', 200, None),
    ('/tools/minutes', 301, '/tools'),
    ('/guide/minutes', 301, '/guide'),
    ('/tools/pdf/', 301, '/tools/pdf'),
]


def get_env_evidence():
    """証跡: ブランチ・rev・Python版"""
    lines = []
    try:
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            text=True,
        ).strip()
        lines.append(f"git branch: {branch}")
    except Exception as e:
        lines.append(f"git branch: (error) {e}")
    try:
        rev = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            text=True,
        ).strip()
        lines.append(f"git rev: {rev}")
    except Exception as e:
        lines.append(f"git rev: (error) {e}")
    lines.append(f"python: {sys.version.split()[0]}")
    return "\n".join(lines)


def run_with_test_client(base_url='http://127.0.0.1:5000'):
    """Flask test client で各パスにリクエストし、curl 風の出力を返す"""
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()
    out_lines = []
    for path, expect_status, expect_location_suffix in ROUTE_CHECKS:
        resp = client.get(path, follow_redirects=False)
        status = resp.status_code
        loc = (resp.headers.get('Location') or '').strip()
        out_lines.append(f"$ curl -I {base_url}{path}")
        out_lines.append(f"HTTP/1.1 {status} {'OK' if status == 200 else 'REDIRECT' if 300 <= status < 400 else ''}")
        if loc:
            out_lines.append(f"Location: {loc}")
        out_lines.append("")
        # 簡易判定
        if status != expect_status:
            out_lines.append(f"  -> FAIL expected {expect_status}")
        elif expect_location_suffix and expect_location_suffix not in loc:
            out_lines.append(f"  -> FAIL expected Location containing {expect_location_suffix}")
        else:
            out_lines.append(f"  -> OK")
        out_lines.append("")
    return "\n".join(out_lines)


def run_live(base_url):
    """実サーバに GET し、curl 風の出力を返す（HEAD 相当で status + headers のみ）"""
    try:
        import urllib.request
        import urllib.error
    except ImportError:
        urllib = None
    try:
        import requests
    except ImportError:
        requests = None

    if requests is not None:
        def _get(u):
            r = requests.get(u, allow_redirects=False)
            return r.status_code, dict(r.headers)
    elif urllib is not None:
        def _get(u):
            req = urllib.request.Request(u, method='GET')
            try:
                with urllib.request.urlopen(req) as r:
                    return r.status, dict(r.headers)
            except urllib.error.HTTPError as e:
                return e.code, dict(e.headers) if e.headers else {}
    else:
        def _get(u):
            raise RuntimeError("need requests or urllib")

    out_lines = []
    for path, expect_status, expect_location_suffix in ROUTE_CHECKS:
        url = base_url.rstrip('/') + path
        out_lines.append(f"$ curl -I {url}")
        try:
            status, headers = _get(url)
        except Exception as e:
            out_lines.append(f"  (error) {e}")
            out_lines.append("")
            continue
        loc = (headers.get('Location') or headers.get('location') or '').strip()
        out_lines.append(f"HTTP/1.1 {status} {'OK' if status == 200 else 'REDIRECT' if 300 <= status < 400 else ''}")
        if loc:
            out_lines.append(f"Location: {loc}")
        out_lines.append("")
        if status != expect_status:
            out_lines.append(f"  -> FAIL expected {expect_status}")
        elif expect_location_suffix and expect_location_suffix not in loc:
            out_lines.append(f"  -> FAIL expected Location containing {expect_location_suffix}")
        else:
            out_lines.append(f"  -> OK")
        out_lines.append("")
    return "\n".join(out_lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Deploy route verification with evidence log')
    parser.add_argument('--live', metavar='BASE_URL', default=None, help='Use live server (e.g. http://127.0.0.1:5000)')
    parser.add_argument('--output', '-o', metavar='FILE', default=None, help='Append evidence to FILE')
    args = parser.parse_args()

    base_url = args.live or 'http://127.0.0.1:5000'
    evidence = []
    evidence.append("=== deploy route verification evidence ===")
    evidence.append(get_env_evidence())
    evidence.append("")
    if args.live:
        evidence.append("(live server)")
        evidence.append(run_live(base_url))
    else:
        evidence.append("(Flask test client, no server)")
        evidence.append(run_with_test_client(base_url))
    evidence.append("=== end ===")
    text = "\n".join(evidence)
    print(text)
    if args.output:
        with open(args.output, 'a', encoding='utf-8') as f:
            f.write(text + "\n")
        print(f"(appended to {args.output})", file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
