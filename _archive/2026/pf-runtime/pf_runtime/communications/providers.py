"""Provider normalization helpers for communications triage.

These helpers do not call remote APIs. They convert provider payloads already
returned by Gmail, Microsoft Graph, or IMAP clients into the normalized schema.
Live OAuth/IMAP clients can be added behind these shapes without changing the
agent policy layer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from email.message import Message as EmailMessage
from email.utils import parsedate_to_datetime
from typing import Any

from pf_runtime.communications.schema import (
    AccountConfig,
    AttachmentMeta,
    NormalizedMessage,
    Provider,
)


def _parse_dt(raw: str | None) -> datetime:
    if not raw:
        return datetime.fromtimestamp(0, tz=UTC)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        dt = parsedate_to_datetime(raw)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _addr(value: Any) -> str:
    if isinstance(value, dict):
        email = value.get("emailAddress")
        if isinstance(email, dict):
            return str(email.get("address") or "")
        return str(value.get("address") or "")
    return str(value or "")


def _addresses(values: list[str]) -> tuple[str, ...]:
    out: list[str] = []
    for value in values:
        for chunk in value.split(","):
            item = chunk.strip()
            if not item:
                continue
            if "<" in item and ">" in item:
                item = item.split("<", maxsplit=1)[1].split(">", maxsplit=1)[0].strip()
            if "@" in item:
                out.append(item)
    return tuple(out)


def normalize_gmail_message(
    account: AccountConfig,
    raw: dict[str, Any],
    *,
    folder_or_label: str = "INBOX",
) -> NormalizedMessage:
    raw_payload = raw.get("payload")
    payload = raw_payload if isinstance(raw_payload, dict) else {}
    headers = {
        str(h.get("name", "")).lower(): str(h.get("value", ""))
        for h in _list(payload.get("headers"))
        if isinstance(h, dict)
    }
    raw_labels = raw.get("labelIds")
    labels = raw_labels if isinstance(raw_labels, list) else []
    recipients = _addresses([headers.get("to", ""), headers.get("cc", ""), headers.get("bcc", "")])
    sender = _addresses([headers.get("from", "")])
    received_at = _parse_dt(headers.get("date"))
    attachments = _gmail_attachments(payload)
    return NormalizedMessage(
        account_id=account.account_id,
        provider=Provider.GOOGLE_MAIL,
        address=account.address,
        folder_or_label=folder_or_label or ",".join(str(x) for x in labels),
        message_id=str(raw.get("id", "")),
        thread_id=str(raw.get("threadId")) if raw.get("threadId") else None,
        sender=sender[0] if sender else headers.get("from", ""),
        recipients=recipients,
        subject=headers.get("subject", ""),
        received_at=received_at,
        snippet=str(raw.get("snippet", "")),
        attachments_meta=tuple(attachments),
        provider_ids={
            "gmail_message_id": str(raw.get("id", "")),
            "gmail_thread_id": str(raw.get("threadId", "")),
        },
    )


def _gmail_attachments(payload: dict[str, Any]) -> list[AttachmentMeta]:
    out: list[AttachmentMeta] = []
    raw_parts = payload.get("parts") or []
    if not isinstance(raw_parts, list):
        return out
    for part in raw_parts:
        if not isinstance(part, dict):
            continue
        filename = str(part.get("filename") or "")
        raw_body = part.get("body")
        body = raw_body if isinstance(raw_body, dict) else {}
        attachment_id = body.get("attachmentId") if isinstance(body, dict) else None
        if filename or attachment_id:
            out.append(
                AttachmentMeta(
                    filename=filename,
                    mime_type=str(part.get("mimeType") or ""),
                    size_bytes=body.get("size") if isinstance(body.get("size"), int) else None,
                    provider_id=str(attachment_id) if attachment_id else None,
                )
            )
    return out


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def normalize_graph_message(
    account: AccountConfig,
    raw: dict[str, Any],
    *,
    folder_or_label: str = "inbox",
) -> NormalizedMessage:
    recipients = tuple(
        _addr(r)
        for key in ("toRecipients", "ccRecipients", "bccRecipients")
        for r in _list(raw.get(key))
        if isinstance(r, dict)
    )
    attachments = tuple(
        AttachmentMeta(
            filename=str(a.get("name") or ""),
            mime_type=str(a.get("contentType") or ""),
            size_bytes=a.get("size") if isinstance(a.get("size"), int) else None,
            provider_id=str(a.get("id")) if a.get("id") else None,
        )
        for a in _list(raw.get("attachments"))
        if isinstance(a, dict)
    )
    return NormalizedMessage(
        account_id=account.account_id,
        provider=Provider.MICROSOFT_GRAPH,
        address=account.address,
        folder_or_label=folder_or_label,
        message_id=str(raw.get("id", "")),
        thread_id=str(raw.get("conversationId")) if raw.get("conversationId") else None,
        sender=_addr(raw.get("sender")),
        recipients=recipients,
        subject=str(raw.get("subject") or ""),
        received_at=_parse_dt(str(raw.get("receivedDateTime") or "")),
        snippet=str(raw.get("bodyPreview") or ""),
        attachments_meta=attachments,
        provider_ids={
            "graph_message_id": str(raw.get("id", "")),
            "graph_conversation_id": str(raw.get("conversationId", "")),
        },
    )


def normalize_imap_message(
    account: AccountConfig,
    message: EmailMessage,
    *,
    uid: str,
    folder: str = "INBOX",
) -> NormalizedMessage:
    recipients = _addresses([message.get("to", ""), message.get("cc", ""), message.get("bcc", "")])
    sender = _addresses([message.get("from", "")])
    attachments: list[AttachmentMeta] = []
    if message.is_multipart():
        for part in message.walk():
            filename = part.get_filename()
            if filename:
                attachment_payload = part.get_payload(decode=True)
                size = len(attachment_payload) if isinstance(attachment_payload, bytes) else None
                attachments.append(
                    AttachmentMeta(
                        filename=filename,
                        mime_type=part.get_content_type(),
                        size_bytes=size,
                    )
                )
    subject = str(message.get("subject", ""))
    return NormalizedMessage(
        account_id=account.account_id,
        provider=Provider.IMAP_HOSTGATOR,
        address=account.address,
        folder_or_label=folder,
        message_id=uid,
        thread_id=message.get("thread-index") or message.get("references"),
        sender=sender[0] if sender else str(message.get("from", "")),
        recipients=recipients,
        subject=subject,
        received_at=_parse_dt(message.get("date")),
        snippet=_plain_snippet(message),
        attachments_meta=tuple(attachments),
        provider_ids={"imap_uid": uid, "imap_message_id": str(message.get("message-id", ""))},
    )


def _plain_snippet(message: EmailMessage, limit: int = 240) -> str:
    parts = message.walk() if message.is_multipart() else [message]
    for part in parts:
        if part.get_content_type() != "text/plain":
            continue
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes):
            continue
        charset = part.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")
        return " ".join(text.split())[:limit]
    return ""
