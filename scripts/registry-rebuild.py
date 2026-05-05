#!/usr/bin/env python3
"""
registry-rebuild.py — Phase 0 substrate primitive.

Walks Hermes profiles and project-spawn manifests, emits ~/.hermes/registry.json.
Decision #4: flat-file registry, 5-min cron rebuild. Atomic write via os.replace.

Native Python (no jq subprocess storm) keeps build time well under the 200ms p95 gate.

Schema (stable, additive only):
  {
    "schema": "hermes-registry/v1",
    "generated_at": "...",
    "build_ms": 12,
    "peer_count": 13,
    "project_agent_count": 0,
    "peers": [...],
    "project_agents": [...]
  }
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
PROFILES_DIR = Path(os.environ.get("HERMES_PROFILES_DIR", HOME / "Projects/agents/hermes/profiles"))
PROJECTS_DIR = Path(os.environ.get("PROJECTS_DIR", HOME / "Projects"))
REGISTRY_DIR = Path(os.environ.get("HERMES_HOME", HOME / ".hermes"))
REGISTRY_FILE = REGISTRY_DIR / "registry.json"

DEFAULT_COST_ENVELOPE = {"budget_usd_per_day": 0, "alert_threshold_pct": 80}


def load_json(path: Path):
    try:
        with path.open("r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def collect_profiles():
    peers = []
    if not PROFILES_DIR.is_dir():
        return peers

    for entry in sorted(PROFILES_DIR.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        manifest = load_json(entry / "manifest.json") or {}
        a2a = load_json(entry / "a2a-card.json") or {}
        paused = (entry / "PAUSED").exists()

        peer = {
            "id": name,
            "tier": manifest.get("tier"),
            "status": "paused" if paused else "active",
            "scaffold_status": manifest.get("status", "active"),
            "side_effects": a2a.get("side_effects", []),
            "eval_suite_uri": a2a.get("eval_suite_uri"),
            "cost_envelope": a2a.get("cost_envelope", DEFAULT_COST_ENVELOPE),
            "channels": a2a.get("channels") or manifest.get("channels", []),
            "source": "profile",
        }
        peers.append(peer)
    return peers


def collect_project_agents():
    """Depth-1 iterdir over ~/Projects/ — looks for .hermes-spawn.json at each
    project root only. Convention (decision #9): one spawn manifest per project
    root. Nested sub-projects (e.g. koho/consult-ops) register at their own
    kebab-case top-level path or via a multi-agent root manifest.

    Profiling under cold OS cache showed os.walk at depth=3 cost 150-200ms across
    the 64 top-level Projects/ entries while returning zero manifests in Phase 0.
    Depth-1 iterdir is ~5ms cold and matches the actual contract.
    """
    agents = []
    if not PROJECTS_DIR.is_dir():
        return agents

    for project in sorted(PROJECTS_DIR.iterdir()):
        if not project.is_dir():
            continue
        # Skip hidden, archive, and template dirs
        if project.name.startswith(".") or project.name.startswith("_"):
            continue

        spawn = project / ".hermes-spawn.json"
        if not spawn.is_file():
            continue

        data = load_json(spawn) or {}
        agent_id = data.get("agent_id") or data.get("id")
        if not agent_id:
            continue

        agents.append({
            "id": agent_id,
            "project": project.name,
            "path": str(project),
            "source": "spawn-manifest",
        })
    return agents


def main():
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter_ns()

    t0 = time.perf_counter_ns()
    peers = collect_profiles()
    profiles_ms = (time.perf_counter_ns() - t0) // 1_000_000

    t1 = time.perf_counter_ns()
    project_agents = collect_project_agents()
    projects_ms = (time.perf_counter_ns() - t1) // 1_000_000

    build_ms = (time.perf_counter_ns() - start) // 1_000_000

    out = {
        "schema": "hermes-registry/v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "build_ms": build_ms,
        "profiles_ms": profiles_ms,
        "projects_ms": projects_ms,
        "peer_count": len(peers),
        "project_agent_count": len(project_agents),
        "peers": peers,
        "project_agents": project_agents,
    }

    tmp = REGISTRY_FILE.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    os.replace(tmp, REGISTRY_FILE)

    summary = {
        "peer_count": out["peer_count"],
        "project_agent_count": out["project_agent_count"],
        "build_ms": out["build_ms"],
    }
    print(f"{REGISTRY_FILE} built: {json.dumps(summary)}")

    # --tsv flag: append a single row to the soak log so the 24h gate can compute p95.
    if "--tsv" in sys.argv:
        tsv = HOME / "Assets/logs/registry-rebuild.tsv"
        tsv.parent.mkdir(parents=True, exist_ok=True)
        new_file = not tsv.exists()
        with tsv.open("a") as f:
            if new_file:
                f.write("ts\tbuild_ms\tpeer_count\tproject_agent_count\tprofiles_ms\tprojects_ms\n")
            f.write(f"{out['generated_at']}\t{out['build_ms']}\t{out['peer_count']}\t{out['project_agent_count']}\t{out['profiles_ms']}\t{out['projects_ms']}\n")


if __name__ == "__main__":
    sys.exit(main() or 0)
