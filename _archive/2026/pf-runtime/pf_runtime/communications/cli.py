"""Communications-triage CLI commands.

Adds the ``comms`` subcommand group to ``python -m pf_runtime``:

  pf_runtime comms proposals list [--status ...]
  pf_runtime comms proposals show <action_id>
  pf_runtime comms proposals approve <action_id>
  pf_runtime comms proposals reject <action_id>
  pf_runtime comms triage [--account <id>]

V1 boundary: approve/reject mutate the local SQLite only; no provider
calls are issued. ``triage`` runs the full read+propose flow against
configured accounts.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from pf_runtime.communications.account_registry import (
    AccountRegistry,
    RegistryEntry,
)
from pf_runtime.communications.proposal_store import ProposalStore
from pf_runtime.communications.sync_state_store import SyncStateStore
from pf_runtime.communications.tools import CreateProposalTool
from pf_runtime.communications.triage_skill import TriageRunResult, triage_all_accounts
from pf_runtime.config import load_profile
from pf_runtime.runtime.model_adapter import ModelAdapter, OpenRouterAdapter

DEFAULT_PROFILE_SLUG = "personal"
DEFAULT_CLASSIFIER_MODEL = "openrouter/cerebras/llama-3.1-8b-instruct"

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_MANIFEST = (
    _REPO_ROOT / "marketplace" / "manifests" / "communications-triage" / "manifest.json"
)


def register_subparser(subparsers: argparse._SubParsersAction[Any]) -> None:
    """Register the ``comms`` parser tree on the parent ``subparsers`` action."""
    comms = subparsers.add_parser("comms", help="Communications triage commands")
    comms_sub = comms.add_subparsers(dest="comms_command", required=True)

    proposals = comms_sub.add_parser("proposals", help="Manage proposed actions")
    proposals_sub = proposals.add_subparsers(dest="proposals_command", required=True)

    p_list = proposals_sub.add_parser("list", help="List proposed actions")
    p_list.add_argument(
        "--status",
        default="proposed",
        choices=["proposed", "approved", "rejected"],
    )
    p_list.add_argument("--limit", type=int, default=50)
    _add_profile_args(p_list)

    p_show = proposals_sub.add_parser("show", help="Show a proposal by action_id")
    p_show.add_argument("action_id")
    _add_profile_args(p_show)

    p_approve = proposals_sub.add_parser(
        "approve", help="Approve a proposal (no provider mutation in v1)"
    )
    p_approve.add_argument("action_id")
    _add_profile_args(p_approve)

    p_reject = proposals_sub.add_parser("reject", help="Reject a proposal")
    p_reject.add_argument("action_id")
    _add_profile_args(p_reject)

    triage = comms_sub.add_parser(
        "triage", help="Run a triage pass against configured accounts"
    )
    triage.add_argument("--account", help="Limit to a specific account_id", default=None)
    triage.add_argument(
        "--model",
        default=DEFAULT_CLASSIFIER_MODEL,
        help=f"Classifier model slug (default: {DEFAULT_CLASSIFIER_MODEL})",
    )
    triage.add_argument(
        "--registry",
        default=None,
        help=(
            "Path to account-registry.yaml "
            "(default: <hermes-home>/profiles/<profile>/account-registry.yaml)"
        ),
    )
    _add_profile_args(triage)


def _add_profile_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE_SLUG,
        help=f"Profile slug (default: {DEFAULT_PROFILE_SLUG})",
    )
    parser.add_argument(
        "--hermes-home",
        default=None,
        help="Path to Hermes home (default: ~/.hermes)",
    )


def handle(args: argparse.Namespace) -> int:
    """Dispatch to the right subcommand. Returns CLI exit code."""
    if args.comms_command == "proposals":
        return _handle_proposals(args)
    if args.comms_command == "triage":
        return _handle_triage(args)
    return 2


# ---------------------------------------------------------------------------
# proposals subgroup
# ---------------------------------------------------------------------------


def _resolve_db_path(profile_slug: str, hermes_home: str | None) -> Path:
    home = Path(hermes_home) if hermes_home else Path.home() / ".hermes"
    return home / "profiles" / profile_slug / "communications.sqlite"


def _handle_proposals(args: argparse.Namespace) -> int:
    db_path = _resolve_db_path(args.profile, args.hermes_home)
    store = ProposalStore(db_path)

    if args.proposals_command == "list":
        proposals = store.list(status=args.status, limit=args.limit)
        if not proposals:
            print(f"No {args.status} proposals.")
            return 0
        # Tab-separated for grep / awk friendliness.
        for p in proposals:
            ts = p.created_at.strftime("%Y-%m-%d %H:%M:%S")
            rationale_short = p.rationale[:60].replace("\t", " ").replace("\n", " ")
            print(
                f"{p.action_id}\t{p.action_type.value}\t{p.account_id}\t"
                f"{p.target_id}\t{ts}\t{rationale_short}"
            )
        return 0

    if args.proposals_command == "show":
        for status in ("proposed", "approved", "rejected"):
            for p in store.list(status=status, limit=10000):
                if p.action_id == args.action_id:
                    print(
                        json.dumps(
                            {
                                "action_id": p.action_id,
                                "action_type": p.action_type.value,
                                "account_id": p.account_id,
                                "target_id": p.target_id,
                                "rationale": p.rationale,
                                "payload": p.payload,
                                "status": p.status,
                                "created_at": p.created_at.isoformat(),
                            },
                            indent=2,
                        )
                    )
                    return 0
        print(f"proposal not found: {args.action_id}", file=sys.stderr)
        return 1

    if args.proposals_command in ("approve", "reject"):
        new_status = "approved" if args.proposals_command == "approve" else "rejected"
        try:
            store.mark_reviewed(args.action_id, status=new_status)
        except KeyError:
            print(f"proposal not found: {args.action_id}", file=sys.stderr)
            return 1
        print(f"{args.action_id}: {new_status}")
        return 0

    return 2


# ---------------------------------------------------------------------------
# triage subcommand
# ---------------------------------------------------------------------------


def _handle_triage(args: argparse.Namespace) -> int:
    home = Path(args.hermes_home) if args.hermes_home else Path.home() / ".hermes"
    try:
        profile = load_profile(args.profile, hermes_home=home)
    except FileNotFoundError as exc:
        print(f"profile not found: {exc}", file=sys.stderr)
        return 1

    registry_path = (
        Path(args.registry)
        if args.registry
        else home / "profiles" / args.profile / "account-registry.yaml"
    )
    if not registry_path.is_file():
        example = (
            _REPO_ROOT
            / "marketplace"
            / "manifests"
            / "communications-triage"
            / "account-registry.example.yaml"
        )
        print(f"account registry not found: {registry_path}", file=sys.stderr)
        print(f"copy {example} and fill in your accounts.", file=sys.stderr)
        return 1

    manifest_path = _DEFAULT_MANIFEST if _DEFAULT_MANIFEST.is_file() else None
    registry = AccountRegistry.load(
        registry_path, manifest_path=manifest_path, env=os.environ
    )

    if args.account:
        filtered = tuple(
            e for e in registry.entries if e.account.account_id == args.account
        )
        if not filtered:
            print(f"no account matching --account {args.account}", file=sys.stderr)
            return 1
        registry = AccountRegistry(entries=filtered)

    db_path = _resolve_db_path(args.profile, args.hermes_home)
    proposal_tool = CreateProposalTool(db_path)
    sync_store = SyncStateStore(db_path)
    adapter = _build_adapter(profile)

    result = asyncio.run(
        triage_all_accounts(
            registry,
            adapter=adapter,
            proposal_tool=proposal_tool,
            sync_store=sync_store,
            classifier_model=args.model,
            profile_slug=args.profile,
        )
    )

    print(_format_run_result(result))
    return 0 if result.errors == 0 else 1


def _build_adapter(profile: Any) -> ModelAdapter:
    """Construct the default adapter. Override via monkeypatch in tests."""
    return OpenRouterAdapter(env_path=profile.env_path)


def _format_run_result(result: TriageRunResult) -> str:
    duration = (result.finished_at - result.started_at).total_seconds()
    lines = [
        f"Triage run {result.run_id} — {duration:.1f}s",
        f"  proposals_created: {result.proposals_created}",
        f"  errors: {result.errors}",
        "  accounts:",
    ]
    for a in result.accounts:
        if a.error:
            status = f"ERROR {a.error}"
        else:
            status = (
                f"fetched={a.fetched} classified={a.classified} proposed={a.proposed}"
            )
        lines.append(f"    {a.account_id} ({a.provider.value}): {status}")
    return "\n".join(lines)


# Convenience for ad-hoc testing — not the canonical entrypoint.
def _entries_with_creds(registry: AccountRegistry) -> list[RegistryEntry]:
    return list(registry.with_credentials())
