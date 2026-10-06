from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time

from tools.schema import ToolResult
from tools.context import ToolContext

class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        pass
        
    @property
    def metadata(self) -> Dict[str, Any]:
        return {}

    def validate_input(self, arguments: Dict[str, Any]) -> bool:
        # Basic validation against schema structure could go here
        return True

    @abstractmethod
    def _execute(self, arguments: Dict[str, Any], context: ToolContext) -> Any:
        pass

    def execute(self, request_id: str, arguments: Dict[str, Any], context: ToolContext) -> ToolResult:
        start_time = time.time()
        
        try:
            if not self.validate_input(arguments):
                return ToolResult(
                    request_id=request_id,
                    tool_name=self.name,
                    success=False,
                    output=None,
                    error="Invalid arguments provided to tool.",
                    error_type="INVALID_TOOL_ARGUMENTS",
                    execution_time=time.time() - start_time
                )
                
            output = self._execute(arguments, context)
            
            return ToolResult(
                request_id=request_id,
                tool_name=self.name,
                success=True,
                output=output,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            error_type = getattr(e, "error_type", "TOOL_EXECUTION_ERROR")
            if type(e).__name__ == "TimeoutError":
                error_type = "TOOL_TIMEOUT"
                
            return ToolResult(
                request_id=request_id,
                tool_name=self.name,
                success=False,
                output=None,
                error=str(e),
                error_type=error_type,
                execution_time=time.time() - start_time
            )
