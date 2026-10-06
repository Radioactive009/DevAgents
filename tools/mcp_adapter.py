from typing import Dict, Any, List
from tools.base import Tool
from tools.schema import ToolResult

class MCPAdapter:
    """
    Adapter to expose tools via Model Context Protocol (MCP) compatible structures.
    Does not require a running MCP server; merely maps schemas.
    """

    @staticmethod
    def to_mcp_tool(tool: Tool) -> Dict[str, Any]:
        """
        Converts a DevAgents Tool to an MCP-compatible tool definition.
        """
        return {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.input_schema
        }

    @staticmethod
    def from_mcp_result(result: ToolResult) -> Dict[str, Any]:
        """
        Converts a DevAgents ToolResult to an MCP-compatible result.
        """
        if not result.success:
            return {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": f"[{result.error_type}] {result.error}"
                    }
                ]
            }

        return {
            "isError": False,
            "content": [
                {
                    "type": "text",
                    "text": str(result.output)
                }
            ]
        }
