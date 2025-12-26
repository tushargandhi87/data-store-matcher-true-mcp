"""MCP Client Wrapper for easier communication with MCP server."""
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClientWrapper:
    """Wrapper around MCP Python SDK for easier tool calls."""
    
    def __init__(self, server_script_path: str):
        self.server_script_path = Path(server_script_path)
        self.session: Optional[ClientSession] = None
        self.read_stream = None
        self.write_stream = None
        self._context = None
        
    async def connect(self):
        """Establish connection to MCP server."""
        try:
            logger.info(f"Connecting to MCP server: {self.server_script_path}")
            
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[str(self.server_script_path)],
                env=None
            )
            
            self._context = stdio_client(server_params)
            self.read_stream, self.write_stream = await self._context.__aenter__()
            
            self.session = ClientSession(self.read_stream, self.write_stream)
            await self.session.__aenter__()
            await self.session.initialize()
            
            logger.info("Successfully connected to MCP server")
            
            tools_result = await self.session.list_tools()
            logger.info(f"Available tools: {[tool.name for tool in tools_result.tools]}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}", exc_info=True)
            raise
    
    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call an MCP tool."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")
        
        try:
            logger.info(f"Calling tool: {tool_name} with arguments: {arguments}")
            
            result = await self.session.call_tool(tool_name, arguments or {})
            
            if result.content and len(result.content) > 0:
                text_content = result.content[0].text
                
                try:
                    import ast
                    parsed_result = ast.literal_eval(text_content)
                    logger.info(f"Tool {tool_name} returned: {type(parsed_result)}")
                    return parsed_result
                except (ValueError, SyntaxError):
                    logger.warning(f"Could not parse tool result as dict: {text_content[:100]}")
                    return {"raw_response": text_content}
            
            logger.warning(f"Tool {tool_name} returned empty content")
            return {"error": "Empty response from tool"}
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}", exc_info=True)
            return {
                "status": "error",
                "error_type": "CLIENT_ERROR",
                "error_message": str(e)
            }
    
    async def close(self):
        """Close connection to MCP server."""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
                logger.info("Closed MCP session")
            
            if self._context:
                await self._context.__aexit__(None, None, None)
                logger.info("Closed MCP client context")
                
        except Exception as e:
            logger.error(f"Error closing MCP connection: {e}", exc_info=True)
