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
    """Manual depth-limited walk that prunes skip dirs BEFORE descent.

    Recursive glob like `**/.hermes-spawn.json` walks the entire tree (millions of files
    in node_modules etc.) before filtering. os.walk with topdown=True lets us mutate
    `dirs` to prune subtrees before they're traversed.
    """
    agents = []
    if not PROJECTS_DIR.is_dir():
        return agents

    skip_dirs = {"node_modules", "_archive", ".git", ".next", "dist", "build",
                 ".venv", "venv", "target", ".turbo", ".cache", "__pycache__"}
    max_depth = 3  # ~/Projects/{a}/{b}/{c}/.hermes-spawn.json

    base_depth = len(PROJECTS_DIR.parts)
    for root, dirs, files in os.walk(PROJECTS_DIR, topdown=True, followlinks=False):
        depth = len(Path(root).parts) - base_depth
        if depth >= max_depth:
            dirs[:] = []  # don't descend further
            continue
        # Prune in-place — must mutate, not reassign, for os.walk to honor it.
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]

        if ".hermes-spawn.json" in files:
            spawn = Path(root) / ".hermes-spawn.json"
            data = load_json(spawn) or {}
            agent_id = data.get("agent_id") or data.get("id")
            if not agent_id:
                continue
            agents.append({
                "id": agent_id,
                "project": str(spawn.parent.relative_to(PROJECTS_DIR)),
                "path": str(spawn.parent),
                "source": "spawn-manifest",
            })
    return agents


def main():
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter_ns()
    peers = collect_profiles()
    project_agents = collect_project_agents()
    build_ms = (time.perf_counter_ns() - start) // 1_000_000

    out = {
        "schema": "hermes-registry/v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "build_ms": build_ms,
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
                f.write("ts\tbuild_ms\tpeer_count\tproject_agent_count\n")
            f.write(f"{out['generated_at']}\t{out['build_ms']}\t{out['peer_count']}\t{out['project_agent_count']}\n")


if __name__ == "__main__":
    sys.exit(main() or 0)
