"""CLI surface tests for `pf_runtime comms` (Slice 5).

The proposals subgroup operates on the local SQLite only — no network. The
triage subcommand is exercised through the registered argparse handlers
with a mocked classifier adapter so we can verify exit codes + arg
plumbing without hitting OpenRouter.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from pf_runtime.communications import cli as cli_module
from pf_runtime.communications.cli import handle, register_subparser
from pf_runtime.communications.proposal_store import ProposalStore
from pf_runtime.communications.schema import ActionType, ProposedAction, Provider
from pf_runtime.communications.triage_skill import (
    AccountTriageResult,
    TriageRunResult,
)
from pf_runtime.runtime.model_adapter import ModelAdapter


def _make_profile_dir(tmp_path: Path) -> Path:
    profile_dir = tmp_path / "profiles" / "personal"
    profile_dir.mkdir(parents=True, exist_ok=True)
    for name in ("SOUL.md", "USER.md", "MEMORY.md"):
        (profile_dir / name).write_text("# x\n", encoding="utf-8")
    (profile_dir / ".env").write_text("OPENROUTER_API_KEY=test\n", encoding="utf-8")
    (profile_dir / "config.yaml").write_text(
        'default: "openrouter/test-model:free"\nprovider: "openrouter"\n',
        encoding="utf-8",
    )
    return profile_dir


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="command", required=True)
    register_subparser(subs)
    return parser


def _seed(db_path: Path, action_id: str, status: str = "proposed") -> None:
    store = ProposalStore(db_path)
    store.add(
        ProposedAction(
            action_id=action_id,
            action_type=ActionType.REPLY_DRAFT,
            account_id="gmail-1",
            target_id="msg-1",
            rationale=f"rationale for {action_id}",
            payload={"draft": "hi"},
            status="proposed",
            created_at=datetime.now(UTC),
        )
    )
    if status != "proposed":
        store.mark_reviewed(action_id, status=status)


def test_proposals_list_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    parser = _build_parser()
    args = parser.parse_args(
        [
            "comms",
            "proposals",
            "list",
            "--profile",
            "personal",
            "--hermes-home",
            str(tmp_path),
        ]
    )
    rc = handle(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No proposed proposals" in out


def test_proposals_list_with_seeded_data(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db_path = tmp_path / "profiles" / "personal" / "communications.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _seed(db_path, "p1")
    _seed(db_path, "p2")

    parser = _build_parser()
    args = parser.parse_args(
        ["comms", "proposals", "list", "--hermes-home", str(tmp_path)]
    )
    rc = handle(args)
    assert rc == 0
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.startswith("p")]
    assert len(lines) == 2
    assert all("\treply_draft\t" in line for line in lines)


def test_proposals_show_known_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db_path = tmp_path / "profiles" / "personal" / "communications.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _seed(db_path, "p1")

    parser = _build_parser()
    args = parser.parse_args(
        ["comms", "proposals", "show", "p1", "--hermes-home", str(tmp_path)]
    )
    rc = handle(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert '"action_id": "p1"' in out
    assert '"status": "proposed"' in out


def test_proposals_show_unknown_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    parser = _build_parser()
    args = parser.parse_args(
        ["comms", "proposals", "show", "nope", "--hermes-home", str(tmp_path)]
    )
    rc = handle(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "proposal not found: nope" in err


def test_proposals_approve_lifecycle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db_path = tmp_path / "profiles" / "personal" / "communications.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _seed(db_path, "p1")

    parser = _build_parser()
    args = parser.parse_args(
        ["comms", "proposals", "approve", "p1", "--hermes-home", str(tmp_path)]
    )
    assert handle(args) == 0
    out = capsys.readouterr().out
    assert out.strip() == "p1: approved"

    args2 = parser.parse_args(
        [
            "comms",
            "proposals",
            "list",
            "--status",
            "approved",
            "--hermes-home",
            str(tmp_path),
        ]
    )
    assert handle(args2) == 0
    out2 = capsys.readouterr().out
    assert "p1\t" in out2


def test_proposals_reject_lifecycle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db_path = tmp_path / "profiles" / "personal" / "communications.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _seed(db_path, "p1")

    parser = _build_parser()
    args = parser.parse_args(
        ["comms", "proposals", "reject", "p1", "--hermes-home", str(tmp_path)]
    )
    assert handle(args) == 0
    out = capsys.readouterr().out
    assert out.strip() == "p1: rejected"


def test_proposals_approve_unknown_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    parser = _build_parser()
    args = parser.parse_args(
        ["comms", "proposals", "reject", "nope", "--hermes-home", str(tmp_path)]
    )
    assert handle(args) == 1
    err = capsys.readouterr().err
    assert "proposal not found: nope" in err


def test_triage_missing_registry_returns_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _make_profile_dir(tmp_path)

    parser = _build_parser()
    args = parser.parse_args(
        ["comms", "triage", "--profile", "personal", "--hermes-home", str(tmp_path)]
    )
    rc = handle(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "account registry not found" in err


def test_triage_runs_with_mocked_adapter_and_clients(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    profile_dir = _make_profile_dir(tmp_path)

    registry = profile_dir / "account-registry.yaml"
    registry.write_text(
        (
            "accounts:\n"
            "  - account_id: gmail-1\n"
            "    provider: google_mail\n"
            "    address: alex@example.com\n"
            "    scopes:\n"
            "      - https://www.googleapis.com/auth/gmail.readonly\n"
            "    read_only: true\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PF_GMAIL_TOKEN_GMAIL_1", "fake-token")

    class _StubAdapter(ModelAdapter):
        async def complete(
            self,
            messages: list[dict[str, Any]],
            *,
            model: str,
            max_tokens: int = 1024,
        ) -> tuple[str, Decimal]:
            del messages, model, max_tokens
            return ("", Decimal("0"))

    monkeypatch.setattr(cli_module, "_build_adapter", lambda profile: _StubAdapter())

    fake_run = TriageRunResult(
        run_id="run-test",
        started_at=datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC),
        finished_at=datetime(2026, 5, 8, 12, 0, 1, tzinfo=UTC),
        accounts=(
            AccountTriageResult(
                account_id="gmail-1",
                provider=Provider.GOOGLE_MAIL,
                fetched=2,
                classified=2,
                proposed=1,
            ),
        ),
    )
    with patch(
        "pf_runtime.communications.cli.triage_all_accounts",
        new=_make_async(fake_run),
    ):
        parser = _build_parser()
        args = parser.parse_args(
            [
                "comms",
                "triage",
                "--profile",
                "personal",
                "--hermes-home",
                str(tmp_path),
            ]
        )
        rc = handle(args)

    out = capsys.readouterr().out
    assert rc == 0
    assert "Triage run run-test" in out
    assert "proposals_created: 1" in out
    assert "errors: 0" in out
    assert "gmail-1 (google_mail): fetched=2 classified=2 proposed=1" in out


def test_triage_unknown_account_returns_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    profile_dir = _make_profile_dir(tmp_path)

    registry = profile_dir / "account-registry.yaml"
    registry.write_text(
        (
            "accounts:\n"
            "  - account_id: gmail-1\n"
            "    provider: google_mail\n"
            "    address: a@example.com\n"
            "    scopes:\n"
            "      - https://www.googleapis.com/auth/gmail.readonly\n"
            "    read_only: true\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "_build_adapter", lambda profile: object())

    parser = _build_parser()
    args = parser.parse_args(
        [
            "comms",
            "triage",
            "--profile",
            "personal",
            "--hermes-home",
            str(tmp_path),
            "--account",
            "ghost",
        ]
    )
    assert handle(args) == 1
    err = capsys.readouterr().err
    assert "no account matching --account ghost" in err


def _make_async(value: Any) -> Any:
    async def _coro(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        return value

    return _coro
