"""CLI entrypoint — help and error paths via subprocess."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run_pf_runtime(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pf_runtime", *argv],
        cwd=_PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_main_missing_subcommand_exits_error() -> None:
    r = _run_pf_runtime([])
    assert r.returncode != 0


def test_run_help_exits_zero() -> None:
    r = _run_pf_runtime(["run", "--help"])
    assert r.returncode == 0
    assert "--profile" in r.stdout
    assert "--message" in r.stdout


def test_gateway_help_exits_zero() -> None:
    r = _run_pf_runtime(["gateway", "--help"])
    assert r.returncode == 0
    assert "--profile" in r.stdout


def test_run_missing_message_exits_nonzero() -> None:
    r = _run_pf_runtime(["run", "--profile", "nope"])
    assert r.returncode != 0


@pytest.mark.skipif(
    not (Path.home() / ".hermes" / "profiles" / "personal").is_dir(),
    reason="Hermes personal profile not present on this machine",
)
def test_run_invocation_smoke_local_profile() -> None:
    r = _run_pf_runtime(
        [
            "run",
            "--profile",
            "personal",
            "--message",
            "hello",
            "--hermes-home",
            str(Path.home() / ".hermes"),
        ],
    )
    assert r.returncode in (0, 1)

