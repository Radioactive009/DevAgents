# DevAgents — A Multi-Agent System for Automated Software Engineering

## 1. Research Problem
Does a structured multi-agent software-engineering workflow improve the functional correctness and debugging performance of LLM-based software development compared with a single-agent LLM baseline?

## 2. Primary Research Question
Does a structured multi-agent software-engineering workflow improve the functional correctness and debugging performance of LLM-based software development compared with a single-agent LLM baseline?

## 3. Secondary Research Questions
- **RQ2:** Does project-specific RAG and memory improve requirement coverage and debugging success compared with the same multi-agent system without RAG?
- **RQ3:** Does integrating an ML-based failure/defect classification component improve debugging efficiency and bug-fix success?

## 4. Experimental Configurations
- **SINGLE_AGENT_BASELINE:** One LLM, no multi-agent orchestration, no RAG, no ML classifier.
- **MULTI_AGENT:** Supervisor, Architecture Agent, Coding Agent, Testing Agent, Debugging Agent, Verification Agent, no RAG, no ML classifier.
- **MULTI_AGENT_RAG:** Same multi-agent workflow + RAG + Project memory, no ML classifier.
- **FULL_DEVAGENTS:** Multi-agent workflow + RAG + Project memory + ML failure classifier + Tool execution + Verification + Observability.

## 5. Planned Metrics
- task_success_rate
- test_pass_rate
- bug_fix_success_rate
- requirement_coverage
- code_coverage
- average_debug_iterations
- average_execution_time
- average_llm_calls
- average_tool_calls
- human_intervention_rate

## 6. Planned Datasets
(To be determined, see datasets/README.md)

## 7. Project Structure
- `agents/`: AI agent implementations (Phase 2+)
- `orchestration/`: Multi-agent orchestration
- `llm/`: Provider-independent LLM interfaces
- `tools/`: Tool implementations
- `execution/`: Code execution and sandbox
- `rag/`: RAG and memory pipelines
- `ml/`: ML failure classification
- `evaluation/`: Evaluation metrics
- `experiments/`: Experiment runners and loggers
- `datasets/`: Dataset resources
- `logs/`: Experiment run logs
- `configs/`: Configuration files

## 8. Environment Setup
Use Python 3.11+. Install dependencies:
```bash
pip install -r requirements.txt
```

## 9. How to run tests
Run all unit tests using pytest:
```bash
py -m pytest
```
Or with unittest:
```bash
py -m unittest discover tests
```

To run UI tests and build:
```bash
cd ui
npm test
npm run build
```

## 10. How to run the System & Dashboard
Start the FastAPI backend:
```bash
py -m uvicorn api.main:app --reload --port 8000
```
Start the web dashboard:
```bash
cd ui
npm run dev
```

To run a demonstration task programmatically:
```bash
py run_demo.py
```

## 11. How experiment logging works
Experiment logs and telemetry events are written in JSONL format to `logs/runs/<run_id>.jsonl` and `logs/runs.jsonl`. Each record is a self-contained, sanitized JSON object containing agent events, execution times, test passes/failures, diffs, and verification metrics.

## 12. Current Implementation Status
**Complete Multi-Agent Software Engineering System Implemented & Stabilized:**
- **Supervisor Agent**: Requirements decomposition, planning, and task coordination.
- **Architecture Agent**: Component design, dependency mapping, and interface specification.
- **Coding Agent**: Complete source code generation with syntax and security validation.
- **Testing Agent**: Isolated execution in Local Process Sandbox or Docker Sandbox, capturing exit codes and test pass rates.
- **Debugging Agent**: Root-cause analysis, patch generation, and deterministic file updates with bounded retries.
- **Verification Agent**: Evidence-based requirement coverage and test validation.
- **Single Agent Baseline**: Comparison baseline for research experiments.
- **Project Knowledge (RAG) & Memory**: Embedding-based code retrieval and episodic memory.
- **Observability & Web Dashboard**: Full visual tracking of requirements, pipeline progress, file tree, test results, debug diffs, and metrics. 

## 13. LLM Provider Architecture
We use provider abstraction so that experimental configurations can be compared without coupling the agent implementation to a single LLM provider.

The architecture isolates the core application from specific AI vendor APIs:

`	ext
Application
    ↓
LLMProvider
    ↓
Provider Factory
    ↓
Groq / Gemini / Hugging Face
`

- **Provider Abstraction**: All LLM calls go through LLMProvider and return a uniform LLMResponse.
- **Provider Factory**: create_llm_provider(config) dynamically selects the provider.
- **Supported Providers**: Groq, Google Gemini, Hugging Face.
- **Mock Provider**: A deterministic MockLLMProvider allows testing without internet access or real API keys.
- **Configuration & API Key Management**: API keys are read from environment variables (GROQ_API_KEY, GEMINI_API_KEY, HF_API_KEY). Keys are never logged. Model and provider selections are managed via configuration files.
- **Error Handling**: Provider-specific API errors, rate limits, and auth failures are normalized into standard exceptions (LLMError, LLMRateLimitError, etc.).
- **Reproducibility**: The provider, model, latency, and token counts are extracted generically and passed to the experiment logger for valid comparisons.
