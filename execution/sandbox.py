from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from .models import ExecutionResult

class Sandbox(ABC):
    @abstractmethod
    def create_workspace(self) -> None:
        pass

    @abstractmethod
    def write_file(self, filename: str, content: str) -> None:
        pass

    @abstractmethod
    def read_file(self, filename: str) -> str:
        pass

    @abstractmethod
    def run_command(self, command: List[str]) -> ExecutionResult:
        pass

    @abstractmethod
    def run_tests(self, test_command: List[str] = ["python", "-m", "pytest"]) -> ExecutionResult:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass
