"""Pinned, bounded HTTP client for untrusted crawl targets.

The client resolves a hostname once per hop, rejects non-public addresses, and
connects directly to one of those validated addresses while preserving the
original Host header and TLS SNI. It intentionally has no proxy, cookie, or
authentication support.
"""

from __future__ import annotations

import http.client
import ipaddress
import re
import socket
import ssl
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping
from urllib.parse import urljoin, urlsplit, urlunsplit


MAX_URL_LENGTH = 2048
MAX_REDIRECTS = 3
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
ALLOWED_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
FIXED_USER_AGENT = "OshigotoSecurityCrawler/1.0"


class SafeHttpError(RuntimeError):
    """An outbound request was rejected or could not be completed safely."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ResolvedTarget:
    url: str
    scheme: str
    hostname: str
    port: int
    host_header: str
    request_target: str
    addresses: tuple[str, ...]


@dataclass(frozen=True)
class SafeHttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes
    url: str

    @property
    def text(self) -> str:
        content_type = self.headers.get("content-type", "")
        match = re.search(r"charset=([A-Za-z0-9._-]+)", content_type, re.IGNORECASE)
        charset = match.group(1) if match else "utf-8"
        try:
            return self.body.decode(charset, errors="replace")
        except LookupError:
            return self.body.decode("utf-8", errors="replace")


Resolver = Callable[[str, int], Iterable[str]]
Transport = Callable[[ResolvedTarget, float, float, int], SafeHttpResponse]


def _normalize_hostname(hostname: str) -> str:
    candidate = hostname.strip().rstrip(".").lower()
    if not candidate or candidate == "localhost" or candidate.endswith(".local"):
        raise SafeHttpError("host_not_allowed")
    try:
        return candidate.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise SafeHttpError("invalid_hostname") from exc


def _normalized_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        address = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError as exc:
        raise SafeHttpError("invalid_resolved_address") from exc
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    if not address.is_global:
        raise SafeHttpError("non_public_address")
    return address


def _default_resolver(hostname: str, port: int) -> tuple[str, ...]:
    try:
        records = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SafeHttpError("dns_resolution_failed") from exc
    return tuple(record[4][0] for record in records)


def resolve_target(url: str, resolver: Resolver | None = None) -> ResolvedTarget:
    if not isinstance(url, str) or not url or len(url) > MAX_URL_LENGTH:
        raise SafeHttpError("invalid_url_length")
    if any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise SafeHttpError("invalid_url_character")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise SafeHttpError("invalid_url") from exc
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise SafeHttpError("scheme_not_allowed")
    if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
        raise SafeHttpError("userinfo_not_allowed")
    if not parsed.hostname:
        raise SafeHttpError("hostname_required")
    hostname = _normalize_hostname(parsed.hostname)
    default_port = 443 if scheme == "https" else 80
    port = port or default_port
    if port != default_port:
        raise SafeHttpError("port_not_allowed")

    try:
        literal = _normalized_ip(hostname)
        raw_addresses = (str(literal),)
    except SafeHttpError as literal_error:
        if literal_error.code == "non_public_address":
            raise
        raw_addresses = tuple((resolver or _default_resolver)(hostname, port))
    if not raw_addresses:
        raise SafeHttpError("dns_resolution_failed")
    addresses = tuple(sorted({str(_normalized_ip(address)) for address in raw_addresses}))

    host_header = hostname
    if ":" in hostname:
        host_header = f"[{hostname}]"
    path = parsed.path or "/"
    request_target = urlunsplit(("", "", path, parsed.query, ""))
    normalized_url = urlunsplit((scheme, host_header, path, parsed.query, ""))
    return ResolvedTarget(
        url=normalized_url,
        scheme=scheme,
        hostname=hostname,
        port=port,
        host_header=host_header,
        request_target=request_target,
        addresses=addresses,
    )


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, hostname: str, address: str, port: int, timeout: float):
        super().__init__(hostname, port=port, timeout=timeout)
        self._address = address

    def connect(self):
        self.sock = socket.create_connection((self._address, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, address: str, port: int, timeout: float):
        super().__init__(hostname, port=port, timeout=timeout, context=ssl.create_default_context())
        self._address = address

    def connect(self):
        raw_socket = socket.create_connection((self._address, self.port), self.timeout)
        self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)


def _default_transport(target: ResolvedTarget, connect_timeout: float, read_timeout: float, max_bytes: int) -> SafeHttpResponse:
    last_error: Exception | None = None
    for address in target.addresses:
        connection = None
        try:
            connection_type = _PinnedHTTPSConnection if target.scheme == "https" else _PinnedHTTPConnection
            connection = connection_type(target.hostname, address, target.port, connect_timeout)
            connection.connect()
            if connection.sock is not None:
                connection.sock.settimeout(read_timeout)
            connection.request(
                "GET",
                target.request_target,
                headers={
                    "Host": target.host_header,
                    "User-Agent": FIXED_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8",
                    "Accept-Encoding": "identity",
                    "Connection": "close",
                },
            )
            response = connection.getresponse()
            headers = {name.lower(): value.strip() for name, value in response.getheaders()}
            if headers.get("content-encoding", "identity").lower() not in {"", "identity"}:
                raise SafeHttpError("content_encoding_not_allowed")
            content_length = headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > max_bytes:
                        raise SafeHttpError("response_too_large")
                except ValueError as exc:
                    raise SafeHttpError("invalid_content_length") from exc
            chunks: list[bytes] = []
            received = 0
            while True:
                chunk = response.read(min(64 * 1024, max_bytes + 1 - received))
                if not chunk:
                    break
                received += len(chunk)
                if received > max_bytes:
                    raise SafeHttpError("response_too_large")
                chunks.append(chunk)
            return SafeHttpResponse(response.status, headers, b"".join(chunks), target.url)
        except SafeHttpError:
            raise
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            last_error = exc
        finally:
            if connection is not None:
                connection.close()
    raise SafeHttpError("connection_failed") from last_error


class SafeHttpClient:
    def __init__(self, *, resolver: Resolver | None = None, transport: Transport | None = None):
        self._resolver = resolver
        self._transport = transport or _default_transport

    def get(
        self,
        url: str,
        *,
        connect_timeout: float = 3.0,
        read_timeout: float = 5.0,
        max_bytes: int = MAX_RESPONSE_BYTES,
        max_redirects: int = MAX_REDIRECTS,
        allowed_content_types: frozenset[str] | None = ALLOWED_CONTENT_TYPES,
        same_origin: str | None = None,
    ) -> SafeHttpResponse:
        max_bytes = min(max(1, int(max_bytes)), 5 * 1024 * 1024)
        max_redirects = min(max(0, int(max_redirects)), MAX_REDIRECTS)
        target = resolve_target(url, self._resolver)
        expected_origin = None
        if same_origin is not None:
            origin = urlsplit(same_origin)
            origin_scheme = origin.scheme.lower()
            if origin_scheme not in {"http", "https"} or not origin.hostname:
                raise SafeHttpError("invalid_same_origin")
            try:
                origin_port = origin.port or (443 if origin_scheme == "https" else 80)
            except ValueError as exc:
                raise SafeHttpError("invalid_same_origin") from exc
            expected_origin = (origin_scheme, _normalize_hostname(origin.hostname), origin_port)

        for redirect_count in range(max_redirects + 1):
            if expected_origin is not None and (target.scheme, target.hostname, target.port) != expected_origin:
                raise SafeHttpError("cross_origin_redirect")
            response = self._transport(target, connect_timeout, read_timeout, max_bytes)
            if len(response.body) > max_bytes:
                raise SafeHttpError("response_too_large")
            if response.status in REDIRECT_STATUSES:
                if redirect_count >= max_redirects:
                    raise SafeHttpError("too_many_redirects")
                location = response.headers.get("location", "").strip()
                if not location:
                    raise SafeHttpError("redirect_without_location")
                target = resolve_target(urljoin(target.url, location), self._resolver)
                continue
            if allowed_content_types is not None:
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if content_type not in allowed_content_types:
                    raise SafeHttpError("content_type_not_allowed")
            return response
        raise SafeHttpError("too_many_redirects")


def is_url_safe(url: str, resolver: Resolver | None = None) -> tuple[bool, str | None]:
    try:
        resolve_target(url, resolver)
    except SafeHttpError as exc:
        return False, exc.code
    return True, None
