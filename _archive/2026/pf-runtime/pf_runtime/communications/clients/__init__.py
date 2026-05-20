"""Sync, stdlib-only provider clients for communications triage v1.

Each client takes a :class:`RegistryEntry` plus a :class:`SyncStateStore` and
exposes a single :meth:`fetch_new` method returning raw provider payloads in
the shape the existing ``providers.normalize_*`` helpers already accept.

The clients re-check the manifest's ``forbidden_v1`` scopes at construction
time as defense-in-depth — even though the registry already enforces this,
construction failure here means a misconfigured caller cannot smuggle a
write-capable token into the read+propose pipeline.

No third-party HTTP libraries: the Gmail and Graph clients use
:mod:`urllib.request` (matching :mod:`pf_runtime.runtime.pfos_emit`); the
HostGator client uses :mod:`imaplib`. Tests inject ``urlopen`` and
``imap_factory`` callables to avoid network I/O.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import IO, Any, Protocol
from urllib.request import Request

from pf_runtime.communications.account_registry import (
    RegistryValidationError,
    ScopeViolationError,
)


class CredentialExpiredError(Exception):
    """Raised when a provider returns 401 / authentication failed.

    The operator is expected to refresh the credential env var
    (``PF_GMAIL_TOKEN_*`` / ``PF_GRAPH_TOKEN_*`` / ``PF_IMAP_PASSWORD_*``)
    and re-run; clients never attempt silent refresh in v1.
    """


class FetchError(Exception):
    """Raised when a non-auth, non-recoverable HTTP/IMAP error occurs."""


# A urlopen-shaped callable. ``urllib.request.urlopen`` matches this contract.
# Using a Protocol avoids over-specifying optional kwargs.
class UrlopenCallable(Protocol):
    def __call__(
        self, req: Request, timeout: float | None = ...
    ) -> IO[bytes]: ...


# IMAP factory shape: returns an object compatible with imaplib.IMAP4_SSL.
# Typed as ``Callable[..., Any]`` because imaplib classes do not declare a
# stable structural protocol.
ImapFactory = Callable[..., Any]


__all__ = [
    "CredentialExpiredError",
    "FetchError",
    "ImapFactory",
    "RegistryValidationError",
    "ScopeViolationError",
    "UrlopenCallable",
]
