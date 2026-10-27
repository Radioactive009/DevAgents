"""
Interactive Terminal Demo for DevAgents Multi-Agent Software Engineering System.
Runs the complete autonomous development lifecycle and prints real-time agent output.
"""
import sys
import time
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from orchestration.workflow import run_phase11_workflow
from llm.base import MockLLMProvider

def main():
    print("=" * 60)
    print("DEVAGENTS -- AUTONOMOUS MULTI-AGENT DEVELOPMENT DEMO")
    print("=" * 60)
    
    requirement = (
        "Build a Python calculator module with add, subtract, multiply, "
        "divide, division-by-zero handling, and pytest tests."
    )
    print(f"\nUser Requirement:\n   \"{requirement}\"\n")
    print("Coordinating agents: Supervisor -> Architecture -> Coding -> Testing -> Debugging -> Verification...\n")
    
    provider = MockLLMProvider()
    run_id = f"demo-run-{int(time.time())}"
    
    state = run_phase11_workflow(
        run_id=run_id,
        user_requirement=requirement,
        supervisor_provider=provider,
        architecture_provider=provider,
        coding_provider=provider,
        testing_provider=provider,
        debugging_provider=provider,
        verification_provider=provider,
        max_debug_iterations=3
    )
    
    print("-" * 60)
    print("1. SUPERVISOR & ARCHITECTURE STAGE")
    print("-" * 60)
    if state.project_plan:
        print(f"Summary: {state.project_plan.project_summary or 'Requirements planned'}")
        print("Identified Requirements:")
        for r in state.project_plan.requirements:
            print(f"  * [{r.id}] {r.description}")
            
    if state.architecture:
        print("\nArchitecture Components:")
        for c in state.architecture.components:
            print(f"  * {c.name}: {c.responsibility}")

    print("\n" + "-" * 60)
    print("2. CODING STAGE (Generated Files)")
    print("-" * 60)
    if state.generated_project:
        for f in state.generated_project.files:
            print(f"\nFile: {f.path}")
            print("-" * 40)
            print(f.content.strip())
            print("-" * 40)

    print("\n" + "-" * 60)
    print("3. TESTING & DEBUGGING STAGE")
    print("-" * 60)
    print(f"Debugging iterations performed: {len(state.debugging_history)}")
    for d in state.debugging_history:
        print(f"  * Iteration {d['iteration']}: Root Cause: {d['root_cause']}")
        print(f"    Failure Category: {d['failure_category']}")
        print(f"    Files Modified: {', '.join(d['files_changed'])}")

    print(f"\nFinal Test Status: {getattr(state.test_result, 'status', 'UNKNOWN')}")
    if state.test_result:
        print(f"Tests Passed: {state.test_result.tests_passed}/{state.test_result.tests_total}")
        print(f"Exit Code: {state.test_result.exit_code}")

    print("\n" + "-" * 60)
    print("4. VERIFICATION STAGE")
    print("-" * 60)
    if state.verification_result:
        print(f"Verification Status: {state.verification_result.status}")
        print(f"Requirement Coverage: {state.verification_result.requirement_coverage * 100:.1f}%")
        print(f"Summary: {state.verification_result.summary}")

    print("\n" + "=" * 60)
    print("DEMO RUN COMPLETE")
    print(f"Log written to: logs/runs/{run_id}.jsonl")
    print("=" * 60)

if __name__ == "__main__":
    main()
