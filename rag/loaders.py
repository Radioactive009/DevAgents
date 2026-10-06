import os
import glob
from typing import List

class DocumentLoader:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.excluded_dirs = [".git", "venv", "env", "node_modules", "BugsInPy", "__pycache__"]
        self.excluded_files = [".env", "PyresBugs.tsv", "credentials"]
        
    def discover_files(self) -> List[str]:
        files = []
        for root, dirs, filenames in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs and not d.startswith('.')]
            for f in filenames:
                if f in self.excluded_files or f.endswith(('.pyc', '.so', '.dll', '.exe', '.tsv', '.log')):
                    continue
                files.append(os.path.join(root, f))
        return files
        
    def load_text(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""
