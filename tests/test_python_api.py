from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import yaml

import softmax
from softmax_client import credentials as credential_store
from softmax_client.credentials import (
    get_cached_player_session,
    load_current_token,
    load_player_session,
    load_user_token,
    save_user_token,
    set_active_player_session,
)


def _activate_player(server: str, token: str, player_id: str = "ply_alpha") -> None:
    set_active_player_session(
        server=server,
        player_id=player_id,
        token=token,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )


def test_unknown_credential_fields_survive_save(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / ".softmax"
    config_dir.mkdir()
    credentials_path = config_dir / "credentials.yaml"
    credentials_path.write_text(yaml.safe_dump({"credential_version": {"major": 2}}))

    save_user_token(server="https://softmax.com/api", token="user-token")

    saved = yaml.safe_load(credentials_path.read_text())
    assert saved["credential_version"] == {"major": 2}


def test_login_returns_user_token_even_with_active_player_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    server = "https://softmax.com/api"
    save_user_token(server=server, token="user-token")
    _activate_player(server, "player-token")

    assert load_current_token(server=server) == "player-token"
    assert softmax.login(api_server=server) == "user-token"


def test_changing_user_token_drops_player_sessions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    server = "https://softmax.com/api"
    save_user_token(server=server, token="user-token")
    _activate_player(server, "player-token", player_id="ply_alpha")
    assert load_current_token(server=server) == "player-token"

    # Re-saving the same token must NOT disturb the active player session.
    save_user_token(server=server, token="user-token")
    assert load_current_token(server=server) == "player-token"

    # Switching the user credential invalidates the old user's player sessions,
    # so commands act as the new user rather than the stale player.
    save_user_token(server=server, token="new-user-token")
    assert load_player_session(server=server) is None
    assert get_cached_player_session(server=server, player_id="ply_alpha") is None
    assert load_current_token(server=server) == "new-user-token"


def test_expired_player_session_falls_through_to_user_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    server = "https://softmax.com/api"
    save_user_token(server=server, token="user-token")

    # Activate a player with an already-expired session.
    set_active_player_session(
        server=server,
        player_id="ply_alpha",
        token="expired-player-token",
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )

    # The active pointer is set, but load_player_session skips the expired token.
    assert load_player_session(server=server) is None
    # load_current_token falls through to the user token.
    assert load_current_token(server=server) == "user-token"


def test_config_dir_env_isolates_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    server = "https://softmax.com/api"
    monkeypatch.setenv("HOME", str(tmp_path))
    save_user_token(server=server, token="shared-user-token")
    _activate_player(server, "shared-player-token")

    override_dir = tmp_path / "lane" / "config"
    monkeypatch.setenv(credential_store.CONFIG_DIR_ENV, str(override_dir))
    assert load_current_token(server=server) is None
    save_user_token(server=server, token="lane-user-token")

    override_path = override_dir / "credentials.yaml"
    assert load_current_token(server=server) == "lane-user-token"
    assert yaml.safe_load(override_path.read_text())["tokens"] == {server: "lane-user-token"}
    assert override_path.stat().st_mode & 0o777 == 0o600
    assert override_dir.stat().st_mode & 0o777 == 0o700

    monkeypatch.delenv(credential_store.CONFIG_DIR_ENV)
    assert load_current_token(server=server) == "shared-player-token"
    assert load_user_token(server=server) == "shared-user-token"
