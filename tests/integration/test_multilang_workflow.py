import pytest
import os
import json
from orchestration.state import ProjectState
from agents.schema import GeneratedProject, GeneratedFile, DebugPatch, DebugChange, Requirement
from agents.testing import TestingAgent
from agents.debugging import DebuggingAgent
from execution.local_sandbox import LocalProcessSandbox
from llm.base import MockLLMProvider

def test_javascript_node_project_execution_and_debugging():
    """
    Validates Phase 2: Multi-Language Execution Engine for Node.js / JavaScript.
    1. Generates a multi-file JavaScript project (package.json, src/math.js, test/math.test.js).
    2. Runs test suite using node's built-in test runner.
    3. Detects assertion failure in math.js.
    4. Applies patch fixing math.js.
    5. Retests and verifies PASSED state.
    """
    state = ProjectState(
        run_id="test-js-run",
        user_requirement="Build a JavaScript math utility with add and multiply functions and node tests."
    )

    package_json = json.dumps({
        "name": "js-math-util",
        "version": "1.0.0",
        "type": "module",
        "scripts": {
            "test": "node --test test/math.test.js"
        }
    }, indent=2)

    # Buggy math.js: multiply returns a + b instead of a * b
    math_js_buggy = """
export function add(a, b) {
    return a + b;
}

export function multiply(a, b) {
    return a + b; // BUG: should be a * b
}
"""

    math_test_js = """
import test from 'node:test';
import assert from 'node:assert';
import { add, multiply } from '../src/math.js';

test('add adds two numbers', () => {
    assert.strictEqual(add(2, 3), 5);
});

test('multiply multiplies two numbers', () => {
    assert.strictEqual(multiply(2, 3), 6);
});
"""

    project = GeneratedProject(
        project_name="js-math-util",
        files=[
            GeneratedFile(path="package.json", content=package_json, description="", requirement_ids=["REQ-1"]),
            GeneratedFile(path="src/math.js", content=math_js_buggy, description="", requirement_ids=["REQ-1"]),
            GeneratedFile(path="test/math.test.js", content=math_test_js, description="", requirement_ids=["REQ-1"])
        ],
        entrypoint="src/math.js",
        run_command="node src/math.js",
        dependencies=[],
        test_command="node --test test/math.test.js",
        requirement_coverage={"REQ-1": ["src/math.js", "test/math.test.js"]}
    )
    state.generated_project = project

    # 1. Execute tests on buggy implementation
    testing_agent = TestingAgent(provider=MockLLMProvider())
    res1 = testing_agent.run(state)

    # Must fail because multiply(2, 3) returned 5 instead of 6
    assert not res1.success
    assert state.test_result.status in ["FAILED", "NONZERO_EXIT"]

    # 2. Apply patch fixing multiply
    math_js_fixed = """
export function add(a, b) {
    return a + b;
}

export function multiply(a, b) {
    return a * b;
}
"""
    patch = DebugPatch(
        root_cause="The multiply function used + instead of *.",
        failure_category="LOGIC_ERROR",
        explanation="Fixed multiply to compute a * b.",
        changes=[
            DebugChange(
                action="modify",
                path="src/math.js",
                reason="Fix multiplication operator",
                new_content=math_js_fixed,
                requirement_ids=["REQ-1"]
            )
        ]
    )

    debugging_agent = DebuggingAgent(provider=MockLLMProvider())
    debugging_agent._apply_patch(patch, state)

    # 3. Retest updated JavaScript source
    res2 = testing_agent.run(state)
    assert res2.success, f"Retest failed: {state.test_result.stdout}\n{state.test_result.stderr}"
    assert state.test_result.status == "PASSED"
