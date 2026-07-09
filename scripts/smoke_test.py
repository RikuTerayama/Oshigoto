#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
スモークテスト: /, /autofill, /about, /tools を複数回アクセスし、
全て 200 かつエラーページ表示がないことを確認する。
使用例: python scripts/smoke_test.py
        BASE_URL=http://localhost:5000 python scripts/smoke_test.py
"""
import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_with_test_client():
    """Flask test client で実行（サーバー不要）"""
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()
    expected = {
        '/': 200,
        '/autofill': 301,
        '/about': 200,
        '/tools': 200,
        '/tools/pdf': 200,
        '/tools/csv': 200,
        '/tools/image-batch': 200,
        '/tools/image-cleanup': 200,
        '/tools/seo': 200,
        '/healthz': 200,
    }
    error_phrase = '⚠️ エラーが発生しました'
    n_per_path = 10
    failed = []

    for path, expected_status in expected.items():
        for i in range(n_per_path):
            response = client.get(path, follow_redirects=False)
            body = response.data.decode('utf-8')
            if response.status_code != expected_status:
                failed.append(f"path={path} run={i+1} expected={expected_status} status={response.status_code}")
            elif path != '/healthz' and error_phrase in body:
                failed.append(f"path={path} run={i+1} body contains error page")

    if failed:
        for f in failed:
            print(f"FAIL: {f}")
        print(f"Total failures: {len(failed)}")
        return 1
    print(f"OK: {len(expected)} paths x {n_per_path} requests = expected statuses, no error page")
    return 0

def run_deploy_verification():
    """
    本番デプロイ前検証: minutes 301 / CSV・SEO ツール 200 / 末尾スラッシュ 301 を確認。
    使用例: python scripts/smoke_test.py --deploy
    """
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()
    error_phrase = '⚠️ エラーが発生しました'
    failed = []

    # 200 期待: エラー表示なし
    for path in ['/tools/seo', '/tools/csv', '/guide/csv']:
        resp = client.get(path, follow_redirects=False)
        body = resp.data.decode('utf-8')
        if resp.status_code != 200:
            failed.append(f"path={path} expected 200 got {resp.status_code}")
        elif error_phrase in body:
            failed.append(f"path={path} body contains error page")

    # 301 期待: /tools/minutes -> /tools, /guide/minutes -> /guide (Location はパスまたは絶対URL)
    for path, expect_suffix in [
        ('/tools/minutes', '/tools'),
        ('/guide/minutes', '/guide'),
        ('/autofill', '/tools'),
    ]:
        resp = client.get(path, follow_redirects=False)
        loc = (resp.headers.get('Location') or '').strip()
        if resp.status_code != 301:
            failed.append(f"path={path} expected 301 got {resp.status_code}")
        elif not loc.endswith(expect_suffix) and expect_suffix not in loc:
            failed.append(f"path={path} expected Location...{expect_suffix} got {loc}")

    # 末尾スラッシュ: /tools/pdf/ -> 301 -> /tools/pdf
    resp = client.get('/tools/pdf/', follow_redirects=False)
    loc = (resp.headers.get('Location') or '').strip()
    if resp.status_code != 301:
        failed.append(f"path=/tools/pdf/ expected 301 got {resp.status_code}")
    elif '/tools/pdf' not in loc:
        failed.append(f"path=/tools/pdf/ expected Location .../tools/pdf got {loc}")

    if failed:
        for f in failed:
            print(f"FAIL: {f}")
        print(f"Total: {len(failed)}")
        return 1
    print("OK: deploy verification (tools/seo, tools/csv, guide/csv=200; minutes 301; /tools/pdf/ 301)")
    return 0


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--deploy', action='store_true', help='Run deploy verification (301/200 checks)')
    args = parser.parse_args()
    if args.deploy:
        sys.exit(run_deploy_verification())
    sys.exit(run_with_test_client())
