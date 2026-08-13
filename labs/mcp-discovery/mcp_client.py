"""Real MCP stdio client for module 9A.

The default mode launches ``mcp_server.py`` as a child process and uses the
official Python SDK over a real JSON-RPC stdio transport.  ``--offline`` is a
deliberately separate deterministic fixture for learners who cannot install
the SDK; the checker marks it partial and never treats it as formal completion.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

from mcp import ClientSession, Implementation, MCPError, StdioServerParameters, stdio_client


LESSON_ID = "t19-mcp-discovery"
FIXTURE_VERSION = "1"
PROTOCOL_VERSION = "2026-07-28"
SERVER_NAME = "t19-discovery-server"
SERVER_VERSION = "1.0.0"
TOOL_NAME = "summarize_telemetry"
RESOURCE_URI = "telemetry://demo/snapshot"
PROMPT_NAME = "review-telemetry"
EXPECTED_TOOLS = [TOOL_NAME]
EXPECTED_RESOURCES = [RESOURCE_URI]
EXPECTED_PROMPTS = [PROMPT_NAME]
INSPECTOR_METHODS = ["tools/list", "resources/list", "prompts/list"]


def _capabilities() -> dict[str, list[str]]:
    return {
        "tools": EXPECTED_TOOLS.copy(),
        "resources": EXPECTED_RESOURCES.copy(),
        "prompts": EXPECTED_PROMPTS.copy(),
    }


def offline_fixture() -> dict[str, Any]:
    """Return a stable non-wire observation for the no-environment path."""

    return {
        "fixture_version": FIXTURE_VERSION,
        "lesson_id": LESSON_ID,
        "mode": "offline-fallback",
        "transport": "deterministic-in-memory",
        "protocol_version": "conceptual-only",
        "server": {"name": SERVER_NAME, "version": SERVER_VERSION},
        "capabilities": _capabilities(),
        "observations": {
            "server_connected": True,
            "tools_listed": True,
            "resources_listed": True,
            "prompts_listed": True,
            "tool_called": True,
            "resource_read": True,
            "prompt_retrieved": True,
            "failure_recovered": True,
        },
        "inspector": {"verified": False, "methods": []},
    }


def _inspector_summary(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"verified": False, "methods": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError("Inspector evidence must be an existing JSON file") from exc
    if not isinstance(value, dict):
        raise ValueError("Inspector evidence must be a JSON object")
    methods = value.get("methods")
    if not isinstance(methods, list) or any(not isinstance(item, str) for item in methods):
        raise ValueError("Inspector evidence methods must be a list of strings")
    return {
        "verified": value.get("status") == "passed" and set(INSPECTOR_METHODS).issubset(methods),
        "methods": sorted(set(methods).intersection(INSPECTOR_METHODS)),
    }


async def run_real(inspector_path: Path | None = None) -> dict[str, Any]:
    """Run the real stdio path and return only stable, non-sensitive evidence."""

    server_path = Path(__file__).with_name("mcp_server.py").resolve()
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
        cwd=server_path.parent,
    )
    client_info = Implementation(name="t19-course-client", version="1.0.0")

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(
            read_stream,
            write_stream,
            client_info=client_info,
        ) as session:
            discovery = await session.discover()
            tools = await session.list_tools()
            resources = await session.list_resources()
            prompts = await session.list_prompts()

            tool_names = sorted(tool.name for tool in tools.tools)
            resource_uris = sorted(resource.uri for resource in resources.resources)
            prompt_names = sorted(prompt.name for prompt in prompts.prompts)

            tool_result = await session.call_tool(TOOL_NAME, {"sensor": "demo"})
            resource_result = await session.read_resource(RESOURCE_URI)
            prompt_result = await session.get_prompt(PROMPT_NAME, {"sensor": "demo"})

            failure_recovered = False
            try:
                missing_result = await session.call_tool("missing_tool_for_recovery", {})
                if missing_result.is_error:
                    # Some SDK/server combinations surface a JSON-RPC tool
                    # failure as a typed ``is_error`` result instead of
                    # raising MCPError.  Both are real protocol evidence.
                    await session.call_tool(TOOL_NAME, {"sensor": "recovered"})
                    failure_recovered = True
            except MCPError:
                # The expected protocol error is evidence that the client kept
                # the connection alive; the known tool call below is the retry.
                await session.call_tool(TOOL_NAME, {"sensor": "recovered"})
                failure_recovered = True

            server_info = session.server_info
            return {
                "fixture_version": FIXTURE_VERSION,
                "lesson_id": LESSON_ID,
                "mode": "real-stdio",
                "transport": "stdio",
                "protocol_version": session.protocol_version,
                "server": {
                    "name": server_info.name if server_info else SERVER_NAME,
                    "version": server_info.version if server_info else SERVER_VERSION,
                },
                "capabilities": {
                    "tools": tool_names,
                    "resources": resource_uris,
                    "prompts": prompt_names,
                },
                "observations": {
                    "server_connected": discovery is not None,
                    "tools_listed": tool_names == EXPECTED_TOOLS,
                    "resources_listed": resource_uris == EXPECTED_RESOURCES,
                    "prompts_listed": prompt_names == EXPECTED_PROMPTS,
                    "tool_called": not bool(tool_result.is_error),
                    "resource_read": bool(resource_result.contents),
                    "prompt_retrieved": bool(prompt_result.messages),
                    "failure_recovered": failure_recovered,
                },
                "inspector": _inspector_summary(inspector_path),
            }


def _write_json(path: Path, value: dict[str, Any], *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Output already exists: {path.name}; choose a new path or pass --force")
    if not path.parent.exists():
        raise FileNotFoundError(f"Output directory does not exist: {path.parent}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="use the non-formal deterministic fallback")
    parser.add_argument("--inspector-evidence", type=Path, help="sanitized JSON produced by inspector_check.mjs")
    parser.add_argument("--output", type=Path, help="write the local fixture JSON")
    parser.add_argument("--force", action="store_true", help="allow replacing the explicitly named output file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        evidence = (
            offline_fixture()
            if args.offline
            else asyncio.run(run_real(args.inspector_evidence))
        )
        if args.output:
            _write_json(args.output.resolve(), evidence, force=args.force)
        print(json.dumps(evidence, ensure_ascii=False, indent=2))
        return 0
    except (FileExistsError, FileNotFoundError, ValueError, OSError, MCPError) as exc:
        print(f"MCP discovery failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
