"""SlackChannel unit tests with slack-bolt mocked at the import boundary."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Skip the entire module when slack-bolt isn't installed; the gateway daemon
# itself raises ChannelConnectError clearly when the lib is missing.
pytest.importorskip("slack_bolt")
pytest.importorskip("slack_sdk")

from slack_sdk.errors import SlackApiError

from pf_runtime.channels.adapter_base import (
    ChannelAuthError,
    ChannelRateLimited,
)
from pf_runtime.channels.slack import SlackChannel

# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def env_file(tmp_path: Path) -> Path:
    p = tmp_path / ".env"
    p.write_text(
        "SLACK_BOT_TOKEN=xoxb-test-bot\nSLACK_APP_TOKEN=xapp-test-app\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def env_file_missing_bot(tmp_path: Path) -> Path:
    p = tmp_path / ".env"
    p.write_text("SLACK_APP_TOKEN=xapp-test-app\n", encoding="utf-8")
    return p


@pytest.fixture
def env_file_missing_app(tmp_path: Path) -> Path:
    p = tmp_path / ".env"
    p.write_text("SLACK_BOT_TOKEN=xoxb-test-bot\n", encoding="utf-8")
    return p


def _make_app_mock(*, auth_user_id: str = "UBOT") -> MagicMock:
    """Build a mock AsyncApp whose ``client.auth_test`` returns ``auth_user_id``."""
    app = MagicMock()
    app.client = MagicMock()
    app.client.auth_test = AsyncMock(return_value={"user_id": auth_user_id})
    app.client.chat_postMessage = AsyncMock(return_value={"ok": True})
    app.client.conversations_open = AsyncMock(
        return_value={"channel": {"id": "D123"}}
    )

    # @app.event(name) decorator returns the decorator function — must accept
    # the handler and return it unchanged.
    def _event_decorator(_name: str) -> Callable[[Any], Any]:
        def wrapper(handler: Any) -> Any:
            return handler

        return wrapper

    app.event = MagicMock(side_effect=_event_decorator)
    return app


def _make_handler_mock() -> MagicMock:
    handler = MagicMock()

    # start_async must NOT return immediately — the gateway treats a
    # done() task during startup as a connect failure. In production
    # start_async() runs the WebSocket pump indefinitely; we mimic that
    # with a never-resolving Future.
    async def _never_returns() -> None:
        await asyncio.Event().wait()

    handler.start_async = AsyncMock(side_effect=_never_returns)
    handler.close_async = AsyncMock(return_value=None)
    return handler


# --------------------------------------------------------------------------- #
# Construction — credential validation
# --------------------------------------------------------------------------- #


def test_missing_bot_token_raises_auth_error(env_file_missing_bot: Path) -> None:
    with pytest.raises(ChannelAuthError, match="SLACK_BOT_TOKEN"):
        SlackChannel(profile_slug="personal", env_path=env_file_missing_bot)


def test_missing_app_token_raises_auth_error(env_file_missing_app: Path) -> None:
    with pytest.raises(ChannelAuthError, match="SLACK_APP_TOKEN"):
        SlackChannel(profile_slug="personal", env_path=env_file_missing_app)


# --------------------------------------------------------------------------- #
# connect()
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_connect_sets_bot_user_id_and_connected(
    env_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _make_app_mock(auth_user_id="UBOT")
    handler = _make_handler_mock()

    monkeypatch.setattr(
        "pf_runtime.channels.slack.AsyncApp", MagicMock(return_value=app)
    )
    monkeypatch.setattr(
        "pf_runtime.channels.slack.AsyncSocketModeHandler",
        MagicMock(return_value=handler),
    )

    ch = SlackChannel(profile_slug="personal", env_path=env_file)
    try:
        await ch.connect()
        assert ch._bot_user_id == "UBOT"
        assert ch._connected is True
    finally:
        await ch.disconnect()


# --------------------------------------------------------------------------- #
# Inbound dedup + filters
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_inbound_dedup_drops_duplicate_event_id(env_file: Path) -> None:
    ch = SlackChannel(profile_slug="personal", env_path=env_file)
    ch._bot_user_id = "UBOT"
    event = {
        "event_id": "Ev1",
        "channel_type": "im",
        "user": "UALEX",
        "channel": "D1",
        "ts": "1.0",
        "text": "hi",
    }
    await ch._on_slack_message(event)
    await ch._on_slack_message(event)
    assert ch._inbound_queue.qsize() == 1
    queued = ch._inbound_queue.get_nowait()
    assert queued.metadata["thread_ts"] == "1.0"


@pytest.mark.asyncio
async def test_inbound_reuses_one_conversation_thread_per_user(env_file: Path) -> None:
    ch = SlackChannel(profile_slug="personal", env_path=env_file)
    ch._bot_user_id = "UBOT"

    await ch._on_slack_message(
        {
            "event_id": "Ev1",
            "channel_type": "im",
            "user": "UALEX",
            "channel": "D1",
            "ts": "1.0",
            "text": "first",
        }
    )
    await ch._on_slack_message(
        {
            "event_id": "Ev2",
            "channel_type": "im",
            "user": "UALEX",
            "channel": "D1",
            "ts": "2.0",
            "text": "second top-level prompt",
        }
    )

    first = ch._inbound_queue.get_nowait()
    second = ch._inbound_queue.get_nowait()
    assert first.metadata["thread_ts"] == "1.0"
    assert second.metadata["thread_ts"] == "1.0"

    restarted = SlackChannel(profile_slug="personal", env_path=env_file)
    restarted._bot_user_id = "UBOT"
    await restarted._on_slack_message(
        {
            "event_id": "Ev3",
            "channel_type": "im",
            "user": "UALEX",
            "channel": "D1",
            "ts": "3.0",
            "text": "after restart",
        }
    )
    after_restart = restarted._inbound_queue.get_nowait()
    assert after_restart.metadata["thread_ts"] == "1.0"


@pytest.mark.asyncio
async def test_self_messages_dropped(env_file: Path) -> None:
    ch = SlackChannel(profile_slug="personal", env_path=env_file)
    ch._bot_user_id = "UBOT"
    await ch._on_slack_message(
        {
            "event_id": "Ev1",
            "channel_type": "im",
            "user": "UBOT",  # self
            "channel": "D1",
            "ts": "1.0",
            "text": "hi",
        }
    )
    assert ch._inbound_queue.qsize() == 0


@pytest.mark.asyncio
async def test_non_dm_messages_dropped(env_file: Path) -> None:
    ch = SlackChannel(profile_slug="personal", env_path=env_file)
    ch._bot_user_id = "UBOT"
    await ch._on_slack_message(
        {
            "event_id": "Ev2",
            "channel_type": "channel",  # not a DM
            "user": "UALEX",
            "channel": "C1",
            "ts": "1.0",
            "text": "hi",
        }
    )
    assert ch._inbound_queue.qsize() == 0


@pytest.mark.asyncio
async def test_subtype_messages_dropped(env_file: Path) -> None:
    """Edits, bot_message etc. carry a subtype and must be ignored."""
    ch = SlackChannel(profile_slug="personal", env_path=env_file)
    ch._bot_user_id = "UBOT"
    await ch._on_slack_message(
        {
            "event_id": "Ev3",
            "channel_type": "im",
            "user": "UALEX",
            "channel": "D1",
            "ts": "1.0",
            "text": "hi",
            "subtype": "message_changed",
        }
    )
    assert ch._inbound_queue.qsize() == 0


# --------------------------------------------------------------------------- #
# Outbound dedup + error mapping
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_outbound_ledger_skips_when_key_pre_recorded(
    env_file: Path,
    tmp_path: Path,
) -> None:
    """Persistent ledger marks reply already sent — no chat_postMessage."""
    from pf_runtime.config import OutboundMessage
    from pf_runtime.runtime.inbound_ledger import SqliteInboundLedger

    ledger_path = tmp_path / "dedup.sqlite"
    ledger = SqliteInboundLedger(ledger_path)
    ledger.record_outbound_sent("personal:evt-pre")

    ch = SlackChannel(
        profile_slug="personal",
        env_path=env_file,
        inbound_ledger=ledger,
    )
    app = _make_app_mock()
    ch._app = app
    ch._connected = True

    msg = OutboundMessage(
        channel="slack",
        profile_slug="personal",
        target_user_id="D123",
        text="hi",
        message_id="slack-reply-evt-pre",
        in_reply_to="evt-pre",
    )
    await ch.send(msg)
    assert app.client.chat_postMessage.await_count == 0


@pytest.mark.asyncio
async def test_outbound_ledger_second_send_skips_after_first_success(
    env_file: Path,
    tmp_path: Path,
) -> None:
    """First send records out_key; second identical logical reply skips Slack API."""
    from pf_runtime.config import OutboundMessage
    from pf_runtime.runtime.inbound_ledger import SqliteInboundLedger

    ledger = SqliteInboundLedger(tmp_path / "dedup2.sqlite")
    ch = SlackChannel(
        profile_slug="personal",
        env_path=env_file,
        inbound_ledger=ledger,
    )
    app = _make_app_mock()
    ch._app = app
    ch._connected = True

    msg = OutboundMessage(
        channel="slack",
        profile_slug="personal",
        target_user_id="D123",
        text="hello",
        message_id="slack-reply-E1",
        in_reply_to="E1",
    )
    await ch.send(msg)
    await ch.send(msg)
    assert app.client.chat_postMessage.await_count == 1


@pytest.mark.asyncio
async def test_outbound_dedup_skips_second_send(env_file: Path) -> None:
    from pf_runtime.config import OutboundMessage

    ch = SlackChannel(profile_slug="personal", env_path=env_file)
    app = _make_app_mock()
    ch._app = app
    ch._connected = True

    msg = OutboundMessage(
        channel="slack",
        profile_slug="personal",
        target_user_id="D123",
        text="hi",
        message_id="out-1",
    )
    await ch.send(msg)
    await ch.send(msg)
    assert app.client.chat_postMessage.await_count == 1


@pytest.mark.asyncio
async def test_send_posts_to_thread_when_thread_ts_present(env_file: Path) -> None:
    from pf_runtime.config import OutboundMessage

    ch = SlackChannel(profile_slug="personal", env_path=env_file)
    app = _make_app_mock()
    ch._app = app
    ch._connected = True

    msg = OutboundMessage(
        channel="slack",
        profile_slug="personal",
        target_user_id="D123",
        text="threaded hi",
        metadata={"thread_ts": "1700000000.000100"},
        message_id="out-threaded",
    )
    await ch.send(msg)

    app.client.chat_postMessage.assert_awaited_once_with(
        channel="D123",
        text="threaded hi",
        thread_ts="1700000000.000100",
    )


@pytest.mark.asyncio
async def test_send_rate_limited_maps_to_typed_error(env_file: Path) -> None:
    from pf_runtime.config import OutboundMessage

    ch = SlackChannel(profile_slug="personal", env_path=env_file)
    app = _make_app_mock()

    response = MagicMock()
    response.get = MagicMock(return_value="ratelimited")
    response.headers = MagicMock()
    response.headers.get = MagicMock(return_value="5")
    app.client.chat_postMessage = AsyncMock(
        side_effect=SlackApiError(message="rate limited", response=response)  # type: ignore[no-untyped-call]
    )
    ch._app = app
    ch._connected = True

    msg = OutboundMessage(
        channel="slack",
        profile_slug="personal",
        target_user_id="D123",
        text="hi",
        message_id="out-rl",
    )
    with pytest.raises(ChannelRateLimited) as excinfo:
        await ch.send(msg)
    assert excinfo.value.retry_after_seconds == 5


@pytest.mark.asyncio
async def test_send_invalid_auth_maps_to_auth_error(env_file: Path) -> None:
    from pf_runtime.config import OutboundMessage

    ch = SlackChannel(profile_slug="personal", env_path=env_file)
    app = _make_app_mock()

    response = MagicMock()
    response.get = MagicMock(return_value="invalid_auth")
    response.headers = MagicMock()
    response.headers.get = MagicMock(return_value="0")
    app.client.chat_postMessage = AsyncMock(
        side_effect=SlackApiError(message="invalid auth", response=response)  # type: ignore[no-untyped-call]
    )
    ch._app = app
    ch._connected = True

    msg = OutboundMessage(
        channel="slack",
        profile_slug="personal",
        target_user_id="D123",
        text="hi",
        message_id="out-auth",
    )
    with pytest.raises(ChannelAuthError):
        await ch.send(msg)
