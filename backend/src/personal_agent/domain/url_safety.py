"""Decide whether a URL points at a local, private or cloud-metadata host.

Used by `web_fetch` and by the MCP transport rules so the agent host is not turned
into a proxy for internal services. This is a check on the URL text only: it does not
resolve DNS, so a public name that resolves to a private address is not caught here.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

DEFAULT_DENY_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "metadata.google.internal",
        "169.254.169.254",
    }
)


def is_private_or_local_url(url: str, deny_hosts: frozenset[str] = DEFAULT_DENY_HOSTS) -> bool:
    """True when the URL has no usable host or targets a local or private address."""
    try:
        host = (urlparse(url).hostname or "").casefold()
    except ValueError:
        return True
    if not host:
        return True
    if host in deny_hosts:
        return True
    if host.endswith((".local", ".internal", ".localhost")):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    )
