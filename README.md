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
```bash
python -m unittest discover tests
```

## 10. How experiment logging works
Experiment logs are written in JSONL format to `logs/runs.jsonl`. Each line is a self-contained JSON object representing a single run, making analysis and aggregation easy.

## 11. Reproducibility
Every run is logged with its configuration, model details, random seed, task information, and timestamp to ensure full reproducibility.

## 12. Current Implementation Status
**Phase 1 foundation only — AI agents are not implemented yet.**
"# DevAgents" 

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
