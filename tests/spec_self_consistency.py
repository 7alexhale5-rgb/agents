"""Spec self-consistency check — Phase 4.7 pre-work.

Asserts every named contract in `pf-runtime/SPEC.md` has a stub implementation in
`pf-runtime/stubs/`. Failing this test means SPEC.md cites APIs that nobody can
build against.
"""
from __future__ import annotations

import inspect


def test_all_spec_dataclasses_importable() -> None:
    """Every dataclass referenced in SPEC.md compiles."""
    from pf_runtime.stubs import spec_stubs as s

    expected_dataclasses = {
        "Manifest", "MCPServerSpec", "ChannelSpec", "Config",
        "A2ACard", "Pricing", "Profile",
        "Attachment", "Message", "InboundMessage", "OutboundMessage",
        "MutationProposal", "ToolContext", "ToolResult", "SessionResult",
    }
    actual = {name for name, obj in inspect.getmembers(s, inspect.isclass)}
    missing = expected_dataclasses - actual
    assert not missing, f"SPEC.md cites these dataclasses but stubs are missing: {missing}"


def test_channel_abc_has_all_required_methods() -> None:
    """Channel ABC has the 6 required abstract methods per ADAPTER_PLUGIN_INTERFACE.md."""
    from pf_runtime.stubs.spec_stubs import Channel

    required = {"connect", "receive", "send", "typing", "ack", "disconnect"}
    abstract = set(Channel.__abstractmethods__)
    missing = required - abstract
    assert not missing, f"Channel ABC missing abstract methods: {missing}"


def test_tool_abc_has_invoke() -> None:
    """Tool ABC has the invoke abstract method."""
    from pf_runtime.stubs.spec_stubs import Tool

    assert "invoke" in Tool.__abstractmethods__, "Tool.invoke must be abstract"


def test_channel_errors_inheritance() -> None:
    """All ChannelError subclasses inherit from ChannelError."""
    from pf_runtime.stubs.spec_stubs import (
        ChannelAuthError,
        ChannelConnectError,
        ChannelError,
        ChannelMessageTooLarge,
        ChannelRateLimited,
    )

    for cls in [ChannelConnectError, ChannelAuthError, ChannelRateLimited, ChannelMessageTooLarge]:
        assert issubclass(cls, ChannelError), f"{cls.__name__} must inherit ChannelError"


if __name__ == "__main__":
    import sys

    test_all_spec_dataclasses_importable()
    test_channel_abc_has_all_required_methods()
    test_tool_abc_has_invoke()
    test_channel_errors_inheritance()
    print("[PASS] spec_self_consistency.py: all 4 contracts verified")
    sys.exit(0)
