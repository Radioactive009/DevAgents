import unittest
import os
import tempfile
import json
from unittest.mock import MagicMock

from tools.schema import ToolRequest, ToolResult
from tools.context import ToolContext
from tools.registry import ToolRegistry
from tools.base import Tool
from tools.mcp_adapter import MCPAdapter
from tools.core import (
    ProjectFileReaderTool,
    ProjectFileListingTool,
    ProjectSearchTool,
    TestExecutionTool,
    RAGRetrievalTool,
    MemoryRetrievalTool,
    ToolSecurityError,
    validate_safe_path
)

class MockTool(Tool):
    @property
    def name(self) -> str: return "mock_tool"
    @property
    def description(self) -> str: return "Mock tool"
    @property
    def input_schema(self) -> dict: return {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}
    def _execute(self, arguments, context):
        if arguments.get("x") == "fail":
            raise ValueError("Failure forced")
        return {"result": arguments["x"]}


class TestTools(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = self.temp_dir.name
        
        # Create some safe files
        with open(os.path.join(self.project_root, "safe.txt"), "w") as f:
            f.write("safe content")
            
        with open(os.path.join(self.project_root, ".env"), "w") as f:
            f.write("SECRET=123")
            
        os.makedirs(os.path.join(self.project_root, ".git"))
        with open(os.path.join(self.project_root, ".git", "config"), "w") as f:
            f.write("git config")
            
        self.context = ToolContext(
            project_root=self.project_root,
            task_id="t1",
            agent_name="TestAgent",
            allowed_tools=["mock_tool", "read_file", "list_files", "search_project", "rag_retrieval", "memory_retrieval"]
        )
        self.registry = ToolRegistry()
        self.registry.register_tool(MockTool())
        self.registry.register_tool(ProjectFileReaderTool())
        self.registry.register_tool(ProjectFileListingTool())
        self.registry.register_tool(ProjectSearchTool())

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_registry_registration(self):
        self.assertTrue(self.registry.has_tool("mock_tool"))
        with self.assertRaises(ValueError):
            self.registry.register_tool(MockTool())

    def test_tool_execution_success(self):
        req = ToolRequest(request_id="1", tool_name="mock_tool", arguments={"x": "hello"}, agent_name="TestAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertTrue(res.success)
        self.assertEqual(res.output["result"], "hello")

    def test_tool_execution_failure(self):
        req = ToolRequest(request_id="1", tool_name="mock_tool", arguments={"x": "fail"}, agent_name="TestAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "TOOL_EXECUTION_ERROR")

    def test_permission_denied(self):
        req = ToolRequest(request_id="1", tool_name="mock_tool", arguments={"x": "hello"}, agent_name="TestAgent")
        ctx = ToolContext(project_root=self.project_root, task_id="t1", agent_name="TestAgent", allowed_tools=[])
        res = self.registry.execute_tool(req, ctx)
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "TOOL_PERMISSION_DENIED")

    def test_unknown_tool(self):
        req = ToolRequest(request_id="1", tool_name="unknown", arguments={}, agent_name="TestAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "UNKNOWN_TOOL")

    def test_file_reader_safe(self):
        req = ToolRequest(request_id="1", tool_name="read_file", arguments={"path": "safe.txt"}, agent_name="TestAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertTrue(res.success)
        self.assertEqual(res.output["content"], "safe content")

    def test_file_reader_path_traversal(self):
        req = ToolRequest(request_id="1", tool_name="read_file", arguments={"path": "../outside.txt"}, agent_name="TestAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "PATH_SECURITY_VIOLATION")

    def test_file_reader_env_access(self):
        req = ToolRequest(request_id="1", tool_name="read_file", arguments={"path": ".env"}, agent_name="TestAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "PATH_SECURITY_VIOLATION")

    def test_file_listing(self):
        req = ToolRequest(request_id="1", tool_name="list_files", arguments={}, agent_name="TestAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertTrue(res.success)
        files = res.output["files"]
        self.assertIn("safe.txt", files)
        self.assertNotIn(".env", files)
        self.assertNotIn(os.path.join(".git", "config"), files)

    def test_project_search(self):
        req = ToolRequest(request_id="1", tool_name="search_project", arguments={"query": "safe"}, agent_name="TestAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertTrue(res.success)
        self.assertEqual(res.output["total_matches"], 1)
        self.assertEqual(res.output["matches"][0]["path"], "safe.txt")

    def test_mcp_adapter(self):
        tool = MockTool()
        mcp_tool = MCPAdapter.to_mcp_tool(tool)
        self.assertEqual(mcp_tool["name"], "mock_tool")
        
        req = ToolRequest(request_id="1", tool_name="mock_tool", arguments={"x": "hello"}, agent_name="TestAgent")
        res = self.registry.execute_tool(req, self.context)
        
        mcp_result = MCPAdapter.from_mcp_result(res)
        self.assertFalse(mcp_result["isError"])
        self.assertEqual(mcp_result["content"][0]["text"], "{'result': 'hello'}")

    def test_rag_retrieval_disabled(self):
        self.registry.register_tool(RAGRetrievalTool())
        req = ToolRequest(request_id="1", tool_name="rag_retrieval", arguments={"query": "test"}, agent_name="TestAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertTrue(res.success)
        self.assertTrue(res.output["disabled"])

if __name__ == "__main__":
    unittest.main()
