# Channel adapter plugin interface

> **Status:** locked 2026-05-06 per architecture-finding-5 in Phase 4.7 PLAN.md §6.D. Slack adapter (sub-phase 4.7.3) ships against this contract.

## Goals

1. **Channels are drop-in replaceable.** A new adapter (e.g., WhatsApp) ships as one new file; runtime picks it up via registry.
2. **Loop primitive never imports a channel concrete.** `runtime/loop.py` only imports the `Channel` ABC.
3. **Idempotency is contractual, not best-effort.** Runtime can crash and restart; outbound messages don't double-send.
4. **Reconnect is the channel's job, not the runtime's.** Runtime emits `ChannelError` and the channel decides how to recover.

## The ABC

```python
# pf-runtime/channels/adapter_base.py

import abc
from typing import AsyncIterator
from pf_runtime.config import InboundMessage, OutboundMessage

class Channel(abc.ABC):
    name: str  # "slack" | "telegram" | "email" | "discord" | ...
    profile_slug: str  # the profile this channel instance serves

    @abc.abstractmethod
    async def connect(self) -> None:
        """Idempotent. Establish whatever long-lived connection the channel needs.
        Slack: open Socket Mode WebSocket.
        Telegram: start long-poll loop.
        Email: open IMAP IDLE.
        Discord: open Gateway connection.
        Called once at runtime startup; called again on ChannelError recovery."""

    @abc.abstractmethod
    async def receive(self) -> AsyncIterator[InboundMessage]:
        """Async iterator over inbound messages for this profile.
        InboundMessage.message_id MUST be set to a deduplication key
        (Slack: event_id; Telegram: update_id; Email: Message-ID; Discord: id).
        Runtime de-duplicates on this key at the Kanban store layer."""

    @abc.abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """Send outbound message. MUST be idempotent on msg.message_id —
        if msg.message_id was previously sent successfully, this is a no-op.
        Runtime may call send() multiple times for the same message_id during
        retry; channel is responsible for the dedup."""

    @abc.abstractmethod
    async def typing(self, target_user_id: str, on: bool) -> None:
        """Set typing indicator. No-op channels (email) silently succeed."""

    @abc.abstractmethod
    async def ack(self, message_id: str) -> None:
        """Mark inbound message_id as processed. Channel updates its
        state (e.g., Slack: nothing needed; Telegram: advance long-poll offset;
        Email: mark IMAP \\Seen). Required for at-least-once delivery."""

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Graceful shutdown. Drain in-flight messages. Close connection."""

    # Optional hooks (ABC provides no-op defaults)
    async def health(self) -> ChannelHealth:
        """Health probe. Default: True if connected, else False."""
        return ChannelHealth(ok=self._connected)
```

## Lifecycle

```
runtime.start()
  → for each profile in profiles:
      for each channel_name in profile.config.channels:
          channel = ChannelRegistry.get(channel_name).create(profile)
          await channel.connect()
          asyncio.create_task(consume_inbound(channel))

# consume_inbound loop:
async def consume_inbound(channel: Channel):
    while not runtime.shutdown:
        try:
            async for msg in channel.receive():
                await runtime.kanban.enqueue(msg)
                await channel.ack(msg.message_id)
        except ChannelError as e:
            log.warning("channel %s error: %s", channel.name, e)
            await asyncio.sleep(backoff(channel.reconnect_attempts))
            await channel.connect()
            channel.reconnect_attempts += 1

runtime.stop()
  → for each channel: await channel.disconnect()
```

## Errors

```python
class ChannelError(Exception): ...
class ChannelConnectError(ChannelError): ...
class ChannelAuthError(ChannelError): ...
class ChannelRateLimited(ChannelError):
    retry_after_seconds: int
class ChannelMessageTooLarge(ChannelError): ...
```

## Reconnect contract

- Runtime calls `channel.connect()` **once** at startup. This is the "initial" call (1 call per startup, not counted against the reconnect budget).
- On `ChannelError` during `receive()` or `send()`, the runtime opens a new **error epoch**: it sleeps with exponential backoff (jittered, base 1s, max 60s) and calls `connect()` again. Each error epoch budgets **N=5 reconnect attempts**; the total `connect()` call count per epoch is therefore **1 (startup) + up to 5 (epoch retries) = 6 maximum** before the runtime gives up on this epoch.
- A successful `connect()` (any one of the 5 attempts) closes the current error epoch and resets `channel.reconnect_attempts = 0`. The next `ChannelError` opens a fresh epoch with its own N=5 budget.
- After 5 failed reconnect attempts within a single epoch, runtime calls `disconnect()` and removes the channel from the active set; alerts `forge-audit`.
- Operator can re-enable via `pf-runtime channel restart --profile <slug> --channel <name>` — this is a fresh startup-equivalent call, not a reconnect.

**Why this matters.** "Max 5 attempts" without epoch semantics is ambiguous: an adapter that flaps every 30 seconds for an hour would silently consume the budget across 120 unrelated incidents. With per-epoch resets, intermittent failures don't accumulate; only sustained inability to reconnect (5 consecutive failures inside one epoch) trips the disable.

## Idempotency contract

| Direction | Key                          | Where dedup happens                                                                                      |
| --------- | ---------------------------- | -------------------------------------------------------------------------------------------------------- |
| Inbound   | `InboundMessage.message_id`  | Kanban store (`UNIQUE(profile_slug, message_id)` constraint)                                             |
| Outbound  | `OutboundMessage.message_id` | Channel adapter (channel decides storage; defaults to in-memory LRU of last 10K message_ids per profile) |

If runtime crashes after `send()` but before `ack()` of the inbound that triggered it, on restart:

1. Runtime re-reads inbound from channel (channel hasn't acked, so it redelivers).
2. Runtime sees inbound `message_id` in Kanban → no-op enqueue.
3. Runtime continues processing pending tasks; outbound that was already sent is rejected at channel layer (LRU hit).

End-to-end semantics: at-least-once inbound + exactly-once outbound. Acceptable for our use case (vs exactly-once both directions, which requires distributed transactions we don't need).

## Registry

```python
# pf-runtime/channels/__init__.py

class ChannelRegistry:
    _registry: dict[str, type[Channel]] = {}

    @classmethod
    def register(cls, name: str, klass: type[Channel]) -> None:
        cls._registry[name] = klass

    @classmethod
    def get(cls, name: str) -> type[Channel]:
        return cls._registry[name]

# Adapters self-register on import
ChannelRegistry.register("slack", SlackChannel)
ChannelRegistry.register("telegram", TelegramChannel)
ChannelRegistry.register("email", EmailChannel)
ChannelRegistry.register("discord", DiscordChannel)
```

## Test gates (sub-phase 4.7.3)

- `tests/channel_abc_test.py` — mock `Channel` implementation; runtime exercises full lifecycle. Chaos test: 10 connection drops; assert zero message duplication, zero missed.
- `tests/slack_idempotency.py` — inject duplicate `event_id`; assert second send is no-op.
- `tests/slack_reconnect.py` — kill Socket Mode connection mid-session; assert reconnect within 5s; zero message loss.
- `tests/slack_parity.py` — 50-message parity test on `atlas-ceo` shadow workspace vs Hermes; identical action sequences (set equality on tool calls).

## Adding a new channel (e.g., WhatsApp post-cutover)

1. Create `pf-runtime/channels/whatsapp.py` extending `Channel` ABC.
2. Implement 6 abstract methods.
3. Register in `pf-runtime/channels/__init__.py`.
4. Add `whatsapp: ...` to profile `config.yaml`.
5. Run `tests/channel_abc_test.py` against the new adapter.
6. No runtime code changes. No loop primitive changes. No memory tier changes.
