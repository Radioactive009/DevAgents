# DevAgents Observability & Experiment Telemetry

This directory contains the telemetry and observability components for the DevAgents system. The goal of this module is to provide structured, lightweight, JSON-serializable event logs for research analysis and experiment reproducibility.

## Telemetry Schema

The observability system logs telemetry in the `logs/runs/<run_id>.jsonl` format. Every event is written as a single line JSON structure (JSONL). The core events include:
- `AgentEvent`: Logs individual agent lifecycle metrics.
- `LLMEvent`: Tracks model latency, provider usage, and token consumption (if available).
- `ToolEvent`: Bounded summaries of tool invocations and execution time.
- `RetrievalEvent`: Tracks RAG and Memory queries.
- `TestEvent`: Summaries of isolated test execution behavior.
- `DebugEvent`: Tracks debug iterations and failure taxonomies.
- `VerificationEvent`: Logs requirement coverage and ultimate output status.
- `ErrorEvent`: Records structured workflow errors natively without swallowing them.

## Captured Metrics

The telemetry architecture guarantees the extraction of:
- Task success rates
- Test pass rates
- Requirement coverage
- Debug iteration frequencies
- Execution timings & Latencies
- LLM calls & strictly available token usage
- System configurations (RAG configurations, Sandbox restrictions)

## Secret Sanitization

Before writing to the disk, the telemetry logger utilizes `sanitize_dict` which automatically filters keys like `GROQ_API_KEY`, `password`, `secret`, `credential`, and others matching deterministic blocklists.

## Using the Context & Telemetry

To trace a run, access the singleton instance:

```python
from observability.telemetry import Telemetry

telemetry = Telemetry.get_instance()
telemetry.start_run(run_id="run-1", task_id="task-1", configuration={"use_rag": True})
# ... record events ...
telemetry.end_run(run_id="run-1", success=True, final_status="VERIFIED")
```

The logger inherently respects maximum file sizes and fails gracefully rather than crashing standard workflow pipelines.
