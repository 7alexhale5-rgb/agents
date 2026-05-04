#!/usr/bin/env python3
"""
LAIK MCP server — Phase 4.5 fusion entrypoint.

Wraps LAIK's hybrid RAG + ReAct orchestrator + MCPToolbox (SQL tools + mutation_proposals
two-phase protocol) as a stdio MCP server consumable by any Hermes profile.

Tools exposed:
  - laik_status                  health + tenant list
  - laik_list_tenants            available LAIK tenants on this host
  - laik_query                   ReAct loop: hybrid RAG + SQL tools fused into one answer
  - laik_search_only             pure HybridRetriever.search() — top-k chunks with citations
  - laik_list_tools              read+write tool names available for a tenant (from mcp.yaml)
  - laik_propose_mutation        write tool — creates a mutation_proposal (NOT executed)
  - laik_confirm_mutation        execute a previously-proposed mutation by ID
  - laik_reject_mutation         reject a proposed mutation by ID

Architectural rules (from LAIK CLAUDE.md + ADR-001 cross-repo grant boundary):
  - Read-only by default; writes always go through propose-not-execute
  - Per-tenant isolation enforced at PG role level (mcp_readonly / mcp_writer)
  - Ragas faithfulness gate (0.85) is enforced upstream by LAIK; this server doesn't bypass it
  - Cross-repo grant boundary preserved: LAIK owns LAIK schema only

Usage:
  Add to a Hermes profile's config.yaml:

      mcp_servers:
        laik:
          command: /Users/alexhale/Projects/agents/mcp-servers/laik/.venv/bin/python
          args: ["/Users/alexhale/Projects/agents/mcp-servers/laik/server.py"]
          env:
            LAIK_ROOT: /Users/alexhale/Projects/local-ai-kit
            LAIK_TENANT: consult-ops
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Make LAIK importable. The MCP server doesn't bundle LAIK; it consumes the
# operator's existing install at LAIK_ROOT (default ~/Projects/local-ai-kit/).
LAIK_ROOT = Path(os.environ.get("LAIK_ROOT", str(Path.home() / "Projects" / "local-ai-kit")))
if not LAIK_ROOT.exists():
    print(
        f"laik MCP: LAIK_ROOT does not exist: {LAIK_ROOT}\n"
        "Set LAIK_ROOT in the profile config to the correct path.",
        file=sys.stderr,
    )
    sys.exit(2)

sys.path.insert(0, str(LAIK_ROOT))

# Lazy import — only when a tool is called, so missing optional deps don't crash startup.
def _import_laik():
    # Verified against LAIK API surface 2026-05-04:
    #   - kit.retrieval.pipeline.HybridRetriever(tenant).search(query, top_k=N) -> list[Hit]
    #   - kit.orchestrator.react_loop.run_query(...) -> OrchestratorResult
    #   - kit.orchestrator.tools.MCPToolbox(tenant) with .propose/.confirm/.reject/.execute/.tool_names
    from kit.retrieval.pipeline import HybridRetriever  # type: ignore  # noqa
    from kit.orchestrator import react_loop  # type: ignore  # noqa
    from kit.orchestrator.tools import MCPToolbox  # type: ignore  # noqa
    return HybridRetriever, react_loop, MCPToolbox


# ---------- MCP server ----------

from mcp.server import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402
from mcp.types import Tool, TextContent  # noqa: E402

server: Server = Server("laik")

DEFAULT_TENANT = os.environ.get("LAIK_TENANT", "consult-ops")
TENANTS_DIR = LAIK_ROOT / "tenants"


def list_tenants() -> list[str]:
    if not TENANTS_DIR.exists():
        return []
    return [
        d.name
        for d in TENANTS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "config.yaml").exists()
    ]


# ---------- tools ----------

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="laik_status",
            description=(
                "Health check + tenant inventory. Call this first to verify LAIK is reachable "
                "and to learn which tenants are available."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="laik_list_tenants",
            description="List the LAIK tenants installed on this host (kebab-case names).",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="laik_search_only",
            description=(
                "Pure HybridRetriever search over a tenant's company artifacts — no LLM, no SQL. "
                "Returns ranked chunks with citations (BM25 + pgvector + RRF + cross-encoder rerank). "
                "Use this when you want grounded facts cheaply, without firing the ReAct loop."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant": {"type": "string", "description": f"Tenant slug (default: {DEFAULT_TENANT})"},
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="laik_query",
            description=(
                "Full ReAct query: hybrid RAG + tenant's SQL tools fused into one grounded answer. "
                "This is more expensive than laik_search_only because it runs the LAIK ReAct loop "
                "(up to MAX_TOOL_ROUNDS=6 LLM turns), but it can mix retrieved facts with operational "
                "data from SQL tools. Use this for questions that need both 'what does the doc say' "
                "and 'what's in the database'. Faithfulness gate is enforced inside LAIK."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant": {"type": "string", "description": f"Tenant slug (default: {DEFAULT_TENANT})"},
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="laik_list_tools",
            description=(
                "List the read-only and write tools registered for a tenant in their mcp.yaml. "
                "Use this to discover what laik_propose_mutation can be called with."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant": {"type": "string", "description": f"Tenant slug (default: {DEFAULT_TENANT})"},
                },
            },
        ),
        Tool(
            name="laik_propose_mutation",
            description=(
                "Create a mutation_proposal for a write to the tenant's database. THIS DOES NOT "
                "EXECUTE — it inserts into the mutation_proposals table for human review. The "
                "operator must call laik_confirm_mutation OR confirm via the LAIK admin UI. "
                "Returns the proposal_id and confirmation card payload."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant": {"type": "string"},
                    "tool_name": {"type": "string", "description": "Write tool name from tenant's mcp.yaml"},
                    "args": {"type": "object", "description": "Arguments to bind into the SQL"},
                    "rationale": {"type": "string", "description": "Why this mutation is being proposed"},
                },
                "required": ["tool_name", "args", "rationale"],
            },
        ),
        Tool(
            name="laik_confirm_mutation",
            description=(
                "Execute a previously proposed mutation by proposal_id. Proposal must exist, must "
                "not be expired, and must not have already been confirmed or rejected. Returns "
                "executed result + audit trail entry."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "approver_id": {"type": "string", "description": "Identity of the approver"},
                },
                "required": ["proposal_id", "approver_id"],
            },
        ),
        Tool(
            name="laik_reject_mutation",
            description="Reject a previously proposed mutation by proposal_id. Audit trail entry recorded.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "rejecter_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["proposal_id", "rejecter_id"],
            },
        ),
    ]


def _err(text: str) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps({"error": text}))]


def _ok(payload: Any) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(payload, indent=2, default=str))]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    args = arguments or {}

    if name == "laik_status":
        tenants = list_tenants()
        return _ok(
            {
                "ok": True,
                "laik_root": str(LAIK_ROOT),
                "default_tenant": DEFAULT_TENANT,
                "tenants_available": tenants,
                "tenant_count": len(tenants),
            }
        )

    if name == "laik_list_tenants":
        return _ok({"tenants": list_tenants()})

    tenant = args.get("tenant") or DEFAULT_TENANT
    if tenant not in list_tenants():
        return _err(f"unknown tenant: {tenant}. Available: {list_tenants()}")

    try:
        HybridRetriever, react_loop, MCPToolbox = _import_laik()
    except Exception as e:  # noqa: BLE001
        return _err(f"failed to import LAIK: {e}. Check LAIK_ROOT={LAIK_ROOT}")

    if name == "laik_search_only":
        query = args.get("query")
        if not query:
            return _err("missing 'query'")
        top_k = args.get("top_k", 5)
        retriever = HybridRetriever(tenant)
        try:
            hits = retriever.search(query, top_k=top_k)
            results = [
                {
                    "rank": i + 1,
                    "score": getattr(h, "score", None),
                    "text": getattr(h, "text", None) or getattr(h, "content", None),
                    "source": getattr(h, "source", None),
                    "metadata": getattr(h, "metadata", None),
                }
                for i, h in enumerate(hits)
            ]
            return _ok({"tenant": tenant, "query": query, "top_k": top_k, "results": results})
        except Exception as e:  # noqa: BLE001
            return _err(f"laik_search_only failed: {e}")
        finally:
            try:
                retriever.close()
            except Exception:  # noqa: BLE001
                pass

    if name == "laik_query":
        query = args.get("query")
        if not query:
            return _err("missing 'query'")
        try:
            # react_loop.run_query is the canonical entrypoint per LAIK 2026-05-04
            result = react_loop.run_query(tenant=tenant, query=query)
            return _ok({"tenant": tenant, "query": query, "result": result})
        except TypeError as e:
            return _err(
                f"laik_query: signature mismatch. {e}. "
                "Run `LAIK_ROOT={root} python3 -c 'import inspect; from kit.orchestrator import react_loop; print(inspect.signature(react_loop.run_query))'` "
                "and update server.py to match.".format(root=LAIK_ROOT)
            )
        except Exception as e:  # noqa: BLE001
            return _err(f"laik_query failed: {e}")

    # MCPToolbox-backed tools (list / propose / confirm / reject)
    if name in ("laik_list_tools", "laik_propose_mutation", "laik_confirm_mutation", "laik_reject_mutation"):
        toolbox = None
        try:
            toolbox = MCPToolbox(tenant)
            if name == "laik_list_tools":
                return _ok(
                    {
                        "tenant": tenant,
                        "read_tools": list(toolbox.read_tool_names()),
                        "write_tools": list(toolbox.write_tool_names()),
                    }
                )
            if name == "laik_propose_mutation":
                tool_name = args.get("tool_name")
                mutation_args = args.get("args", {})
                rationale = args.get("rationale")
                if not (tool_name and rationale):
                    return _err("missing 'tool_name' or 'rationale'")
                proposal = toolbox.propose(tool_name=tool_name, args=mutation_args, rationale=rationale)
                return _ok({"tenant": tenant, "proposal": proposal})
            if name == "laik_confirm_mutation":
                proposal_id = args.get("proposal_id")
                approver_id = args.get("approver_id")
                if not (proposal_id and approver_id):
                    return _err("missing 'proposal_id' or 'approver_id'")
                result = toolbox.confirm(proposal_id=proposal_id, approver_id=approver_id)
                return _ok({"tenant": tenant, "result": result})
            if name == "laik_reject_mutation":
                proposal_id = args.get("proposal_id")
                rejecter_id = args.get("rejecter_id")
                reason = args.get("reason", "")
                if not (proposal_id and rejecter_id):
                    return _err("missing 'proposal_id' or 'rejecter_id'")
                result = toolbox.reject(proposal_id=proposal_id, rejecter_id=rejecter_id, reason=reason)
                return _ok({"tenant": tenant, "result": result})
        except Exception as e:  # noqa: BLE001
            return _err(f"{name} failed: {e}")
        finally:
            if toolbox is not None:
                try:
                    toolbox.close()
                except Exception:  # noqa: BLE001
                    pass

    return _err(f"unknown tool: {name}")


# ---------- entrypoint ----------

async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    import asyncio

    asyncio.run(_run())


if __name__ == "__main__":
    main()
