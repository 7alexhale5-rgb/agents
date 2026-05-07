"""Channel adapter base class, registry, health type, and error hierarchy.

Locked contract: ``docs/ADAPTER_PLUGIN_INTERFACE.md`` (sub-phase 4.7.3).

Concrete channels (``slack``, ``telegram``, ``email``, ``discord``, ...) extend
the :class:`Channel` ABC and self-register in
``pf_runtime/channels/__init__.py`` via :class:`ChannelRegistry`.

Design notes:
    - Errors are a small explicit hierarchy so the runtime can branch on
      semantics (auth → fail-closed; rate-limit → backoff; transient
      connect → reconnect with epoch budget).
    - ``ChannelHealth`` is a simple dataclass; the default ``health()``
      implementation surfaces ``self._connected`` if the subclass tracks
      it as an attribute, else the subclass overrides.
    - ``ChannelRegistry`` is a class with a class-level dict; this keeps
      registration behavior identical to the contract example and makes
      lookup deterministic.
"""
from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import ClassVar

from pf_runtime.config import InboundMessage, OutboundMessage

# ----- error hierarchy -----


class ChannelError(Exception):
    """Base class for all channel adapter errors.

    Caught by the runtime's per-consumer reconnect loop. Subclasses convey
    enough semantics for the runtime to decide whether to retry, back off,
    or disable the channel entirely.
    """


class ChannelConnectError(ChannelError):
    """Raised when the channel could not establish (or re-establish) its
    long-lived transport (Socket Mode WebSocket, IMAP IDLE, etc.)."""


class ChannelAuthError(ChannelError):
    """Raised when credentials are missing, revoked, or rejected by the
    upstream service. Runtime should NOT retry on this error."""


class ChannelRateLimited(ChannelError):
    """Raised when the upstream service signals rate limiting.

    ``retry_after_seconds`` is the wait period the runtime should observe
    before the next attempt (typically lifted from a ``Retry-After``
    header).
    """

    def __init__(self, message: str = "rate limited", *, retry_after_seconds: int = 30) -> None:
        super().__init__(message)
        self.retry_after_seconds: int = retry_after_seconds


class ChannelMessageTooLarge(ChannelError):
    """Raised when an outbound message exceeds the upstream service's
    per-message size limit. Caller should split or truncate."""


# ----- health -----


@dataclass
class ChannelHealth:
    """Lightweight health probe result.

    ``ok`` reflects whether the channel believes its upstream connection
    is alive. ``detail`` carries an optional human-readable note (e.g.
    ``"reconnecting (attempt 3/5)"``).
    """

    ok: bool
    detail: str = ""


# ----- ABC -----


class Channel(abc.ABC):
    """Base class for all channel adapters.

    Concrete adapters must implement the six abstract methods below. The
    default :py:meth:`health` implementation surfaces ``self._connected``;
    subclasses that don't track that attribute should override.

    Attributes:
        name: Stable channel identifier (``"slack"``, ``"telegram"``, ...).
        profile_slug: The profile this channel instance serves. Set by
            the constructor of each concrete subclass.
        reconnect_attempts: Public counter the runtime increments inside
            an error epoch (see ADAPTER_PLUGIN_INTERFACE.md §Reconnect
            contract). Reset by the runtime on a successful reconnect.
    """

    name: str
    profile_slug: str
    reconnect_attempts: int = 0

    # Subclasses are expected to maintain this so the default health()
    # works without an override.
    _connected: bool = False

    @abc.abstractmethod
    async def connect(self) -> None:
        """Establish (or re-establish) the long-lived upstream connection.

        Must be idempotent — calling twice is a no-op if already connected.
        Raise :class:`ChannelConnectError` on transport failure or
        :class:`ChannelAuthError` on credential failure.
        """

    @abc.abstractmethod
    def receive(self) -> AsyncIterator[InboundMessage]:
        """Yield inbound messages until the channel is disconnected.

        ``InboundMessage.message_id`` MUST be set to a deduplication key
        (Slack: ``event_id``; Telegram: ``update_id``; Email: ``Message-ID``;
        Discord: ``id``).

        NOTE: This is declared as a regular method returning an
        ``AsyncIterator`` rather than ``async def`` so subclasses can
        implement it as an ``async def ... yield`` async generator
        cleanly. ``abc.abstractmethod`` works with both shapes.
        """

    @abc.abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """Send an outbound message.

        MUST be idempotent on ``msg.message_id``: if the same message_id
        was previously sent successfully, this call is a silent no-op.
        Implementations should record the message_id in their LRU AFTER
        a successful upstream API response so transient failures remain
        retryable.
        """

    @abc.abstractmethod
    async def typing(self, target_user_id: str, on: bool) -> None:
        """Set the typing indicator for ``target_user_id``.

        Channels with no native typing indicator (email, Slack bot DMs)
        silently succeed.
        """

    @abc.abstractmethod
    async def ack(self, message_id: str) -> None:
        """Mark inbound ``message_id`` as processed.

        Required for at-least-once delivery semantics. Some channels
        (Slack Socket Mode) ack at the transport layer automatically; in
        those cases this is a no-op.
        """

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Graceful shutdown — drain in-flight, close the connection.

        Best-effort: implementations should swallow and log exceptions
        rather than re-raising during shutdown.
        """

    async def health(self) -> ChannelHealth:
        """Health probe. Default surfaces ``self._connected``."""
        return ChannelHealth(ok=self._connected)


# ----- registry -----


class ChannelRegistry:
    """Process-wide registry of channel name → channel class.

    Concrete adapters register themselves at import time inside
    ``pf_runtime/channels/__init__.py``. The runtime looks up the class
    by name when constructing per-profile channels.
    """

    _registry: ClassVar[dict[str, type[Channel]]] = {}

    @classmethod
    def register(cls, name: str, klass: type[Channel]) -> None:
        """Register ``klass`` under ``name``. Idempotent — re-registering
        the same name overwrites the previous entry (safe for re-imports
        in tests)."""
        cls._registry[name] = klass

    @classmethod
    def get(cls, name: str) -> type[Channel]:
        """Return the registered channel class for ``name``.

        Raises:
            KeyError: if no channel is registered under ``name``. The
                error message includes the list of registered names so
                callers can diagnose typos quickly.
        """
        try:
            return cls._registry[name]
        except KeyError as exc:
            registered = sorted(cls._registry.keys())
            raise KeyError(
                f"No channel registered under {name!r}. "
                f"Registered channels: {registered}"
            ) from exc

    @classmethod
    def names(cls) -> list[str]:
        """Return the list of registered channel names (sorted)."""
        return sorted(cls._registry.keys())
