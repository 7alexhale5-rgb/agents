"""In-process coverage for ``pf_runtime.__main__`` (pytest-cov attributes here)."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import pf_runtime.__main__ as m


def test_main_missing_subcommand_system_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["pf_runtime"])
    with pytest.raises(SystemExit):
        m.main()


def test_main_run_short_circuit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[object] = []

    def fake_run(coro: object, *a: object, **k: object) -> None:
        calls.append(coro)
        coro.close()  # type: ignore[attr-defined]

    import asyncio as asyncio_mod

    monkeypatch.setattr(asyncio_mod, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pf_runtime",
            "run",
            "--profile",
            "p",
            "--message",
            "hi",
            "--hermes-home",
            str(tmp_path),
        ],
    )
    m.main()
    assert len(calls) == 1


def test_main_gateway_short_circuit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[int] = []

    def fake_run(coro: object, *a: object, **k: object) -> None:
        calls.append(1)
        coro.close()  # type: ignore[attr-defined]

    import asyncio as asyncio_mod

    monkeypatch.setattr(asyncio_mod, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pf_runtime",
            "gateway",
            "--profile",
            "p",
            "--hermes-home",
            str(tmp_path),
        ],
    )
    m.main()
    assert len(calls) == 1


def test_main_run_exception_exits_one(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def boom(coro: object, *a: object, **k: object) -> None:
        coro.close()  # type: ignore[attr-defined]
        raise ValueError("nope")

    import asyncio as asyncio_mod

    monkeypatch.setattr(asyncio_mod, "run", boom)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pf_runtime",
            "run",
            "--profile",
            "p",
            "--message",
            "hi",
            "--hermes-home",
            str(tmp_path),
        ],
    )

    exit_codes: list[int] = []

    def capture_exit(code: int | str | None = None) -> None:
        exit_codes.append(int(code) if code is not None else 0)
        raise SystemExit(code)

    monkeypatch.setattr(sys, "exit", capture_exit)
    with pytest.raises(SystemExit):
        m.main()
    assert exit_codes == [1]


def test_main_gateway_exception_exits_one(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def boom(coro: object, *a: object, **k: object) -> None:
        coro.close()  # type: ignore[attr-defined]
        raise RuntimeError("gw")

    import asyncio as asyncio_mod

    monkeypatch.setattr(asyncio_mod, "run", boom)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pf_runtime",
            "gateway",
            "--profile",
            "p",
            "--hermes-home",
            str(tmp_path),
        ],
    )

    exit_codes: list[int] = []

    def capture_exit(code: int | str | None = None) -> None:
        exit_codes.append(int(code) if code is not None else 0)
        raise SystemExit(code)

    monkeypatch.setattr(sys, "exit", capture_exit)
    with pytest.raises(SystemExit):
        m.main()
    assert exit_codes == [1]


def test_main_unknown_command_prints_help(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = MagicMock()
    parser.parse_args.return_value = SimpleNamespace(command="__other__")

    monkeypatch.setattr(m, "_build_parser", lambda: parser)
    monkeypatch.setattr(sys, "argv", ["pf_runtime", "bogus"])

    exit_codes: list[int] = []

    def capture_exit(code: int | str | None = None) -> None:
        exit_codes.append(int(code) if code is not None else 0)
        raise SystemExit(code)

    monkeypatch.setattr(sys, "exit", capture_exit)
    with pytest.raises(SystemExit):
        m.main()
    parser.print_help.assert_called_once()
    assert exit_codes == [1]
