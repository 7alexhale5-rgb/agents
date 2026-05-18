"""Communications triage primitives for mail + calendar connectors.

V1 is deliberately read/propose only: provider adapters normalize source
objects, and every mailbox/calendar mutation is represented as a proposal.
"""

from pf_runtime.communications.policy import (
    MutationNotAllowedError,
    assert_v1_action_allowed,
)
from pf_runtime.communications.proposal_store import ProposalStore
from pf_runtime.communications.schema import (
    AccountConfig,
    AttachmentMeta,
    CalendarEvent,
    NormalizedMessage,
    ProposedAction,
    TriageBucket,
)

__all__ = [
    "AccountConfig",
    "AttachmentMeta",
    "CalendarEvent",
    "MutationNotAllowedError",
    "NormalizedMessage",
    "ProposalStore",
    "ProposedAction",
    "TriageBucket",
    "assert_v1_action_allowed",
]
