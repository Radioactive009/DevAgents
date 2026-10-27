import pytest
from rag.context_optimizer import ContextOptimizer
from agents.schema import GeneratedFile

def test_context_optimizer_extracts_python_traceback():
    optimizer = ContextOptimizer()
    files = [
        GeneratedFile(path="src/calc.py", content="def add(a, b): return a + b", description="", requirement_ids=[]),
        GeneratedFile(path="src/utils.py", content="def helper(): pass", description="", requirement_ids=[]),
        GeneratedFile(path="tests/test_calc.py", content="from src.calc import add\ndef test_add(): assert add(1, 2) == 4", description="", requirement_ids=[]),
        GeneratedFile(path="requirements.txt", content="pytest>=7.0.0", description="", requirement_ids=[])
    ]
    
    traceback = """
Traceback (most recent call last):
  File "tests/test_calc.py", line 2, in test_add
    assert add(1, 2) == 4
AssertionError: assert 3 == 4
    """
    relevant = optimizer.extract_relevant_files(traceback, files)
    assert "tests/test_calc.py" in relevant
    assert "requirements.txt" in relevant
    # utils.py is untouched and was not referenced in the failure
    assert "src/utils.py" not in relevant

def test_context_optimizer_computes_diff_and_reduction():
    optimizer = ContextOptimizer()
    f1 = GeneratedFile(path="main.py", content="print('hello world')", description="", requirement_ids=[])
    f2 = GeneratedFile(path="large_module.py", content="\n".join([f"line_{i} = {i}" for i in range(100)]), description="", requirement_ids=[])
    files = [f1, f2]
    
    relevant = ["main.py"]
    context_files, metrics = optimizer.optimize_project_files_context(files, relevant)
    
    assert metrics["reduction_percent"] > 0
    assert metrics["relevant_files_count"] == 1
    assert any(cf["path"] == "main.py" and cf["type"] == "full" for cf in context_files)
    assert any(cf["path"] == "large_module.py" and cf["type"] == "summary" for cf in context_files)
