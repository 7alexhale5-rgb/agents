"""Normalized communications schema.

This module is provider-neutral on purpose. Gmail labels, Microsoft Graph
folders/categories, and IMAP folders all round-trip through ``provider_ids``
while the agent reasons over one stable message shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class Provider(StrEnum):
    GOOGLE_MAIL = "google_mail"
    GOOGLE_CALENDAR = "google_calendar"
    MICROSOFT_GRAPH = "microsoft_graph"
    IMAP_HOSTGATOR = "imap_hostgator"


class TriageBucket(StrEnum):
    NEEDS_ALEX_TODAY = "needs_alex_today"
    NEEDS_REPLY = "needs_reply"
    SCHEDULE = "schedule"
    WAITING = "waiting"
    FYI = "fyi"
    PROMOTION = "promotion"
    RELEASE_UPDATE = "release_update"
    NOISE = "noise"


class ActionType(StrEnum):
    LABEL = "label"
    ARCHIVE = "archive"
    MOVE_FOLDER = "move_folder"
    MARK_READ = "mark_read"
    TRASH = "trash"
    UNSUBSCRIBE_DRAFT = "unsubscribe_draft"
    REPLY_DRAFT = "reply_draft"
    CALENDAR_HOLD = "calendar_hold"
    CALENDAR_UPDATE = "calendar_update"
    FOLLOW_UP_TASK = "follow_up_task"


@dataclass(frozen=True)
class AccountConfig:
    """One connected mailbox or calendar account."""

    account_id: str
    provider: Provider
    address: str
    display_name: str = ""
    scopes: tuple[str, ...] = ()
    read_only: bool = True


@dataclass(frozen=True)
class AttachmentMeta:
    filename: str
    mime_type: str = ""
    size_bytes: int | None = None
    provider_id: str | None = None


@dataclass(frozen=True)
class ProposedAction:
    """A proposed mutation or operator-facing follow-up.

    ``status`` starts as ``proposed``. V1 never applies mailbox/calendar
    mutations directly; approval is handled by a separate operator flow.
    """

    action_id: str
    action_type: ActionType
    account_id: str
    target_id: str
    rationale: str
    payload: dict[str, Any] = field(default_factory=dict)
    status: str = "proposed"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class NormalizedMessage:
    account_id: str
    provider: Provider
    address: str
    folder_or_label: str
    message_id: str
    thread_id: str | None
    sender: str
    recipients: tuple[str, ...]
    subject: str
    received_at: datetime
    snippet: str
    body_text_ref: str | None = None
    attachments_meta: tuple[AttachmentMeta, ...] = ()
    importance_score: float = 0.0
    triage_bucket: TriageBucket = TriageBucket.FYI
    proposed_actions: tuple[ProposedAction, ...] = ()
    provider_ids: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CalendarEvent:
    account_id: str
    provider: Provider
    address: str
    event_id: str
    calendar_id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    attendees: tuple[str, ...] = ()
    location: str | None = None
    provider_ids: dict[str, str] = field(default_factory=dict)
