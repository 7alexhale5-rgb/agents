"""Schema-validated tool dispatch for PF Runtime."""

from __future__ import annotations

import abc
import hashlib
import json
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, ClassVar

from pf_runtime.runtime.trace import emit_tool_trace


class ToolValidationError(ValueError):
    def __init__(self, name: str, schema_path: str, message: str) -> None:
        super().__init__(f"{name} args invalid at {schema_path}: {message}")
        self.name = name
        self.schema_path = schema_path
        self.message = message


class ToolCycleError(RuntimeError):
    pass


@dataclass
class MutationProposal:
    proposal_id: str
    operation: str
    table: str
    rows_affected: list[dict[str, Any]]
    rationale: str


@dataclass
class ToolContext:
    profile_slug: str
    session_id: str
    langfuse_trace_id: str = ""
    mutation_proposal_callback: Callable[[MutationProposal], Awaitable[str]] | None = None


@dataclass
class ToolResult:
    ok: bool
    output: Any
    error: str | None = None
    cost_usd: Decimal = Decimal("0")


class Tool(abc.ABC):
    name: str
    description: str
    parameters: ClassVar[dict[str, Any]]

    @abc.abstractmethod
    async def invoke(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        raise NotImplementedError


class ToolDispatcher:
    """Dispatch tools after validating args against a small JSONSchema subset."""

    def __init__(self, tools: list[Tool], *, max_same_call: int = 3) -> None:
        self._tools = {tool.name: tool for tool in tools}
        self._call_counts: Counter[str] = Counter()
        self._max_same_call = max_same_call

    @property
    def tool_names(self) -> list[str]:
        return sorted(self._tools)

    def prompt_catalog(self) -> str:
        if not self._tools:
            return ""
        rows = [
            "# AVAILABLE TOOLS",
            "Call a tool by replying with JSON: "
            '{"tool_call":{"name":"tool.name","arguments":{...}}}',
        ]
        for tool in self._tools.values():
            rows.append(
                json.dumps(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                    sort_keys=True,
                )
            )
        return "\n".join(rows)

    async def dispatch(
        self,
        name: str,
        args: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"unknown tool: {name}")
        _validate_schema(name, args, tool.parameters, "$")
        args_hash = _hash_args(args)
        cycle_key = f"{name}:{args_hash}"
        self._call_counts[cycle_key] += 1
        if self._call_counts[cycle_key] > self._max_same_call:
            raise ToolCycleError(f"repeated tool call detected: {name}")

        t0 = time.perf_counter()
        try:
            result = await tool.invoke(args, context)
            emit_tool_trace(
                profile_slug=context.profile_slug,
                session_id=context.session_id,
                tool_name=name,
                tool_server="builtin",
                arguments_hash=args_hash,
                success=result.ok,
                error_class="other" if result.error else "",
                latency_ms=(time.perf_counter() - t0) * 1000,
            )
            return result
        except Exception as exc:
            emit_tool_trace(
                profile_slug=context.profile_slug,
                session_id=context.session_id,
                tool_name=name,
                tool_server="builtin",
                arguments_hash=args_hash,
                success=False,
                error_class=_error_class(exc),
                latency_ms=(time.perf_counter() - t0) * 1000,
            )
            raise


def _hash_args(args: dict[str, Any]) -> str:
    normalized = json.dumps(args, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _error_class(exc: Exception) -> str:
    if isinstance(exc, ToolValidationError):
        return "validation"
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, KeyError):
        return "not_found"
    if isinstance(exc, PermissionError):
        return "auth"
    return "other"


def _validate_schema(name: str, value: Any, schema: dict[str, Any], path: str) -> None:
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            raise ToolValidationError(name, path, "expected object")
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise ToolValidationError(name, f"{path}.{key}", "missing required property")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise ToolValidationError(name, path, f"unexpected properties: {extra}")
        for key, child_schema in properties.items():
            if key in value:
                _validate_schema(name, value[key], child_schema, f"{path}.{key}")
    elif expected == "array":
        if not isinstance(value, list):
            raise ToolValidationError(name, path, "expected array")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(value):
                _validate_schema(name, item, item_schema, f"{path}[{idx}]")
    elif expected == "string":
        if not isinstance(value, str):
            raise ToolValidationError(name, path, "expected string")
        if "minLength" in schema and len(value) < int(schema["minLength"]):
            raise ToolValidationError(name, path, "string shorter than minLength")
    elif expected == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ToolValidationError(name, path, "expected integer")
    elif expected == "number":
        if not isinstance(value, int | float) or isinstance(value, bool):
            raise ToolValidationError(name, path, "expected number")
    elif expected == "boolean":
        if not isinstance(value, bool):
            raise ToolValidationError(name, path, "expected boolean")

    enum = schema.get("enum")
    if enum is not None and value not in enum:
        raise ToolValidationError(name, path, f"expected one of {enum}")
