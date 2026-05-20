"""Optional Sentry — initialized from profile ``.env`` (``SENTRY_DSN``).

DSN is read only via the same per-profile dotenv mapping as providers
(never logged). Install ``sentry-sdk`` via the ``runtime`` extra; if the
package is missing, a warning is logged once and startup continues.
"""
from __future__ import annotations

import logging
import os
from typing import Any, cast

from pf_runtime.config import Profile
from pf_runtime.runtime.model_adapter import _load_dotenv

_log = logging.getLogger(__name__)

_initialized = False


def reset_sentry_init_for_tests() -> None:
    """Test hook — do not use in production code."""
    global _initialized
    _initialized = False


def sentry_initialized() -> bool:
    """True after a successful ``sentry_sdk.init`` from this module."""
    return _initialized


def init_sentry_from_profile(profile: Profile, *, component: str) -> None:
    """Call once per process after ``load_profile`` when running gateway or CLI.

    Tags every event with ``profile_slug`` and ``pf_component``. Trace sampling
    defaults to 0; set ``SENTRY_TRACES_SAMPLE_RATE`` (env) to ``0.0``-``1.0``
    for performance monitoring.
    """
    global _initialized
    if _initialized:
        return

    env_map = _load_dotenv(profile.env_path)
    dsn = (env_map.get("SENTRY_DSN") or "").strip()
    if not dsn:
        return

    try:
        import sentry_sdk
    except ImportError:
        _log.warning(
            "SENTRY_DSN is set but sentry-sdk is not installed; "
            "pip install 'pf-runtime[runtime]' to enable",
        )
        return

    traces_raw = os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0")
    try:
        traces_sample_rate = max(0.0, min(1.0, float(traces_raw)))
    except ValueError:
        traces_sample_rate = 0.0

    environment = (
        os.environ.get("PF_ENV")
        or os.environ.get("SENTRY_ENVIRONMENT")
        or "development"
    )
    release = os.environ.get("PF_RELEASE") or os.environ.get("SENTRY_RELEASE")

    def _before_send(event: dict[str, Any], hint: object) -> dict[str, Any] | None:
        return event

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        before_send=cast(Any, _before_send),
    )
    sentry_sdk.set_tag("profile_slug", profile.slug)
    sentry_sdk.set_tag("pf_component", component)
    _initialized = True
    _log.info("sentry initialized (profile=%s component=%s)", profile.slug, component)
