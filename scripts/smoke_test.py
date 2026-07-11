#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke tests for the public Oshigoto routes."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _looks_like_error_page(body):
    lowered = body.lower()
    return (
        '<title>error' in lowered
        or '<h1>error' in lowered
        or 'internal server error' in lowered
        or 'traceback (most recent call last)' in lowered
    )


def run_with_test_client():
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
        '/guide': 200,
        '/blog': 200,
        '/glossary': 200,
        '/healthz': 200,
    }
    failed = []
    for path, expected_status in expected.items():
        for i in range(10):
            response = client.get(path, follow_redirects=False)
            body = response.data.decode('utf-8', errors='replace')
            if response.status_code != expected_status:
                failed.append(f"path={path} run={i+1} expected={expected_status} status={response.status_code}")
            elif path != '/healthz' and _looks_like_error_page(body):
                failed.append(f"path={path} run={i+1} body contains error page")
    if failed:
        for item in failed:
            print(f"FAIL: {item}")
        print(f"Total failures: {len(failed)}")
        return 1
    print(f"OK: {len(expected)} paths x 10 requests = expected statuses, no error page")
    return 0


def run_deploy_verification():
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()
    failed = []
    for path in ['/', '/tools', '/tools/seo', '/tools/csv', '/tools/pdf', '/tools/image-batch', '/tools/image-cleanup', '/guide/csv']:
        resp = client.get(path, follow_redirects=False)
        body = resp.data.decode('utf-8', errors='replace')
        if resp.status_code != 200:
            failed.append(f"path={path} expected 200 got {resp.status_code}")
        elif _looks_like_error_page(body):
            failed.append(f"path={path} body contains error page")
    resp = client.get('/autofill', follow_redirects=False)
    loc = (resp.headers.get('Location') or '').strip()
    if resp.status_code != 301 or not loc.endswith('/tools'):
        failed.append(f"path=/autofill expected 301 to /tools got {resp.status_code} {loc}")
    resp = client.get('/api/pdf/unlock', follow_redirects=False)
    if resp.status_code != 404:
        failed.append(f"path=/api/pdf/unlock expected 404 got {resp.status_code}")
    resp = client.get('/tools/pdf/', follow_redirects=False)
    loc = (resp.headers.get('Location') or '').strip()
    if resp.status_code != 301 or '/tools/pdf' not in loc:
        failed.append(f"path=/tools/pdf/ expected 301 to /tools/pdf got {resp.status_code} {loc}")
    if failed:
        for item in failed:
            print(f"FAIL: {item}")
        print(f"Total: {len(failed)}")
        return 1
    print("OK: deploy verification public routes, /autofill 301, /api/pdf/unlock 404")
    return 0


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--deploy', action='store_true')
    args = parser.parse_args()
    sys.exit(run_deploy_verification() if args.deploy else run_with_test_client())
