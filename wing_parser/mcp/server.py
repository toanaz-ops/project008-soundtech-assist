"""FastMCP wiring over stdio. Registration only — behaviour is in tools.py."""

from __future__ import annotations

import sys

from wing_parser.mcp import tools


def build():
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("wing-parser")
    for name, function in tools.TOOLS.items():
        server.add_tool(function, name=name, description=function.__doc__ or "")
    return server


def main() -> None:
    try:
        server = build()
    except ImportError:
        print(
            'error: the mcp extra is not installed. Run: pip install "wing-parser[mcp]"',
            file=sys.stderr,
        )
        raise SystemExit(1)
    server.run()


if __name__ == "__main__":
    main()
