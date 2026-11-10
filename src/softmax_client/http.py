"""Shared HTTP client construction for Observatory endpoints."""

from __future__ import annotations

import httpx

from softmax_client.agent import user_agent
from softmax_client.rate_limits import RateLimitTransport

_CORE_API_SERVERS = frozenset(
    {
        "https://softmax-api.softmax.com",
        "https://api.softmax.com",
        "https://api.observatory.softmax-research.net",
    }
)


def core_api_origin(server: str) -> str | None:
    url = httpx.URL(server.rstrip("/"))
    if url.scheme == "https" and url.port == 443:
        url = url.copy_with(port=None)
    origin = str(url)
    return origin if origin in _CORE_API_SERVERS else None


def observatory_base_url(server: str, *, base: str = "/observatory") -> str:
    server = server.rstrip("/")
    origin = core_api_origin(server)
    if origin is not None:
        server = origin
        base = base.removeprefix("/observatory")
    return f"{server}{base}"


def observatory_client(
    *,
    server: str,
    token: str,
    base: str = "/observatory",
    transport: httpx.BaseTransport | None = None,
    timeout: float = 10.0,
    product: str = "softmax-cli",
) -> httpx.Client:
    """Construct an authenticated client with bounded rate-limit retries; the caller owns closing it."""
    return httpx.Client(
        base_url=observatory_base_url(server, base=base),
        headers={"Authorization": f"Bearer {token}", "User-Agent": user_agent(product)},
        timeout=timeout,
        follow_redirects=True,
        transport=RateLimitTransport(transport),
    )
