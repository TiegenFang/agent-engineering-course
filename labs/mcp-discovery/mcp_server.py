"""最小、无副作用的 MCP Server，供模块 9A 的真实 stdio 实验使用。

The server deliberately serves only synthetic telemetry.  It never reads a
file, calls a network service, invokes a model, or writes to stdout except for
the MCP wire owned by ``MCPServer.run("stdio")``.  Logs belong on stderr if a
learner adds diagnostics.
"""

from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer


SERVER_NAME = "t19-discovery-server"
SERVER_VERSION = "1.0.0"
SNAPSHOT_URI = "telemetry://demo/snapshot"

server = MCPServer(
    SERVER_NAME,
    version=SERVER_VERSION,
    description="Synthetic telemetry server for the Agent 工程入门 MCP lesson.",
    instructions=(
        "This server exposes synthetic, read-only telemetry. "
        "It does not access files, networks, credentials, or paid APIs."
    ),
)


@server.tool(
    name="summarize_telemetry",
    description=(
        "Return a deterministic summary for one synthetic sensor label. "
        "This tool has no external side effect."
    ),
)
def summarize_telemetry(sensor: str = "demo") -> str:
    """Summarize a synthetic sensor without touching external state."""

    sensor_label = sensor.strip() or "demo"
    return json.dumps(
        {
            "sensor": sensor_label,
            "status": "nominal",
            "samples": 3,
            "unit": "synthetic-units",
        },
        ensure_ascii=False,
        sort_keys=True,
    )


@server.resource(
    SNAPSHOT_URI,
    name="telemetry-snapshot",
    description="A static synthetic snapshot used to demonstrate resources/read.",
    mime_type="application/json",
)
def telemetry_snapshot() -> str:
    """Return a static resource; no file or network access is performed."""

    return json.dumps(
        {
            "dataset": "synthetic-telemetry",
            "records": 3,
            "quality": "teaching-fixture",
        },
        ensure_ascii=False,
        sort_keys=True,
    )


@server.prompt(
    name="review-telemetry",
    description="Build a review instruction for the synthetic telemetry label.",
)
def review_telemetry(sensor: str = "demo") -> list[dict[str, object]]:
    """Return one user-controlled prompt template message."""

    sensor_label = sensor.strip() or "demo"
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": (
                    f"Review the synthetic telemetry summary for sensor '{sensor_label}'. "
                    "State the evidence and do not infer real-device behavior."
                ),
            },
        }
    ]


def main() -> None:
    # stdout is the stdio transport.  Keep this call under the main guard so
    # Inspector and ClientSession can import the module without starting it.
    server.run("stdio")


if __name__ == "__main__":
    main()
