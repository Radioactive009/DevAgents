import os
import glob
from typing import Dict, Any, List

from tools.base import Tool
from tools.context import ToolContext
from execution.docker_sandbox import DockerSandbox

class ToolSecurityError(Exception):
    def __init__(self, message, error_type="PATH_SECURITY_VIOLATION"):
        super().__init__(message)
        self.error_type = error_type

def validate_safe_path(requested_path: str, project_root: str) -> str:
    # Resolve the requested path against the project root
    abs_root = os.path.abspath(project_root)
    abs_path = os.path.abspath(os.path.join(abs_root, requested_path))
    
    # Path traversal / escape check
    if not abs_path.startswith(abs_root):
        raise ToolSecurityError(f"Path escape attempted: {requested_path}")
        
    # Excluded files check (basename checks for safety)
    basename = os.path.basename(abs_path)
    if basename == ".env" or basename.endswith(".pem") or basename.endswith(".key"):
        raise ToolSecurityError(f"Access to sensitive file denied: {requested_path}")
        
    # Also check if any part of the path is .git
    parts = abs_path.split(os.sep)
    if ".git" in parts:
        raise ToolSecurityError(f"Access to .git directory denied: {requested_path}")

    return abs_path


class ProjectFileReaderTool(Tool):
    MAX_FILE_SIZE = 100 * 1024 # 100KB

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Reads the contents of a specified file within the project workspace."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to the file."}
            },
            "required": ["path"]
        }

    def _execute(self, arguments: Dict[str, Any], context: ToolContext) -> Any:
        rel_path = arguments["path"]
        abs_path = validate_safe_path(rel_path, context.project_root)
        
        if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
            raise ToolSecurityError(f"File not found: {rel_path}", error_type="RESOURCE_NOT_FOUND")
            
        file_size = os.path.getsize(abs_path)
        if file_size > self.MAX_FILE_SIZE:
            raise ToolSecurityError(f"File exceeds maximum readable size: {rel_path}", error_type="RESOURCE_LIMIT_EXCEEDED")
            
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        return {
            "path": rel_path,
            "content": content,
            "size": file_size
        }


class ProjectFileListingTool(Tool):
    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "Lists files within the project root."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def _execute(self, arguments: Dict[str, Any], context: ToolContext) -> Any:
        abs_root = os.path.abspath(context.project_root)
        files = []
        
        for root, dirs, filenames in os.walk(abs_root):
            # Prune unwanted directories
            if ".git" in dirs:
                dirs.remove(".git")
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
                
            for filename in filenames:
                if filename == ".env" or filename.endswith(".pem") or filename.endswith(".key"):
                    continue
                
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, abs_root)
                files.append(rel_path)
                
        # Deterministic order
        files.sort()
        return {"files": files}

class ProjectSearchTool(Tool):
    MAX_MATCHES = 50

    @property
    def name(self) -> str:
        return "search_project"

    @property
    def description(self) -> str:
        return "Searches project files for a string or pattern."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "String to search for."}
            },
            "required": ["query"]
        }

    def _execute(self, arguments: Dict[str, Any], context: ToolContext) -> Any:
        query = arguments["query"]
        abs_root = os.path.abspath(context.project_root)
        
        matches = []
        truncated = False
        
        for root, dirs, filenames in os.walk(abs_root):
            if ".git" in dirs: dirs.remove(".git")
            if "__pycache__" in dirs: dirs.remove("__pycache__")
            
            for filename in filenames:
                if filename == ".env" or filename.endswith(".pem") or filename.endswith(".key"):
                    continue
                
                abs_path = os.path.join(root, filename)
                try:
                    with open(abs_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                except UnicodeDecodeError:
                    continue # Skip binary files
                
                for i, line in enumerate(lines):
                    if query in line:
                        if len(matches) >= self.MAX_MATCHES:
                            truncated = True
                            break
                        rel_path = os.path.relpath(abs_path, abs_root)
                        matches.append({
                            "path": rel_path,
                            "line": i + 1,
                            "content": line.strip()[:200] # bounded snippet size
                        })
                if truncated:
                    break
            if truncated:
                break
                
        return {
            "query": query,
            "matches": matches,
            "total_matches": len(matches),
            "truncated": truncated
        }

class TestExecutionTool(Tool):
    @property
    def name(self) -> str:
        return "execute_tests"

    @property
    def description(self) -> str:
        return "Executes tests securely inside the project's DockerSandbox."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "test_command": {"type": "string", "description": "Command to run tests (e.g. 'pytest')."}
            },
            "required": ["test_command"]
        }

    def _execute(self, arguments: Dict[str, Any], context: ToolContext) -> Any:
        test_command = arguments["test_command"]
        sandbox_config = context.configuration.get("sandbox_config", {})
        
        # We reuse DockerSandbox infrastructure!
        sandbox = DockerSandbox(config=sandbox_config)
        try:
            sandbox.create_workspace()
            
            # Setup files inside the sandbox
            abs_root = os.path.abspath(context.project_root)
            for root, dirs, filenames in os.walk(abs_root):
                if ".git" in dirs: dirs.remove(".git")
                for filename in filenames:
                    abs_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(abs_path, abs_root)
                    with open(abs_path, "r", encoding="utf-8") as f:
                        try:
                            content = f.read()
                            sandbox.write_file(rel_path, content)
                        except UnicodeDecodeError:
                            continue

            # In the original flow, we install dependencies, but testing agent does that.
            # Here, the tool is a simple wrapper for testing. It may need pip install first.
            # For this tool abstraction, we will just run the tests.
            # The agent can explicitly invoke 'pip install' if we add a command tool, 
            # but since we want to constrain it, let's just use sandbox.run_tests.
            
            result = sandbox.run_tests(test_command)
            
            return {
                "success": result.success,
                "exit_code": result.exit_code,
                "stdout": result.stdout, # already sanitized by ExecutionResult
                "stderr": result.stderr,
                "duration": result.duration,
                "timed_out": result.timed_out
            }
        finally:
            sandbox.cleanup()

class RAGRetrievalTool(Tool):
    @property
    def name(self) -> str:
        return "rag_retrieval"

    @property
    def description(self) -> str:
        return "Retrieves context from project files using the RAG infrastructure."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Semantic search query."}
            },
            "required": ["query"]
        }

    def _execute(self, arguments: Dict[str, Any], context: ToolContext) -> Any:
        use_rag = context.configuration.get("use_rag", False)
        if not use_rag:
            return {"disabled": True, "results": []}
            
        retriever = context.configuration.get("retriever")
        if not retriever:
            raise ToolSecurityError("Retriever not initialized in context.", error_type="TOOL_INTERNAL_ERROR")
            
        query = arguments["query"]
        chunks, latency = retriever.retrieve(query, top_k=5)
        
        return {
            "disabled": False,
            "query": query,
            "results": [
                {
                    "id": c.chunk_id,
                    "content": c.content,
                    "metadata": c.metadata,
                    "score": getattr(c, "score", 0.0)
                } for c in chunks
            ],
            "retrieval_latency": latency
        }

class MemoryRetrievalTool(Tool):
    @property
    def name(self) -> str:
        return "memory_retrieval"

    @property
    def description(self) -> str:
        return "Retrieves historical debugging patterns and learnings from ProjectMemory."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Semantic search query."}
            },
            "required": ["query"]
        }

    def _execute(self, arguments: Dict[str, Any], context: ToolContext) -> Any:
        use_memory = context.configuration.get("use_memory", False)
        if not use_memory:
            return {"disabled": True, "results": []}
            
        memory = context.configuration.get("memory")
        if not memory:
            raise ToolSecurityError("ProjectMemory not initialized in context.", error_type="TOOL_INTERNAL_ERROR")
            
        query = arguments["query"]
        records, latency = memory.retrieve_relevant_memory(query, top_k=3)
        
        return {
            "disabled": False,
            "query": query,
            "results": [
                {
                    "type": r.memory_type,
                    "description": r.description,
                    "cause": r.cause,
                    "solution": r.solution,
                    "score": getattr(r, "score", 0.0)
                } for r in records
            ],
            "retrieval_latency": latency
        }
