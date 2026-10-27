import os
import re
import difflib
import json
from typing import List, Dict, Any, Tuple, Optional
from agents.schema import GeneratedFile

class ContextOptimizer:
    """
    Context Optimization engine for software development and debugging (Phase 4).
    Reduces unnecessary context sent to LLMs by:
    1. Identifying relevant files from test/build failures and stack traces.
    2. Generating diffs of modified files instead of repeatedly sending unchanged source.
    3. Pruning irrelevant files while safeguarding necessary configuration and interfaces.
    """
    def __init__(self, max_context_chars: int = 14000):
        self.max_context_chars = max_context_chars

    def extract_relevant_files(self, failure_output: str, all_files: List[GeneratedFile]) -> List[str]:
        """
        Parses failure outputs (pytest, jest, vitest, compiler) to extract filenames
        directly referenced in tracebacks or failure summaries.
        """
        if not failure_output:
            return [f.path for f in all_files]

        relevant_paths = set()
        file_map = {f.path: f for f in all_files}
        known_basenames = {os.path.basename(f.path): f.path for f in all_files}

        # Python traceback patterns: File "...", line \d+
        py_matches = re.findall(r'File\s+"([^"]+)"', failure_output)
        for match in py_matches:
            clean = os.path.normpath(match).replace("\\", "/")
            bname = os.path.basename(clean)
            if bname in known_basenames:
                relevant_paths.add(known_basenames[bname])
            elif clean in file_map:
                relevant_paths.add(clean)

        # JS / TS traceback patterns: at ... (path/to/file.ts:12:34)
        js_matches = re.findall(r'(?:at\s+.*?\((.*?):\d+:\d+\)|at\s+(.*?):\d+:\d+)', failure_output)
        for group in js_matches:
            for path_cand in group:
                if not path_cand:
                    continue
                clean = os.path.normpath(path_cand).replace("\\", "/")
                bname = os.path.basename(clean)
                if bname in known_basenames:
                    relevant_paths.add(known_basenames[bname])

        # Test failure headers: e.g. tests/test_calc.py:25: in test_add
        test_path_matches = re.findall(r'([\w/\\]+\.(?:py|js|ts|tsx|jsx)):\d+', failure_output)
        for cand in test_path_matches:
            clean = os.path.normpath(cand).replace("\\", "/")
            bname = os.path.basename(clean)
            if bname in known_basenames:
                relevant_paths.add(known_basenames[bname])

        # Always include config and manifest files (package.json, requirements.txt, pyproject.toml)
        for f in all_files:
            bname = os.path.basename(f.path).lower()
            if bname in ["package.json", "requirements.txt", "pyproject.toml", "setup.py"]:
                relevant_paths.add(f.path)

        # If no specific files were identified in stack trace, fall back to all project files
        if not relevant_paths:
            return [f.path for f in all_files]

        return sorted(list(relevant_paths))

    def compute_file_diff(self, old_content: str, new_content: str, filename: str) -> str:
        """Generates unified diff between previous and current file contents."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        )
        return "".join(diff)

    def optimize_project_files_context(
        self,
        files: List[GeneratedFile],
        relevant_file_paths: List[str],
        previous_files_map: Optional[Dict[str, str]] = None
    ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """
        Builds optimized project files representation:
        - Full content for directly failing/relevant files.
        - Diffs or concise summaries for unchanged/unrelated files.
        """
        context_files = []
        original_size = sum(len(f.content) for f in files)
        
        for f in files:
            if f.path in relevant_file_paths:
                # Include full content for relevant files
                context_files.append({
                    "path": f.path,
                    "type": "full",
                    "content": f.content
                })
            elif previous_files_map and f.path in previous_files_map:
                diff_text = self.compute_file_diff(previous_files_map[f.path], f.content, f.path)
                if diff_text.strip():
                    context_files.append({
                        "path": f.path,
                        "type": "diff",
                        "content": diff_text
                    })
                else:
                    context_files.append({
                        "path": f.path,
                        "type": "summary",
                        "content": f"// [Unchanged - {len(f.content.splitlines())} lines. Omitted for context optimization]"
                    })
            else:
                # Non-relevant file: include concise summary to save context
                lines = f.content.splitlines()
                summary_sample = "\n".join(lines[:15]) if len(lines) > 20 else f.content
                context_files.append({
                    "path": f.path,
                    "type": "summary",
                    "content": summary_sample + (f"\n// ... [{len(lines)-15} additional lines omitted]" if len(lines) > 20 else "")
                })

        optimized_size = sum(len(c["content"]) for c in context_files)
        metrics = {
            "original_char_count": original_size,
            "optimized_char_count": optimized_size,
            "reduction_percent": round((1.0 - (optimized_size / max(1, original_size))) * 100, 2),
            "relevant_files_count": len(relevant_file_paths),
            "total_files_count": len(files)
        }
        return context_files, metrics
