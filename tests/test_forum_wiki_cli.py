from __future__ import annotations

import shlex
from pathlib import Path

import pytest
from typer.testing import CliRunner

from softmax.cli import app
from softmax_client.forum_wiki import (
    WikiEditConflictDetail,
    WikiEditConflictResponse,
    WikiPagePublic,
)

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


class FakeApi:
    def __enter__(self) -> "FakeApi":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read_wiki_page(self, *_: object, **__: object) -> WikiPagePublic:
        return WikiPagePublic.model_validate(PAGE)

    def edit_wiki_page(self, *_: object, **__: object) -> WikiEditConflictResponse:
        return WikiEditConflictResponse(
            detail=WikiEditConflictDetail(
                current_revision_id="wrv_2",
                current_body="Current body",
            )
        )


@pytest.fixture(autouse=True)
def _fake_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("softmax.wiki.ForumWikiClient.from_current_token", lambda server, *, product: FakeApi())


def test_wiki_edit_conflict_writes_three_files_and_prints_merge_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proposed = tmp_path / "proposed-input.md"
    proposed.write_text("Proposed body")
    conflict_dir = tmp_path / "conflict"

    def make_conflict_dir(*_: object, **__: object) -> str:
        conflict_dir.mkdir()
        return str(conflict_dir)

    monkeypatch.setattr("softmax.wiki.tempfile.mkdtemp", make_conflict_dir)

    result = CliRunner().invoke(
        app,
        [
            "wiki",
            "edit",
            "global",
            "guide/start",
            "--file",
            str(proposed),
            "--title",
            "Guide's start",
            "--note",
            "Resolve conflict; keep examples",
        ],
    )

    assert result.exit_code != 0
    assert (conflict_dir / "base.md").read_text() == "Base"
    assert (conflict_dir / "current.md").read_text() == "Current body"
    assert (conflict_dir / "proposed.md").read_text() == "Proposed body"
    retry_command = next(line for line in result.output.splitlines() if line.startswith("softmax wiki edit"))
    assert shlex.split(retry_command) == [
        "softmax",
        "wiki",
        "edit",
        "global",
        "guide/start",
        "--file",
        str(conflict_dir / "proposed.md"),
        "--server",
        "https://softmax.com/api",
        "--title",
        "Guide's start",
        "--note",
        "Resolve conflict; keep examples",
    ]
