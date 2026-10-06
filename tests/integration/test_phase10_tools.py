import unittest
import os
import tempfile

from tools.registry import ToolRegistry
from tools.context import ToolContext
from tools.schema import ToolRequest
from tools.core import (
    ProjectFileReaderTool,
    ProjectFileListingTool,
    ProjectSearchTool,
    TestExecutionTool,
    RAGRetrievalTool,
    MemoryRetrievalTool
)
from tools.mcp_adapter import MCPAdapter

class TestPhase10Integration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = self.temp_dir.name
        
        # Create a toy project
        with open(os.path.join(self.project_root, "main.py"), "w") as f:
            f.write("def add(a, b):\n    return a + b\n")
            
        with open(os.path.join(self.project_root, "test_main.py"), "w") as f:
            f.write("from main import add\n\ndef test_add():\n    assert add(1, 2) == 3\n")
            
        with open(os.path.join(self.project_root, ".env"), "w") as f:
            f.write("SECRET_KEY=12345")
            
        # Register tools
        self.registry = ToolRegistry()
        self.registry.register_tool(ProjectFileReaderTool())
        self.registry.register_tool(ProjectFileListingTool())
        self.registry.register_tool(ProjectSearchTool())
        self.registry.register_tool(TestExecutionTool())
        self.registry.register_tool(RAGRetrievalTool())
        self.registry.register_tool(MemoryRetrievalTool())
        
        # Agent context (Coding/Debugging style)
        self.context = ToolContext(
            project_root=self.project_root,
            task_id="t1",
            agent_name="DebuggingAgent",
            allowed_tools=[
                "read_file", 
                "list_files", 
                "search_project", 
                "execute_tests",
                "rag_retrieval",
                "memory_retrieval"
            ],
            configuration={
                "use_rag": False,
                "use_memory": False,
                "sandbox_config": {"network_enabled": False}
            }
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_phase10_tool_flow(self):
        # 1. Read project file
        req = ToolRequest(request_id="1", tool_name="read_file", arguments={"path": "main.py"}, agent_name="DebuggingAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertTrue(res.success)
        self.assertIn("def add(a, b):", res.output["content"])

        # 2. Search project
        req = ToolRequest(request_id="2", tool_name="search_project", arguments={"query": "assert"}, agent_name="DebuggingAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertTrue(res.success)
        self.assertEqual(res.output["total_matches"], 1)
        self.assertEqual(res.output["matches"][0]["path"], "test_main.py")
        
        # 3. Test Execution via Sandbox
        req = ToolRequest(request_id="3", tool_name="execute_tests", arguments={"test_command": "pytest test_main.py"}, agent_name="DebuggingAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertTrue(res.success)
        # Even if it fails (pytest missing in sandbox), it returns a structured result without crashing
        self.assertIn("success", res.output)
        self.assertIn("exit_code", res.output)
        
        # 4. RAG / Memory retrieval (disabled)
        req = ToolRequest(request_id="4", tool_name="rag_retrieval", arguments={"query": "test"}, agent_name="DebuggingAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertTrue(res.success)
        self.assertTrue(res.output["disabled"])
        
        # 5. Unauthorized tool
        self.context.allowed_tools = ["read_file"]
        req = ToolRequest(request_id="5", tool_name="execute_tests", arguments={"test_command": "pytest"}, agent_name="DebuggingAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "TOOL_PERMISSION_DENIED")
        
        # 6. Path traversal rejection
        self.context.allowed_tools = ["read_file"]
        req = ToolRequest(request_id="6", tool_name="read_file", arguments={"path": "../something"}, agent_name="DebuggingAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "PATH_SECURITY_VIOLATION")

        # 7. Env access rejection
        req = ToolRequest(request_id="7", tool_name="read_file", arguments={"path": ".env"}, agent_name="DebuggingAgent")
        res = self.registry.execute_tool(req, self.context)
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "PATH_SECURITY_VIOLATION")

        # 8. MCP format validation
        mcp_res = MCPAdapter.from_mcp_result(res) # The failure from 7
        self.assertTrue(mcp_res["isError"])
        self.assertIn("PATH_SECURITY_VIOLATION", mcp_res["content"][0]["text"])

if __name__ == '__main__':
    unittest.main()
