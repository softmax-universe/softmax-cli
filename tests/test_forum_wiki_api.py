from __future__ import annotations

import json

import httpx

from softmax_client.forum_wiki import ForumWikiClient

POST = {
    "id": "post_1",
    "title": "Hello",
    "author": {"type": "user", "user_id": "usr_1", "name": "Ada"},
    "content_format": "markdown",
    "body": "Body",
    "media": [],
    "created_at": "2026-08-29T00:00:00Z",
    "score": 1,
    "vote_count": 1,
}
COMMENT = {
    "id": "cmt_1",
    "parent_id": None,
    "author": {"type": "player", "player_id": "ply_1", "name": "Bot", "avatar_url": None},
    "body": "Reply",
    "created_at": "2026-08-29T00:01:00Z",
}
PAGE = {
    "id": "wpg_1",
    "wiki_id": "wiki_1",
    "slug": "guide/start",
    "title": "Start",
    "current_revision_id": "wrv_1",
    "created_at": "2026-08-29T00:00:00Z",
    "current_revision": {
        "id": "wrv_1",
        "page_id": "wpg_1",
        "body": "Base",
        "author": {"type": "user", "user_id": "usr_1", "name": "Ada"},
        "note": None,
        "parent_revision_id": None,
        "created_at": "2026-08-29T00:00:00Z",
    },
}


def test_mutations_retain_idempotency_keys_across_retries() -> None:
    bodies: dict[str, list[dict[str, object]]] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        path_bodies = bodies.setdefault(path, [])
        path_bodies.append(json.loads(request.content))
        if len(path_bodies) == 1:
            return httpx.Response(503, json={"detail": "retry"})
        if path == "/observatory/v2/posts":
            return httpx.Response(201, json=POST)
        if path == "/observatory/v2/posts/post_1/comments":
            return httpx.Response(201, json=COMMENT)
        if path == "/observatory/v2/wikis/global/pages/guide/start":
            summary = {key: value for key, value in PAGE.items() if key != "current_revision"}
            return httpx.Response(200, json={"page": summary, "revision": PAGE["current_revision"]})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    with ForumWikiClient(
        server="https://softmax.test",
        token="identity-token",
        transport=httpx.MockTransport(handler),
    ) as api:
        api.create_post(title="Hello", body="Body", idempotency_key="stable-key")
        api.create_comment("post_1", body="Reply", idempotency_key="comment-key")
        api.edit_wiki_page(
            "global",
            page_slug="guide/start",
            title="Start",
            body="Proposed",
            base_revision_id="wrv_1",
            idempotency_key="edit-key",
        )

    assert [body["idempotency_key"] for body in bodies["/observatory/v2/posts"]] == ["stable-key", "stable-key"]
    assert [body["idempotency_key"] for body in bodies["/observatory/v2/posts/post_1/comments"]] == [
        "comment-key",
        "comment-key",
    ]
    assert [body["idempotency_key"] for body in bodies["/observatory/v2/wikis/global/pages/guide/start"]] == [
        "edit-key",
        "edit-key",
    ]
