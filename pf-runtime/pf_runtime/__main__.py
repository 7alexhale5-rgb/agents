"""CLI entry point for PF Runtime.

Usage:
    python -m pf_runtime run --profile <slug> --message <text>

Exit codes:
    0  — success (REPLY: ... printed to stdout)
    1  — any exception (traceback to stderr, nothing to stdout)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import traceback
from pathlib import Path

from pf_runtime.config import InboundMessage, load_profile
from pf_runtime.memory import MemoryStack
from pf_runtime.memory.tier1_soul import SoulReader
from pf_runtime.memory.tier2_buffer import BufferStore
from pf_runtime.memory.tier3_episodic import NoOpEpisodicClient
from pf_runtime.memory.tier4_skills import default_skill_registry
from pf_runtime.runtime.loop import run_session
from pf_runtime.runtime.model_adapter import OpenRouterAdapter


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pf_runtime",
        description="PrettyFly Runtime — bare-metal agent loop",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a single session")
    run_parser.add_argument(
        "--profile",
        required=True,
        help="Profile slug (e.g. 'personal')",
    )
    run_parser.add_argument(
        "--message",
        required=True,
        help="Message text to send to the agent",
    )
    run_parser.add_argument(
        "--hermes-home",
        default=None,
        help=(
            "Path to Hermes home directory (default: ~/.hermes). "
            "Useful for testing against a custom profile dir."
        ),
    )

    gateway_parser = subparsers.add_parser(
        "gateway",
        help="Run the long-running channel gateway",
    )
    gateway_parser.add_argument(
        "--profile",
        required=True,
        help="Profile slug (e.g. 'personal')",
    )
    gateway_parser.add_argument(
        "--hermes-home",
        default=None,
        help="Path to Hermes home directory (default: ~/.hermes)",
    )

    return parser


async def _run(profile_slug: str, message: str, hermes_home: Path) -> None:
    profile = load_profile(profile_slug, hermes_home=hermes_home)
    adapter = OpenRouterAdapter(env_path=profile.env_path)

    # Build the memory stack. BufferStore is used as a context manager so
    # the SQLite connection is properly closed after the session completes.
    soul_reader = SoulReader()
    with BufferStore(profile.slug) as buffer:
        memory = MemoryStack(
            soul=soul_reader,
            buffer=buffer,
            episodic=NoOpEpisodicClient(),
            skills=default_skill_registry(hermes_home),
        )

        inbound = InboundMessage(
            channel="cli",
            profile_slug=profile_slug,
            user_id="alex",
            text=message,
        )

        result = await run_session(
            profile,
            inbound,
            model_adapter=adapter,
            memory=memory,
        )

    # Extract reply outside the context manager (connection already closed).
    # The result object holds the messages in memory so this is safe.

    # Find the last assistant message
    assistant_reply = ""
    for msg in reversed(result.messages):
        if msg.role == "assistant":
            assistant_reply = msg.content
            break

    if not assistant_reply:
        raise RuntimeError("Session completed but no assistant reply was produced.")

    # Print on one line — strip internal newlines so output is grep-friendly
    reply_line = " ".join(assistant_reply.split())
    print(f"REPLY: {reply_line}")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "run":
        hermes_home = (
            Path(args.hermes_home) if args.hermes_home else Path.home() / ".hermes"
        )
        try:
            asyncio.run(_run(args.profile, args.message, hermes_home))
        except Exception:
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
    elif args.command == "gateway":
        from pf_runtime.runtime.gateway import run_gateway

        hermes_home = (
            Path(args.hermes_home) if args.hermes_home else Path.home() / ".hermes"
        )
        try:
            asyncio.run(run_gateway(args.profile, hermes_home))
        except Exception:
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help(sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
