"""Read/propose policy for communications triage v1."""

from __future__ import annotations

from pf_runtime.communications.schema import ActionType, ProposedAction


class MutationNotAllowedError(PermissionError):
    """Raised when a live provider mutation is attempted in v1."""


_PROPOSABLE_ACTIONS = {
    ActionType.LABEL,
    ActionType.ARCHIVE,
    ActionType.MOVE_FOLDER,
    ActionType.MARK_READ,
    ActionType.TRASH,
    ActionType.UNSUBSCRIBE_DRAFT,
    ActionType.REPLY_DRAFT,
    ActionType.CALENDAR_HOLD,
    ActionType.CALENDAR_UPDATE,
    ActionType.FOLLOW_UP_TASK,
}


def assert_v1_action_allowed(action: ProposedAction, *, applying: bool = False) -> None:
    """Allow proposal creation, reject live application.

    This keeps Gmail ``gmail.modify``, Graph ``Mail.ReadWrite``, SMTP send, and
    calendar writes out of the v1 execution path even when an adapter exists.
    """
    if action.action_type not in _PROPOSABLE_ACTIONS:
        raise MutationNotAllowedError(f"unknown communications action: {action.action_type}")
    if applying:
        raise MutationNotAllowedError(
            "communications-triage v1 is read/propose only; "
            f"refusing to apply {action.action_type}"
        )
