"""FastMCP wiring over stdio. Registration only — behaviour is in tools.py."""

from __future__ import annotations

from wing_parser.mcp import tools


def build():
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("wing-parser")
    for name, function in tools.TOOLS.items():
        server.add_tool(function, name=name, description=function.__doc__ or "")
    return server


def main() -> None:
    build().run()


if __name__ == "__main__":
    main()
