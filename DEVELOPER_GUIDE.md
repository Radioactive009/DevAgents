# DevAgents — Developer & Contributor Guide

This guide details how to extend, customize, and maintain the DevAgents autonomous software engineering platform.

---

## 1. Repository Structure & Core Modules

| Directory | Purpose | Key Files |
|---|---|---|
| `agents/` | Agent definitions and prompt templates | `base.py`, `models.py`, `schema.py`, `supervisor.py`, `architecture.py`, `coding.py`, `testing.py`, `debugging.py`, `verification.py`, `single_agent_baseline.py` |
| `orchestration/` | Workflow execution pipelines and shared state | `workflow.py`, `state.py` |
| `execution/` | Sandboxed environments for safe code execution | `sandbox.py`, `local_sandbox.py`, `docker_sandbox.py`, `models.py` |
| `llm/` | Model abstraction layer and provider adapters | `base.py`, `factory.py`, `providers/` (`groq_provider.py`, `gemini_provider.py`, `openrouter_provider.py`) |
| `rag/` | Retrieval-Augmented Generation & episodic memory | `pipeline.py`, `retriever.py`, `context.py`, `context_optimizer.py`, `memory.py`, `vector_store.py` |
| `evaluation/` | Empirical metrics and failure classification | `metrics.py`, `failure_classifier.py` |
| `observability/` | Telemetry recording and JSONL event logging | `telemetry.py`, `schema.py` |
| `api/` | FastAPI backend server | `main.py` |
| `ui/` | React, TypeScript & Vite dashboard | `src/App.tsx`, `src/Dashboard.tsx`, `src/RunView.tsx` |
| `experiments/` | Research evaluation runners | `runner.py`, `run_research_evaluation.py` |

---

## 2. Adding a New Agent

To add a new specialized agent (e.g. `SecurityAuditAgent` or `DocumentationAgent`):

1. **Subclass `Agent`**:
   In `agents/my_agent.py`:
   ```python
   from agents.base import Agent
   from agents.models import AgentResult
   from orchestration.state import ProjectState

   class SecurityAuditAgent(Agent):
       def __init__(self, provider):
           super().__init__("SecurityAuditAgent", "SecurityAudit", provider)

       def run(self, state: ProjectState) -> AgentResult:
           # Read generated project
           files = state.generated_project.files
           # Generate audit review
           response = self.provider.generate(f"Audit these files: {files}")
           # Return structured result
           return self._create_result(
               success=True,
               run_id=state.run_id,
               output={"audit": response.text}
           )
   ```

2. **Register in Orchestration Workflow**:
   In `orchestration/workflow.py`, import `SecurityAuditAgent` and invoke it within `run_phase11_workflow`:
   ```python
   from agents.my_agent import SecurityAuditAgent
   audit_agent = SecurityAuditAgent(provider=audit_provider)
   audit_res = audit_agent.run(state)
   telemetry.record_agent(AgentEvent(run_id=run_id, agent_name="SecurityAuditAgent", ...))
   ```

---

## 3. Adding a New Language Executor

To support a new language (e.g. Go, Rust, or Java):

1. **In `execution/local_sandbox.py`**:
   Add command path resolution and test invocation rules in `run_command`:
   ```python
   if cmd[0] == "go":
       cmd[0] = shutil.which("go")
   elif cmd[0] == "cargo":
       cmd[0] = shutil.which("cargo")
   ```

2. **In `agents/testing.py`**:
   - Detect project manifests (e.g. `go.mod`, `Cargo.toml`).
   - Add test runner detection:
     ```python
     has_cargo = "Cargo.toml" in file_paths
     if has_cargo:
         test_res = sandbox.run_tests(["cargo", "test"])
     ```
   - Add test summary parser for the language's stdout/stderr.

3. **In `agents/debugging.py`**:
   - Add AST or compiler syntax checks for the new file extension if applicable.

---

## 4. Modifying Workflow Routing & Human Checkpoints

Workflows are composed as pure functional transitions over `ProjectState`.

To add conditional routing or approval:
1. In `orchestration/state.py`, add necessary metadata fields.
2. In `orchestration/workflow.py`, check `state.metadata`:
   ```python
   if state.metadata.get("require_review"):
       approval_event.wait(timeout=600)
       if state.metadata.get("approval_status") == "REJECTED":
           return state
   ```
3. Expose API trigger in `api/main.py` and UI button in `ui/src/RunView.tsx`.

---

## 5. Adding a Model Provider

DevAgents abstracts all LLM calls through `LLMProvider`.

To add a provider (e.g. Anthropic, Ollama, Azure OpenAI):
1. Create `llm/providers/my_provider.py`:
   ```python
   from llm.base import LLMProvider, LLMResponse

   class MyProvider(LLMProvider):
       def __init__(self, api_key: str, model: str = "default"):
           super().__init__("my_provider", model)
           self.api_key = api_key

       def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> LLMResponse:
           # Call vendor API
           return LLMResponse(
               text="output text",
               provider=self.name,
               model=self.model,
               total_tokens=100,
               latency_seconds=1.2
           )
   ```
2. Register the provider in `llm/factory.py`:
   ```python
   elif provider_name == "my_provider":
       return MyProvider(api_key=os.environ.get("MY_PROVIDER_API_KEY"), model=model)
   ```

---

## 6. Extending RAG Retrieval & Project Memory

1. **Custom Embeddings**:
   `rag/embeddings.py` provides `Embedder` interface. Override `embed(text)` with dense embeddings (e.g. sentence-transformers or text-embedding-3-small).
2. **Episodic Memory**:
   `rag/memory.py` maintains `ProjectMemory`.
   Add new memory types (e.g. `SECURITY_LESSON`, `OPTIMIZATION_TIP`) by writing `MemoryRecord(memory_type="...", content="...")`.
3. **Context Optimization**:
   `rag/context_optimizer.py` contains `ContextOptimizer`. You can customize traceback regexes or adjust context character limits.

---

## 7. Adding Benchmark Tasks

To add benchmark evaluation tasks:
1. Open `experiments/run_research_evaluation.py` or `configs/task_manifest.json`.
2. Append a task definition:
   ```json
   {
       "task_id": "TASK-03-ALGO",
       "name": "Binary Search Tree Module",
       "description": "Implement a balanced BST in Python with insert, delete, search, and pytest suite.",
       "requirements": [
           "Implement Node and BST classes",
           "Support insertion, deletion, and search",
           "Include full pytest tests"
       ]
   }
   ```
3. Run `py experiments/run_research_evaluation.py` to regenerate empirical comparisons across the 4 configurations.

---

## 8. Interpreting Telemetry & Event Logs

Each run generates a structured JSONL file at `logs/runs/<run_id>.jsonl`.
Sample records:
- `AgentEvent`: `{ "event_type": "agent", "agent_name": "CodingAgent", "duration_ms": 3400, "success": true }`
- `TestEvent`: `{ "event_type": "test", "exit_code": 0, "test_pass_rate": 1.0, "duration_ms": 1200 }`
- `DebugEvent`: `{ "event_type": "debug", "iteration": 1, "success": true, "duration_ms": 850 }`
- `VerificationEvent`: `{ "event_type": "verification", "status": "VERIFIED", "requirement_coverage": 1.0 }`

All logs have secrets automatically scrubbed before serialization.
