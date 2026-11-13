"""Shared HTTP client construction for Observatory endpoints."""

from __future__ import annotations

import os
from functools import partial

import httpx

from softmax_client.agent import user_agent
from softmax_client.rate_limits import RateLimitTransport

MANAGED_API_SERVER = "http://softmax.internal/api"
COMMAND_HANDLE_ENV = "SOFTMAX_COMMAND_HANDLE"
COMMAND_HANDLE_HEADER = "X-Cogent-Command"

_CORE_API_SERVERS = frozenset(
    {
        "https://softmax-api.softmax.com",
        "https://api.softmax.com",
        "https://api.observatory.softmax-research.net",
    }
)


def is_managed_api_server(server: str) -> bool:
    return httpx.URL(server.rstrip("/")) == httpx.URL(MANAGED_API_SERVER)


def _managed_request_headers(request: httpx.Request, *, command_handle: str | None) -> None:
    request.headers.pop(COMMAND_HANDLE_HEADER, None)
    managed_origin = httpx.URL(MANAGED_API_SERVER)
    if (request.url.scheme, request.url.host, request.url.port) == (
        managed_origin.scheme,
        managed_origin.host,
        managed_origin.port,
    ):
        request.headers.pop("Authorization", None)
        request.headers.pop("X-Use-Elevated-Privileges", None)
        if command_handle:
            request.headers[COMMAND_HANDLE_HEADER] = command_handle


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
    token: str | None,
    base: str = "/observatory",
    transport: httpx.BaseTransport | None = None,
    timeout: float = 10.0,
    product: str = "softmax-cli",
) -> httpx.Client:
    """Construct a client with bounded rate-limit retries; the caller owns closing it."""
    headers = {"User-Agent": user_agent(product)}
    command_handle = None
    if is_managed_api_server(server):
        command_handle = os.environ.get(COMMAND_HANDLE_ENV)
    elif token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(
        base_url=observatory_base_url(server, base=base),
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
        transport=RateLimitTransport(transport),
        event_hooks={"request": [partial(_managed_request_headers, command_handle=command_handle)]},
    )
