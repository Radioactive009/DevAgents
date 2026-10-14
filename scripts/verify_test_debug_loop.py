from orchestration.state import ProjectState
from agents.testing import TestingAgent
from agents.debugging import DebuggingAgent
from agents.schema import GeneratedProject, GeneratedFile

calc_code = """def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError('Cannot divide by zero')
    return a / b + 1  # INJECTED BUG FOR DEMO
"""

test_code = """import pytest
from calculator import add, subtract, multiply, divide

def test_divide():
    assert divide(6, 2) == 3
"""

s = ProjectState('test-run-focus', 'Build a Python calculator module with add, subtract, multiply, divide, division-by-zero handling, and pytest tests.')
s.generated_project = GeneratedProject(
    project_name='calculator',
    files=[GeneratedFile('calculator.py', calc_code), GeneratedFile('test_calculator.py', test_code)],
    entrypoint='calculator.py',
    run_command='python calculator.py',
    test_command='pytest test_calculator.py',
    dependencies=[],
    requirement_coverage={}
)

test_agent = TestingAgent(None)
debug_agent = DebuggingAgent(None)

# Step 1: Initial test
res1 = test_agent.run(s)
print(f"INITIAL_TEST_STATUS={s.test_result.status}")
print(f"INITIAL_TEST_FAILED={s.test_result.tests_failed}")
print(f"INITIAL_TEST_EXIT_CODE={s.test_result.exit_code}")

# Step 2: Debugging
d_res = debug_agent.run(s)
print(f"DEBUG_SUCCESS={d_res.success}")
patched_code = next(f.content for f in s.generated_project.files if 'calculator.py' in f.path)
print(f"PATCHED_CONTAINS_BUG={'+ 1' in patched_code}")

# Step 3: Retest
res2 = test_agent.run(s)
print(f"RETEST_STATUS={s.test_result.status}")
print(f"RETEST_PASSED={s.test_result.tests_passed}")
print(f"RETEST_EXIT_CODE={s.test_result.exit_code}")
