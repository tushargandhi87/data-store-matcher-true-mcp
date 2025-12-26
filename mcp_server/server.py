"""Main MCP Server for ACAT Datastore Service."""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp import types

sys.path.insert(0, str(Path(__file__).parent))

from config import ACAT_REFERENCE_FILE, ENDOFLIFE_API_TIMEOUT, ENDOFLIFE_API_RETRIES, LOG_LEVEL
from tools.get_acat_reference import get_acat_reference as get_acat_ref_func
from tools.endoflife_lookup import endoflife_lookup as eol_lookup_func

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('mcp_server.log'), logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

app = Server("acat-datastore-service")


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="get_acat_reference",
            description=(
                "Retrieves the complete list of standardized datastore names from ACAT database. "
                "This should be called ONCE at the start to get the reference list for matching "
                "user-provided datastore names against ACAT standards."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        types.Tool(
            name="endoflife_lookup",
            description=(
                "Queries endoflife.date API to get version information, EOL dates, and support status for datastores.\n\n"
                "USE THIS TOOL WHEN:\n"
                "- LLM matching returns confidence score < 0.7 (indicates datastore likely not in ACAT reference)\n"
                "- You need to verify version information from an external authoritative source\n"
                "- User-provided datastore name doesn't match ACAT standard naming conventions\n\n"
                "This tool helps identify datastores that exist in endoflife.date database but may not be "
                "in the ACAT reference list. The results indicate whether the datastore version is still "
                "supported or has reached end-of-life."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "product": {"type": "string", "description": "Product name (e.g., 'PostgreSQL', 'MySQL', 'SQL Server')"},
                    "version": {"type": "string", "description": "Version number (e.g., '14', '5.0', '2019')"}
                },
                "required": ["product", "version"]
            }
        )
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    """Handle tool execution requests."""
    try:
        logger.info(f"Tool called: {name} with arguments: {arguments}")
        
        if name == "get_acat_reference":
            result = get_acat_ref_func(Path(ACAT_REFERENCE_FILE))
            return [types.TextContent(type="text", text=str(result))]
            
        elif name == "endoflife_lookup":
            if not arguments:
                return [types.TextContent(type="text", text=str({
                    "status": "error",
                    "error_type": "INVALID_INPUT",
                    "error_message": "Arguments required: product and version"
                }))]
            
            result = eol_lookup_func(
                product=arguments.get("product", ""),
                version=arguments.get("version", ""),
                timeout=ENDOFLIFE_API_TIMEOUT,
                max_retries=ENDOFLIFE_API_RETRIES
            )
            return [types.TextContent(type="text", text=str(result))]
            
        else:
            return [types.TextContent(type="text", text=str({
                "status": "error",
                "error_type": "UNKNOWN_TOOL",
                "error_message": f"Tool '{name}' not found"
            }))]
            
    except Exception as e:
        logger.error(f"Error handling tool call: {e}", exc_info=True)
        return [types.TextContent(type="text", text=str({
            "status": "error",
            "error_type": "SERVER_ERROR",
            "error_message": str(e)
        }))]


async def main():
    """Main server entry point."""
    logger.info("Starting ACAT Datastore MCP Server")
    logger.info(f"ACAT Reference File: {ACAT_REFERENCE_FILE}")
    logger.info("Server is reactive - data loaded only when tools are called")
    
    async with stdio_server() as (read_stream, write_stream):
        logger.info("MCP Server running on stdio transport")
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="acat-datastore-service",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
