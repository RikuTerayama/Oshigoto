#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 5: レート制限の検証。
- /upload: 11回 POST で 11回目に 429 + Retry-After
- /status/<id>: 121回 GET で 121回目に 429
- /healthz: 連打でも 200（除外確認）
- /api/seo/crawl-urls: 既存の 1/min 制限のみ（当スクリプトのレート制限では除外されていることを確認）

使用: python scripts/verify_rate_limit.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()
    failed = []

    # 1) /upload: 11回 POST（空でOK）。11回目に 429
    for i in range(11):
        r = client.post('/upload', data={}, content_type='multipart/form-data')
        if i < 10:
            if r.status_code == 429:
                failed.append(f"upload: request {i+1} got 429 (expected only 11th)")
                break
        else:
            if r.status_code != 429:
                failed.append(f"upload: request 11 got {r.status_code} expected 429")
            elif 'Retry-After' not in r.headers:
                failed.append("upload: 429 response missing Retry-After header")
    print("upload: 11 POSTs -> 11th 429 with Retry-After: OK" if not any('upload' in f for f in failed) else "upload: FAIL")

    # 2) /status/<job_id>: 121回 GET。121回目に 429
    for i in range(121):
        r = client.get('/status/fake-job-id-for-rate-limit-test')
        if i < 120:
            if r.status_code == 429:
                failed.append(f"status: request {i+1} got 429 (expected only 121st)")
                break
        else:
            if r.status_code != 429:
                failed.append(f"status: request 121 got {r.status_code} expected 429")
            elif 'Retry-After' not in r.headers:
                failed.append("status: 429 response missing Retry-After header")
    print("status: 121 GETs -> 121st 429 with Retry-After: OK" if not any('status' in f for f in failed) else "status: FAIL")

    # 3) /healthz: 50回 GET、すべて 200
    for i in range(50):
        r = client.get('/healthz')
        if r.status_code != 200:
            failed.append(f"healthz: request {i+1} got {r.status_code}")
            break
    print("healthz: 50 GETs -> all 200: OK" if not any('healthz' in f for f in failed) else "healthz: FAIL")

    # 4) /api/seo/crawl-urls: 1回目は 429 でない（当スクリプトの api 制限は 60/min なので 1 回は通る）。2回目は既存の 1/min で 429
    r1 = client.post(
        '/api/seo/crawl-urls',
        json={'start_url': 'https://example.com'},
        content_type='application/json'
    )
    r2 = client.post(
        '/api/seo/crawl-urls',
        json={'start_url': 'https://example.com'},
        content_type='application/json'
    )
    if r1.status_code == 429:
        failed.append("crawl-urls: 1st request got 429 (our api limiter should not apply to crawl-urls)")
    if r2.status_code != 429:
        failed.append(f"crawl-urls: 2nd request got {r2.status_code} expected 429 (existing 1/min limit)")
    print("crawl-urls: 1st not 429, 2nd 429 (existing limit): OK" if not any('crawl' in f for f in failed) else "crawl-urls: FAIL")

    if failed:
        for f in failed:
            print(f"FAIL: {f}")
        return 1
    print("All rate limit checks passed.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
