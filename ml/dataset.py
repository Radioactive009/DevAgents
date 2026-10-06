import json
import os
from typing import List

from .schemas import FailureSample

def load_dataset(path: str) -> List[FailureSample]:
    if not os.path.exists(path):
        return []
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    return [
        FailureSample(
            sample_id=item.get("sample_id", ""),
            text=item.get("text", ""),
            label=item.get("label", ""),
            source=item.get("source", ""),
            project=item.get("project", ""),
            bug_id=item.get("bug_id", ""),
            metadata=item.get("metadata", {})
        )
        for item in data
    ]

def save_dataset(dataset: List[FailureSample], path: str):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    
    data = [
        {
            "sample_id": s.sample_id,
            "text": s.text,
            "label": s.label,
            "source": s.source,
            "project": s.project,
            "bug_id": s.bug_id,
            "metadata": s.metadata
        }
        for s in dataset
    ]
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def generate_synthetic_bugsinpy_dataset() -> List[FailureSample]:
    """Generates a synthetic subset representing BugsInPy structure for testing/demo purposes."""
    samples = [
        FailureSample("s1", "SyntaxError: invalid syntax", "SYNTAX_ERROR", "BugsInPy", "pandas", "1"),
        FailureSample("s2", "ModuleNotFoundError: No module named 'numpy'", "IMPORT_ERROR", "BugsInPy", "scipy", "2"),
        FailureSample("s3", "TypeError: can only concatenate str (not 'int') to str", "TYPE_ERROR", "BugsInPy", "pandas", "3"),
        FailureSample("s4", "AttributeError: 'NoneType' object has no attribute 'shape'", "ATTRIBUTE_ERROR", "BugsInPy", "scikit-learn", "4"),
        FailureSample("s5", "NameError: name 'plt' is not defined", "NAME_ERROR", "BugsInPy", "matplotlib", "5"),
        FailureSample("s6", "ValueError: math domain error", "VALUE_ERROR", "BugsInPy", "numpy", "6"),
        FailureSample("s7", "AssertionError: assert 5 == 6", "ASSERTION_FAILURE", "BugsInPy", "pytest", "7"),
        FailureSample("s8", "KeyError: 'missing_col'", "RUNTIME_ERROR", "BugsInPy", "pandas", "8"),
        FailureSample("s9", "IndexError: list index out of range", "RUNTIME_ERROR", "BugsInPy", "core", "9"),
        FailureSample("s10", "TimeoutError: operation timed out after 30s", "TIMEOUT", "BugsInPy", "requests", "10"),
    ]
    # Multiply to have enough samples for splitting and training
    expanded = []
    for i in range(10):
        for s in samples:
            expanded.append(FailureSample(
                f"{s.sample_id}_{i}",
                f"{s.text} additional context {i}",
                s.label,
                s.source,
                s.project,
                s.bug_id
            ))
            
    return expanded
