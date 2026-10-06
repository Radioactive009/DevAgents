from typing import List, Dict, Any

def task_success_rate(runs: List[Dict[str, Any]]) -> float:
    if not runs:
        return 0.0
    successes = sum(1 for run in runs if run.get("task_success", False))
    return successes / len(runs)

def calculate_test_pass_rate(runs: List[Dict[str, Any]]) -> float:
    if not runs:
        return 0.0
    total_tests = sum(run.get("tests_total", 0) for run in runs)
    if total_tests == 0:
        return 0.0
    passed_tests = sum(run.get("tests_passed", 0) for run in runs)
    return passed_tests / total_tests

def bug_fix_success_rate(runs: List[Dict[str, Any]]) -> float:
    if not runs:
        return 0.0
    successes = sum(1 for run in runs if run.get("bug_fixed", False))
    return successes / len(runs)

def requirement_coverage(runs: List[Dict[str, Any]]) -> float:
    if not runs:
        return 0.0
    total_coverage = sum(run.get("requirement_coverage", 0.0) for run in runs)
    return total_coverage / len(runs)

def code_coverage(runs: List[Dict[str, Any]]) -> float:
    if not runs:
        return 0.0
    total_coverage = sum(run.get("code_coverage", 0.0) for run in runs)
    return total_coverage / len(runs)

def average_debug_iterations(runs: List[Dict[str, Any]]) -> float:
    if not runs:
        return 0.0
    total_iterations = sum(run.get("debug_iterations", 0) for run in runs)
    return total_iterations / len(runs)

def average_execution_time(runs: List[Dict[str, Any]]) -> float:
    if not runs:
        return 0.0
    total_time = sum(run.get("execution_time_seconds", 0.0) for run in runs)
    return total_time / len(runs)

def average_llm_calls(runs: List[Dict[str, Any]]) -> float:
    if not runs:
        return 0.0
    total_calls = sum(run.get("llm_calls", 0) for run in runs)
    return total_calls / len(runs)

def average_tool_calls(runs: List[Dict[str, Any]]) -> float:
    if not runs:
        return 0.0
    total_calls = sum(run.get("tool_calls", 0) for run in runs)
    return total_calls / len(runs)

def human_intervention_rate(runs: List[Dict[str, Any]]) -> float:
    if not runs:
        return 0.0
    interventions = sum(1 for run in runs if run.get("human_intervention", False))
    return interventions / len(runs)

# Basic ML metric placeholders for later
def accuracy(y_true: List[Any], y_pred: List[Any]) -> float:
    pass

def precision(y_true: List[Any], y_pred: List[Any]) -> float:
    pass

def recall(y_true: List[Any], y_pred: List[Any]) -> float:
    pass

def f1(y_true: List[Any], y_pred: List[Any]) -> float:
    pass
