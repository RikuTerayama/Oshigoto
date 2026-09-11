#!/usr/bin/env python3
"""IndexNow ownership and submission regression tests. No real network requests."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app
from lib.indexnow import ENDPOINT, KEY_PATH, build_payload, valid_key
from lib.robots_policy import parse_policy
from scripts.submit_indexnow import prepare, submit

BASE = 'https://oshigoto.onrender.com'
KEY = 'test-ownership-key-123'
URL = BASE + '/tools/pdf'


def response(body, content_type='text/html', status=200):
    return Mock(status_code=status, content=body.encode(), text=body,
                headers={'Content-Type': content_type})


class IndexNowTests(unittest.TestCase):
    def test_robots_specificity(self):
        policy = parse_policy('User-agent: *\nAllow: /\nDisallow: /api/\nAllow: /api/public/')
        self.assertTrue(policy.can_fetch('Bingbot', BASE + '/tools/pdf'))
        self.assertFalse(policy.can_fetch('Bingbot', BASE + '/api/pdf/lock'))
        self.assertTrue(policy.can_fetch('Bingbot', BASE + '/api/public/item'))
        with self.assertRaises(ValueError):
            parse_policy('User-agent: *\nDisallow: /*private')

    def test_key_endpoint(self):
        client = app.test_client()
        for key in ('', 'short', 'x' * 129, '../not-valid', '１２３４５６７８'):
            with patch.dict(os.environ, INDEXNOW_KEY=key):
                self.assertFalse(valid_key(key))
                self.assertEqual(client.get(KEY_PATH).status_code, 404)
        with patch.dict(os.environ, INDEXNOW_KEY=KEY):
            result = client.get(KEY_PATH)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.data, KEY.encode())
            self.assertEqual(result.mimetype, 'text/plain')
        self.assertTrue(valid_key('a' * 8))
        self.assertTrue(valid_key('a' * 128))

    def test_payload_boundaries(self):
        result = build_payload([URL, URL], KEY, BASE, {URL})
        self.assertEqual(result, {'host': 'oshigoto.onrender.com', 'key': KEY,
                                 'keyLocation': BASE + KEY_PATH, 'urlList': [URL]})
        for url in ('https://example.com/tools/pdf', BASE + '/privacy', BASE + '/autofill',
                    BASE + '/api/pdf/lock', BASE + '/_internal/status',
                    URL + '?utm_source=x', URL + '#top', 'http://localhost/tools/pdf'):
            with self.assertRaises(ValueError):
                build_payload([url], KEY, BASE, {URL})
        for origin in ('http://localhost', 'https://127.0.0.1', 'https://192.168.1.1',
                       'https://test.local', BASE + ':443', BASE + '/path'):
            with self.assertRaises(ValueError):
                build_payload([URL], KEY, origin, {URL})

    def session(self, page=None, key=KEY, robots='User-agent: *\nAllow: /'):
        session = Mock()
        session.get.side_effect = [
            response(f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{URL}</loc></url></urlset>', 'application/xml'),
            response(key, 'text/plain'), response(robots, 'text/plain'),
            page or response(f'<link rel="canonical" href="{URL}"><meta name="robots" content="index,follow">')]
        return session

    def test_live_validation_and_explicit_submission(self):
        session = self.session()
        payload = prepare(session, [URL], KEY, BASE)
        session.post.assert_not_called()
        for status in (200, 202):
            session.post.return_value = response('', status=status)
            self.assertEqual(submit(session, payload), status)
        session.post.assert_called_with(ENDPOINT, json=payload, timeout=15, allow_redirects=False)
        session.post.return_value = response('', status=429)
        with self.assertRaises(ValueError):
            submit(session, payload)

    def test_reject_live_conflicts(self):
        for page in (response('', status=301), response('', status=404),
                     response(f'<link rel="canonical" href="{URL}"><meta name="robots" content="noindex nofollow">'),
                     response(f'<link rel="canonical" href="{URL}"><meta name="robots" content="noindex,follow">'),
                     response('<link rel="canonical" href="https://example.com/">')):
            with self.assertRaises(ValueError):
                prepare(self.session(page=page), [URL], KEY, BASE)
        with self.assertRaises(ValueError):
            prepare(self.session(key='wrong-key'), [URL], KEY, BASE)
        with self.assertRaises(ValueError):
            prepare(self.session(robots='User-agent: *\nDisallow: /'), [URL], KEY, BASE)


if __name__ == '__main__':
    unittest.main()
