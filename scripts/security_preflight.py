#!/usr/bin/env python3
"""Deterministic defense-in-depth checks for Oshigoto."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def expect_safe_http_error(call, code: str) -> None:
    from lib.safe_http import SafeHttpError

    try:
        call()
    except SafeHttpError as exc:
        require(exc.code == code, f"expected {code}, got {exc.code}")
        return
    raise AssertionError(f"expected SafeHttpError({code})")


def check_http_boundary() -> None:
    import app as app_module

    app = app_module.app
    app.config.update(TESTING=True)
    client = app.test_client()

    require(client.get('/', headers={'Host': 'evil.example'}).status_code == 400, 'invalid Host must be rejected')
    root = client.get('/', base_url='https://oshigoto.onrender.com')
    require(root.status_code == 200, 'public Host must be accepted')
    headers = root.headers
    require(headers.get('Strict-Transport-Security') == 'max-age=31536000', 'HTTPS must use HSTS')
    require(headers.get('X-Content-Type-Options') == 'nosniff', 'nosniff missing')
    require(headers.get('X-Permitted-Cross-Domain-Policies') == 'none', 'cross-domain policy missing')
    require(headers.get('X-XSS-Protection') == '0', 'legacy XSS filter must be disabled')
    require(headers.get('Referrer-Policy'), 'Referrer-Policy missing')
    require(headers.get('Permissions-Policy'), 'Permissions-Policy missing')
    require(headers.get('X-Frame-Options') == 'SAMEORIGIN', 'frame protection missing')
    csp = headers.get('Content-Security-Policy', '')
    require(all(item in csp for item in ("object-src 'none'", "base-uri 'self'", "frame-ancestors 'self'")), 'enforced CSP baseline missing')
    require(headers.get('Content-Security-Policy-Report-Only'), 'CSP report-only policy missing')
    require(headers.get('Access-Control-Allow-Origin') != '*', 'wildcard CORS is forbidden')
    require(app.config['SESSION_COOKIE_SECURE'] is True, 'secure session cookie default missing')
    require(app.config['SESSION_COOKIE_HTTPONLY'] is True, 'HttpOnly session cookie default missing')
    require(app.config['SESSION_COOKIE_SAMESITE'] == 'Lax', 'SameSite session cookie default missing')

    for method in ('TRACE', 'TRACK', 'CONNECT'):
        require(client.open('/', method=method).status_code == 405, f'{method} must be rejected')

    cross_site = client.post(
        '/api/seo/crawl-urls', json={'start_url': 'https://example.com'},
        headers={'Sec-Fetch-Site': 'cross-site'},
    )
    require(cross_site.status_code == 403, 'cross-site API POST must be rejected')
    bad_origin = client.post(
        '/api/seo/crawl-urls', json={'start_url': 'https://example.com'},
        headers={'Origin': 'https://evil.example'},
    )
    require(bad_origin.status_code == 403, 'foreign Origin must be rejected')
    wrong_json = client.post('/api/seo/crawl-urls', data='{}', content_type='text/plain')
    require(wrong_json.status_code == 415, 'SEO API must require JSON')
    wrong_pdf = client.post('/api/pdf/lock', json={})
    require(wrong_pdf.status_code == 415, 'PDF API must require multipart')
    require('no-store' in wrong_pdf.headers.get('Cache-Control', ''), 'API errors must not be cached')

    malicious = client.post(
        '/api/pdf/lock',
        data={'file': (io.BytesIO(b'%PDF-1.4\n'), '../evil.pdf'), 'password': 'test'},
        content_type='multipart/form-data',
    )
    require(malicious.status_code == 400 and malicious.get_json()['error_code'] == 'invalid_filename', 'path filename must be rejected')
    require(
        app_module._validate_pdf_upload_metadata(SimpleNamespace(filename='evil\r\n.pdf', mimetype='application/pdf')) == 'invalid_filename',
        'CRLF filename must be rejected',
    )

    oversized = client.post(
        '/api/pdf/lock',
        data=b'',
        content_type='multipart/form-data; boundary=security-test',
        environ_overrides={'CONTENT_LENGTH': str(app_module.MAX_TOTAL_UPLOAD_BYTES + 1)},
    )
    require(oversized.status_code == 413, 'oversized upload must be rejected before parsing')

    too_many = {f'part-{index}': 'x' for index in range(26)}
    too_many['file'] = (io.BytesIO(b'%PDF-1.4\n'), 'safe.pdf')
    too_many['password'] = 'test'
    require(
        client.post('/api/pdf/lock', data=too_many, content_type='multipart/form-data').status_code == 413,
        'too many multipart parts must be rejected',
    )

    require(app_module.MAX_TOTAL_UPLOAD_MB <= 100, 'upload hard ceiling expanded')
    require(app_module.MAX_FILES_PER_REQUEST <= 25, 'file-count hard ceiling expanded')
    require(app_module.MAX_OUTPUT_SIZE_MB <= 150, 'output hard ceiling expanded')
    require(app_module.MAX_ACTIVE_PDF_JOBS <= 2, 'PDF concurrency hard ceiling expanded')
    require(app_module._RATE_LIMITS['seo_crawl'] <= 8, 'SEO rate ceiling expanded')
    require(app_module._RATE_LIMITS['pdf'] <= 30, 'PDF rate ceiling expanded')
    require(app_module._RATE_LIMITS['api'] <= 120, 'API rate ceiling expanded')
    require(app.config['MAX_FORM_PARTS'] <= 25, 'multipart part ceiling expanded')
    require(app.config['MAX_FORM_MEMORY_SIZE'] <= 512 * 1024, 'form memory ceiling expanded')

    missing = client.post('/api/pdf/lock', data={}, content_type='multipart/form-data')
    require(missing.status_code == 400, 'missing PDF input must fail safely')
    require('no-store' in missing.headers.get('Cache-Control', ''), 'PDF error must be no-store')
    require(client.get('/api/pdf/unlock').status_code == 404, 'PDF unlock route must remain absent')
    not_found = client.get('/definitely-not-a-route')
    require(not_found.status_code == 404, '404 status changed')
    require(b'Traceback' not in not_found.data and b'File "' not in not_found.data, '404 leaks internals')

    app_module._rate_limiter._data.clear()
    rate_responses = [
        client.post('/api/seo/crawl-urls', json={'start_url': 'http://127.0.0.1'})
        for _ in range(app_module._RATE_LIMITS['seo_crawl'] + 1)
    ]
    limited = rate_responses[-1]
    require(limited.status_code == 429, 'SEO endpoint rate limit must reject excess requests')
    require(limited.headers.get('Retry-After'), 'rate limit must include Retry-After')
    app_module._rate_limiter._data.clear()


def check_ssrf() -> None:
    from lib.safe_http import SafeHttpClient, SafeHttpResponse, resolve_target

    rejected = {
        'http://127.0.0.1': 'non_public_address',
        'http://localhost': 'host_not_allowed',
        'http://[::1]': 'non_public_address',
        'http://[::ffff:169.254.169.254]': 'non_public_address',
        'http://169.254.169.254': 'non_public_address',
        'http://10.0.0.1': 'non_public_address',
        'http://172.16.0.1': 'non_public_address',
        'http://192.168.0.1': 'non_public_address',
        'http://0.0.0.0': 'non_public_address',
        'file:///etc/passwd': 'scheme_not_allowed',
        'data:text/plain,test': 'scheme_not_allowed',
        'http://user:pass@example.com': 'userinfo_not_allowed',
        'http://example.com:22': 'port_not_allowed',
    }
    for url, code in rejected.items():
        expect_safe_http_error(lambda url=url: resolve_target(url), code)

    resolver_calls = []

    def public_resolver(host, port):
        resolver_calls.append((host, port))
        return ['93.184.216.34']

    pinned_targets = []

    def ok_transport(target, connect_timeout, read_timeout, max_bytes):
        pinned_targets.append(target)
        return SafeHttpResponse(200, {'content-type': 'text/html'}, b'<html></html>', target.url)

    response = SafeHttpClient(resolver=public_resolver, transport=ok_transport).get('https://example.com/test')
    require(response.status == 200, 'public HTTPS URL must be accepted')
    require(len(resolver_calls) == 1, 'hostname must resolve once per hop')
    require(pinned_targets[0].addresses == ('93.184.216.34',), 'transport must receive validated pinned IP')
    require(pinned_targets[0].host_header == 'example.com', 'Host header hostname must be preserved')

    def redirect_private(target, connect_timeout, read_timeout, max_bytes):
        return SafeHttpResponse(302, {'location': 'http://127.0.0.1/private'}, b'', target.url)

    expect_safe_http_error(
        lambda: SafeHttpClient(resolver=public_resolver, transport=redirect_private).get('https://example.com'),
        'non_public_address',
    )

    rebind_count = 0

    def rebinding_resolver(host, port):
        nonlocal rebind_count
        rebind_count += 1
        return ['93.184.216.34'] if rebind_count == 1 else ['127.0.0.1']

    def one_redirect(target, connect_timeout, read_timeout, max_bytes):
        return SafeHttpResponse(302, {'location': '/next'}, b'', target.url)

    expect_safe_http_error(
        lambda: SafeHttpClient(resolver=rebinding_resolver, transport=one_redirect).get('https://example.com'),
        'non_public_address',
    )
    require(rebind_count == 2, 'redirect target must be resolved and validated independently')

    def oversized(target, connect_timeout, read_timeout, max_bytes):
        return SafeHttpResponse(200, {'content-type': 'text/html'}, b'x' * (max_bytes + 1), target.url)

    expect_safe_http_error(
        lambda: SafeHttpClient(resolver=public_resolver, transport=oversized).get('https://example.com', max_bytes=16),
        'response_too_large',
    )

    expect_safe_http_error(
        lambda: SafeHttpClient(resolver=public_resolver, transport=one_redirect).get('https://example.com', max_redirects=3),
        'too_many_redirects',
    )

    source = (ROOT / 'lib' / 'safe_http.py').read_text(encoding='utf-8')
    require('requests.' not in source, 'safe HTTP client must not use environment-aware requests')
    require('"Cookie"' not in source and '"Authorization"' not in source, 'outbound crawler must not send credentials')


def check_supply_chain() -> None:
    manifest = json.loads((ROOT / 'data' / 'vendor_integrity.json').read_text(encoding='utf-8'))
    require(manifest.get('schema_version') == 1, 'vendor manifest schema missing')
    require(len(manifest.get('vendors', [])) >= 8, 'critical vendor entries missing')
    for vendor in manifest['vendors']:
        bundle = ROOT / vendor['path']
        license_path = ROOT / vendor['license']
        require(bundle.is_file(), f"missing vendor file: {vendor['path']}")
        require(license_path.is_file(), f"missing vendor license: {vendor['license']}")
        digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
        require(digest == vendor['sha256'], f"vendor checksum mismatch: {vendor['name']}")

    template_text = '\n'.join(path.read_text(encoding='utf-8') for path in (ROOT / 'templates').rglob('*.html'))
    critical_hosts = ('cdnjs.cloudflare.com/ajax/libs/jszip', 'cdnjs.cloudflare.com/ajax/libs/pdf', 'cdn.jsdelivr.net/npm/encoding-japanese', 'cdn.sheetjs.com')
    require(not any(host in template_text for host in critical_hosts), 'critical browser library still uses CDN')

    requirements = (ROOT / 'requirements.txt').read_text(encoding='utf-8')
    require('>=' not in requirements and '~=' not in requirements, 'production requirements must be exact pins')
    lock = (ROOT / 'requirements.lock.txt').read_text(encoding='utf-8')
    require('--hash=sha256:' in lock, 'hashed dependency lock missing')
    dockerfile = (ROOT / 'Dockerfile').read_text(encoding='utf-8')
    require(re.search(r'^FROM python:3\.11\.15-slim-bookworm@sha256:[0-9a-f]{64}$', dockerfile, re.M), 'Docker base digest missing')
    require('USER 10001:10001' in dockerfile, 'Docker runtime must be non-root')
    require('--require-hashes --only-binary=:all:' in dockerfile, 'Docker must enforce locked wheels')
    require(all(flag in dockerfile for flag in ('--limit-request-line', '--limit-request-fields', '--limit-request-field_size')), 'Gunicorn limits missing')

    workflows = list((ROOT / '.github' / 'workflows').glob('*.yml'))
    require(workflows, 'workflows missing')
    uses_pattern = re.compile(r'^\s*uses:\s*[^@\s]+@([^\s#]+)', re.M)
    for workflow in workflows:
        text = workflow.read_text(encoding='utf-8')
        require('permissions:' in text and 'contents: read' in text, f'least-privilege permissions missing: {workflow.name}')
        for ref in uses_pattern.findall(text):
            require(re.fullmatch(r'[0-9a-f]{40}', ref) is not None, f'action not SHA pinned: {workflow.name} {ref}')

    require((ROOT / '.github' / 'dependabot.yml').is_file(), 'Dependabot config missing')
    require((ROOT / '.github' / 'workflows' / 'codeql.yml').is_file(), 'CodeQL workflow missing')
    require((ROOT / '.github' / 'workflows' / 'security.yml').is_file(), 'security workflow missing')
    require((ROOT / 'SECURITY.md').is_file(), 'SECURITY.md missing')
    require((ROOT / '.dockerignore').is_file(), '.dockerignore missing')


def check_no_go_and_secrets() -> None:
    from app import app

    client = app.test_client()
    for path in (
        '/tools/ocr', '/guide/ocr', '/api/ocr', '/_internal/ocr-spike',
        '/tools/background-removal', '/guide/background-removal',
        '/api/background-removal', '/_internal/background-removal-spike',
        '/api/pdf/unlock',
    ):
        require(client.get(path).status_code == 404, f'NO-GO route exposed: {path}')

    secret_patterns = {
        'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
        'AWS access key': re.compile(r'AKIA[0-9A-Z]{16}'),
        'GitHub token': re.compile(r'gh[pousr]_[A-Za-z0-9_]{30,}'),
    }
    excluded_roots = {'.git', '.claude', 'static'}
    for path in ROOT.rglob('*'):
        if not path.is_file() or any(part in excluded_roots for part in path.relative_to(ROOT).parts):
            continue
        if path.stat().st_size > 2 * 1024 * 1024:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in secret_patterns.items():
            require(pattern.search(text) is None, f'possible tracked {label}: {path.relative_to(ROOT)}')

    source = '\n'.join((ROOT / path).read_text(encoding='utf-8') for path in ('app.py', 'render.yaml', 'lib/amazon_creators.py'))
    forbidden_tags = ('jobcan' + 'auto-22', 'ielts' + 'consult-22')
    require(not any(tag in source for tag in forbidden_tags), 'Amazon associate tag must not be hard-coded')


def main() -> int:
    checks = (
        ('HTTP boundary', check_http_boundary),
        ('SSRF', check_ssrf),
        ('supply chain', check_supply_chain),
        ('NO-GO and secrets', check_no_go_and_secrets),
    )
    for label, check in checks:
        check()
        print(f'PASS: {label}')
    print('PASS: security preflight')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
