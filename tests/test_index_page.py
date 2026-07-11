# -*- coding: utf-8 -*-
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_index_returns_200(client):
    response = client.get('/')
    assert response.status_code == 200
    body = response.data.decode('utf-8')
    assert '??????' in body
    assert 'Jobcan' not in body


def test_autofill_redirects_to_tools(client):
    response = client.get('/autofill', follow_redirects=False)
    assert response.status_code == 301
    assert response.headers['Location'].endswith('/tools')


def test_public_routes_return_expected_status(client):
    for path in ['/', '/about', '/tools', '/tools/pdf', '/tools/csv', '/tools/image-batch', '/tools/image-cleanup', '/tools/seo', '/guide', '/blog', '/glossary', '/healthz']:
        response = client.get(path)
        assert response.status_code == 200, path


def test_missing_page_returns_404(client):
    response = client.get('/this-page-does-not-exist')
    assert response.status_code == 404
