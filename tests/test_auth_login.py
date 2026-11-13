from __future__ import annotations

import pytest
from typer.testing import CliRunner

from softmax.cli import app
from softmax_client.credentials import save_user_token

runner = CliRunner()


def test_status_elevated_flag_requests_team_privileges(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    save_user_token(server="https://softmax.com/api", token="usr_team")
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "user_email": "team@example.com",
                "is_softmax_team_member": True,
                "is_softmax_admin": False,
                "subject_type": "user",
                "subject_id": "user-team-1",
                "owner_user_id": "user-team-1",
                "scopes": [],
            }

    def fake_get(_client, url: str, *, headers: dict[str, str]) -> FakeResponse:
        captured["headers"] = headers
        return FakeResponse()

    monkeypatch.setattr("softmax_client.auth.httpx.Client.get", fake_get)

    result = runner.invoke(app, ["status", "--elevated"])
    assert result.exit_code == 0
    assert captured["headers"]["X-Use-Elevated-Privileges"] == "true"  # type: ignore[index]


def test_status_without_elevated_flag_does_not_request_team_privileges(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    save_user_token(server="https://softmax.com/api", token="usr_team")
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "user_email": "team@example.com",
                "is_softmax_team_member": False,
                "is_softmax_admin": False,
                "subject_type": "user",
                "subject_id": "user-team-1",
                "owner_user_id": "user-team-1",
                "scopes": [],
            }

    def fake_get(_client, url: str, *, headers: dict[str, str]) -> FakeResponse:
        captured["headers"] = headers
        return FakeResponse()

    monkeypatch.setattr("softmax_client.auth.httpx.Client.get", fake_get)

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "X-Use-Elevated-Privileges" not in captured["headers"]  # type: ignore[operator]


def test_status_fails_for_anonymous_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    save_user_token(server="https://softmax.com/api", token="bad-token")

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "user_email": "unknown",
                "is_softmax_team_member": False,
                "is_softmax_admin": False,
                "subject_type": "anonymous",
                "subject_id": None,
                "owner_user_id": None,
                "scopes": [],
            }

    monkeypatch.setattr("softmax_client.auth.httpx.Client.get", lambda *args, **kwargs: FakeResponse())

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 1
