import logging
from mcp.server.fastmcp import FastMCP
from .rv_client import RvClient

logging.basicConfig(level=logging.INFO, format="%(message)s")

mcp = FastMCP("rv-mcp")
client = RvClient()

# Import tool modules to trigger @mcp.tool() registration
from .tools import execute, playback, sources, compare, color, ocio  # noqa: E402, F401


@mcp.prompt()
def rv_assistant() -> str:
    """Default assistant instructions for MCP clients."""
    return (
        "You are an RV media review assistant connected via MCP.\n"
        "Use dedicated tools when available; fall back to execute_mu for advanced ops.\n"
        "RV must be running with -network flag on port 45124.\n"
        "Commands are executed as Mu code via remote-eval.\n"
        "Use 'require commands;' at the start of Mu blocks that call command functions.\n"
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
