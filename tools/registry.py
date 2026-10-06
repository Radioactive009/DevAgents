import time
from typing import Dict, List, Optional, Any

from tools.base import Tool
from tools.context import ToolContext
from tools.schema import ToolRequest, ToolResult

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name} is already registered.")
        self._tools[tool.name] = tool

    def unregister_tool(self, tool_name: str) -> None:
        if tool_name in self._tools:
            del self._tools[tool_name]

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        return self._tools.get(tool_name)

    def list_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def execute_tool(self, request: ToolRequest, context: ToolContext) -> ToolResult:
        start_time = time.time()
        
        if not self.has_tool(request.tool_name):
            return ToolResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                success=False,
                output=None,
                error=f"Tool {request.tool_name} is unknown.",
                error_type="UNKNOWN_TOOL",
                execution_time=time.time() - start_time
            )
            
        if not context.has_permission(request.tool_name):
            return ToolResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                success=False,
                output=None,
                error=f"Agent {request.agent_name} lacks permission for {request.tool_name}.",
                error_type="TOOL_PERMISSION_DENIED",
                execution_time=time.time() - start_time
            )
            
        tool = self.get_tool(request.tool_name)
        return tool.execute(request.request_id, request.arguments, context)
