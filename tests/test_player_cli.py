from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pytest_httpserver import HTTPServer
from typer.testing import CliRunner

from softmax.cli import app
from softmax_client.credentials import (
    get_active_player_id,
    load_player_session,
    load_user_token,
    save_user_token,
    set_active_player_session,
)

PLAYER_ALPHA = {
    "id": "ply_00000000-0000-0000-0000-0000000000a1",
    "name": "Alpha",
    "is_default": True,
    "avatar_url": None,
    "created_at": "2026-06-05T12:00:00Z",
    "disabled_at": None,
    "user_id": "usr_owner",
}
PLAYER_BETA = {
    "id": "ply_00000000-0000-0000-0000-0000000000b2",
    "name": "Beta",
    "is_default": False,
    "avatar_url": None,
    "created_at": "2026-06-06T12:00:00Z",
    "disabled_at": None,
    "user_id": "usr_owner",
}


@pytest.fixture(autouse=True)
def _sandbox_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    # Isolate ~/.softmax/credentials.yaml under tmp.
    monkeypatch.setenv("HOME", str(tmp_path))


def _activate(server: str, player_id: str, token: str = "ply_session", hours: int = 24) -> None:
    set_active_player_session(
        server=server,
        player_id=player_id,
        token=token,
        expires_at=datetime.now(UTC) + timedelta(hours=hours),
    )


def test_use_mints_and_activates(httpserver: HTTPServer) -> None:
    server = httpserver.url_for("")
    save_user_token(server=server, token="user-token")
    expires_at = (datetime.now(UTC) + timedelta(hours=24)).isoformat()
    httpserver.expect_request(
        "/observatory/players",
        method="GET",
        headers={"Authorization": "Bearer user-token"},
    ).respond_with_json([PLAYER_ALPHA, PLAYER_BETA])
    httpserver.expect_request(
        f"/observatory/players/{PLAYER_BETA['id']}/login",
        method="POST",
        headers={"Authorization": "Bearer user-token"},
    ).respond_with_json({"player_id": PLAYER_BETA["id"], "token": "ply_minted", "expires_at": expires_at})

    result = CliRunner().invoke(app, ["player", "use", PLAYER_BETA["id"], "--server", server])

    assert result.exit_code == 0, result.output
    assert get_active_player_id(server=server) == PLAYER_BETA["id"]
    assert load_player_session(server=server) == "ply_minted"


def test_unset_clears_active_keeps_user_token(httpserver: HTTPServer) -> None:
    server = httpserver.url_for("")
    save_user_token(server=server, token="user-token")
    _activate(server, PLAYER_ALPHA["id"])

    result = CliRunner().invoke(app, ["player", "unset", "--server", server])

    assert result.exit_code == 0, result.output
    assert load_player_session(server=server) is None
    assert load_user_token(server=server) == "user-token"
