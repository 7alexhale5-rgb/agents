"""Channel adapter package — channels self-register on import.

Importing this package triggers registration of every concrete adapter
into :class:`ChannelRegistry`. The runtime / gateway looks adapters up by
name (e.g. ``ChannelRegistry.get("slack")``); it never imports concrete
classes directly. Adding a new channel = drop a module here + register it
in this file.
"""
from pf_runtime.channels.adapter_base import (
    Channel,
    ChannelAuthError,
    ChannelConnectError,
    ChannelError,
    ChannelHealth,
    ChannelMessageTooLarge,
    ChannelRateLimited,
    ChannelRegistry,
)
from pf_runtime.channels.slack import SlackChannel

ChannelRegistry.register("slack", SlackChannel)

__all__ = [
    "Channel",
    "ChannelAuthError",
    "ChannelConnectError",
    "ChannelError",
    "ChannelHealth",
    "ChannelMessageTooLarge",
    "ChannelRateLimited",
    "ChannelRegistry",
    "SlackChannel",
]
