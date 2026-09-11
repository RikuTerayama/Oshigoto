#!/usr/bin/env python3
"""Validate explicitly changed live URLs; POST only with --submit. Never run in deploy."""

import argparse
import os
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.indexnow import ENDPOINT, KEY_PATH, build_payload, public_origin, valid_key
from lib.robots_policy import parse_policy


def fetch(session, url):
    response = session.get(url, timeout=15, allow_redirects=False)
    if response.status_code != 200:
        raise ValueError(f'Expected HTTP 200 without redirect: {url} ({response.status_code})')
    return response


def prepare(session, urls, key, base_url):
    origin = public_origin(base_url)
    if not valid_key(key):
        raise ValueError('Set a valid INDEXNOW_KEY before validation')
    sitemap = ET.fromstring(fetch(session, origin + '/sitemap.xml').content)
    allowed = {node.text for node in sitemap.findall('{*}url/{*}loc')}
    payload = build_payload(urls, key, origin, allowed)
    key_response = fetch(session, origin + KEY_PATH)
    if (key_response.content != key.encode('utf-8')
            or not key_response.headers.get('Content-Type', '').startswith('text/plain')):
        raise ValueError('Live ownership file must be text/plain and contain the exact key')
    robots = parse_policy(fetch(session, origin + '/robots.txt').text)
    for url in payload['urlList']:
        if not robots.can_fetch('Bingbot', url):
            raise ValueError('Bingbot is blocked for a submitted URL')
        response = fetch(session, url)
        if 'text/html' not in response.headers.get('Content-Type', ''):
            raise ValueError('Only public HTML pages can be submitted')
        soup = BeautifulSoup(response.content, 'html.parser')
        canonicals = soup.select('link[rel="canonical"]')
        directives = [response.headers.get('X-Robots-Tag', '')]
        directives.extend(node.get('content', '') for node in soup.select('meta[name="robots"], meta[name="bingbot"]'))
        tokens = {token.lower() for value in directives for token in re.split(r'[\s,:]+', value)}
        if len(canonicals) != 1 or canonicals[0].get('href') != url or tokens & {'noindex', 'none'}:
            raise ValueError('Live page must be indexable and self-canonical')
    return payload


def submit(session, payload):
    response = session.post(ENDPOINT, json=payload, timeout=15, allow_redirects=False)
    if response.status_code not in (200, 202):
        raise ValueError(f'IndexNow submission failed (HTTP {response.status_code}); indexing state is unknown')
    return response.status_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', action='append', required=True, help='Repeat for each changed canonical URL')
    parser.add_argument('--submit', action='store_true', help='Send after live validation; otherwise dry-run')
    args = parser.parse_args()
    try:
        with requests.Session() as session:
            payload = prepare(session, args.url, os.getenv('INDEXNOW_KEY', ''),
                              os.getenv('BASE_URL', 'https://oshigoto.onrender.com'))
            if args.submit:
                status = submit(session, payload)
                print(f'RECEIVED: HTTP {status}; this is not an indexing or citation guarantee')
            else:
                print(f'DRY RUN: {len(payload["urlList"])} changed URLs validated; no submission sent')
        return 0
    except (ValueError, requests.RequestException, ET.ParseError) as exc:
        print(f'IndexNow validation/submission: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
