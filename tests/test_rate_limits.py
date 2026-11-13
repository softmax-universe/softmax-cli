import httpx
import pytest

from softmax_client import rate_limits
from softmax_client.http import observatory_client


@pytest.mark.parametrize("recover", [False, True])
def test_shared_rejection_retries_preserve_the_request_and_stop(monkeypatch, recover):
    monkeypatch.setattr(rate_limits.time, "sleep", lambda _: None)
    requests = []
    responses = []

    def handle(request):
        requests.append((request.headers["Authorization"], request.content))
        response = httpx.Response(
            200 if recover and len(requests) == 2 else 429,
            headers={"X-RateLimit-Outcome": "rejected", "Retry-After": "1"},
            json={"ok": True},
        )
        responses.append(response)
        return response

    with observatory_client(
        server="https://example.com", token="token", transport=httpx.MockTransport(handle), product="softmax-cli"
    ) as client:
        response = client.post("/submit", json={"idempotency_key": "submission-1"})

    assert response.status_code == (200 if recover else 429)
    assert len(requests) == (2 if recover else 3)
    assert all(request == requests[0] for request in requests)
    assert requests[0][0] == "Bearer token"
    assert all(response.is_closed for response in responses)


def test_rate_limited_response_without_rejection_is_not_retried(monkeypatch):
    def no_sleep(_seconds):
        pytest.fail("This response must remain actionable without automatic retries")

    monkeypatch.setattr(rate_limits.time, "sleep", no_sleep)
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "1"})

    with observatory_client(
        server="https://example.com", token="token", transport=httpx.MockTransport(handle), product="softmax-cli"
    ) as client:
        assert client.get("/resource").status_code == 429
    assert len(calls) == 1


def test_streaming_upload_is_not_retried_after_transport_buffers_it():
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(429, headers={"X-RateLimit-Outcome": "rejected", "Retry-After": "0"})

    with observatory_client(
        server="https://example.com", token="token", transport=httpx.MockTransport(handle), product="softmax-cli"
    ) as client:
        response = client.post("/upload", content=iter([b"payload"]))
    assert response.status_code == 429
    assert len(calls) == 1
