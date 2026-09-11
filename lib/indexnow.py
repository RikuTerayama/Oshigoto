"""Validation shared by the ownership endpoint and explicit IndexNow command."""

import ipaddress
import re
from urllib.parse import urlsplit

KEY_PATH = '/indexnow-key.txt'
ENDPOINT = 'https://api.indexnow.org/IndexNow'


def valid_key(key):
    return isinstance(key, str) and re.fullmatch(r'[A-Za-z0-9-]{8,128}', key) is not None


def public_origin(base_url):
    parsed = urlsplit(base_url)
    host = parsed.hostname or ''
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port
            or parsed.query or parsed.fragment or parsed.path not in ('', '/')
            or '.' not in host or host.endswith(('.localhost', '.local', '.internal'))):
        raise ValueError('BASE_URL must be a public HTTPS origin without credentials or a port')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None:
        raise ValueError('IP-address origins are not supported')
    return 'https://' + host


def build_payload(urls, key, base_url, allowed_urls):
    if not valid_key(key):
        raise ValueError('INDEXNOW_KEY must contain 8-128 ASCII letters, digits or hyphens')
    origin = public_origin(base_url)
    unique = list(dict.fromkeys(urls))
    if not 1 <= len(unique) <= 10000:
        raise ValueError('Specify 1-10000 changed canonical URLs explicitly')
    for url in unique:
        parsed = urlsplit(url)
        if (url not in allowed_urls or parsed.scheme != 'https'
                or parsed.netloc != urlsplit(origin).netloc or parsed.query or parsed.fragment
                or parsed.path.startswith(('/api/', '/_internal/', '/static/'))):
            raise ValueError('Only same-host canonical public sitemap URLs can be submitted')
    return {'host': urlsplit(origin).netloc, 'key': key,
            'keyLocation': origin + KEY_PATH, 'urlList': unique}
